from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str
    MEDIA_DIR: str = "./media"
    MEDIA_BASE_URL: str = "http://localhost:8000"
    INSTAGRAM_SERVICE_URL: str = "http://localhost:8001"
    YOUTUBE_SERVICE_URL: str = "http://localhost:8003"
    TIKTOK_SERVICE_URL: str = "http://localhost:8004"
    AUTH_SERVICE_URL: str = "http://localhost:8002"
    CORE_CALLBACK_URL: str = "http://localhost:8000"
    INTERNAL_API_KEY: str
    MAX_VIDEO_SIZE_MB: int = 500
    ALLOWED_CONTENT_TYPES: List[str] = [
        "video/mp4",
        "video/quicktime",
        "video/x-m4v",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()