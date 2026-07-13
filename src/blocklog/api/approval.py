"""
blocklog.api.approval
~~~~~~~~~~~~~~~~~~~~~
Layer 2 client for Human-in-the-Loop (HITL) approval workflows.

Available via ``client.approval.*``.

Backend endpoints
-----------------
- POST  /api/v1/hitl/approve
- POST  /api/v1/hitl/reject
- POST  /api/v1/hitl/escalate
- GET   /api/v1/hitl/overrides
- GET   /api/v1/hitl/overrides/{id}
- GET   /api/v1/hitl/audit-trail
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blocklog.client import BlocklogClient


class ApprovalClient:
    """Manage human approval workflows (HITL).

    Accessed as ``client.approval``.

    Examples
    --------
    >>> client.approval.request(
    ...     decision_id="dec_abc123",
    ...     reason="Trade exceeds $500k threshold",
    ...     reviewer="risk-team@fund.com",
    ... )
    """

    def __init__(self, client: "BlocklogClient") -> None:
        self._client = client

    def request(
        self,
        decision_id: str | None = None,
        *,
        reason: str,
        reviewer: str | None = None,
        log_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Request human approval for a decision or log entry.

        This is a **non-blocking** operation.  It registers the approval
        request in Blocklog and triggers any configured webhooks or
        notification rules.  Execution continues immediately.

        Parameters
        ----------
        decision_id:
            UUID of the decision requiring approval.
        reason:
            Human-readable explanation of why approval is needed.
        reviewer:
            Email or identifier of the intended reviewer.
        log_id:
            UUID of the specific log entry, if approval is on a log
            rather than a top-level decision.
        metadata:
            Extra context to attach to the approval request.

        Returns
        -------
        dict
            Backend response confirming the request was registered.
        """
        payload: dict[str, Any] = {"reason": reason}
        if decision_id is not None:
            payload["decision_id"] = decision_id
        if reviewer is not None:
            payload["reviewer"] = reviewer
        if log_id is not None:
            payload["log_id"] = log_id
        if metadata is not None:
            payload["metadata"] = metadata

        return self._client.retry.run(
            lambda: self._client.transport.request(
                "POST",
                "/hitl/request",
                json=payload,
            )
        )

    def reject(
        self,
        reviewer: str,
        *,
        reason: str,
        decision_id: str | None = None,
    ) -> dict[str, Any]:
        """Record that a reviewer has rejected a decision.

        Parameters
        ----------
        reviewer:
            Identity of the person rejecting.
        reason:
            Explanation for the rejection.
        decision_id:
            Optional reference to the decision being rejected.
        """
        payload: dict[str, Any] = {
            "reviewer": reviewer,
            "rejection_reason": reason,
        }
        if decision_id is not None:
            payload["decision_id"] = decision_id

        return self._client.retry.run(
            lambda: self._client.transport.request("POST", "/hitl/reject", json=payload)
        )

    def escalate(
        self,
        from_reviewer: str,
        to_reviewer: str,
        *,
        reason: str,
    ) -> dict[str, Any]:
        """Escalate an approval request to a different reviewer.

        Parameters
        ----------
        from_reviewer:
            Current reviewer escalating the decision.
        to_reviewer:
            Target reviewer who should take over.
        reason:
            Explanation for the escalation.
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("POST", "/hitl/escalate", json={
                "current_reviewer": from_reviewer,
                "escalation_target": to_reviewer,
                "escalation_reason": reason,
            })
        )

    def list_overrides(self) -> list[dict[str, Any]]:
        """Return all HITL override records for the company.

        Returns
        -------
        list[dict]
            List of override records (approvals that changed an outcome).
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("GET", "/hitl/overrides")
        )

    def get_override(self, override_id: int) -> dict[str, Any]:
        """Fetch a specific HITL override record.

        Parameters
        ----------
        override_id:
            Integer ID of the override.
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("GET", f"/hitl/overrides/{override_id}")
        )

    def audit_trail(self) -> list[dict[str, Any]]:
        """Return the full HITL audit trail for the company.

        Includes all approve / reject / escalate events in reverse
        chronological order.

        Returns
        -------
        list[dict]
            Ordered list of HITL audit log entries.
        """
        return self._client.retry.run(
            lambda: self._client.transport.request("GET", "/hitl/audit-trail")
        )
