"""
blocklog._init_fn
~~~~~~~~~~~~~~~~~
Implements the top-level ``blocklog.init()`` call.

Usage::

    import blocklog
    blocklog.init(api_key="blk_...")

    # or via environment variable BLOCKLOG_API_KEY
    blocklog.init()
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blocklog.client import BlocklogClient


def init(
    api_key: str | None = None,
    *,
    base_url: str | None = None,
    signing_key: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
    debug: bool = False,
) -> "BlocklogClient":
    """Initialise the Blocklog SDK.

    Call once at application startup — typically right after your other
    infrastructure initialisation (logging, config loading, etc.).

    Parameters
    ----------
    api_key:
        Your Blocklog API key.  Falls back to the ``BLOCKLOG_API_KEY``
        environment variable when omitted.
    base_url:
        Override the default API base URL.  Useful for self-hosted
        deployments.  Falls back to ``BLOCKLOG_BASE_URL``.
    signing_key:
        Ed25519 private key used to sign log payloads for tamper-evidence.
        Falls back to ``BLOCKLOG_SDK_SIGNING_KEY``.
    timeout:
        Per-request timeout in seconds (default: 10).
    max_retries:
        Number of automatic retries on transient failures (default: 3).
    debug:
        When ``True``, logs every outbound request to stderr.

    Returns
    -------
    BlocklogClient
        The configured global client instance.  You normally don't need
        to store this — all module-level helpers (``decision``,
        ``approval``, ``incident``, ``replay``, ``verify``,
        ``compliance``) pick it up automatically.

    Examples
    --------
    >>> import blocklog
    >>> blocklog.init(api_key="blk_live_...")

    >>> # Environment-variable driven (CI / production)
    >>> blocklog.init()
    """
    from blocklog._global import set_client
    from blocklog.client import BlocklogClient
    from blocklog.config import BlocklogConfig

    overrides: dict = {}
    if api_key is not None:
        overrides["api_key"] = api_key
    if base_url is not None:
        overrides["base_url"] = base_url
    if signing_key is not None:
        overrides["signing_key"] = signing_key
    if timeout is not None:
        overrides["timeout"] = timeout
    if max_retries is not None:
        overrides["max_retries"] = max_retries
    overrides["debug"] = debug

    config = BlocklogConfig(**overrides)

    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("blocklog").setLevel(logging.DEBUG)

    client = BlocklogClient(config)
    set_client(client)
    return client


def health() -> dict[str, Any]:
    """Perform a health check on the Blocklog SDK and API connection.

    Checks if the API is reachable, if the configured API key is valid,
    if a signing key is loaded, and reports the context backend and SDK version.

    Returns
    -------
    dict
        A dictionary containing the health status fields:
        - api_reachable (bool)
        - auth_valid (bool)
        - signing_key_loaded (bool)
        - context_backend (str)
        - sdk_version (str)

    Raises
    ------
    BlocklogAuthError
        If the API key is not configured or is invalid.
    """
    from blocklog._global import get_client
    from blocklog.exceptions import BlocklogAuthError
    from blocklog import __version__

    client = get_client()

    signing_key_loaded = bool(client.config.signing_key)
    context_backend = "contextvars"
    sdk_version = __version__

    api_reachable = False
    auth_valid = False

    if not client.config.api_key:
        raise BlocklogAuthError(
            "Blocklog API key is not configured. "
            "Please initialize the SDK using blocklog.init(api_key='your_key') "
            "or set the BLOCKLOG_API_KEY environment variable."
        )

    # Check API reachability via unauthenticated GET /health
    try:
        client.transport.request("GET", "/health")
        api_reachable = True
    except Exception as exc:
        status_code = None
        if hasattr(exc, "response") and exc.response is not None:
            status_code = getattr(exc.response, "status_code", None)
        if status_code in (401, 403):
            api_reachable = True
        else:
            api_reachable = False

    # Check authentication validity via decisions list (authenticated endpoint)
    try:
        client.decisions.list()
        auth_valid = True
        api_reachable = True
    except Exception as exc:
        status_code = None
        if hasattr(exc, "response") and exc.response is not None:
            status_code = getattr(exc.response, "status_code", None)

        if status_code in (401, 403):
            auth_valid = False
            api_reachable = True
        elif status_code is not None:
            api_reachable = True
            auth_valid = True
        else:
            auth_valid = False

    if not auth_valid:
        raise BlocklogAuthError(
            "Blocklog authentication failed. Please verify that your API key is valid "
            "and has the correct permissions. Ensure BLOCKLOG_API_KEY environment variable "
            "is correctly set or api_key parameter in blocklog.init() is correct."
        )

    return {
        "api_reachable": api_reachable,
        "auth_valid": auth_valid,
        "signing_key_loaded": signing_key_loaded,
        "context_backend": context_backend,
        "sdk_version": sdk_version,
    }
