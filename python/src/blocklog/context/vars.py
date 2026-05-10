from contextvars import ContextVar

from blocklog.models.events import SessionContext

_context: ContextVar[SessionContext | None] = ContextVar("blocklog_context", default=None)


def set_context(context: SessionContext | None):
    return _context.set(context)


def get_context() -> SessionContext | None:
    return _context.get()
