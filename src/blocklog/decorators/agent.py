"""
blocklog.decorators.agent
~~~~~~~~~~~~~~~~~~~~~~~~~
The ``@agent`` decorator — wraps a function (or class) so that every
execution is automatically traced, timed, and linked to a Blocklog
session.

Usage::

    import blocklog
    blocklog.init(api_key="blk_...")

    @blocklog.agent
    def market_analyst():
        ...

    # With options:
    @blocklog.agent(name="market-analyst", version="2.1", tags=["prod"])
    def market_analyst():
        ...

    # On a class:
    @blocklog.agent(name="hedge-fund-orchestrator")
    class HedgeFundOrchestrator:
        def run(self):
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


def agent(
    func: F | None = None,
    *,
    name: str | None = None,
    version: str = "1.0",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> F | Callable[[F], F]:
    """Decorator that traces an AI agent function or class.

    Automatically:
    - Opens a Blocklog ``agent_session`` (sets trace/session context)
    - Emits ``AGENT_START`` event with agent name, version, tags
    - Emits ``AGENT_COMPLETE`` event with duration on clean return
    - Emits ``AGENT_ERROR`` event with traceback on exception

    Can be used with or without arguments:

    .. code-block:: python

        @blocklog.agent
        def my_agent(): ...

        @blocklog.agent(name="my-agent", version="2.0")
        def my_agent(): ...

    .. warning::
        Class decoration only emits ``AGENT_START``. Full lifecycle tracing
        requires decorating the specific method (e.g. ``run``, ``execute``)
        rather than the class itself.

    Parameters
    ----------
    func:
        The function to decorate (when used without arguments).
    name:
        Human-readable agent name.  Defaults to ``func.__name__``.
    version:
        Semver-style version string stored in agent metadata.
    tags:
        Optional list of string tags.
    metadata:
        Arbitrary extra data stored in the agent metadata.

    Returns
    -------
    Callable
        The decorated function (or a decorator if called with arguments).
    """
    def decorator(fn: F) -> F:
        agent_name = name or fn.__name__
        agent_meta = {
            "agent_name": agent_name,
            "agent_version": version,
            "tags": tags or [],
            **(metadata or {}),
        }

        if inspect.isclass(fn):
            return _wrap_class(fn, agent_name, agent_meta)  # type: ignore[return-value]

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return _run_sync(fn, args, kwargs, agent_name, agent_meta)

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_async(fn, args, kwargs, agent_name, agent_meta)

        if inspect.iscoroutinefunction(fn):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    # Called as @agent (no args)
    if func is not None:
        return decorator(func)

    # Called as @agent(...) — return the decorator
    return decorator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_sync(fn: Callable, args: tuple, kwargs: dict, agent_name: str, meta: dict) -> Any:
    from blocklog.context.managers import agent_session
    started_at = _now()
    with agent_session(agent_id=agent_name, source=f"agent:{agent_name}") as ctx:
        logger.debug("Agent context pushed: agent_name=%s, trace_id=%s, session_id=%s", agent_name, ctx.trace_id, ctx.session_id)
        _emit("AGENT_START", {
            "agent_name": agent_name,
            "started_at": started_at,
            **meta,
        }, ctx)
        try:
            result = fn(*args, **kwargs)
            _emit("AGENT_COMPLETE", {
                "agent_name": agent_name,
                "duration_ms": _elapsed_ms(started_at),
                "status": "ok",
            }, ctx)
            logger.debug("Agent context popped: agent_name=%s, status=ok", agent_name)
            return result
        except BaseException as exc:
            _emit("AGENT_ERROR", {
                "agent_name": agent_name,
                "duration_ms": _elapsed_ms(started_at),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": _traceback.format_exc(),
            }, ctx)
            logger.debug("Agent context popped: agent_name=%s, status=error", agent_name)
            raise


async def _run_async(fn: Callable, args: tuple, kwargs: dict, agent_name: str, meta: dict) -> Any:
    from blocklog.context.managers import agent_session
    started_at = _now()
    with agent_session(agent_id=agent_name, source=f"agent:{agent_name}") as ctx:
        logger.debug("Agent context pushed: agent_name=%s, trace_id=%s, session_id=%s", agent_name, ctx.trace_id, ctx.session_id)
        _emit("AGENT_START", {
            "agent_name": agent_name,
            "started_at": started_at,
            **meta,
        }, ctx)
        try:
            result = await fn(*args, **kwargs)
            _emit("AGENT_COMPLETE", {
                "agent_name": agent_name,
                "duration_ms": _elapsed_ms(started_at),
                "status": "ok",
            }, ctx)
            logger.debug("Agent context popped: agent_name=%s, status=ok", agent_name)
            return result
        except BaseException as exc:
            _emit("AGENT_ERROR", {
                "agent_name": agent_name,
                "duration_ms": _elapsed_ms(started_at),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": _traceback.format_exc(),
            }, ctx)
            logger.debug("Agent context popped: agent_name=%s, status=error", agent_name)
            raise


def _wrap_class(cls: type, agent_name: str, meta: dict) -> type:
    """Wrap the ``__init__`` of a class to open an agent session."""
    logger.warning(
        "blocklog: @agent on a class only emits AGENT_START. "
        "For full tracing, use @blocklog.agent on the method that runs the agent."
    )
    original_init = cls.__init__

    @functools.wraps(original_init)
    def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
        from blocklog.context.vars import set_context
        from blocklog.models.events import SessionContext

        ctx = SessionContext(agent_id=agent_name, source=f"agent:{agent_name}")
        set_context(ctx)
        logger.debug("Agent context pushed: agent_name=%s, trace_id=%s, session_id=%s", agent_name, ctx.trace_id, ctx.session_id)
        _emit("AGENT_START", {"agent_name": agent_name, **meta}, ctx)
        original_init(self, *args, **kwargs)

    cls.__init__ = new_init
    return cls


def _emit(event_type: str, payload: dict, ctx: Any) -> None:
    try:
        from blocklog._global import get_client
        client = get_client()
        client.event(
            event_type,
            payload=payload,
            trace_id=str(ctx.trace_id) if ctx else None,
            session_id=str(ctx.session_id) if ctx else None,
            agent_id=ctx.agent_id if ctx else None,
            agent_type="agent",
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("blocklog: emit %s failed: %s", event_type, exc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed_ms(since_iso: str) -> int:
    start = datetime.fromisoformat(since_iso)
    return int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
