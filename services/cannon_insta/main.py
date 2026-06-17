"""
Reels/main.py

The Instagram Reels microservice.
Runs independently on port 8001.
Accepts the standardized PublishPayload from Core, handles all Instagram quirks
internally, and reports results back to Core via callback_url.
"""
from fastapi import FastAPI, BackgroundTasks
from services.shared.schemas import PublishPayload
from services.cannon_insta.service import ReelsService

app = FastAPI(
    title="Boardside — Instagram Reels MS",
    version="0.1.0",
)


@app.post("/publish", status_code=202)
async def publish(payload: PublishPayload, background_tasks: BackgroundTasks):
    """
    Core calls this. We accept immediately and process in the background.
    Results are POSTed back to payload.callback_url when done.
    """
    background_tasks.add_task(ReelsService().handle, payload)
    return {"accepted": True, "job_id": payload.job_id}


@app.get("/health")
def health():
    return {"status": "ok", "service": "instagram-reels"}