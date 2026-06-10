import os
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import PROJECTS_DIR, STORAGE_DIR
from backend.app.utils.storage import save_project
from backend.app.models.project import Project, Timeline, SubtitleTrackItem

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_ai_keys_backup():
    """Backs up local api_keys.json to avoid messing up user settings during test runs."""
    keys_file = STORAGE_DIR / "api_keys.json"
    backup_file = STORAGE_DIR / "api_keys_backup.json"
    has_backup = False
    
    if keys_file.exists():
        os.rename(keys_file, backup_file)
        has_backup = True
        
    yield
    
    # Restore
    if keys_file.exists():
        keys_file.unlink()
    if has_backup:
        os.rename(backup_file, keys_file)

def test_api_keys_save_and_status():
    # Initially status should show false for all keys because mock setup guarantees empty config
    response = client.get("/api/ai/keys")
    assert response.status_code == 200
    data = response.json()
    assert not data["openai"]
    assert not data["gemini"]
    
    # Save keys
    response = client.post("/api/ai/keys", json={
        "openai": "sk-testkey",
        "anthropic": "",
        "gemini": "AIzaSy-geminikey"
    })
    assert response.status_code == 204
    
    # Verify status reflects configurations
    response = client.get("/api/ai/keys")
    assert response.status_code == 200
    data = response.json()
    assert data["openai"]
    assert not data["anthropic"]
    assert data["gemini"]

@patch("backend.app.routers.ai.call_llm")
def test_generate_metadata(mock_call_llm):
    # Setup test project with some subtitle data
    project_id = "test-ai-project-id"
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    sub1 = SubtitleTrackItem(id="s1", name="sub1", start=1.0, duration=2.0, sourceStart=1.0, text="Goal achieved")
    sub2 = SubtitleTrackItem(id="s2", name="sub2", start=3.0, duration=2.0, sourceStart=3.0, text="Stunning strike")
    
    project = Project(
        id=project_id,
        name="Test AI Project",
        createdAt="2026-06-10T12:00:00Z",
        updatedAt="2026-06-10T12:00:00Z",
        timeline=Timeline(
            tracks={
                "video": [], "audio": [], "subtitle": [sub1, sub2], "text": [], "image": []
            }
        ),
        assets=[]
    )
    save_project(project)
    
    # Mock LLM JSON output
    mock_call_llm.return_value = json.dumps({
        "titles": ["Epic Goal Shorts", "Amazing Strike!"],
        "description": "What a goal by the forward!",
        "tags": ["soccer", "goals"],
        "keywords": ["football"]
    })
    
    response = client.post("/api/ai/generate-metadata", json={
        "projectId": project_id,
        "provider": "openai"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "Epic Goal Shorts" in data["titles"]
    assert len(data["tags"]) == 2
    
    # Clean up project
    project_file = PROJECTS_DIR / f"{project_id}.json"
    if project_file.exists():
        project_file.unlink()

@patch("backend.app.routers.ai.call_llm")
def test_detect_highlights(mock_call_llm):
    project_id = "test-ai-project-id-2"
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    sub1 = SubtitleTrackItem(id="s1", name="sub1", start=1.0, duration=2.0, sourceStart=1.0, text="Welcome everyone")
    sub2 = SubtitleTrackItem(id="s2", name="sub2", start=5.0, duration=3.0, sourceStart=5.0, text="He shoots and scores!")
    
    project = Project(
        id=project_id,
        name="Test AI Project 2",
        createdAt="2026-06-10T12:00:00Z",
        updatedAt="2026-06-10T12:00:00Z",
        timeline=Timeline(
            tracks={
                "video": [], "audio": [], "subtitle": [sub1, sub2], "text": [], "image": []
            }
        ),
        assets=[]
    )
    save_project(project)
    
    # Mock LLM JSON output
    mock_call_llm.return_value = json.dumps({
        "highlights": [
            {"start": 5.0, "end": 8.0, "reason": "Exciting goal moment!"}
        ]
    })
    
    response = client.post("/api/ai/detect-highlights", json={
        "projectId": project_id,
        "provider": "gemini"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["highlights"]) == 1
    assert data["highlights"][0]["start"] == 5.0
    assert data["highlights"][0]["reason"] == "Exciting goal moment!"
    
    # Clean up project
    project_file = PROJECTS_DIR / f"{project_id}.json"
    if project_file.exists():
        project_file.unlink()
