"""
YouTube/client.py

Thin async wrapper around the YouTube Data API v3.
Handles resumable uploads — required for any video over 5MB.

YouTube Shorts upload flow:
  1. POST /videos?uploadType=resumable  → get upload session URI
  2. PUT  {session_uri}                 → stream video in chunks
  3. Video metadata (title, description, tags) sent in step 1

YouTube auto-classifies as a Short if:
  - Duration ≤ 60 seconds
  - Aspect ratio is vertical (9:16)
  - Title optionally contains #Shorts (helps discovery but not required)
"""
import httpx
from services.cannon_shorts.config import settings


class YouTubeAPIError(Exception):
    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(f"[YouTube API] {message} (code={code})")


class YouTubeClient:

    def __init__(self, access_token: str):
        self.access_token = access_token
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def create_upload_session(
        self,
        title: str,
        description: str,
        file_size_bytes: int,
    ) -> str:
        """
        Step 1 — Initiates a resumable upload session.
        Returns the upload session URI to stream video to.
        """
        metadata = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["Shorts"],
                "categoryId": "22",  # People & Blogs — safe default
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.YOUTUBE_UPLOAD_BASE}/videos",
                params={
                    "uploadType": "resumable",
                    "part": "snippet,status",
                },
                headers={
                    **self._headers,
                    "X-Upload-Content-Type": "video/mp4",
                    "X-Upload-Content-Length": str(file_size_bytes),
                },
                json=metadata,
            )

        self._raise_for_error(resp)

        # Google returns the session URI in the Location header
        session_uri = resp.headers.get("Location")
        if not session_uri:
            raise YouTubeAPIError(
                message="No upload session URI returned.",
                code="NO_SESSION_URI",
            )
        return session_uri

    async def upload_video_from_url(
        self,
        session_uri: str,
        video_url: str,
        file_size_bytes: int,
    ) -> str:
        """
        Step 2 — Streams video from Core's media URL to YouTube in chunks.
        Returns the YouTube video ID on completion.

        Fetches the video from video_url and forwards it to YouTube
        in UPLOAD_CHUNK_SIZE_BYTES chunks — avoids loading the full
        video into memory.
        """
        chunk_size = settings.UPLOAD_CHUNK_SIZE_BYTES
        offset = 0

        async with httpx.AsyncClient(timeout=300.0) as yt_client:
            # Stream the video from Core's media endpoint
            async with httpx.AsyncClient(timeout=60.0) as media_client:
                async with media_client.stream("GET", video_url) as media_resp:
                    media_resp.raise_for_status()

                    buffer = b""
                    async for raw_chunk in media_resp.aiter_bytes(chunk_size):
                        buffer += raw_chunk

                        # Only upload when we have a full chunk or it's the last one
                        while len(buffer) >= chunk_size:
                            chunk = buffer[:chunk_size]
                            buffer = buffer[chunk_size:]
                            offset = await self._upload_chunk(
                                yt_client, session_uri, chunk,
                                offset, file_size_bytes, is_last=False
                            )

                    # Upload remaining bytes as the final chunk
                    if buffer:
                        resp = await self._upload_final_chunk(
                            yt_client, session_uri, buffer,
                            offset, file_size_bytes
                        )
                        return self._extract_video_id(resp)

        raise YouTubeAPIError("Upload completed without a final response.", "UPLOAD_INCOMPLETE")

    async def _upload_chunk(
        self,
        client: httpx.AsyncClient,
        session_uri: str,
        chunk: bytes,
        offset: int,
        total_size: int,
        is_last: bool,
    ) -> int:
        end = offset + len(chunk) - 1
        content_range = (
            f"bytes {offset}-{end}/{total_size}"
            if is_last
            else f"bytes {offset}-{end}/*"
        )

        resp = await client.put(
            session_uri,
            content=chunk,
            headers={
                "Content-Length": str(len(chunk)),
                "Content-Range": content_range,
            },
        )

        # 308 Resume Incomplete — chunk accepted, keep going
        if resp.status_code == 308:
            return offset + len(chunk)

        self._raise_for_error(resp)
        return offset + len(chunk)

    async def _upload_final_chunk(
        self,
        client: httpx.AsyncClient,
        session_uri: str,
        chunk: bytes,
        offset: int,
        total_size: int,
    ) -> httpx.Response:
        end = offset + len(chunk) - 1
        resp = await client.put(
            session_uri,
            content=chunk,
            headers={
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {offset}-{end}/{total_size}",
            },
        )
        self._raise_for_error(resp)
        return resp

    def _extract_video_id(self, resp: httpx.Response) -> str:
        data = resp.json()
        video_id = data.get("id")
        if not video_id:
            raise YouTubeAPIError("No video ID in upload response.", "NO_VIDEO_ID")
        return video_id

    def _raise_for_error(self, response: httpx.Response) -> None:
        if response.status_code in (200, 201, 308):
            return
        try:
            err = response.json().get("error", {})
            errors = err.get("errors", [{}])
            reason = errors[0].get("reason", "unknown") if errors else "unknown"
            raise YouTubeAPIError(
                message=err.get("message", "Unknown error"),
                code=reason,
            )
        except (ValueError, KeyError):
            raise YouTubeAPIError(
                message=f"Unexpected HTTP {response.status_code}",
                code=str(response.status_code),
            )