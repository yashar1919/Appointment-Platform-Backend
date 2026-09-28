from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    name: str
    payload: dict[str, Any]


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)

    async def publish(self, event: Event) -> None:
        for handler in self._handlers.get(event.name, []):
            try:
                await handler(event)
            except Exception:
                logger.exception("Event handler failed", extra={"event": event.name})


bus = EventBus()
