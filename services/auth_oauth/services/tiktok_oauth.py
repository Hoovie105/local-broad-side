"""
Auth/services/tiktok_oauth.py

TikTok OAuth 2.0 flow.
TikTok uses PKCE and requires specific scopes approved per app.

For testing: use TikTok's sandbox environment.
Sandbox approval needed: video.upload, video.publish

Flow:
  1. Build authorization URL → redirect user to TikTok consent
  2. Receive code → exchange for access token
  3. Fetch TikTok user's open_id (their unique identifier)
  4. Store encrypted access token
"""
import hashlib
import httpx
import secrets
import base64
from services.auth_oauth.config import settings


TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USER_URL = "https://open.tiktokapis.com/v2/user/info/"

SCOPES = "user.info.basic,video.upload,video.publish"


class TikTokOAuthError(Exception):
    pass


def _generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def _generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def build_authorization_url(state: str) -> tuple[str, str]:
    """
    Returns (authorization_url, code_verifier).
    Store code_verifier temporarily — needed for token exchange.
    TikTok uses PKCE for security.
    """
    verifier = _generate_code_verifier()
    challenge = _generate_code_challenge(verifier)

    url = (
        f"{TIKTOK_AUTH_URL}"
        f"?client_key={settings.TIKTOK_CLIENT_KEY}"
        f"&scope={SCOPES}"
        f"&response_type=code"
        f"&redirect_uri={settings.TIKTOK_REDIRECT_URI}"
        f"&state={state}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
    )
    return url, verifier


async def exchange_code_for_token(code: str, code_verifier: str) -> dict:
    """Exchange authorization code for access token using PKCE verifier."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TIKTOK_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": settings.TIKTOK_CLIENT_KEY,
                "client_secret": settings.TIKTOK_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.TIKTOK_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )
    data = resp.json()
    if "error" in data or data.get("message") == "error":
        raise TikTokOAuthError(data.get("error_description", "Token exchange failed"))
    return data


async def get_tiktok_user_id(access_token: str) -> str:
    """Get the TikTok user's open_id."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            TIKTOK_USER_URL,
            params={"fields": "open_id,display_name"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    data = resp.json()
    if data.get("error", {}).get("code") != "ok":
        raise TikTokOAuthError(
            data.get("error", {}).get("message", "Failed to fetch user info")
        )
    return data["data"]["user"]["open_id"]