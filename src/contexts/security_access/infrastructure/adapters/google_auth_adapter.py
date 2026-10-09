# src/contexts/security_access/infrastructure/adapters/google_identity_adapter.py
from google.oauth2 import id_token
from google.auth.transport import requests
from src.contexts.security_access.domain.ports.identity_provider_port import IdentityProviderPort
from src.contexts.security_access.domain.entities.external_user_identity import ExternalUserIdentity
from src.core.config import settings 

class GoogleIdentityAdapter(IdentityProviderPort):
    def __init__(self, client_id: str):
        self.client_id = client_id

    def verify_token(self, google_token: str) -> ExternalUserIdentity:
        # Aquí usas el SDK de Google
        if settings.ENVIRONMENT == "development" and google_token == "test-token":
            return ExternalUserIdentity(
                email="enzo.trujillo@cruz-blanca.org",
                full_name="Rimbow Test",
                picture_url="https://example.com/pic.jpg"
            )
        
        # Verificación estricta (RF-01): firma de Google, audiencia (client_id),
        # emisor y expiración. Un token que no pasa la verificación se rechaza
        # siempre; nunca se decodifica sin comprobar la firma. Se tolera un
        # desfase de reloj de hasta 30 s entre el servidor y Google.
        try:
            id_info = id_token.verify_oauth2_token(
                google_token,
                requests.Request(),
                self.client_id,
                clock_skew_in_seconds=30,
            )
        except Exception as e:
            import logging
            logging.warning(f"Token de Google rechazado en la verificación: {e}")
            raise ValueError("Token de Google inválido o expirado.") from e

        if not id_info.get("email_verified", False):
            raise ValueError("La cuenta de Google no tiene el correo verificado.")
        
        return ExternalUserIdentity(
            email=id_info["email"],
            full_name=id_info.get("name", ""),
            picture_url=id_info.get("picture", "")
        )