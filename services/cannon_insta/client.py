"""
Reels/client.py

Thin async wrapper around the Instagram Graph API.
Knows how to make API calls — not when, why, or what to do with errors.

Instagram Reels upload: 3-step process
  1. POST /{ig-user-id}/media          → create container  → container_id
  2. GET  /{container-id}?fields=...   → poll status_code until FINISHED
  3. POST /{ig-user-id}/media_publish  → publish container → ig_post_id
"""
import httpx
from services.cannon_insta.config import settings


class InstagramAPIError(Exception):
    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(f"[Instagram API] {message} (code={code})")


class InstagramClient:

    def __init__(self, access_token: str):
        self.access_token = access_token
        self._base = f"{settings.GRAPH_API_BASE}/{settings.GRAPH_API_VERSION}"

    async def create_reels_container(
        self, ig_user_id: str, video_url: str, caption: str
    ) -> str:
        """Step 1 — Returns container_id."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base}/{ig_user_id}/media",
                params={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "access_token": self.access_token,
                },
            )
        self._raise_for_error(resp)
        return resp.json()["id"]

    async def get_container_status(self, container_id: str) -> str:
        """Step 2 (polling) — Returns status_code string e.g. 'FINISHED', 'ERROR'."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self._base}/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": self.access_token,
                },
            )
        self._raise_for_error(resp)
        return resp.json()["status_code"]

    async def publish_container(self, ig_user_id: str, container_id: str) -> str:
        """Step 3 — Returns ig_post_id."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base}/{ig_user_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": self.access_token,
                },
            )
        self._raise_for_error(resp)
        return resp.json()["id"]

    def _raise_for_error(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            err = response.json().get("error", {})
            raise InstagramAPIError(
                message=err.get("message", "Unknown error"),
                code=str(err.get("code")),
            )
        except (ValueError, KeyError):
            raise InstagramAPIError(
                message=f"Unexpected HTTP {response.status_code}",
                code=str(response.status_code),
            )