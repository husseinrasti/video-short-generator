from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from pathlib import Path
from backend.app.config import VIDEOS_DIR, AUDIO_DIR, IMAGES_DIR
from backend.app.utils.download import start_download_task, get_task_status
from backend.app.utils.storage import load_project, save_project
from backend.app.utils.ffmpeg import trim_video, extract_audio, get_video_metadata, extract_thumbnail
from backend.app.models.project import Asset

router = APIRouter(prefix="/api/videos", tags=["videos"])

class DownloadRequest(BaseModel):
    url: str
    projectId: str

class DownloadResponse(BaseModel):
    taskId: str
    status: str

class TrimRequest(BaseModel):
    projectId: str
    assetId: str
    start: float = Field(..., description="Start time in seconds")
    duration: float = Field(..., description="Duration of the clip in seconds")

class ExtractAudioRequest(BaseModel):
    projectId: str
    assetId: str
    format: str = Field("mp3", description="Audio format: mp3 or wav")

@router.post("/download", response_model=DownloadResponse, status_code=status.HTTP_202_ACCEPTED)
def download_video(request: DownloadRequest):
    """Triggers a background download task for the given video URL."""
    try:
        task_id = start_download_task(request.url, request.projectId)
        return DownloadResponse(taskId=task_id, status="pending")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start download task: {e}"
        )

@router.get("/download/{task_id}")
def check_download_status(task_id: str):
    """Checks the progress and status of a video download task."""
    task = get_task_status(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Download task {task_id} not found"
        )
    return task

@router.post("/download/{task_id}/cancel")
def cancel_download(task_id: str):
    """Cancels a background video download task."""
    from backend.app.utils.download import DOWNLOAD_TASKS, tasks_lock
    with tasks_lock:
        task = DOWNLOAD_TASKS.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Download task {task_id} not found"
            )
        task["status"] = "cancelled"
    return {"taskId": task_id, "status": "cancelled"}

@router.post("/trim", response_model=Asset, status_code=status.HTTP_201_CREATED)
def trim_existing_video(request: TrimRequest):
    """Cuts a clip from an existing video asset and adds it as a new asset in the project."""
    project = load_project(request.projectId)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.projectId} not found"
        )
        
    # Find the source asset
    source_asset = next((a for a in project.assets if a.id == request.assetId), None)
    if not source_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {request.assetId} not found in project"
        )
        
    if source_asset.type != "video":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source asset must be a video"
        )
        
    # Resolve source path
    # Path is relative in asset, e.g. "videos/xxx.mp4"
    source_path = VIDEOS_DIR.parent / source_asset.path
    if not source_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source video file not found on disk"
        )
        
    # Generate new clip IDs
    new_asset_id = str(uuid.uuid4())
    new_filename = f"clip_{new_asset_id}.mp4"
    output_path = VIDEOS_DIR / new_filename
    
    # Run the trim operation
    success = trim_video(str(source_path), str(output_path), request.start, request.duration)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FFmpeg failed to extract clip"
        )
        
    # Get metadata of the new clip
    metadata = get_video_metadata(str(output_path))
    new_duration = metadata["duration"]
    resolution = f"{metadata['width']}x{metadata['height']}"
    
    # Generate thumbnail
    thumbnail_name = f"{new_asset_id}_thumb.jpg"
    thumbnail_path = IMAGES_DIR / thumbnail_name
    extract_thumbnail(str(output_path), str(thumbnail_path), timestamp=0.5)
    
    # Create the new asset record
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    new_asset = Asset(
        id=new_asset_id,
        name=f"Trimmed {source_asset.name[:15]} ({request.start:.1f}s)",
        type="video",
        path=f"videos/{new_filename}",
        duration=new_duration,
        resolution=resolution,
        createdAt=timestamp
    )
    
    # Save project state
    project.assets.append(new_asset)
    save_project(project)
    
    return new_asset

@router.post("/extract-audio", response_model=Asset, status_code=status.HTTP_201_CREATED)
def extract_audio_from_video(request: ExtractAudioRequest):
    """Extracts the audio track from a video asset and saves it as an audio asset."""
    project = load_project(request.projectId)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.projectId} not found"
        )
        
    # Find the source asset
    source_asset = next((a for a in project.assets if a.id == request.assetId), None)
    if not source_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {request.assetId} not found in project"
        )
        
    if source_asset.type != "video":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source asset must be a video"
        )
        
    # Resolve source path
    source_path = VIDEOS_DIR.parent / source_asset.path
    if not source_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source video file not found on disk"
        )
        
    # Configure output format
    fmt = request.format.lower()
    if fmt not in ["mp3", "wav"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'mp3' or 'wav'"
        )
        
    new_asset_id = str(uuid.uuid4())
    new_filename = f"audio_{new_asset_id}.{fmt}"
    output_path = AUDIO_DIR / new_filename
    
    # Run audio extraction
    success = extract_audio(str(source_path), str(output_path), out_format=fmt)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FFmpeg failed to extract audio"
        )
        
    # Get audio duration
    metadata = get_video_metadata(str(output_path))
    duration = metadata["duration"]
    
    # Create the new asset record
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    new_asset = Asset(
        id=new_asset_id,
        name=f"Audio {source_asset.name[:20]}.{fmt}",
        type="audio",
        path=f"audio/{new_filename}",
        duration=duration,
        resolution=None,
        createdAt=timestamp
    )
    
    # Save project state
    project.assets.append(new_asset)
    save_project(project)
    
    return new_asset
