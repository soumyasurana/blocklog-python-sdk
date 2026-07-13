import asyncio

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - exercised in local fallback mode
    httpx = None
    import requests
else:
    requests = None

from blocklog.exceptions import TransportError, map_http_error
from .auth import build_headers


class AsyncTransport:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        access_token: str = "",
        timeout: float,
        debug: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.access_token = access_token
        self.timeout = timeout
        self.debug = debug
        self.client = httpx.AsyncClient(timeout=timeout) if httpx is not None else None
        self.requests_session = requests.Session() if requests is not None else None

    def set_access_token(self, token: str) -> None:
        self.access_token = token

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        headers: dict[str, str] | None = None,
        skip_auth: bool = False,
        token_override: str | None = None,
    ):
        request_headers = build_headers(
            api_key=self.api_key,
            access_token=token_override or self.access_token,
            extra=headers,
            skip_auth=skip_auth,
        )
        if self.client is not None:
            response = await self.client.request(
                method,
                f"{self.base_url}{path}",
                json=json,
                params=params,
                headers=request_headers,
            )
        else:
            response = await asyncio.to_thread(
                self.requests_session.request,
                method,
                f"{self.base_url}{path}",
                json=json,
                params=params,
                headers=request_headers,
                timeout=self.timeout,
            )
        status_code = getattr(response, "status_code", 0)
        ok = getattr(response, "is_success", None)
        if ok is None:
            ok = getattr(response, "ok", False)
        if not ok:
            message = response.text or f"HTTP Error {status_code}"
            raise map_http_error(status_code, message)
        if status_code == 204:
            return None
        try:
            return response.json()
        except Exception as exc:  # noqa: BLE001
            raise TransportError("Response was not valid JSON") from exc
