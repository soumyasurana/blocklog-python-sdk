"""
blocklog.managers.decision
~~~~~~~~~~~~~~~~~~~~~~~~~~
The ``decision()`` context manager — the highest-priority surface of the SDK.

Usage (Layer 1)::

    import blocklog

    blocklog.init(api_key="blk_...")

    with blocklog.decision(type="BUY", asset="TSLA", confidence=0.87) as d:
        price = fetch_price("TSLA")
        d.record_input(price=price, signal="momentum_crossover")

        order = place_order("TSLA", qty=100)
        d.record_output(order_id=order.id, filled_at=order.price)

        if order.value > 500_000:
            d.request_approval(reason="Trade exceeds threshold")

    # After the block:
    print(d.id)          # UUID of the recorded decision
    print(d.verified)    # True if cryptographically signed
"""
from __future__ import annotations

import logging
import traceback as _traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

from blocklog.exceptions import BlocklogCommitError

logger = logging.getLogger("blocklog")


class DecisionContext:
    """Live handle to a decision being recorded.

    Obtained from the ``decision()`` context manager.  Do not instantiate
    directly.

    Attributes
    ----------
    id : str | None
        The backend-assigned UUID for this decision.  Available after the
        context body starts executing (set during ``__enter__``).
    decision_type : str
        The decision type you passed in (e.g. ``"BUY"``, ``"TRADE"``,
        ``"APPROVE"``).
    status : str
        ``"open"`` while inside the ``with`` block, ``"complete"`` on
        clean exit, ``"error"`` on exception.
    """

    def __init__(
        self,
        *,
        decision_type: str,
        asset: str | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
        agent_id: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        self.decision_type = decision_type
        self.asset = asset
        self.confidence = confidence
        self.metadata: dict[str, Any] = metadata or {}
        self.agent_id = agent_id
        self._trace_id = trace_id

        self.id: str | None = None
        self.status: str = "open"
        self._inputs: list[dict] = []
        self._outputs: list[dict] = []
        self._tags: list[str] = []
        self._started_at: datetime = datetime.now(timezone.utc)
        self._approval_requested: bool = False

        self._event_buffer: list[tuple[str, dict]] = []
        self._send_event_failures: int = 0
        self._send_event_last_error: Exception | None = None
        self._issues: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public methods available inside the ``with`` block
    # ------------------------------------------------------------------

    def record_input(self, **kwargs: Any) -> "DecisionContext":
        """Record structured inputs that fed into this decision.

        Call this before the AI model / logic runs.

        Parameters
        ----------
        **kwargs
            Arbitrary key-value pairs describing the inputs.  Will be
            stored verbatim and appear in replays and forensic timelines.

        Examples
        --------
        >>> d.record_input(price=412.50, volume=1_200_000, signal="rsi_oversold")
        """
        self._inputs.append({"recorded_at": _now_iso(), **kwargs})
        self._send_event("DECISION_INPUT", kwargs)
        return self

    def record_output(self, **kwargs: Any) -> "DecisionContext":
        """Record structured outputs / results of this decision.

        Call this after the AI model / logic produces a result.

        Parameters
        ----------
        **kwargs
            Arbitrary key-value pairs describing the outputs.

        Examples
        --------
        >>> d.record_output(order_id="ord_88", filled_at=413.10, qty=100)
        """
        self._outputs.append({"recorded_at": _now_iso(), **kwargs})
        self._send_event("DECISION_OUTPUT", kwargs)
        return self

    def tag(self, *tags: str) -> "DecisionContext":
        """Attach one or more string labels to this decision.

        Tags appear in the dashboard and can be used to filter/search.

        Examples
        --------
        >>> d.tag("high-value", "requires-review", "momentum-strategy")
        """
        self._tags.extend(tags)
        return self

    def request_approval(
        self,
        reason: str,
        reviewer: str | None = None,
    ) -> "DecisionContext":
        """Request human approval for this decision (HITL).

        This is a **non-blocking** call.  It records the approval request
        against the decision and notifies the reviewer (via backend
        webhooks / email, as configured in your Blocklog workspace).
        Execution continues; it is the caller's responsibility to gate
        further actions on approval status.

        Parameters
        ----------
        reason:
            Human-readable explanation for why approval is needed.
        reviewer:
            Optional email / identifier of the intended reviewer.

        Examples
        --------
        >>> if order_value > 500_000:
        ...     d.request_approval(
        ...         reason="Trade exceeds $500k threshold",
        ...         reviewer="risk-team@fund.com",
        ...     )
        """
        self._approval_requested = True
        try:
            from blocklog._global import get_client
            client = get_client()
            client.approval.request(
                decision_id=self.id,
                reason=reason,
                reviewer=reviewer,
            )
        except Exception as exc:  # noqa: BLE001
            status_code = None
            if hasattr(exc, "response") and exc.response is not None:
                status_code = getattr(exc.response, "status_code", None)
            if status_code in (401, 403):
                raise
            logger.warning("blocklog: approval.request() failed: %s", exc)
        return self

    def verify(self) -> dict[str, Any]:
        """Immediately verify this decision against the Ed25519 signature.

        Returns
        -------
        dict
            Verification result from ``GET /decisions/{id}/verify``.
        """
        if not self.id:
            raise RuntimeError("Decision has not been committed yet.")
        from blocklog._global import get_client
        return get_client().decisions.verify(self.id)

    @property
    def issues(self) -> list[dict[str, Any]]:
        """Get the list of issues detected during the context lifecycle.

        Returns
        -------
        list[dict]
            A list of dictionary objects describing each detected issue.
            Each dictionary has keys: 'level' (str), 'code' (str), and 'message' (str).
        """
        return self._issues

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_event(self, event_type: str, payload: dict) -> None:
        """Fire an event log to the ingest endpoint (best-effort)."""
        if self.id is None:
            self._event_buffer.append((event_type, payload))
            return

        trace_id = None
        try:
            from blocklog._global import get_client
            from blocklog.context.vars import get_context

            ctx = get_context()
            client = get_client()
            trace_id = str(ctx.trace_id) if ctx else self._trace_id
            client.event(
                event_type,
                payload={
                    "decision_id": self.id,
                    "decision_type": self.decision_type,
                    "asset": self.asset,
                    **payload,
                },
                trace_id=trace_id,
                session_id=str(ctx.session_id) if ctx else None,
                agent_id=self.agent_id or (ctx.agent_id if ctx else None),
                agent_type="agent",
            )
            logger.debug(
                "Event send: type=%s, decision_id=%s, trace_id=%s, success=True",
                event_type, self.id, trace_id
            )
        except Exception as exc:  # noqa: BLE001
            self._send_event_failures += 1
            self._send_event_last_error = exc
            logger.debug(
                "Event send: type=%s, decision_id=%s, trace_id=%s, success=False, error=%s",
                event_type, self.id, trace_id, exc
            )

    def _flush_events(self) -> None:
        """Flush buffered events after successful decision commit."""
        buffered = list(self._event_buffer)
        self._event_buffer.clear()
        for event_type, payload in buffered:
            self._send_event(event_type, payload)

    def _commit(self) -> None:
        """Create the decision record in the backend.

        Raises
        ------
        BlocklogCommitError
            If committing the decision to the backend fails.
        """
        logger.debug("Decision commit attempted: type=%s, asset=%s", self.decision_type, self.asset)
        try:
            from blocklog._global import get_client
            from blocklog.context.vars import get_context

            ctx = get_context()
            client = get_client()
            result = client.decisions.create(
                decision_type=self.decision_type,
                asset=self.asset,
                confidence=self.confidence,
                metadata={
                    **self.metadata,
                    "tags": self._tags,
                    "started_at": self._started_at.isoformat(),
                },
                trace_id=str(ctx.trace_id) if ctx else self._trace_id,
                session_id=str(ctx.session_id) if ctx else None,
                agent_id=self.agent_id or (ctx.agent_id if ctx else None),
            )
            self.id = str(result.get("id", result.get("decision_id", "")))
            logger.debug("Decision commit succeeded: id=%s", self.id)
            self._flush_events()
        except Exception as exc:  # noqa: BLE001
            self._event_buffer.clear()
            logger.warning("blocklog: Decision commit failed. Discarding buffered events.")
            logger.debug("Decision commit failed: %s", exc)
            raise BlocklogCommitError(f"Decision commit failed: {exc}") from exc

    def _detect_issues(self) -> None:
        """Detect potential issues with the decision context state and record them."""
        self._issues = []
        if self.id is None:
            self._issues.append({
                "level": "error",
                "code": "COMMIT_FAILED",
                "message": "Decision commit failed; no decision ID was generated."
            })
        if len(self._inputs) == 0:
            self._issues.append({
                "level": "warning",
                "code": "NO_INPUTS",
                "message": "No inputs were recorded for this decision."
            })
        if len(self._outputs) == 0:
            self._issues.append({
                "level": "warning",
                "code": "NO_OUTPUTS",
                "message": "No outputs were recorded for this decision."
            })
        if self.confidence is None:
            self._issues.append({
                "level": "info",
                "code": "CONFIDENCE_MISSING",
                "message": "Confidence score is missing."
            })
        if self._send_event_failures > 0:
            self._issues.append({
                "level": "error",
                "code": "EVENTS_DROPPED",
                "message": f"{self._send_event_failures} events were dropped. Last error: {self._send_event_last_error}"
            })

    def _complete(self) -> None:
        self.status = "complete"
        self._send_event("DECISION_COMPLETE", {
            "inputs": self._inputs,
            "outputs": self._outputs,
            "tags": self._tags,
            "approval_requested": self._approval_requested,
            "completed_at": _now_iso(),
        })
        logger.debug("Decision context exit: status=%s, issue_count=%d", self.status, len(self._issues))

    def _error(self, exc: BaseException) -> None:
        self.status = "error"
        self._send_event("DECISION_ERROR", {
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": _traceback.format_exc(),
            "tags": self._tags,
            "failed_at": _now_iso(),
        })
        logger.debug("Decision context exit: status=%s, issue_count=%d", self.status, len(self._issues))


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

@contextmanager
def decision(
    *,
    type: str,  # noqa: A002
    asset: str | None = None,
    confidence: float | None = None,
    metadata: dict[str, Any] | None = None,
    agent_id: str | None = None,
    trace_id: str | None = None,
) -> Generator[DecisionContext, None, None]:
    """Context manager for recording an AI decision.

    Creates a decision record in Blocklog, lets you annotate it with
    inputs/outputs, then automatically closes it on exit — cleanly or
    with an error event if an exception is raised.

    Parameters
    ----------
    type:
        Decision type identifier.  Use a short, uppercase string that is
        meaningful in your domain (``"BUY"``, ``"SELL"``, ``"APPROVE"``,
        ``"REJECT"``, ``"ROUTE"``, ``"SUMMARISE"``…).
    asset:
        Optional asset or resource this decision is about
        (``"TSLA"``, ``"customer_123"``, ``"invoice_456"``…).
    confidence:
        Optional model confidence score between 0 and 1.
    metadata:
        Arbitrary extra fields stored with the decision record.
    agent_id:
        Override the agent identity for this decision.  Normally
        inherited from the surrounding ``@agent`` context.
    trace_id:
        Override the trace ID.  Normally inherited automatically.

    Yields
    ------
    DecisionContext
        A live handle you can use to call ``record_input()``,
        ```record_output()``, ``tag()``, ``request_approval()``, etc.

    Examples
    --------
    >>> with blocklog.decision(type="BUY", asset="TSLA", confidence=0.87) as d:
    ...     d.record_input(price=412.50, signal="momentum")
    ...     order = place_order("TSLA", qty=100)
    ...     d.record_output(order_id=order.id)
    """
    ctx = DecisionContext(
        decision_type=type,
        asset=asset,
        confidence=confidence,
        metadata=metadata,
        agent_id=agent_id,
        trace_id=trace_id,
    )
    ctx._commit()
    try:
        yield ctx
        ctx._detect_issues()
        ctx._complete()
    except BaseException as exc:
        ctx._detect_issues()
        ctx._error(exc)
        raise


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
