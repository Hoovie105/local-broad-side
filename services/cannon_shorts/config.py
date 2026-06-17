from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    YOUTUBE_API_BASE: str = "https://www.googleapis.com/youtube/v3"
    YOUTUBE_UPLOAD_BASE: str = "https://www.googleapis.com/upload/youtube/v3"

    # Resumable upload chunk size — 8MB recommended by Google
    UPLOAD_CHUNK_SIZE_BYTES: int = 8 * 1024 * 1024

    # YouTube Shorts requirements
    MAX_DURATION_SECONDS: int = 60
    MIN_DURATION_SECONDS: int = 1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()