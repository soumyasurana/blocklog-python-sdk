from functools import wraps

from .managers import agent_session


def instrumented_agent(*, source: str = "python-sdk"):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            with agent_session(agent_id=getattr(fn, "__name__", "agent"), source=source):
                return fn(*args, **kwargs)

        return wrapper

    return decorator
