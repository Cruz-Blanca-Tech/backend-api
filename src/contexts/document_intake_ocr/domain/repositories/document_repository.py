from abc import ABC, abstractmethod
from typing import Iterator
from xml.dom.minidom import Document

class DocumentRepository(ABC):
    @abstractmethod
    async def save(self, document: Document) -> None: pass