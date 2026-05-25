from google.oauth2 import id_token
from google.auth.transport import requests
from google.auth.exceptions import GoogleAuthError 
from src.contexts.security_access.domain.ports.auth_provider import AuthProvider
from src.contexts.security_access.domain.entities.authenticated_user import AuthenticatedUser
from src.contexts.security_access.domain.value_objects.email import Email

class GoogleAuthAdapter(AuthProvider):
    def __init__(self, client_id: str):
        self.client_id = client_id

    def verify_token(self, token: str) -> AuthenticatedUser:
        # Esta librería de Google verifica la firma y fecha del token
        try:
            id_info = id_token.verify_oauth2_token(
                token, requests.Request(), self.client_id
            )
        except (ValueError, GoogleAuthError) as e:
            # Si cae acá, es que Google dijo "este token no sirve"
            raise PermissionError("Token de autenticación inválido o expirado.") from e
        
        if id_info.get("hd") != "cruz-blanca.org":
            raise PermissionError("Dominio no autorizado. Solo miembros de Cruz Blanca.")

        return AuthenticatedUser(
                email=Email(id_info["email"]),
                full_name=id_info.get("name", ""),
                picture_url=id_info.get("picture", "")
            )