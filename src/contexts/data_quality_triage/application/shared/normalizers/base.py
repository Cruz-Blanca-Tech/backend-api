from abc import ABC, abstractmethod

class FieldNormalizer(ABC):
    @abstractmethod
    def normalize(self, value):
        pass
