from hashlib import sha256

from .canonical import canonical_json


def pseudo_sign(payload: dict, private_key: str | None = None) -> str:
    seed = private_key or "blocklog"
    return sha256(seed.encode("utf-8") + canonical_json(payload)).hexdigest()
