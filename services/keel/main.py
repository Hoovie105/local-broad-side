# TODO: set proper origins for prod
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from services.keel.config import settings
from services.keel.database import Base, engine
from services.keel.api.v1.publish import router as publish_router
from services.keel.api.v1.jobs import router as jobs_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Boardside — Core",
    version="0.1.0",
    description="Central orchestration layer. All data flows through here.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # TODO: set proper origins for prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded videos so platform MSes can fetch them by URL.
# Prod: replace with S3 + set MEDIA_BASE_URL to your CDN.
media_dir = Path(settings.MEDIA_DIR)
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

app.include_router(publish_router, prefix="/api/v1", tags=["Publish"])
app.include_router(jobs_router, prefix="/api/v1", tags=["Jobs"])


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "core"}