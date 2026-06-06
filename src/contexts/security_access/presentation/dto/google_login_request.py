from pydantic import BaseModel


class GoogleLoginRequest(BaseModel):
    google_token: str