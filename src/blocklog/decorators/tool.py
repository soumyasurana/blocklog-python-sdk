"""
blocklog.decorators.tool
~~~~~~~~~~~~~~~~~~~~~~~~
The ``@tool`` decorator — wraps a function so every call is recorded as a
``TOOL_CALL`` event, capturing inputs, outputs, duration, and errors.

The decorator inherits the parent ``@agent`` trace context automatically.

Usage::

    import blocklog

    @blocklog.tool
    def fetch_price(ticker: str) -> float:
        return market_api.get_price(ticker)

    # With a custom name and schema hint:
    @blocklog.tool(name="fetch-market-price", schema={"ticker": "str"})
    def fetch_price(ticker: str) -> float:
        ...
"""
from __future__ import annotations

import functools
import inspect
import logging
import traceback as _traceback
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

logger = logging.getLogger("blocklog")

F = TypeVar("F", bound=Callable[..., Any])


def tool(
    func: F | None = None,
    *,
    name: str | None = None,
    schema: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> F | Callable[[F], F]:
    """Decorator that records a tool call as a Blocklog event.

    Automatically captures:
    - Function name, call arguments
    - Return value
    - Duration in milliseconds
    - Any exception raised

    Inherits the trace/session context set by the surrounding ``@agent``.

    Can be used with or without arguments:

    .. code-block:: python

        @blocklog.tool
        def my_tool(x: int) -> int: ...

        @blocklog.tool(name="my-tool", tags=["external-api"])
        def my_tool(x: int) -> int: ...

    Parameters
    ----------
    func:
        The function to decorate (when used without arguments).
    name:
        Human-readable tool name.  Defaults to ``func.__name__``.
    schema:
        Optional dict describing the input schema (for documentation /
        dashboard display purposes).
    tags:
        Optional string tags.
    metadata:
        Arbitrary extra data stored with each tool call event.
    """
    def decorator(fn: F) -> F:
        tool_name = name or fn.__name__
        tool_meta = {
            "tool_name": tool_name,
            "tags": tags or [],
            "schema": schema or {},
            **(metadata or {}),
        }

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return _run_sync(fn, args, kwargs, tool_name, tool_meta)

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_async(fn, args, kwargs, tool_name, tool_meta)

        if inspect.iscoroutinefunction(fn):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    if func is not None:
        return decorator(func)
    return decorator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_sync(fn: Callable, args: tuple, kwargs: dict, tool_name: str, meta: dict) -> Any:
    started_at = _now()
    call_args = _safe_args(fn, args, kwargs)
    logger.debug("Tool call started: tool_name=%s", tool_name)
    try:
        result = fn(*args, **kwargs)
        _emit("TOOL_CALL", {
            **meta,
            "inputs": call_args,
            "output": _safe_repr(result),
            "duration_ms": _elapsed_ms(started_at),
            "status": "ok",
        })
        logger.debug("Tool call completed: tool_name=%s, status=ok", tool_name)
        return result
    except BaseException as exc:
        _emit("TOOL_CALL", {
            **meta,
            "inputs": call_args,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": _traceback.format_exc(),
            "duration_ms": _elapsed_ms(started_at),
            "status": "error",
        })
        logger.debug("Tool call completed: tool_name=%s, status=error", tool_name)
        raise


async def _run_async(fn: Callable, args: tuple, kwargs: dict, tool_name: str, meta: dict) -> Any:
    started_at = _now()
    call_args = _safe_args(fn, args, kwargs)
    logger.debug("Tool call started: tool_name=%s", tool_name)
    try:
        result = await fn(*args, **kwargs)
        _emit("TOOL_CALL", {
            **meta,
            "inputs": call_args,
            "output": _safe_repr(result),
            "duration_ms": _elapsed_ms(started_at),
            "status": "ok",
        })
        logger.debug("Tool call completed: tool_name=%s, status=ok", tool_name)
        return result
    except BaseException as exc:
        _emit("TOOL_CALL", {
            **meta,
            "inputs": call_args,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": _traceback.format_exc(),
            "duration_ms": _elapsed_ms(started_at),
            "status": "error",
        })
        logger.debug("Tool call completed: tool_name=%s, status=error", tool_name)
        raise


def _emit(event_type: str, payload: dict) -> None:
    try:
        from blocklog._global import get_client
        from blocklog.context.vars import get_context
        ctx = get_context()
        client = get_client()
        client.event(
            event_type,
            payload=payload,
            trace_id=str(ctx.trace_id) if ctx else None,
            session_id=str(ctx.session_id) if ctx else None,
            agent_id=ctx.agent_id if ctx else None,
            agent_type="tool",
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("blocklog: tool emit failed: %s", exc)


def _safe_args(fn: Callable, args: tuple, kwargs: dict) -> dict:
    """Build a safe dict of call arguments, best-effort."""
    try:
        sig = inspect.signature(fn)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return {k: _safe_repr(v) for k, v in bound.arguments.items()}
    except Exception:  # noqa: BLE001
        return {"args": str(args), "kwargs": str(kwargs)}


def _safe_repr(value: Any) -> Any:
    """Truncate large values so they don't bloat the event payload."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    try:
        s = repr(value)
        return s if len(s) <= 512 else s[:509] + "..."
    except Exception:  # noqa: BLE001
        return "<unserializable>"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed_ms(since_iso: str) -> int:
    start = datetime.fromisoformat(since_iso)
    return int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
