from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GRAPH_API_VERSION: str = "v21.0"
    GRAPH_API_BASE: str = "https://graph.facebook.com"

    # Instagram Reels processing: typically 30–90s
    POLL_INTERVAL_SECONDS: int = 5
    POLL_MAX_ATTEMPTS: int = 36   # 36 × 5s = 3 min max

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()