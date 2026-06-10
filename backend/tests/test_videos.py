import os
import shutil
import subprocess
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import VIDEOS_DIR, AUDIO_DIR, IMAGES_DIR, PROJECTS_DIR
from backend.app.utils.download import DOWNLOAD_TASKS, tasks_lock
from backend.app.utils.storage import save_project
from backend.app.models.project import Project, Timeline, Asset

client = TestClient(app)

@pytest.fixture
def test_project_with_dummy_video():
    """Generates a real 2-second dummy video using FFmpeg and sets up a test project."""
    # Ensure directories exist
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    project_id = "test-video-project-id"
    video_id = "test-source-video-id"
    video_filename = f"{video_id}.mp4"
    video_path = VIDEOS_DIR / video_filename
    
    # Run FFmpeg to create a 2-second test video
    cmd = [
        "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg",
        "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
        "-c:v", "libx264",
        "-c:a", "aac",
        str(video_path)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except Exception as e:
        pytest.fail(f"Failed to create dummy video using FFmpeg: {e}")
        
    # Create project and save it
    project = Project(
        id=project_id,
        name="Test Video Project",
        createdAt="2026-06-10T12:00:00Z",
        updatedAt="2026-06-10T12:00:00Z",
        timeline=Timeline(),
        assets=[
            Asset(
                id=video_id,
                name="dummy_source.mp4",
                type="video",
                path=f"videos/{video_filename}",
                duration=2.0,
                resolution="1280x720",
                createdAt="2026-06-10T12:00:00Z"
            )
        ]
    )
    save_project(project)
    
    yield project_id, video_id
    
    # Cleanup files
    if video_path.exists():
        video_path.unlink()
    
    project_file = PROJECTS_DIR / f"{project_id}.json"
    if project_file.exists():
        project_file.unlink()
        
    # Clean up generated trimmed files and audio files
    for f in VIDEOS_DIR.glob("clip_*"):
        f.unlink()
    for f in IMAGES_DIR.glob("*_thumb.jpg"):
        f.unlink()
    for f in AUDIO_DIR.glob("audio_*"):
        f.unlink()

def test_download_task_not_found():
    response = client.get("/api/videos/download/non-existent-task-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Download task non-existent-task-id not found"

def test_trigger_download_validation_error():
    response = client.post("/api/videos/download", json={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "projectId": "non-existent-project-id"
    })
    assert response.status_code == 202
    data = response.json()
    assert "taskId" in data
    assert data["status"] == "pending"
    
    task_id = data["taskId"]
    status_response = client.get(f"/api/videos/download/{task_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["id"] == task_id
    
    with tasks_lock:
        if task_id in DOWNLOAD_TASKS:
            del DOWNLOAD_TASKS[task_id]

def test_trim_video_endpoint(test_project_with_dummy_video):
    project_id, video_id = test_project_with_dummy_video
    
    # Trim 1.0 second from dummy video (duration 2s)
    response = client.post("/api/videos/trim", json={
        "projectId": project_id,
        "assetId": video_id,
        "start": 0.5,
        "duration": 1.0
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "video"
    assert "trimmed" in data["name"].lower()
    assert data["duration"] == pytest.approx(1.0, abs=0.1)
    
    # Check that file exists
    assert os.path.exists(VIDEOS_DIR.parent / data["path"])
    
    # Verify that asset was added to the project
    proj_response = client.get(f"/api/projects/{project_id}")
    assert proj_response.status_code == 200
    proj_data = proj_response.json()
    assert len(proj_data["assets"]) == 2
    assert proj_data["assets"][1]["id"] == data["id"]

def test_extract_audio_endpoint(test_project_with_dummy_video):
    project_id, video_id = test_project_with_dummy_video
    
    # Extract audio as mp3
    response = client.post("/api/videos/extract-audio", json={
        "projectId": project_id,
        "assetId": video_id,
        "format": "mp3"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "audio"
    assert data["name"].endswith(".mp3")
    assert data["duration"] == pytest.approx(2.0, abs=0.1)
    
    # Check that file exists
    assert os.path.exists(VIDEOS_DIR.parent / data["path"])
    
    # Verify that asset was added to the project
    proj_response = client.get(f"/api/projects/{project_id}")
    assert proj_response.status_code == 200
    proj_data = proj_response.json()
    assert len(proj_data["assets"]) == 2
    assert proj_data["assets"][1]["id"] == data["id"]
