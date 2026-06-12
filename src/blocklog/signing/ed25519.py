import hmac
from hashlib import sha256

from .canonical import canonical_json


def hash_sign(payload: dict, private_key: str | None = None) -> str:
    """Generate an HMAC-SHA256 signature for a payload.
    
    Uses HMAC-SHA256 for tamper-evidence — the signing_key is required
    to reproduce the signature. Not Ed25519; for asymmetric signing use
    the cryptography library.
    """
    key = (private_key or "blocklog").encode("utf-8")
    return hmac.new(key, canonical_json(payload), sha256).hexdigest()


pseudo_sign = hash_sign  # backward compat
