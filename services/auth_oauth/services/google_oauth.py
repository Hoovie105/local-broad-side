"""
Auth/services/google_oauth.py

Google OAuth 2.0 flow for YouTube.
Simpler than Meta — no secondary account required.
User just needs a Google account with a YouTube channel.

Flow:
  1. Build authorization URL → redirect user to Google consent
  2. Receive code from callback → exchange for tokens
  3. Get YouTube channel ID
  4. Store encrypted access token + refresh token
"""
import httpx
from services.auth_oauth.config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class GoogleOAuthError(Exception):
    pass


def build_authorization_url(state: str) -> str:
    scope = " ".join(SCOPES)
    return (
        f"{GOOGLE_AUTH_URL}"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={state}"
        f"&access_type=offline"   # gets refresh token
        f"&prompt=consent"        # forces refresh token on every connect
    )


async def exchange_code_for_tokens(code: str) -> dict:
    """Returns dict with access_token and refresh_token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    data = resp.json()
    if "error" in data:
        raise GoogleOAuthError(data.get("error_description", "Token exchange failed"))
    return data


async def get_youtube_channel_id(access_token: str) -> str:
    """Get the user's YouTube channel ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{YOUTUBE_API_BASE}/channels",
            params={"part": "id", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    data = resp.json()
    if "error" in data:
        raise GoogleOAuthError(data["error"].get("message", "Failed to fetch channel"))

    items = data.get("items", [])
    if not items:
        raise GoogleOAuthError(
            "No YouTube channel found. Make sure your Google account has a YouTube channel."
        )
    return items[0]["id"]