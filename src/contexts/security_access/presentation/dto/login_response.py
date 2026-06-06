from pydantic import BaseModel

class UserResponse(BaseModel):
    email: str
    full_name: str
    role: str
    picture_url: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse