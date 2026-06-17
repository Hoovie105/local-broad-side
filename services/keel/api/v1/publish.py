"""
api/v1/publish.py

Credentials are no longer accepted in the request body.
Core calls Auth to validate the JWT and fetch platform credentials.
The frontend only sends: video, caption, platforms.
"""
import uuid
from typing import Annotated, List

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.keel.database import get_db
from services.keel.models import PublishJob
from services.keel.services.dispatcher import Dispatcher
from services.keel.services.video import VideoProcessor
from services.keel.services.auth_client import AuthClient
from services.shared.schemas import Platform, PublishStatus

router = APIRouter()


class PublishResponse(BaseModel):
    job_id: str
    status: PublishStatus
    message: str


async def get_current_user_id(request: Request) -> str:
    """Extract and validate JWT from Authorization header via Auth service."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token.")

    token = auth_header.split(" ")[1]
    return await AuthClient().validate_token(token)


@router.post("/publish", response_model=PublishResponse, status_code=202)
async def publish_video(
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    video: UploadFile = File(...),
    caption: str = Form(...),
    user_id: str = Depends(get_current_user_id),
    # Accept as raw strings then parse — fixes single-platform form submission
    platforms: List[str] = Form(...),
):
    # Parse and deduplicate platforms
    parsed_platforms: list[Platform] = []
    for p in platforms:
        try:
            parsed_platforms.append(Platform(p.strip().lower()))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Unsupported platform: {p}")

    parsed_platforms = list(dict.fromkeys(parsed_platforms))  # deduplicate, preserve order

    if not parsed_platforms:
        raise HTTPException(status_code=422, detail="Select at least one platform.")

    print(f"[Publish] user={user_id} platforms={[p.value for p in parsed_platforms]}")

    # 1. General video processing
    processor = VideoProcessor()
    video_url, video_meta = await processor.process(video)

    # 2. Fetch credentials for each platform from Auth
    auth_client = AuthClient()
    platform_credentials = {}

    for platform in parsed_platforms:
        creds = await auth_client.get_platform_credentials(user_id, platform.value)
        # Use a generic key structure — each MS knows what it needs
        platform_credentials[platform.value] = {
            "access_token": creds["access_token"],
            "platform_user_id": creds["platform_user_id"],
            # Keep ig_user_id alias for Instagram MS backwards compat
            "ig_user_id": creds["platform_user_id"],
        }
        print(f"[Publish] credentials fetched for {platform.value}")

    # 3. One job row per platform
    job_id = str(uuid.uuid4())

    for platform in parsed_platforms:
        job = PublishJob(
            id=f"{job_id}_{platform.value}",
            user_id=user_id,
            platform=platform,
            status=PublishStatus.PENDING,
            video_url=video_url,
            caption=caption,
            duration_seconds=video_meta.duration_seconds,
            width=video_meta.width,
            height=video_meta.height,
            size_bytes=video_meta.size_bytes,
        )
        db.add(job)

    db.commit()
    print(f"[Publish] job_id={job_id} created for {[p.value for p in parsed_platforms]}")

    # 4. Fan out in the background
    background_tasks.add_task(
        Dispatcher().fan_out,
        job_id=job_id,
        video_url=video_url,
        video_meta=video_meta,
        caption=caption,
        platforms=parsed_platforms,
        platform_credentials=platform_credentials,
    )

    return PublishResponse(
        job_id=job_id,
        status=PublishStatus.PENDING,
        message="Video accepted. Publishing in progress.",
    )