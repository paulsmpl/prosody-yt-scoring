from __future__ import annotations

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from uuid import uuid4
import os

from app.schemas import AnalyzeRequest, AnalyzeResponse, AnalyzeResult
from app.services.downloader import download_audio
from app.services.audio import extract_segment_to_mp3, get_audio_duration_seconds
from app.services.analysis import analyze_prosody


app = FastAPI(title="Prosody WebApp")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", DEFAULT_STORAGE_DIR))

SEGMENT_DURATION_SECONDS = 60

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/audio", StaticFiles(directory=STORAGE_DIR), name="audio")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    results = []

    for item in request.items:
        start_seconds = item.start_minute * 60
        end_minute = item.start_minute + 1
        job_id = uuid4().hex
        job_dir = STORAGE_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            source_path = download_audio(str(item.url), job_dir)
            duration = get_audio_duration_seconds(source_path)
            if duration is not None and duration < (start_seconds + SEGMENT_DURATION_SECONDS):
                start_seconds = 0
                end_minute = 1
            output_mp3 = job_dir / "segment.mp3"
            extract_segment_to_mp3(
                input_path=source_path,
                output_path=output_mp3,
                start_seconds=start_seconds,
                duration_seconds=SEGMENT_DURATION_SECONDS,
            )
            scores = analyze_prosody(str(output_mp3))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        audio_url = f"/audio/{job_id}/segment.mp3"
        results.append(
            AnalyzeResult(
                url=item.url,
                start_minute=(0 if start_seconds == 0 else item.start_minute),
                end_minute=end_minute,
                melody_score=scores.melody_score,
                tonality_score=scores.tonality_score,
                audio_url=audio_url,
            )
        )

    return AnalyzeResponse(results=results)


@app.post("/analyze-upload", response_model=AnalyzeResponse)
async def analyze_upload(
    files: list[UploadFile] = File(...),
    start_minute: int = Form(10),
) -> AnalyzeResponse:
    if start_minute < 0 or start_minute > 600:
        raise HTTPException(status_code=400, detail="Minute invalide.")

    results = []
    for upload in files:
        job_id = uuid4().hex
        job_dir = STORAGE_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            raw_path = job_dir / f"upload_{upload.filename or 'audio'}"
            with raw_path.open("wb") as buffer:
                content = await upload.read()
                buffer.write(content)

            start_seconds = start_minute * 60
            end_minute = start_minute + 1
            duration = get_audio_duration_seconds(raw_path)
            if duration is not None and duration < (start_seconds + SEGMENT_DURATION_SECONDS):
                start_seconds = 0
                end_minute = 1
            output_mp3 = job_dir / "segment.mp3"
            extract_segment_to_mp3(
                input_path=raw_path,
                output_path=output_mp3,
                start_seconds=start_seconds,
                duration_seconds=SEGMENT_DURATION_SECONDS,
            )
            scores = analyze_prosody(str(output_mp3))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        audio_url = f"/audio/{job_id}/segment.mp3"
        results.append(
            AnalyzeResult(
                url=upload.filename or "upload",
                start_minute=(0 if start_seconds == 0 else start_minute),
                end_minute=end_minute,
                melody_score=scores.melody_score,
                tonality_score=scores.tonality_score,
                audio_url=audio_url,
            )
        )

    return AnalyzeResponse(results=results)
