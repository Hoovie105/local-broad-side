"""
TikTok/service.py

Orchestrates TikTok Content Posting API flow.
All TikTok-specific errors caught here — Core never sees them.
"""
import asyncio
import httpx

from services.cannon_tiktok.client import TikTokClient, TikTokAPIError
from services.cannon_tiktok.config import settings
from services.shared.schemas import PublishPayload, PublishResult, PublishStatus, Platform

TT_MAX_TITLE_LENGTH = 2200


class TikTokService:

    async def handle(self, payload: PublishPayload) -> None:
        try:
            self._validate(payload)
            publish_id = await self._upload_and_publish(payload)
            await self._poll_until_complete(payload, publish_id)

        except _ValidationError as exc:
            await self._report_failure(payload, str(exc))

        except TikTokAPIError as exc:
            await self._report_failure(payload, exc.message)

        except Exception as exc:
            await self._report_failure(payload, f"Unexpected error: {str(exc)}")

    def _validate(self, payload: PublishPayload) -> None:
        meta = payload.video_meta
        creds = payload.platform_credentials

        if not creds.get("access_token"):
            raise _ValidationError("Missing TikTok access token.")
        if meta.duration_seconds < settings.MIN_DURATION_SECONDS:
            raise _ValidationError(
                f"Video too short ({meta.duration_seconds:.1f}s). "
                f"TikTok minimum: {settings.MIN_DURATION_SECONDS}s."
            )
        if meta.duration_seconds > settings.MAX_DURATION_SECONDS:
            raise _ValidationError(
                f"Video too long ({meta.duration_seconds:.1f}s). "
                f"TikTok maximum: {settings.MAX_DURATION_SECONDS}s."
            )
        if meta.size_bytes > settings.MAX_SIZE_BYTES:
            raise _ValidationError("Video exceeds TikTok's 287 MB size limit.")
        if len(payload.caption) > TT_MAX_TITLE_LENGTH:
            raise _ValidationError(
                f"Caption too long ({len(payload.caption)} chars). "
                f"TikTok maximum: {TT_MAX_TITLE_LENGTH}."
            )

    async def _upload_and_publish(self, payload: PublishPayload) -> str:
        creds = payload.platform_credentials
        meta = payload.video_meta

        # Client now receives app credentials for request signing
        client = TikTokClient(
            access_token=creds["access_token"],
            client_key=settings.TIKTOK_CLIENT_KEY,
            client_secret=settings.TIKTOK_CLIENT_SECRET,
        )

        # Step 1: Initialize
        session = await client.initialize_upload(file_size_bytes=meta.size_bytes)
        print(f"[TikTok] Upload initialized. publish_id: {session['publish_id']}")

        # Step 2: Transfer video
        await client.upload_video_from_url(
            upload_url=session["upload_url"],
            video_url=payload.video_url,
            file_size_bytes=meta.size_bytes,
            chunk_size=session["chunk_size"],
            total_chunks=session["total_chunks"],
        )
        print(f"[TikTok] Video transfer complete.")

        # Step 3: Publish
        publish_id = await client.publish_post(
            publish_id=session["publish_id"],
            caption=payload.caption,
        )
        print(f"[TikTok] Post published. Polling for completion...")
        return publish_id

    async def _poll_until_complete(
        self, payload: PublishPayload, publish_id: str
    ) -> None:
        client = TikTokClient(
            access_token=payload.platform_credentials["access_token"],
            client_key=settings.TIKTOK_CLIENT_KEY,
            client_secret=settings.TIKTOK_CLIENT_SECRET,
        )

        for attempt in range(settings.POLL_MAX_ATTEMPTS):
            status = await client.get_post_status(publish_id)
            print(f"[TikTok] Status: {status}")

            if status == "PUBLISH_COMPLETE":
                await self._report_success(payload, publish_id)
                return
            if status == "FAILED":
                raise TikTokAPIError(
                    message="TikTok rejected the video during processing.",
                    code="PUBLISH_FAILED",
                )

            await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)

        raise TikTokAPIError(
            message=f"Post did not complete after "
                    f"{settings.POLL_MAX_ATTEMPTS * settings.POLL_INTERVAL_SECONDS}s.",
            code="POLL_TIMEOUT",
        )

    async def _report_success(self, payload: PublishPayload, publish_id: str) -> None:
        print(f"[TikTok] Published successfully. publish_id: {publish_id}")
        await self._callback(payload.callback_url, PublishResult(
            job_id=payload.job_id,
            platform=Platform.TIKTOK,
            status=PublishStatus.PUBLISHED,
            platform_post_id=publish_id,
        ))

    async def _report_failure(self, payload: PublishPayload, error: str) -> None:
        print(f"[TikTok] Failed: {error}")
        await self._callback(payload.callback_url, PublishResult(
            job_id=payload.job_id,
            platform=Platform.TIKTOK,
            status=PublishStatus.FAILED,
            error=error,
        ))

    async def _callback(self, url: str, result: PublishResult) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.patch(url, json=result.model_dump())
            except Exception as exc:
                print(f"[TikTok] Callback failed: {exc}")


class _ValidationError(Exception):
    pass