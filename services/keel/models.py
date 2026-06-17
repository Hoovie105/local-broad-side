from sqlalchemy import Column, String, Float, Integer, DateTime, Enum as SAEnum, func
from services.keel.database import Base
from services.shared.schemas import Platform, PublishStatus


class PublishJob(Base):
    """
    One row per platform per upload.
    User selects Instagram + TikTok → two rows, same job_id prefix.
    """
    __tablename__ = "publish_jobs"

    # Format: "{upload_uuid}_{platform}" e.g. "abc123_instagram"
    id = Column(String, primary_key=True)

    user_id = Column(String, nullable=False, index=True)
    platform = Column(SAEnum(Platform), nullable=False)
    status = Column(SAEnum(PublishStatus), default=PublishStatus.PENDING, nullable=False)

    video_url = Column(String, nullable=False)
    caption = Column(String, nullable=False)

    # General metadata extracted by Core (not platform-specific)
    duration_seconds = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)

    # Written by the MS via callback
    platform_post_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())