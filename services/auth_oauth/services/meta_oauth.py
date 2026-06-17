"""
Auth/services/meta_oauth.py

Handles Meta's OAuth 2.0 flow for Instagram.
Step 1: build the authorization URL → redirect user there
Step 2: receive code from callback → exchange for short-lived token
Step 3: exchange short-lived token for long-lived token (60 days)
Step 4: fetch the user's Instagram Business Account ID
Step 5: store encrypted token in PlatformConnection
"""
import httpx
from services.auth_oauth.config import settings

GRAPH_BASE = "https://graph.facebook.com/v21.0"
AUTH_URL = "https://www.facebook.com/dialog/oauth"
TOKEN_URL = f"{GRAPH_BASE}/oauth/access_token"
LONG_LIVED_URL = f"{GRAPH_BASE}/oauth/access_token"

SCOPES = [
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
    "business_management",
]


class MetaOAuthError(Exception):
    pass


def build_authorization_url(state: str) -> str:
    """Step 1 — URL to redirect the user to Meta's consent screen."""
    scope = ",".join(SCOPES)
    return (
        f"{AUTH_URL}"
        f"?client_id={settings.META_APP_ID}"
        f"&redirect_uri={settings.META_REDIRECT_URI}"
        f"&scope={scope}"
        f"&state={state}"
        f"&response_type=code"
    )


async def exchange_code_for_token(code: str) -> str:
    """Step 2 — Exchange authorization code for a short-lived token."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            TOKEN_URL,
            params={
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "redirect_uri": settings.META_REDIRECT_URI,
                "code": code,
            },
        )
    data = resp.json()
    if "error" in data:
        raise MetaOAuthError(data["error"].get("message", "Token exchange failed"))
    return data["access_token"]


async def exchange_for_long_lived_token(short_lived_token: str) -> str:
    """Step 3 — Exchange short-lived (1hr) token for long-lived (60 days) token."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            LONG_LIVED_URL,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "fb_exchange_token": short_lived_token,
            },
        )
    data = resp.json()
    if "error" in data:
        raise MetaOAuthError(data["error"].get("message", "Long-lived token exchange failed"))
    return data["access_token"]


async def get_instagram_business_account_id(long_lived_token: str) -> str:
    """Step 4 — Get the Instagram Business Account ID linked to the user's Page."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GRAPH_BASE}/me/accounts",
            params={
                "fields": "id,name,instagram_business_account",
                "access_token": long_lived_token,
            },
        )
    data = resp.json()
    if "error" in data:
        raise MetaOAuthError(data["error"].get("message", "Failed to fetch accounts"))

    pages = data.get("data", [])
    if not pages:
        raise MetaOAuthError(
            "No Facebook Pages found. Make sure you have a Page linked to your "
            "Instagram Business or Creator account."
        )

    for page in pages:
        ig_account = page.get("instagram_business_account")
        if ig_account:
            return ig_account["id"]

    raise MetaOAuthError(
        "No Instagram Business Account linked to your Facebook Page. "
        "Make sure your Instagram account is set to Business or Creator "
        "and is linked to a Facebook Page."
    )