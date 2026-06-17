"""
Auth/routers/internal.py

Internal endpoints — Core calls these over HTTP to:
  1. Validate a JWT and get the user_id
  2. Get a user's platform credentials for publishing

These are NEVER called by the frontend.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from services.auth_oauth.config import settings
from services.auth_oauth.database import get_db
from services.auth_oauth.models import PlatformConnection
from services.auth_oauth.schemas import PlatformCredentialsResponse, ValidateTokenRequest, ValidateTokenResponse
from services.auth_oauth.services.security import decode_token
from services.auth_oauth.services.token_encryption import decrypt_token

router = APIRouter(prefix="/internal", tags=["Internal"])


def verify_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal API key.")


@router.post("/validate-token", response_model=ValidateTokenResponse)
def validate_token(
    payload: ValidateTokenRequest,
    _: Annotated[None, Depends(verify_internal_key)],
):
    """
    Core calls this to validate a JWT and get the user_id.
    Returns valid: false instead of raising — Core decides what to do.
    """
    user_id = decode_token(payload.token)
    if not user_id:
        return ValidateTokenResponse(valid=False)
    return ValidateTokenResponse(valid=True, user_id=user_id)


@router.get("/credentials/{user_id}/{platform}", response_model=PlatformCredentialsResponse)
def get_platform_credentials(
    user_id: str,
    platform: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(verify_internal_key)],
):
    """
    Core calls this instead of reading PlatformConnection directly.
    Returns decrypted credentials — Core never touches the encryption layer.
    """
    connection = db.query(PlatformConnection).filter_by(
        user_id=user_id,
        platform=platform,
        is_active=True,
    ).first()

    if not connection:
        raise HTTPException(
            status_code=404,
            detail=f"No active {platform} connection found for this user."
        )

    return PlatformCredentialsResponse(
        platform=platform,
        access_token=decrypt_token(connection.access_token),
        platform_user_id=connection.platform_user_id,
    )