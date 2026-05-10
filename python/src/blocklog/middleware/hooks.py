from collections.abc import Callable


Hook = Callable[[dict], dict]


def apply_hooks(payload: dict, hooks: list[Hook]) -> dict:
    current = payload
    for hook in hooks:
        current = hook(current)
    return current
