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
        agent: str | None = None,
        agent_id: str | None = None,
        model: str | None = None,
        prompt: str | None = None,
        inputs: dict | list | None = None,
        outputs: dict | list | None = None,
        tools: list | dict | None = None,
        policies: list | dict | None = None,
        evidence_links: list | dict | None = None,
        status: str | None = None,
        asset: str | None = None,
        confidence: float | None = None,
        confidence_score: float | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
        session_id: str | None = None,
        workflow_id: str | None = None,
        approval_references: list | dict | None = None,
        signatures: list | dict | None = None,
        ) -> dict[str, Any]:
        """Create a new AI Decision record."""

        payload: dict[str, Any] = {
            "decision_type": decision_type,
        }

        optional_fields = {
            "agent": agent,
            "agent_id": agent_id,
            "model": model,
            "prompt": prompt,
            "inputs": inputs,
            "outputs": outputs,
            "tools": tools,
            "policies": policies,
            "evidence_links": evidence_links,
            "status": status,
            "asset": asset,
            "confidence": confidence,
            "confidence_score": confidence_score,
            "metadata": metadata,
            "trace_id": trace_id,
            "session_id": session_id,
            "workflow_id": workflow_id,
            "approval_references": approval_references,
            "signatures": signatures,
        }

        payload.update(
            {
                key: value
                for key, value in optional_fields.items()
                if value is not None
            }
        )

        return self._client.retry.run(
            lambda: self._client.transport.request(
                "POST",
                "/decisions",
                json=payload,
            )
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
