from .config import BlocklogConfig
from .context.managers import agent_session
from .context.vars import get_context, set_context

__all__ = [
    "AsyncBlocklogClient",
    "BlocklogClient",
    "BlocklogConfig",
    "agent_session",
    "get_context",
    "set_context",
]


def __getattr__(name: str):
    if name == "BlocklogClient":
        from .client import BlocklogClient

        return BlocklogClient
    if name == "AsyncBlocklogClient":
        from .async_client import AsyncBlocklogClient

        return AsyncBlocklogClient
    raise AttributeError(name)
