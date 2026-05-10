def build_headers(api_key: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }
    if extra:
        headers.update(extra)
    return headers
