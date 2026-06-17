import asyncio
import httpx

from services.keel.config import settings
from services.shared.schemas import Platform, PublishPayload, VideoMeta

PLATFORM_URLS: dict[Platform, str] = {
    Platform.INSTAGRAM: settings.INSTAGRAM_SERVICE_URL,
    Platform.YOUTUBE: settings.YOUTUBE_SERVICE_URL,
    Platform.TIKTOK: settings.TIKTOK_SERVICE_URL,
}


class Dispatcher:

    async def fan_out(
        self,
        job_id: str,
        video_url: str,
        video_meta: VideoMeta,
        caption: str,
        platforms: list[Platform],
        platform_credentials: dict,
    ) -> None:
        tasks = [
            self._dispatch(
                platform=platform,
                payload=PublishPayload(
                    job_id=job_id,
                    video_url=video_url,
                    caption=caption,
                    video_meta=video_meta,
                    platform_credentials=platform_credentials.get(platform.value, {}),
                    callback_url=(
                        f"{settings.CORE_CALLBACK_URL}/api/v1/jobs/{job_id}/status"
                        f"?platform={platform.value}"
                    ),
                ),
            )
            for platform in platforms
            if platform in PLATFORM_URLS
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _dispatch(self, platform: Platform, payload: PublishPayload) -> None:
        url = f"{PLATFORM_URLS[platform]}/publish"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload.model_dump())
                response.raise_for_status()
            except httpx.RequestError as exc:
                print(f"[Dispatcher] Could not reach {platform.value} MS: {exc}")
            except httpx.HTTPStatusError as exc:
                print(f"[Dispatcher] {platform.value} MS returned {exc.response.status_code}")