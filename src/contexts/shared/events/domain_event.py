# shared/events/domain_event.py

from typing import Protocol
from datetime import datetime


class DomainEvent(Protocol):
    event_name: str
    occurred_at: datetime