from __future__ import annotations

from dataclasses import dataclass, field

from blocklog.models.events import EventEnvelope


@dataclass(slots=True)
class EventBuffer:
    batch_size: int
    items: list[EventEnvelope] = field(default_factory=list)

    def add(self, event: EventEnvelope) -> list[EventEnvelope] | None:
        self.items.append(event)
        if len(self.items) >= self.batch_size:
            return self.flush()
        return None

    def flush(self) -> list[EventEnvelope]:
        drained = list(self.items)
        self.items.clear()
        return drained
