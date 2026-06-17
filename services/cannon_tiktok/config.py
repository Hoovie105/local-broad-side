from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TIKTOK_API_BASE: str = "https://open.tiktokapis.com/v2"
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""

    # TikTok Content Posting API chunk size
    UPLOAD_CHUNK_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB minimum for inbox API

    # TikTok Shorts requirements
    MAX_DURATION_SECONDS: int = 60
    MIN_DURATION_SECONDS: int = 3
    MAX_SIZE_BYTES: int = 287 * 1024 * 1024  # 287 MB

    # Upload status polling
    POLL_INTERVAL_SECONDS: int = 3
    POLL_MAX_ATTEMPTS: int = 40  # 40 × 3s = 2 min max

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()