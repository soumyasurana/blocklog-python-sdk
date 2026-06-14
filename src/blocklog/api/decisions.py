"""
blocklog.api.decisions
~~~~~~~~~~~~~~~~~~~~~~
Layer 2 client for AI Decisions.

Available via ``client.decisions.*`` or via the ``decision()`` context
manager internally.

Backend endpoints
-----------------
- POST   /api/v1/decisions
- GET    /api/v1/decisions
- GET    /api/v1/decisions/{id}
- GET    /api/v1/decisions/{id}/verify
- GET    /api/v1/decisions/{id}/timeline
- GET    /api/v1/decisions/{id}/evidence
- GET    /api/v1/decisions/{id}/replay
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blocklog.client import BlocklogClient


class DecisionsClient:
    """Manage AI Decision records.

    Accessed as ``client.decisions``.

    Examples
    --------
    >>> decision = client.decisions.create(
    ...     decision_type="BUY",
    ...     asset="TSLA",
    ...     confidence=0.91,
    ... )
    >>> client.decisions.timeline(decision["id"])
    """

    def __init__(self, client: "BlocklogClient") -> None:
        self._client = client

    def create(
        self,
        decision_type: str,
        *,
        asset: str | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
        session_id: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new AI Decision record.

        Parameters
        ----------
        decision_type:
            Short identifier for the decision category (``"BUY"``,
            ``"SELL"``, ``"APPROVE"``…).
        asset:
            Asset or resource this decision concerns.
        confidence:
            Model confidence score 0–1.
        metadata:
            Arbitrary extra data to store with the decision.
        trace_id:
            Associate with an existing trace.
        session_id:
            Associate with an existing session.
        agent_id:
            Identifier of the agent making the decision.

        Returns
        -------
        dict
            The created decision record from the backend.
        """
        payload: dict[str, Any] = {"decision_type": decision_type}
        if asset is not None:
            payload["asset"] = asset
        if confidence is not None:
            payload["confidence"] = confidence
        if metadata is not None:
            payload["metadata"] = metadata
        if trace_id is not None:
            payload["trace_id"] = trace_id
        if session_id is not None:
            payload["session_id"] = session_id
        if agent_id is not None:
            payload["agent_id"] = agent_id

        return self._client.retry.run(
            lambda: self._client.transport.request("POST", "/decisions", json=payload)
        )

    def list(self) -> list[dict[str, Any]]:
        """List all decisions for the authenticated company.

        Returns
        -------
        list[dict]
            List of decision records.
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("GET", "/decisions")
        )

    def get(self, decision_id: str) -> dict[str, Any]:
        """Fetch a single decision by ID.

        Parameters
        ----------
        decision_id:
            UUID of the decision.
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("GET", f"/decisions/{decision_id}")
        )

    def verify(self, decision_id: str) -> dict[str, Any]:
        """Verify a decision against the Ed25519 signature.

        Parameters
        ----------
        decision_id:
            UUID of the decision to verify.

        Returns
        -------
        dict
            Verification result with Merkle proof and signature
            details.
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("GET", f"/decisions/{decision_id}/verify")
        )

    def timeline(self, decision_id: str) -> list[dict[str, Any]]:
        """Return the chronological event timeline for a decision.

        Parameters
        ----------
        decision_id:
            UUID of the decision.
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("GET", f"/decisions/{decision_id}/timeline")
        )

    def evidence(self, decision_id: str) -> dict[str, Any]:
        """Return the evidence bundle for a decision.

        Parameters
        ----------
        decision_id:
            UUID of the decision.
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("GET", f"/decisions/{decision_id}/evidence")
        )

    def replay(self, decision_id: str) -> dict[str, Any]:
        """Return the replay data attached to a specific decision.

        For a full forensic replay session, use ``client.replay.create()``.

        Parameters
        ----------
        decision_id:
            UUID of the decision.
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("GET", f"/decisions/{decision_id}/replay")
        )
