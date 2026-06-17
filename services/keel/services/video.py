"""
services/video.py

Core's responsibility is narrow:
  1. Reject clearly invalid files (wrong type, too large)
  2. Extract general metadata (duration, dimensions, codec)
  3. Save the file and return a URL the MSes can fetch from

Platform-specific validation (aspect ratio, max duration, codec requirements)
belongs in each MS — not here.

TODO: 1- _extract_metadata is async but uses blocking subprocess.
      2- _store be storeing info in wrong dir.
"""
import asyncio
import json
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException

from services.keel.config import settings
from services.shared.schemas import VideoMeta

import subprocess


class VideoProcessor:

    MAX_BYTES = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024

    async def process(self, file: UploadFile) -> tuple[str, VideoMeta]:
        """
        Returns (public_video_url, VideoMeta).
        Raises HTTPException on validation failure.
        """
        self._check_content_type(file.content_type)

        video_id = str(uuid.uuid4())
        stored_path = await self._store(file, video_id)
        meta = await self._extract_metadata(stored_path)
        video_url = f"{settings.MEDIA_BASE_URL}/media/{video_id}.mp4"

        return video_url, meta

    # ------------------------------------------------------------------ #

    def _check_content_type(self, content_type: str | None):
        if content_type not in settings.ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Unsupported file type: '{content_type}'. "
                    f"Accepted: {settings.ALLOWED_CONTENT_TYPES}"
                ),
            )

    async def _store(self, file: UploadFile, video_id: str) -> Path:
        """Stream upload to disk in 1 MB chunks. Enforces size limit mid-stream."""
        dest_dir = Path(settings.MEDIA_DIR)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{video_id}.mp4"

        written = 0
        with dest.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > self.MAX_BYTES:
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Video exceeds the {settings.MAX_VIDEO_SIZE_MB} MB limit.",
                    )
                out.write(chunk)

        return dest

    

    async def _extract_metadata(self, path: Path) -> VideoMeta:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams",
                    "-show_format",
                    str(path),
                ],
                capture_output=True,
                text=True,
            )
            print(f"[ffprobe] returncode: {result.returncode}")
            print(f"[ffprobe] stdout: {result.stdout[:200]}")
            print(f"[ffprobe] stderr: {result.stderr[:200]}")

            data = json.loads(result.stdout)
            video_stream = next(
                (s for s in data["streams"] if s.get("codec_type") == "video"), {}
            )
            fmt = data.get("format", {})

            return VideoMeta(
                duration_seconds=float(fmt.get("duration", 0)),
                width=int(video_stream.get("width", 0)),
                height=int(video_stream.get("height", 0)),
                size_bytes=int(fmt.get("size", path.stat().st_size)),
                codec=video_stream.get("codec_name", "unknown"),
                format=fmt.get("format_name", "unknown"),
            )

        except Exception as e:
            print(f"[ffprobe] FAILED: {e}")
            return VideoMeta(
                duration_seconds=0,
                width=0,
                height=0,
                size_bytes=path.stat().st_size,
                codec="unknown",
                format="unknown",
            )