from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from uuid import uuid4
import os

from app.schemas import AnalyzeRequest, AnalyzeResponse, AnalyzeResult
from app.services.downloader import download_audio
from app.services.audio import extract_segment_to_mp3
from app.services.analysis import analyze_prosody


app = FastAPI(title="Prosody WebApp")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", DEFAULT_STORAGE_DIR))

WEIGHT_MELODY = float(os.getenv("WEIGHT_MELODY", "0.5"))
WEIGHT_FREQUENCY = float(os.getenv("WEIGHT_FREQUENCY", "0.5"))
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
            output_mp3 = job_dir / "segment.mp3"
            extract_segment_to_mp3(
                input_path=source_path,
                output_path=output_mp3,
                start_seconds=start_seconds,
                duration_seconds=SEGMENT_DURATION_SECONDS,
            )
            scores = analyze_prosody(str(output_mp3), WEIGHT_MELODY, WEIGHT_FREQUENCY)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        audio_url = f"/audio/{job_id}/segment.mp3"
        results.append(
            AnalyzeResult(
                url=item.url,
                start_minute=item.start_minute,
                end_minute=end_minute,
                melody_score=scores.melody_score,
                frequency_score=scores.frequency_score,
                combined_score=scores.combined_score,
                audio_url=audio_url,
            )
        )

    return AnalyzeResponse(results=results)
