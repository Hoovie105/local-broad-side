"""
Reels/service.py

Orchestrates Instagram's 3-step Reels upload.
All Instagram-specific errors are caught, translated, and reported back to Core
via callback_url. Core never sees an InstagramAPIError.

Flow:
  receive PublishPayload
    → validate Instagram-specific requirements
    → create media container
    → poll until FINISHED (or ERROR / timeout)
    → publish container
    → POST result to callback_url
"""
import asyncio
import httpx

from services.cannon_insta.client import InstagramClient, InstagramAPIError
from services.cannon_insta.config import settings
from services.shared.schemas import PublishPayload, PublishResult, PublishStatus, Platform

# Instagram Reels requirements
# https://developers.facebook.com/docs/instagram-api/reference/ig-user/media
IG_MAX_DURATION_SECONDS = 90
IG_MIN_DURATION_SECONDS = 3
IG_MAX_SIZE_BYTES = 1_000 * 1024 * 1024  # 1 GB
IG_REQUIRED_ASPECT_RATIOS = (9, 16)       # width:height must be 9:16


class ReelsService:

    async def handle(self, payload: PublishPayload) -> None:
        """
        Entry point called by the /publish route.
        All errors are caught here and reported via callback — never propagated up.
        """
        try:
            self._validate(payload)
            ig_post_id = await self._upload(payload)
            await self._report_success(payload, ig_post_id)

        except _ValidationError as exc:
            await self._report_failure(payload, str(exc))

        except InstagramAPIError as exc:
            await self._report_failure(payload, exc.message)

        except Exception as exc:
            await self._report_failure(payload, f"Unexpected error: {str(exc)}")

    # ------------------------------------------------------------------ #
    # Private                                                              #
    # ------------------------------------------------------------------ #

    def _validate(self, payload: PublishPayload) -> None:
        """Instagram-specific validation. Core does not know these rules exist."""
        meta = payload.video_meta
        creds = payload.platform_credentials

        if not creds.get("access_token"):
            raise _ValidationError("Missing Instagram access_token.")
        if not creds.get("ig_user_id"):
            raise _ValidationError("Missing Instagram ig_user_id.")

        if meta.duration_seconds < IG_MIN_DURATION_SECONDS:
            raise _ValidationError(
                f"Video too short ({meta.duration_seconds:.1f}s). "
                f"Instagram Reels minimum: {IG_MIN_DURATION_SECONDS}s."
            )
        if meta.duration_seconds > IG_MAX_DURATION_SECONDS:
            raise _ValidationError(
                f"Video too long ({meta.duration_seconds:.1f}s). "
                f"Instagram Reels maximum: {IG_MAX_DURATION_SECONDS}s."
            )
        if meta.size_bytes > IG_MAX_SIZE_BYTES:
            raise _ValidationError(
                f"Video exceeds Instagram's 1 GB size limit."
            )
        if meta.width > 0 and meta.height > 0:
            actual_ratio = meta.width / meta.height
            target_ratio = 9 / 16
            if abs(actual_ratio - target_ratio) > 0.01:  # 1% tolerance
                raise _ValidationError(
                    f"Instagram Reels requires 9:16 aspect ratio. "
                    f"Got {meta.width}×{meta.height}."
                )

    async def _upload(self, payload: PublishPayload) -> str:
        """Runs the 3-step Graph API flow. Returns the published post ID."""
        creds = payload.platform_credentials
        client = InstagramClient(access_token=creds["access_token"])
        ig_user_id = creds["ig_user_id"]

        # Step 1: Create container
        container_id = await client.create_reels_container(
            ig_user_id=ig_user_id,
            video_url=payload.video_url,
            caption=payload.caption,
        )

        # Step 2: Poll until FINISHED
        await self._wait_for_container(client, container_id)

        # Step 3: Publish
        ig_post_id = await client.publish_container(
            ig_user_id=ig_user_id,
            container_id=container_id,
        )

        return ig_post_id

    async def _wait_for_container(
        self, client: InstagramClient, container_id: str
    ) -> None:
        """
        Polls container status_code until FINISHED, ERROR, or timeout.
        Instagram processes video server-side before it can be published.
        """
        for attempt in range(settings.POLL_MAX_ATTEMPTS):
            status = await client.get_container_status(container_id)
            print(f"[Reels] Container {container_id} status: {status}")

            if status == "FINISHED":
                return
            if status == "ERROR":
                raise InstagramAPIError(
                    message="Instagram rejected the video during processing. "
                            "Check format, codec (H.264), and aspect ratio.",
                    code="CONTAINER_ERROR",
                )
            if status == "EXPIRED":
                raise InstagramAPIError(
                    message="Media container expired before publishing.",
                    code="CONTAINER_EXPIRED",
                )

            # IN_PROGRESS or other transient status — keep polling
            await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)

        raise InstagramAPIError(
            message=(
                f"Container did not finish processing after "
                f"{settings.POLL_MAX_ATTEMPTS * settings.POLL_INTERVAL_SECONDS}s."
            ),
            code="POLL_TIMEOUT",
        )

    async def _report_success(self, payload: PublishPayload, ig_post_id: str) -> None:
        result = PublishResult(
            job_id=payload.job_id,
            platform=Platform.INSTAGRAM,
            status=PublishStatus.PUBLISHED,
            platform_post_id=ig_post_id,
        )
        await self._callback(payload.callback_url, result)

    async def _report_failure(self, payload: PublishPayload, error: str) -> None:
        result = PublishResult(
            job_id=payload.job_id,
            platform=Platform.INSTAGRAM,
            status=PublishStatus.FAILED,
            error=error,
        )
        await self._callback(payload.callback_url, result)

    async def _callback(self, url: str, result: PublishResult) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.patch(url, json=result.model_dump())
            except Exception as exc:
                # Callback failed — log it, but don't re-raise.
                # The job will stay PROCESSING until it times out on Core's side.
                # TODO: retry with backoff
                print(f"[ReelsService] Callback failed: {exc}")


class _ValidationError(Exception):
    """Instagram-specific validation failure. Stays within this MS."""
    pass