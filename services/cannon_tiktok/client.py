"""
TikTok/client.py

Thin async wrapper around TikTok's Content Posting API v2.
Includes HMAC-SHA256 request signing required by TikTok.

Upload flow:
  1. POST /post/video/init/      → initialize upload → upload_url + publish_id
  2. PUT  {upload_url}           → stream video in chunks
  3. POST /post/video/publish/   → publish with metadata
  4. POST /post/video/status/    → poll until PUBLISH_COMPLETE
"""
import hashlib
import hmac
import httpx
import json
import secrets
import time

from services.cannon_tiktok.config import settings


class TikTokAPIError(Exception):
    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(f"[TikTok API] {message} (code={code})")


class TikTokClient:

    def __init__(self, access_token: str, client_key: str, client_secret: str):
        self.access_token = access_token
        self.client_key = client_key
        self.client_secret = client_secret

    def _make_headers(self, body: dict | None = None) -> dict:
        """
        Builds signed headers for every API request.
        TikTok requires HMAC-SHA256 signature over:
          client_key + timestamp + nonce + body_hash
        """
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        body_str = json.dumps(body, separators=(",", ":")) if body else ""
        body_hash = hashlib.sha256(body_str.encode()).hexdigest()

        sign_str = f"{self.client_key}\n{timestamp}\n{nonce}\n{body_hash}"
        signature = hmac.new(
            self.client_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Tiktok-Client-Key": self.client_key,
            "X-Tiktok-Timestamp": timestamp,
            "X-Tiktok-Nonce": nonce,
            "X-Tiktok-Signature": signature,
        }

    async def initialize_upload(self, file_size_bytes: int) -> dict:
        chunk_size = settings.UPLOAD_CHUNK_SIZE_BYTES

        # TikTok requires chunk_size * (total_chunks - 1) < file_size <= chunk_size * total_chunks
        total_chunks = -(-file_size_bytes // chunk_size)  # ceiling division

        # Enforce minimum chunk size for small files
        if file_size_bytes < chunk_size:
            chunk_size = file_size_bytes
            total_chunks = 1

        body = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size_bytes,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.TIKTOK_API_BASE}/post/publish/inbox/video/init/",
                headers=self._make_headers(body),
                json=body,
            )

        self._raise_for_error(resp)
        print(f"[TikTok] Init response: {resp.json()}")
        data = resp.json().get("data", {})
        return {
            "upload_url": data["upload_url"],
            "publish_id": data["publish_id"],
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
        }

    async def upload_video_from_url(
        self,
        upload_url: str,
        video_url: str,
        file_size_bytes: int,
        chunk_size: int,
        total_chunks: int,
    ) -> None:
        """
        Step 2 — Stream video from Core's media URL to TikTok in chunks.
        Chunk uploads go directly to TikTok's storage URL — no signing needed,
        auth is baked into the upload_url itself.
        """
        async with httpx.AsyncClient(timeout=300.0) as tt_client:
            async with httpx.AsyncClient(timeout=60.0) as media_client:
                async with media_client.stream("GET", video_url) as media_resp:
                    media_resp.raise_for_status()

                    chunk_index = 0
                    offset = 0
                    buffer = b""

                    async for raw_bytes in media_resp.aiter_bytes(chunk_size):
                        buffer += raw_bytes

                        while len(buffer) >= chunk_size and chunk_index < total_chunks - 1:
                            chunk = buffer[:chunk_size]
                            buffer = buffer[chunk_size:]
                            await self._upload_chunk(
                                tt_client, upload_url, chunk,
                                offset, file_size_bytes, chunk_index,
                            )
                            offset += len(chunk)
                            chunk_index += 1

                    if buffer:
                        await self._upload_chunk(
                            tt_client, upload_url, buffer,
                            offset, file_size_bytes, chunk_index,
                            is_last=True,
                        )

    async def _upload_chunk(
        self,
        client: httpx.AsyncClient,
        upload_url: str,
        chunk: bytes,
        offset: int,
        total_size: int,
        chunk_index: int,
        is_last: bool = False,
    ) -> None:
        end = offset + len(chunk) - 1
        resp = await client.put(
            upload_url,
            content=chunk,
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {offset}-{end}/{total_size}",
            },
        )
        if resp.status_code not in (200, 201, 206):
            self._raise_for_error(resp)

    async def publish_post(self, publish_id: str, caption: str) -> str:
        body = {
            "publish_id": publish_id,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.TIKTOK_API_BASE}/post/publish/inbox/video/publish/",
                headers=self._make_headers(body),
                json=body,
            )
        print(f"[TikTok] Publish response: {resp.status_code} {resp.text[:300]}")
        self._raise_for_error(resp)
        return publish_id

    async def get_post_status(self, publish_id: str) -> str:
        """Step 4 — Poll publish status."""
        body = {"publish_id": publish_id}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.TIKTOK_API_BASE}/post/video/status/",
                headers=self._make_headers(body),
                json=body,
            )
        self._raise_for_error(resp)
        data = resp.json().get("data", {})
        return data.get("status", "UNKNOWN")

    def _raise_for_error(self, response: httpx.Response) -> None:
        if response.status_code in (200, 201, 206):
            return
        print(f"[TikTok] HTTP {response.status_code} from {response.url}")
        print(f"[TikTok] Response body: {response.text[:500]}")
        try:
            body = response.json()
            err = body.get("error", {})
            raise TikTokAPIError(
                message=err.get("message", "Unknown TikTok API error"),
                code=str(err.get("code", response.status_code)),
            )
        except (ValueError, KeyError):
            raise TikTokAPIError(
                message=f"Unexpected HTTP {response.status_code}",
                code=str(response.status_code),
            )