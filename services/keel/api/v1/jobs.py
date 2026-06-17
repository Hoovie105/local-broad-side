"""
api/v1/jobs.py

GET  /jobs/{job_id}          — frontend polls for publish status
PATCH /jobs/{job_id}/status  — MSes call this when done (internal callback)
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.keel.database import get_db
from services.keel.models import PublishJob
from services.shared.schemas import Platform, PublishStatus

router = APIRouter()


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str, db: Annotated[Session, Depends(get_db)]):
    """
    Returns publish status for all platforms on a given upload.
    Poll until all statuses are terminal: published | failed.
    """
    jobs = db.query(PublishJob).filter(PublishJob.id.like(f"{job_id}_%")).all()

    if not jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "job_id": job_id,
        "platforms": [
            {
                "platform": job.platform,
                "status": job.status,
                "platform_post_id": job.platform_post_id,
                "error": job.error_message,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
            for job in jobs
        ],
    }


class StatusUpdate(BaseModel):
    status: PublishStatus
    platform_post_id: str | None = None
    error: str | None = None


@router.patch("/jobs/{job_id}/status")
def update_job_status(
    job_id: str,
    platform: Annotated[Platform, Query(...)],
    update: StatusUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Internal — only platform MSes should call this via their callback_url.
    TODO: protect with shared internal secret before production.
    """
    job = db.query(PublishJob).filter_by(id=f"{job_id}_{platform.value}").first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    job.status = update.status
    job.platform_post_id = update.platform_post_id
    job.error_message = update.error
    db.commit()

    return {"ok": True}