"""
Main service entrypoint for the Auth.
Keel does not know much about how Auth works,
it simply requests a authentication Auth handles the rest.
"""
# TODO: set proper origins for prod

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.auth_oauth.database import Base, engine
from services.auth_oauth.routers.users import router as users_router
from services.auth_oauth.routers.oauth import router as oauth_router
from services.auth_oauth.routers.youtube_oauth import router as youtube_oauth_router
from services.auth_oauth.routers.internal import router as internal_router
from services.auth_oauth.routers.tiktok_oauth import router as tiktok_oauth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Boardside — Auth Service",
    version="0.1.0",
    description="User accounts, JWT sessions, and platform OAuth flows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, # TODO: set proper origins for prod
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(oauth_router)
app.include_router(youtube_oauth_router)
app.include_router(tiktok_oauth_router)
app.include_router(internal_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "auth"}