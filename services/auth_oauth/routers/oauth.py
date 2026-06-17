"""
Auth/routers/oauth.py

GET /auth/instagram          — redirects user to Meta consent screen
GET /auth/instagram/callback — Meta redirects here with code
                               exchanges code → long-lived token
                               fetches Instagram Business Account ID
                               stores encrypted PlatformConnection
                               redirects user back to frontend
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from services.auth_oauth.config import settings
from services.auth_oauth.database import get_db
from services.auth_oauth.dependencies import get_current_user
from services.auth_oauth.models import PlatformConnection, TokenBlacklist, User
from services.auth_oauth.services.meta_oauth import (
    MetaOAuthError,
    build_authorization_url,
    exchange_code_for_token,
    exchange_for_long_lived_token,
    get_instagram_business_account_id,
)
from services.auth_oauth.services.security import decode_token
from services.auth_oauth.services.token_encryption import encrypt_token

router = APIRouter(prefix="/auth", tags=["OAuth"])


@router.get("/instagram")
def connect_instagram(
    db: Annotated[Session, Depends(get_db)],
    token: str = Query(...),
):
    if db.query(TokenBlacklist).filter_by(token=token).first():
        raise HTTPException(status_code=401, detail="Token invalidated.")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token.")
    user = db.query(User).filter_by(id=user_id, is_active=True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    url = build_authorization_url(state=user.id)
    return RedirectResponse(url)


@router.get("/instagram/callback")
async def instagram_callback(
    db: Annotated[Session, Depends(get_db)],
    code: str = Query(...),
    state: str = Query(...),   # user_id we passed in the authorization URL
    error: str = Query(None),  # Meta sends this if user denied permission
):
    """
    Meta redirects here after the user grants or denies permission.
    State carries the user_id we set when starting the flow.
    """
    if error:
        return RedirectResponse(
            f"{settings.FRONTEND_ERROR_URL}?error=instagram_denied"
        )

    user = db.query(User).filter_by(id=state).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid state parameter.")

    try:
        short_lived_token = await exchange_code_for_token(code)
        long_lived_token = await exchange_for_long_lived_token(short_lived_token)
        ig_user_id = await get_instagram_business_account_id(long_lived_token)
    except MetaOAuthError as exc:
        return RedirectResponse(
            f"{settings.FRONTEND_ERROR_URL}?error={exc}"
        )

    # Upsert — update if already connected, insert if new
    existing = db.query(PlatformConnection).filter_by(
        user_id=user.id, platform="instagram"
    ).first()

    if existing:
        existing.access_token = encrypt_token(long_lived_token)
        existing.platform_user_id = ig_user_id
        existing.is_active = True
    else:
        connection = PlatformConnection(
            id=str(uuid.uuid4()),
            user_id=user.id,
            platform="instagram",
            access_token=encrypt_token(long_lived_token),
            platform_user_id=ig_user_id,
        )
        db.add(connection)

    db.commit()

    return RedirectResponse(
        f"{settings.FRONTEND_SUCCESS_URL}?connected=instagram"
    )


@router.get("/connections")
def get_connections(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Frontend calls this to check which platforms are connected."""
    connections = db.query(PlatformConnection).filter_by(
        user_id=current_user.id,
        is_active=True,
    ).all()
    return [{"platform": c.platform} for c in connections]