import jwt
from datetime import datetime, timedelta
from src.contexts.security_access.domain.entities.user import User
from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims

class TokenMapper:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def create_token_from_user(self, user: User) -> str:
        claims = TokenClaims(email=user.email, role=user.role)
        payload = claims.to_dict()
        payload.update({
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        })
        return jwt.encode(payload, self.secret_key, algorithm="HS256")