from __future__ import annotations

from dataclasses import dataclass
from random import random
from time import sleep


@dataclass(slots=True)
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 0.25

    def backoff(self, attempt: int) -> float:
        return self.base_delay * (2 ** attempt) + random() * 0.1

    def run(self, fn):
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                status_code = None
                if hasattr(exc, "response") and exc.response is not None:
                    status_code = getattr(exc.response, "status_code", None)
                if status_code in (401, 403):
                    raise

                last_error = exc
                if attempt == self.max_retries - 1:
                    raise
                sleep(self.backoff(attempt))
        raise RuntimeError("retry failed") from last_error
