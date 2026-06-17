from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Shared DB — same URL as Backend, different connection pool
    DATABASE_URL: str = "sqlite:///./boardside.db"

    # JWT — no expiry for MVP, add timeout logic later
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    # Meta OAuth
    META_APP_ID: str
    META_APP_SECRET: str
    META_REDIRECT_URI: str = "http://localhost:8002/auth/instagram/callback"

    # Google / YouTube
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8002/auth/youtube/callback"

    # TokTok
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_REDIRECT_URI: str = ""

    # Where Auth redirects the user after connecting a platform
    FRONTEND_SUCCESS_URL: str
    FRONTEND_ERROR_URL: str = "http://localhost:3000/connect-error"
    INTERNAL_API_KEY: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()