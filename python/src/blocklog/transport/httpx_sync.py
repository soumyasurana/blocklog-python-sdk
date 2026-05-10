import httpx

from .auth import build_headers


class SyncTransport:
    def __init__(self, *, base_url: str, api_key: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def request(self, method: str, path: str, *, json: dict | None = None, headers: dict[str, str] | None = None):
        response = self.client.request(
            method,
            f"{self.base_url}{path}",
            json=json,
            headers=build_headers(self.api_key, headers),
        )
        response.raise_for_status()
        return response.json()
