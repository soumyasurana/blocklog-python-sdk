__all__ = ["AsyncBlocklogClient", "BlocklogClient"]


def __getattr__(name: str):
    if name in {"BlocklogClient", "AsyncBlocklogClient"}:
        from .src import blocklog as package

        return getattr(package, name)
    raise AttributeError(name)
