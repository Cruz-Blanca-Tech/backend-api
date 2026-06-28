from abc import ABC, abstractmethod
from asyncio import Protocol
from collections import defaultdict
from datetime import datetime
from typing import Callable, Dict, List, Type, TypeVar, Any

from abc import ABC, abstractmethod
from typing import Callable


class EventBus(ABC):

    @abstractmethod
    async def publish(
        self,
        event
    ):
        pass


    @abstractmethod
    def subscribe(
        self,
        event_type,
        handler: Callable
    ):
        pass

class InMemoryEventBus(EventBus):

    def __init__(self):

        self.handlers = {}


    async def publish(self,event):

        handlers = self.handlers.get(
            type(event),
            []
        )

        for handler in handlers:
            await handler(event)



    def subscribe(
        self,
        event_type,
        handler
    ):

        if event_type not in self.handlers:
            self.handlers[event_type]=[]

        self.handlers[event_type].append(handler)

_bus = InMemoryEventBus()

def get_event_bus() -> EventBus:
    return _bus