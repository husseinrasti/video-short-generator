import os
import uuid
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
import whisper
from datetime import datetime, timezone
from backend.app.config import VIDEOS_DIR, SUBTITLES_DIR
from backend.app.utils.storage import load_project, save_project
from backend.app.models.project import SubtitleTrackItem

# Thread-safe in-memory transcription tracker
TRANSCRIPTION_TASKS: Dict[str, Dict[str, Any]] = {}
transcription_lock = threading.Lock()

# Global variable to cache the loaded Whisper model
_WHISPER_MODEL = None
model_lock = threading.Lock()

def get_whisper_model(model_name: str = "tiny") -> whisper.Whisper:
    """Loads and caches the Whisper model in a thread-safe manner."""
    global _WHISPER_MODEL
    with model_lock:
        if _WHISPER_MODEL is None:
            print(f"Loading local Whisper model '{model_name}'...")
            _WHISPER_MODEL = whisper.load_model(model_name)
            print("Whisper model loaded successfully.")
        return _WHISPER_MODEL

def update_transcription_status(task_id: str, updates: Dict[str, Any]):
    with transcription_lock:
        if task_id in TRANSCRIPTION_TASKS:
            TRANSCRIPTION_TASKS[task_id].update(updates)

def get_transcription_status(task_id: str) -> Optional[Dict[str, Any]]:
    with transcription_lock:
        return TRANSCRIPTION_TASKS.get(task_id)

def _transcribe_worker(task_id: str, project_id: str, asset_id: str):
    """Background worker for loading whisper model and transcribing."""
    try:
        project = load_project(project_id)
        if not project:
            update_transcription_status(task_id, {"status": "failed", "error": "Project not found"})
            return
            
        asset = next((a for a in project.assets if a.id == asset_id), None)
        if not asset:
            update_transcription_status(task_id, {"status": "failed", "error": f"Asset {asset_id} not found"})
            return
            
        # Resolve video/audio file path
        file_path = VIDEOS_DIR.parent / asset.path
        if not file_path.exists():
            update_transcription_status(task_id, {"status": "failed", "error": f"File not found on disk: {file_path}"})
            return
            
        update_transcription_status(task_id, {"status": "transcribing"})
        
        # Run Whisper transcription
        model = get_whisper_model("tiny")
        result = model.transcribe(str(file_path))
        
        segments = result.get("segments", [])
        
        # Convert Whisper segments into SubtitleTrackItems
        subtitles: List[SubtitleTrackItem] = []
        for seg in segments:
            start_time = float(seg.get("start", 0))
            end_time = float(seg.get("end", 0))
            duration = end_time - start_time
            if duration <= 0:
                continue
                
            sub_id = str(uuid.uuid4())
            sub_item = SubtitleTrackItem(
                id=sub_id,
                assetId=asset_id,
                name=f"Sub {seg.get('id', 0)}",
                start=start_time,
                duration=duration,
                sourceStart=start_time,
                text=seg.get("text", "").strip()
            )
            subtitles.append(sub_item)
            
        # Save transcript to subtitles folder as JSON
        transcript_filename = f"transcript_{task_id}.json"
        transcript_path = SUBTITLES_DIR / transcript_filename
        
        import json
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump({
                "projectId": project_id,
                "assetId": asset_id,
                "text": result.get("text", ""),
                "subtitles": [s.model_dump() for s in subtitles]
            }, f, indent=2, ensure_ascii=False)
            
        # Update project timeline automatically
        # For simplicity, we overwrite the subtitle track with these generated subtitles
        project = load_project(project_id)
        if project:
            project.timeline.tracks.subtitle = subtitles
            save_project(project)
            
        update_transcription_status(task_id, {
            "status": "completed",
            "progress": 100.0,
            "transcriptPath": f"subtitles/{transcript_filename}",
            "subtitlesCount": len(subtitles)
        })
        
    except Exception as e:
        print(f"Error during transcription: {e}")
        update_transcription_status(task_id, {
            "status": "failed",
            "error": str(e)
        })

def start_transcription_task(project_id: str, asset_id: str) -> str:
    """Spawns background task to transcribe video/audio via Whisper."""
    task_id = str(uuid.uuid4())
    
    with transcription_lock:
        TRANSCRIPTION_TASKS[task_id] = {
            "id": task_id,
            "projectId": project_id,
            "assetId": asset_id,
            "status": "pending",
            "progress": 0.0,
            "error": None,
            "transcriptPath": None
        }
        
    thread = threading.Thread(
        target=_transcribe_worker,
        args=(task_id, project_id, asset_id),
        daemon=True
    )
    thread.start()
    return task_id
