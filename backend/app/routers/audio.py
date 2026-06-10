from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from backend.app.utils.whisper_transcribe import start_transcription_task, get_transcription_status
from backend.app.utils.ffmpeg import detect_silence
from backend.app.config import STORAGE_DIR
from backend.app.utils.storage import load_project

router = APIRouter(prefix="/api/audio", tags=["audio"])

class TranscribeRequest(BaseModel):
    projectId: str
    assetId: str

class TranscribeResponse(BaseModel):
    taskId: str
    status: str

class SilenceDetectRequest(BaseModel):
    projectId: str
    assetId: str
    noiseThreshold: float = -30.0
    minDuration: float = 0.5

class SilenceSegment(BaseModel):
    start: float
    end: float
    duration: float

@router.post("/transcribe", response_model=TranscribeResponse, status_code=status.HTTP_202_ACCEPTED)
def transcribe_video_asset(request: TranscribeRequest):
    """Triggers a background Whisper speech-to-text transcription task for a video asset."""
    try:
        task_id = start_transcription_task(request.projectId, request.assetId)
        return TranscribeResponse(taskId=task_id, status="pending")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start transcription task: {e}"
        )

@router.get("/transcribe/{task_id}")
def check_transcription_status(task_id: str):
    """Polls the status of a Whisper transcription task."""
    task = get_transcription_status(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription task {task_id} not found"
        )
    return task

@router.post("/detect-silence", response_model=List[SilenceSegment])
def detect_audio_silence(request: SilenceDetectRequest):
    """Detects silences in a video or audio asset's soundtrack."""
    project = load_project(request.projectId)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.projectId} not found"
        )
        
    asset = next((a for a in project.assets if a.id == request.assetId), None)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {request.assetId} not found in project"
        )
        
    file_path = STORAGE_DIR / asset.path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset file not found on disk at {file_path}"
        )
        
    try:
        silences = detect_silence(str(file_path), request.noiseThreshold, request.minDuration)
        return [
            SilenceSegment(
                start=s["start"],
                end=s["end"],
                duration=s["duration"]
            )
            for s in silences
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Silence detection failed: {e}"
        )

