# src/contexts/document_intake_ocr/infrastructure/events/event_bus_adapter.py


import logging
from typing import Any, Callable, Dict, List, Type

from src.contexts.shared.infrastructure.bus.event_bus import T, EventBus
logger = logging.getLogger(__name__)

class IngestionEventBus(EventBus):
    def __init__(self):
        self.subscribers: Dict[Type, List[Callable]] = {}

    async def publish(self, event: Any) -> None:
        event_type = type(event)
        if event_type in self.subscribers:
            logger.info(f"Publicando evento: {event_type.__name__}")
            for handler in self.subscribers[event_type]:
                # IMPORTANTE: Await al handler porque serán funciones async
                await handler(event)
        else:
            logger.warning(f"No hay suscriptores para: {event_type.__name__}")

    def subscribe(self, event_type: Type, handler: Callable[[Any], None]) -> None:
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.info(f"Nuevo suscriptor registrado para: {event_type.__name__}")