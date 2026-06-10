import os
import shutil
import subprocess
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import VIDEOS_DIR, AUDIO_DIR, RENDERS_DIR, PROJECTS_DIR
from backend.app.utils.storage import save_project
from backend.app.utils.render import RENDER_TASKS, renders_lock
from backend.app.models.project import Project, Timeline, Asset, VideoTrackItem, AudioTrackItem

client = TestClient(app)

@pytest.fixture
def test_project_with_video_on_timeline():
    """Generates a dummy 2s video and inserts it on the timeline video track."""
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    
    project_id = "test-render-project-id"
    video_id = "test-src-video-id"
    video_filename = f"{video_id}.mp4"
    video_path = VIDEOS_DIR / video_filename
    
    # Create a 2-second dummy source video using FFmpeg
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
        pytest.fail(f"Failed to generate test source video: {e}")
        
    # Setup timeline track items
    video_item = VideoTrackItem(
        id="timeline-v-item-1",
        assetId=video_id,
        name="test-clip",
        start=0.0,
        duration=1.5,  # Take 1.5s of the 2s source
        sourceStart=0.0,
        volume=1.0,
        muted=False
    )
    
    project = Project(
        id=project_id,
        name="Test Render Project",
        createdAt="2026-06-10T12:00:00Z",
        updatedAt="2026-06-10T12:00:00Z",
        timeline=Timeline(
            tracks={
                "video": [video_item],
                "audio": [],
                "subtitle": [],
                "text": [],
                "image": []
            }
        ),
        assets=[
            Asset(
                id=video_id,
                name="source.mp4",
                type="video",
                path=f"videos/{video_filename}",
                duration=2.0,
                resolution="1280x720",
                createdAt="2026-06-10T12:00:00Z"
            )
        ]
    )
    save_project(project)
    
    yield project_id
    
    # Cleanup files
    if video_path.exists():
        video_path.unlink()
        
    project_file = PROJECTS_DIR / f"{project_id}.json"
    if project_file.exists():
        project_file.unlink()
        
    for f in RENDERS_DIR.glob("render_*"):
        f.unlink()

def test_render_task_not_found():
    response = client.get("/api/timeline/render/non-existent-render-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Render task non-existent-render-id not found"

def test_trigger_render_validation_error():
    # Attempting to render an empty/non-existent project
    response = client.post("/api/timeline/render", json={
        "projectId": "does-not-exist",
        "aspectRatio": "9:16",
        "resolution": "1080p"
    })
    assert response.status_code == 202
    task_id = response.json()["taskId"]
    
    # Let the thread fail
    # Check status, should fail with project not found error
    import time
    time.sleep(0.5) # Wait for thread execution
    
    status_response = client.get(f"/api/timeline/render/{task_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "failed"
    assert "not found" in status_data["error"].lower()
    
    with renders_lock:
        if task_id in RENDER_TASKS:
            del RENDER_TASKS[task_id]

def test_timeline_rendering_success(test_project_with_video_on_timeline):
    project_id = test_project_with_video_on_timeline
    
    # Trigger compile/render
    response = client.post("/api/timeline/render", json={
        "projectId": project_id,
        "aspectRatio": "9:16",
        "resolution": "720p"
    })
    
    assert response.status_code == 202
    task_id = response.json()["taskId"]
    
    # Poll status until completed (should take under 3s since it's a 1.5s video)
    import time
    completed = False
    for _ in range(30):
        status_response = client.get(f"/api/timeline/render/{task_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        if status_data["status"] == "completed":
            completed = True
            assert status_data["progress"] == 100.0
            assert status_data["outputPath"].startswith("renders/render_")
            # Verify output file exists
            out_file = RENDERS_DIR.parent / status_data["outputPath"]
            assert out_file.exists()
            break
        elif status_data["status"] == "failed":
            pytest.fail(f"Timeline rendering failed: {status_data['error']}")
            
        time.sleep(0.2)
        
    assert completed, "Timeline rendering task timed out"
    
    with renders_lock:
        if task_id in RENDER_TASKS:
            del RENDER_TASKS[task_id]
