"""
YouTube/service.py

Orchestrates YouTube Shorts upload.
All YouTube-specific errors caught here — Core never sees them.

Flow:
  receive PublishPayload
    → validate YouTube Shorts requirements
    → create resumable upload session
    → stream video to YouTube
    → POST result to callback_url
"""
import httpx

from services.cannon_shorts.client import YouTubeClient, YouTubeAPIError
from services.cannon_shorts.config import settings
from services.shared.schemas import PublishPayload, PublishResult, PublishStatus, Platform

# YouTube Shorts requirements
YT_MAX_DURATION = settings.MAX_DURATION_SECONDS
YT_MIN_DURATION = settings.MIN_DURATION_SECONDS
YT_MAX_SIZE_BYTES = 256 * 1024 * 1024  # 256 MB for Shorts
YT_MAX_TITLE_LENGTH = 100


class YouTubeService:

    async def handle(self, payload: PublishPayload) -> None:
        try:
            self._validate(payload)
            video_id = await self._upload(payload)
            await self._report_success(payload, video_id)

        except _ValidationError as exc:
            await self._report_failure(payload, str(exc))

        except YouTubeAPIError as exc:
            await self._report_failure(payload, exc.message)

        except Exception as exc:
            await self._report_failure(payload, f"Unexpected error: {str(exc)}")

    # ------------------------------------------------------------------ #

    def _validate(self, payload: PublishPayload) -> None:
        meta = payload.video_meta
        creds = payload.platform_credentials

        if not creds.get("access_token"):
            raise _ValidationError("Missing YouTube access token.")

        if meta.duration_seconds < YT_MIN_DURATION:
            raise _ValidationError(
                f"Video too short ({meta.duration_seconds:.1f}s). "
                f"Minimum: {YT_MIN_DURATION}s."
            )
        if meta.duration_seconds > YT_MAX_DURATION:
            raise _ValidationError(
                f"Video too long ({meta.duration_seconds:.1f}s). "
                f"YouTube Shorts maximum: {YT_MAX_DURATION}s."
            )
        if meta.size_bytes > YT_MAX_SIZE_BYTES:
            raise _ValidationError(
                f"Video exceeds YouTube Shorts 256 MB size limit."
            )
        if len(payload.caption) > YT_MAX_TITLE_LENGTH:
            raise _ValidationError(
                f"Caption too long ({len(payload.caption)} chars). "
                f"YouTube title maximum: {YT_MAX_TITLE_LENGTH} chars."
            )

    async def _upload(self, payload: PublishPayload) -> str:
        creds = payload.platform_credentials
        client = YouTubeClient(access_token=creds["access_token"])

        # Append #Shorts to help YouTube classify it — doesn't affect length limit
        title = payload.caption
        if "#Shorts" not in title and "#shorts" not in title:
            title = f"{title} #Shorts"

        # Trim to YouTube's 100 char title limit after appending
        title = title[:YT_MAX_TITLE_LENGTH]

        session_uri = await client.create_upload_session(
            title=title,
            description=payload.caption,
            file_size_bytes=payload.video_meta.size_bytes,
        )

        video_id = await client.upload_video_from_url(
            session_uri=session_uri,
            video_url=payload.video_url,
            file_size_bytes=payload.video_meta.size_bytes,
        )

        print(f"[YouTube] Uploaded successfully. Video ID: {video_id}")
        return video_id

    async def _report_success(self, payload: PublishPayload, video_id: str) -> None:
        result = PublishResult(
            job_id=payload.job_id,
            platform=Platform.YOUTUBE,
            status=PublishStatus.PUBLISHED,
            platform_post_id=video_id,
        )
        await self._callback(payload.callback_url, result)

    async def _report_failure(self, payload: PublishPayload, error: str) -> None:
        print(f"[YouTube] Failed: {error}")
        result = PublishResult(
            job_id=payload.job_id,
            platform=Platform.YOUTUBE,
            status=PublishStatus.FAILED,
            error=error,
        )
        await self._callback(payload.callback_url, result)

    async def _callback(self, url: str, result: PublishResult) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.patch(url, json=result.model_dump())
            except Exception as exc:
                print(f"[YouTube] Callback failed: {exc}")


class _ValidationError(Exception):
    pass