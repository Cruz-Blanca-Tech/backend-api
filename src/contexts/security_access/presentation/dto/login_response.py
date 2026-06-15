from pydantic import BaseModel

from src.contexts.security_access.presentation.dto.user_dto import UserResponse

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse