"""
Backend/services/auth_client.py

Core's only way to talk to Auth — over HTTP.
Never imports Auth code directly. Loose coupling preserved.
"""
import httpx
from fastapi import HTTPException
from services.keel.config import settings


class AuthClient:

    def __init__(self):
        self._base = settings.AUTH_SERVICE_URL
        self._headers = {"x-internal-key": settings.INTERNAL_API_KEY}

    async def validate_token(self, token: str) -> str:
        """
        Validates a JWT and returns user_id.
        Raises 401 if invalid.
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{self._base}/internal/validate-token",
                json={"token": token},
                headers=self._headers,
            )
        resp.raise_for_status()
        data = resp.json()

        if not data["valid"]:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")

        return data["user_id"]

    async def get_platform_credentials(self, user_id: str, platform: str) -> dict:
        """
        Returns decrypted platform credentials for a user.
        Raises 404 if the user hasn't connected that platform yet.
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{self._base}/internal/credentials/{user_id}/{platform}",
                headers=self._headers,
            )

        if resp.status_code == 404:
            raise HTTPException(
                status_code=400,
                detail=f"You haven't connected {platform} yet. "
                       f"Go to settings to connect your account."
            )

        resp.raise_for_status()
        return resp.json()