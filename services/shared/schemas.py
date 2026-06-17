"""
shared/schemas.py

The contract between Core and every platform microservice.
Neither side should break this shape without coordinating with the other.
"""
from pydantic import BaseModel
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class PublishStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


class VideoMeta(BaseModel):
    """General metadata Core extracts. MSes use this for platform-specific validation."""
    duration_seconds: float
    width: int
    height: int
    size_bytes: int
    codec: str
    format: str


class PublishPayload(BaseModel):
    """
    What Core sends to every platform MS. Every MS must accept this shape.
    Platform-specific quirks are the MS's problem — not Core's.
    """
    job_id: str
    video_url: str              # Publicly accessible URL. Instagram fetches from here directly.
    caption: str
    video_meta: VideoMeta
    platform_credentials: dict  # {access_token, user_id, ...} — platform-specific keys
    callback_url: str           # Core endpoint the MS calls when done (success or failure)


class PublishResult(BaseModel):
    """
    What every MS reports back to Core via callback_url.
    Core only sees this shape — never sees platform-specific error types.
    """
    job_id: str
    platform: Platform
    status: PublishStatus
    platform_post_id: Optional[str] = None
    error: Optional[str] = None  # human-readable, safe to surface to the user