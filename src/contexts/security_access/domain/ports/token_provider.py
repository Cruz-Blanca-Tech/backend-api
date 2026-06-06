from abc import ABC, abstractmethod
from src.contexts.security_access.domain.entities.user import User
from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims
from src.contexts.security_access.domain.value_objects.token_pair import TokenPair

class TokenProvider(ABC):
    @abstractmethod
    def create_internal_token_pair(self, user: User) -> TokenPair:
        pass

    @abstractmethod
    def decode_internal_token(self, token: str) -> TokenClaims:
        pass

    @abstractmethod
    def hash_token(self, token: str) -> str:
        """Convierte un token en un hash seguro para guardar en BD"""
        pass