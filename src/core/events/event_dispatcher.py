import logging
from typing import Dict, Type, List, Callable, Any

logger = logging.getLogger(__name__)

class EventDispatcher:
    """Bus de eventos in-process"""
    _handlers: Dict[Type, List[Callable]] = {}

    @classmethod
    def register(cls, event_type: Type, handler: Callable) -> None:
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)
        logger.info(f"Handler '{handler.__name__}' registrado para evento '{event_type.__name__}'")

    @classmethod
    async def dispatch(cls, event: Any) -> None:
        event_type = type(event)
        handlers = cls._handlers.get(event_type, [])
        for handler in handlers:
            await handler(event)

    @classmethod
    def clear(cls) -> None:
        cls._handlers.clear()
