import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = {}
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def dispatch(self, event_type: str, data: dict[str, Any]) -> None:
        logger.debug("Dispatching event: %s", event_type)
        for cb in self._subscribers.get(event_type, []):
            try:
                cb(event_type, data)
            except Exception:
                logger.exception("Event subscriber error for %s", event_type)
        for cb in self._subscribers.get("*", []):
            try:
                cb(event_type, data)
            except Exception:
                logger.exception("Event subscriber error for %s", event_type)


event_bus = EventBus()
