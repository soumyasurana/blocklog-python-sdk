"""
blocklog.verify
~~~~~~~~~~~~~~~
Module-level namespace for cryptographic verification.

Usage (Layer 1)::

    import blocklog

    result = blocklog.verify.log("log-uuid-here")
    result = blocklog.verify.batch("batch-uuid-here")
    result = blocklog.verify.decision("dec-uuid-here")

    print(result["status"])          # "verified"
    print(result["signature"])
"""
from __future__ import annotations

from typing import Any


def log(log_id: str) -> dict[str, Any]:
    """Verify a single log entry against its Merkle proof.

    Parameters
    ----------
    log_id:
        UUID of the log entry to verify.

    Returns
    -------
    dict
        Keys: ``status``, ``merkle_proof``, ``batch_proof``,
        ``details``.
    """
    from blocklog._global import get_client
    return get_client().verify.log(log_id)


def batch(batch_id: str) -> dict[str, Any]:
    """Verify an entire batch against its Ed25519 signature.

    Parameters
    ----------
    batch_id:
        ID of the batch to verify.

    Returns
    -------
    dict
        Keys: ``status``, ``signature``, ``signed_at``,
        ``details``.
    """
    from blocklog._global import get_client
    return get_client().verify.batch(batch_id)


def decision(decision_id: str) -> dict[str, Any]:
    """Verify all evidence attached to a specific decision.

    Parameters
    ----------
    decision_id:
        UUID of the decision to verify.

    Returns
    -------
    dict
        Verification summary including Merkle and signature evidence.
    """
    from blocklog._global import get_client
    return get_client().verify.decision(decision_id)
