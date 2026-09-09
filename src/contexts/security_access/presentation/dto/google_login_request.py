from typing import Optional
from pydantic import BaseModel, model_validator


class GoogleLoginRequest(BaseModel):
    google_token: Optional[str] = None
    auth_code: Optional[str] = None

    @model_validator(mode="after")
    def check_token_provided(self) -> "GoogleLoginRequest":
        if not self.google_token and not self.auth_code:
            raise ValueError("Debe proporcionar google_token o auth_code.")
        if not self.google_token and self.auth_code:
            self.google_token = self.auth_code
        return self