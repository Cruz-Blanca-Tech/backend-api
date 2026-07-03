from pydantic import BaseModel


class GoogleLoginRequest(BaseModel):
    auth_code: str