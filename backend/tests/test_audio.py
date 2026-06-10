import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import VIDEOS_DIR, PROJECTS_DIR, SUBTITLES_DIR
from backend.app.utils.storage import save_project
from backend.app.utils.whisper_transcribe import TRANSCRIPTION_TASKS, transcription_lock
from backend.app.models.project import Project, Timeline, Asset

client = TestClient(app)

@pytest.fixture
def test_project_with_video():
    """Sets up a test project and dummy files for transcription testing."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)
    
    project_id = "test-transcribe-project-id"
    video_id = "test-transcribe-video-id"
    video_filename = f"{video_id}.mp4"
    video_path = VIDEOS_DIR / video_filename
    
    # Touch dummy video file
    with open(video_path, "w") as f:
        f.write("dummy video data")
        
    project = Project(
        id=project_id,
        name="Test Transcribe Project",
        createdAt="2026-06-10T12:00:00Z",
        updatedAt="2026-06-10T12:00:00Z",
        timeline=Timeline(),
        assets=[
            Asset(
                id=video_id,
                name="test_video.mp4",
                type="video",
                path=f"videos/{video_filename}",
                duration=10.0,
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
        
    # Clean up generated transcripts
    for f in SUBTITLES_DIR.glob("transcript_*"):
        f.unlink()

def test_transcribe_task_not_found():
    response = client.get("/api/audio/transcribe/non-existent-task")
    assert response.status_code == 404

@patch("backend.app.utils.whisper_transcribe.get_whisper_model")
def test_transcription_success(mock_get_model, test_project_with_video):
    project_id, video_id = test_project_with_video
    
    # Mock Whisper model behavior
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "text": "Hello world welcome back",
        "segments": [
            {"id": 0, "start": 0.0, "end": 2.0, "text": "Hello world"},
            {"id": 1, "start": 2.0, "end": 5.0, "text": "welcome back"}
        ]
    }
    mock_get_model.return_value = mock_model
    
    # Trigger transcription
    response = client.post("/api/audio/transcribe", json={
        "projectId": project_id,
        "assetId": video_id
      })
    
    assert response.status_code == 202
    task_id = response.json()["taskId"]
    
    # Wait for thread to finish
    import time
    completed = False
    for _ in range(10):
        status_response = client.get(f"/api/audio/transcribe/{task_id}")
        status_data = status_response.json()
        if status_data["status"] == "completed":
            completed = True
            assert status_data["subtitlesCount"] == 2
            assert "transcript_" in status_data["transcriptPath"]
            break
        elif status_data["status"] == "failed":
            pytest.fail(f"Transcription failed: {status_data['error']}")
        time.sleep(0.1)
        
    assert completed
    
    # Verify subtitles are stored in project timeline
    proj_response = client.get(f"/api/projects/{project_id}")
    proj_data = proj_response.json()
    subs = proj_data["timeline"]["tracks"]["subtitle"]
    assert len(subs) == 2
    assert subs[0]["text"] == "Hello world"
    assert subs[0]["start"] == 0.0
    assert subs[0]["duration"] == 2.0
    assert subs[1]["text"] == "welcome back"
    
    with transcription_lock:
        if task_id in TRANSCRIPTION_TASKS:
            del TRANSCRIPTION_TASKS[task_id]

@patch("backend.app.routers.audio.detect_silence")
def test_detect_silence_endpoint(mock_detect_silence, test_project_with_video):
    project_id, video_id = test_project_with_video
    
    mock_detect_silence.return_value = [
        {"start": 1.0, "end": 3.0, "duration": 2.0},
        {"start": 6.0, "end": 6.5, "duration": 0.5}
    ]
    
    response = client.post("/api/audio/detect-silence", json={
        "projectId": project_id,
        "assetId": video_id,
        "noiseThreshold": -35.0,
        "minDuration": 0.5
    })
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["start"] == 1.0
    assert data[0]["end"] == 3.0
    assert data[0]["duration"] == 2.0

