import httpx
from google.oauth2 import id_token
from google.auth.transport import requests
from src.contexts.security_access.domain.ports.identity_provider_port import IdentityProviderPort
from src.contexts.security_access.domain.entities.external_user_identity import ExternalUserIdentity
from src.core.config import settings 

class GoogleIdentityAdapter(IdentityProviderPort):
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://oauth2.googleapis.com/token"

    async def verify_token(self, auth_code: str) -> ExternalUserIdentity:
        if settings.ENVIRONMENT == "development" and auth_code == "test-token":
            return ExternalUserIdentity(
                email="enzo.trujillo@cruz-blanca.org",
                full_name="Rimbow Test",
                picture_url="https://example.com/pic.jpg"
            )
        
        # Intercambiar Authorization Code por Tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "code": auth_code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": "postmessage",
                    "grant_type": "authorization_code"
                }
            )
            
            if response.status_code != 200:
                raise ValueError(f"Error intercambiando el código de autorización: {response.text}")
                
            token_data = response.json()
            id_token_jwt = token_data.get("id_token")
            # google_access_token = token_data.get("access_token")
            # google_refresh_token = token_data.get("refresh_token")
            
            if not id_token_jwt:
                raise ValueError("La respuesta de Google no incluyó un id_token.")
        
        # Verificar el ID Token para extraer la identidad
        id_info = id_token.verify_oauth2_token(id_token_jwt, requests.Request(), self.client_id)
        
        return ExternalUserIdentity(
            email=id_info["email"],
            full_name=id_info.get("name", ""),
            picture_url=id_info.get("picture", "")
        )