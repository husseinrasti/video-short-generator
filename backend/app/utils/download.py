import os
import uuid
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp
from datetime import datetime, timezone
from backend.app.config import VIDEOS_DIR, IMAGES_DIR
from backend.app.utils.ffmpeg import get_video_metadata, extract_thumbnail
from backend.app.utils.storage import load_project, save_project
from backend.app.models.project import Asset

# Thread-safe in-memory task tracker
DOWNLOAD_TASKS: Dict[str, Dict[str, Any]] = {}
tasks_lock = threading.Lock()

def update_task_status(task_id: str, updates: Dict[str, Any]):
    """Safely updates progress state for a download job."""
    with tasks_lock:
        if task_id in DOWNLOAD_TASKS:
            DOWNLOAD_TASKS[task_id].update(updates)

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Safely reads the status of a download job."""
    with tasks_lock:
        return DOWNLOAD_TASKS.get(task_id)

def _download_worker(task_id: str, url: str, project_id: str):
    """Background worker thread function for running yt-dlp."""
    asset_id = str(uuid.uuid4())
    temp_filename_tmpl = f"{asset_id}.%(ext)s"
    output_tmpl = str(VIDEOS_DIR / temp_filename_tmpl)

    def progress_hook(d):
        with tasks_lock:
            task = DOWNLOAD_TASKS.get(task_id)
            if task and task.get("status") == "cancelled":
                raise ValueError("Download task cancelled by user")

        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                progress = round((downloaded / total) * 100, 1)
                update_task_status(task_id, {
                    "progress": progress,
                    "status": "downloading"
                })
        elif d['status'] == 'finished':
            update_task_status(task_id, {
                "progress": 100.0,
                "status": "processing"
            })

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_tmpl,
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_hook],
        'nocheckcertificate': True,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        # Check if project exists first
        project = load_project(project_id)
        if not project:
            update_task_status(task_id, {
                "status": "failed",
                "error": f"Project {project_id} not found."
            })
            return

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First extract metadata to get exact title or filename
            info = ydl.extract_info(url, download=True)
            
            # Check if task was cancelled during download
            with tasks_lock:
                task = DOWNLOAD_TASKS.get(task_id)
                if task and task.get("status") == "cancelled":
                    return

            # Find the actual downloaded file name (it should end with .mp4 because of format/merge rules)
            filename = f"{asset_id}.mp4"
            downloaded_file_path = VIDEOS_DIR / filename

            # Fallback if yt-dlp saved it under another extension or failed merging
            if not downloaded_file_path.exists():
                # Search if asset_id.* file exists
                possible_files = list(VIDEOS_DIR.glob(f"{asset_id}.*"))
                if possible_files:
                    downloaded_file_path = possible_files[0]
                    filename = downloaded_file_path.name
                else:
                    raise FileNotFoundError("yt-dlp did not produce the expected output file.")

            # Query video metadata
            metadata = get_video_metadata(str(downloaded_file_path))
            duration = metadata["duration"]
            resolution = f"{metadata['width']}x{metadata['height']}"

            # Extract thumbnail
            thumbnail_name = f"{asset_id}_thumb.jpg"
            thumbnail_path = IMAGES_DIR / thumbnail_name
            extract_thumbnail(str(downloaded_file_path), str(thumbnail_path), timestamp=min(1.0, duration / 2))

            # Create asset object
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            new_asset = Asset(
                id=asset_id,
                name=info.get("title", f"Imported Video {asset_id[:8]}"),
                type="video",
                path=f"videos/{filename}",
                duration=duration,
                resolution=resolution,
                createdAt=timestamp
            )

            # Reload project to ensure we do not overwrite concurrent edits, add asset, and save
            project = load_project(project_id)
            if project:
                project.assets.append(new_asset)
                # Auto-append to timeline if timeline is empty (optional convenience for user)
                # But standard is to just put it in asset library. Let's just add it to assets.
                save_project(project)

            update_task_status(task_id, {
                "status": "completed",
                "progress": 100.0,
                "asset": new_asset.model_dump()
            })

    except Exception as e:
        print(f"Error downloading video from {url}: {e}")
        with tasks_lock:
            task = DOWNLOAD_TASKS.get(task_id)
            if task and task.get("status") == "cancelled":
                return
        update_task_status(task_id, {
            "status": "failed",
            "error": str(e)
        })

def start_download_task(url: str, project_id: str) -> str:
    """Spawns a background worker thread to download a video."""
    task_id = str(uuid.uuid4())
    
    with tasks_lock:
        DOWNLOAD_TASKS[task_id] = {
            "id": task_id,
            "url": url,
            "projectId": project_id,
            "status": "pending",
            "progress": 0.0,
            "error": None,
            "asset": None
        }

    thread = threading.Thread(
        target=_download_worker,
        args=(task_id, url, project_id),
        daemon=True
    )
    thread.start()
    return task_id
