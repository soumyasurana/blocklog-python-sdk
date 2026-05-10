from contextlib import contextmanager

from blocklog.models.events import SessionContext

from .vars import set_context


@contextmanager
def agent_session(*, agent_id: str | None = None, source: str = "python-sdk", workflow_id=None):
    context = SessionContext(agent_id=agent_id, source=source, workflow_id=workflow_id)
    token = set_context(context)
    try:
        yield context
    finally:
        set_context(None)
