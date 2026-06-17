from pydantic import BaseModel, EmailStr
from typing import Optional


# ------------------------------------------------------------------ #
# User                                                                 #
# ------------------------------------------------------------------ #

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str


# ------------------------------------------------------------------ #
# Internal — Core calls these endpoints, not the frontend             #
# ------------------------------------------------------------------ #

class ValidateTokenRequest(BaseModel):
    token: str


class ValidateTokenResponse(BaseModel):
    valid: bool
    user_id: Optional[str] = None


class PlatformCredentialsResponse(BaseModel):
    """
    What Core receives when it asks Auth for a user's platform credentials.
    Core builds PublishPayload from this — never touches the raw token directly.
    """
    platform: str
    access_token: str
    platform_user_id: str