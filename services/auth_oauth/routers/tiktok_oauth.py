"""
Auth/routers/tiktok_oauth.py

GET /auth/tiktok          → redirect to TikTok consent screen
GET /auth/tiktok/callback → exchange code, store connection

PKCE verifier stored in DB instead of memory — fixes the issue where
the callback coming through a tunnel hits a fresh process context
and can't find the in-memory verifier.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from services.auth_oauth.config import settings
from services.auth_oauth.database import get_db
from services.auth_oauth.models import PlatformConnection, User, TokenBlacklist, PKCEVerifier
from services.auth_oauth.services.tiktok_oauth import (
    TikTokOAuthError,
    build_authorization_url,
    exchange_code_for_token,
    get_tiktok_user_id,
)
from services.auth_oauth.services.security import decode_token
from services.auth_oauth.services.token_encryption import encrypt_token

router = APIRouter(prefix="/auth", tags=["TikTok OAuth"])


@router.get("/tiktok")
def connect_tiktok(
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

    url, verifier = build_authorization_url(state=user.id)

    # Store verifier in DB — survives across process restarts and tunnel hops
    db.merge(PKCEVerifier(state=user.id, verifier=verifier))
    db.commit()

    return RedirectResponse(url)


@router.get("/tiktok/callback")
async def tiktok_callback(
    db: Annotated[Session, Depends(get_db)],
    code: str = Query(None),
    state: str = Query(...),
    error: str = Query(None),
    error_description: str = Query(None),
):
    print(f"[TikTok CB] code={'...' if code else None} state={state} error={error}")

    if error:
        return RedirectResponse(
            f"{settings.FRONTEND_ERROR_URL}?error={error_description or error}"
        )

    user = db.query(User).filter_by(id=state).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid state parameter.")

    # Read verifier from DB — single use, delete immediately
    pkce = db.query(PKCEVerifier).filter_by(state=state).first()
    print(f"[TikTok CB] verifier found: {pkce is not None}")
    if not pkce:
        raise HTTPException(
            status_code=400,
            detail="PKCE verifier not found. Try connecting again."
        )

    verifier = pkce.verifier
    db.delete(pkce)
    db.commit()

    try:
        tokens = await exchange_code_for_token(code, verifier)
        access_token = tokens["access_token"]
        open_id = await get_tiktok_user_id(access_token)
    except TikTokOAuthError as exc:
        return RedirectResponse(
            f"{settings.FRONTEND_ERROR_URL}?error={exc}"
        )

    # Upsert PlatformConnection
    existing = db.query(PlatformConnection).filter_by(
        user_id=user.id, platform="tiktok"
    ).first()

    if existing:
        existing.access_token = encrypt_token(access_token)
        existing.platform_user_id = open_id
        existing.is_active = True
    else:
        db.add(PlatformConnection(
            id=str(uuid.uuid4()),
            user_id=user.id,
            platform="tiktok",
            access_token=encrypt_token(access_token),
            platform_user_id=open_id,
        ))

    db.commit()
    print(f"[TikTok CB] Connection saved for user {user.id} open_id={open_id}")

    return RedirectResponse(
        f"{settings.FRONTEND_SUCCESS_URL}?connected=tiktok"
    )