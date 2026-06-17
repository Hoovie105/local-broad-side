from fastapi import FastAPI, BackgroundTasks
from services.shared.schemas import PublishPayload
from services.cannon_shorts.service import YouTubeService

app = FastAPI(
    title="Boardside — YouTube Shorts MS",
    version="0.1.0",
)


@app.post("/publish", status_code=202)
async def publish(payload: PublishPayload, background_tasks: BackgroundTasks):
    background_tasks.add_task(YouTubeService().handle, payload)
    return {"accepted": True, "job_id": payload.job_id}


@app.get("/health")
def health():
    return {"status": "ok", "service": "youtube-shorts"}