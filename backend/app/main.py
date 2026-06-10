from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .schemas import AnalysisResponse
from .services import analyze_audio_file, validate_audio_filename


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chord-detector")

app = FastAPI(title="Chord Detector API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "null",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health")
async def api_healthcheck() -> dict[str, str]:
    return {"status": "ok"}


async def _analyze_uploaded_file(file: UploadFile) -> AnalysisResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    try:
        validate_audio_filename(file.filename)
        content = await file.read()
        result = analyze_audio_file(content, file.filename)
        return AnalysisResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Backend dependency or audio decoding error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Audio analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Audio analysis failed. Check that FFmpeg is installed and try a shorter WAV/MP3 file first.",
        ) from exc


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...)) -> AnalysisResponse:
    return await _analyze_uploaded_file(file)


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_api(file: UploadFile = File(...)) -> AnalysisResponse:
    return await _analyze_uploaded_file(file)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        requested_file = FRONTEND_DIST / full_path
        if full_path and requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(FRONTEND_DIST / "index.html")
