# src/contexts/security_access/infrastructure/adapters/google_identity_adapter.py
from google.oauth2 import id_token
from google.auth.transport import requests
from src.contexts.security_access.domain.ports.identity_provider import IdentityProvider
from src.contexts.security_access.domain.entities.external_user_identity import ExternalUserIdentity
from src.core.config import settings 

class GoogleIdentityAdapter(IdentityProvider):
    def __init__(self, client_id: str):
        self.client_id = client_id

    def verify_token(self, google_token: str) -> ExternalUserIdentity:
        # Aquí usas el SDK de Google
        if settings.ENVIRONMENT == "development" and google_token == "test-token":
            return ExternalUserIdentity(
                email="operativo@cruz-blanca.org",
                full_name="Rimbow Test",
                picture_url="https://example.com/pic.jpg"
            )
        
        id_info = id_token.verify_oauth2_token(google_token, requests.Request(), self.client_id)
        
        return ExternalUserIdentity(
            email=id_info["email"],
            full_name=id_info.get("name", ""),
            picture_url=id_info.get("picture", "")
        )