import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import AUDIO_DIR, PROJECTS_DIR
from backend.app.utils.storage import save_project
from backend.app.models.project import Project, Timeline

client = TestClient(app)

@pytest.fixture
def test_project():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    project_id = "test-narration-project-id"
    project = Project(
        id=project_id,
        name="Test Narration Project",
        createdAt="2026-06-10T12:00:00Z",
        updatedAt="2026-06-10T12:00:00Z",
        timeline=Timeline(),
        assets=[]
    )
    save_project(project)
    
    yield project_id
    
    # Cleanup files
    project_file = PROJECTS_DIR / f"{project_id}.json"
    if project_file.exists():
        project_file.unlink()

@patch("backend.app.routers.narration.call_llm")
def test_generate_script(mock_call_llm, test_project):
    mock_call_llm.return_value = "This is a polished script about FIFA World Cup controversies."
    
    response = client.post("/api/narration/generate-script", json={
        "projectId": test_project,
        "provider": "openai",
        "mode": "topic",
        "inputValue": "FIFA controversies"
    })
    
    assert response.status_code == 200
    assert response.json()["script"] == "This is a polished script about FIFA World Cup controversies."
    mock_call_llm.assert_called_once()

@patch("backend.app.routers.narration.call_llm")
def test_generate_script_with_modifier(mock_call_llm, test_project):
    mock_call_llm.return_value = "Shorter script."
    
    response = client.post("/api/narration/generate-script", json={
        "projectId": test_project,
        "provider": "openai",
        "mode": "topic",
        "inputValue": "Draft text",
        "modifier": "shorter"
    })
    
    assert response.status_code == 200
    assert response.json()["script"] == "Shorter script."
    
    # Verify that the modifier prompt is sent
    args, kwargs = mock_call_llm.call_args
    assert "shorter" in args[1].lower()

@patch("backend.app.routers.narration.generate_openai_tts")
@patch("backend.app.routers.narration.get_video_metadata")
def test_generate_voiceover_success(mock_metadata, mock_tts, test_project):
    mock_metadata.return_value = {"duration": 15.5, "width": 0, "height": 0}
    
    # Simulate generate_openai_tts creating a file
    def side_effect(text, voice, speed, model, output_path):
        with open(output_path, "w") as f:
            f.write("dummy audio data")
            
    mock_tts.side_effect = side_effect
    
    response = client.post("/api/narration/generate-voiceover", json={
        "projectId": test_project,
        "script": "Script to read.",
        "provider": "openai",
        "voice": "alloy",
        "speed": 1.0
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "audio"
    assert data["duration"] == 15.5
    assert "audio/narration_" in data["path"]
    
    # Cleanup created audio file
    filename = data["path"].split("/")[-1]
    audio_path = AUDIO_DIR / filename
    if audio_path.exists():
        audio_path.unlink()

@patch("backend.app.routers.narration.get_whisper_model")
def test_generate_subtitles_success(mock_get_model, test_project):
    # Setup project with a mock voiceover asset
    project_id = test_project
    asset_id = "test-voiceover-asset-id"
    filename = f"narration_{asset_id}.mp3"
    audio_path = AUDIO_DIR / filename
    
    with open(audio_path, "w") as f:
        f.write("dummy audio")
        
    project = Project(
        id=project_id,
        name="Test Project",
        createdAt="2026-06-10T12:00:00Z",
        updatedAt="2026-06-10T12:00:00Z",
        timeline=Timeline(),
        assets=[
            {
                "id": asset_id,
                "name": "Narration Voiceover",
                "type": "audio",
                "path": f"audio/{filename}",
                "duration": 5.0,
                "createdAt": "2026-06-10T12:00:00Z"
            }
        ]
    )
    save_project(project)
    
    # Mock Whisper transcribing
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "text": "Hello world",
        "segments": [
            {"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world"}
        ]
    }
    mock_get_model.return_value = mock_model
    
    response = client.post("/api/narration/generate-subtitles", json={
        "projectId": project_id,
        "audioAssetId": asset_id,
        "script": "Hello world"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["text"] == "Hello world"
    assert data[0]["start"] == 0.0
    assert data[0]["duration"] == 2.5
    
    # Cleanup audio
    if audio_path.exists():
        audio_path.unlink()

@patch("backend.app.routers.narration.call_llm")
def test_generate_metadata(mock_call_llm, test_project):
    mock_call_llm.return_value = (
        "{\n"
        '  "titles": ["Controversy 1", "Controversy 2"],\n'
        '  "description": "Short description.",\n'
        '  "tags": ["shorts", "football"],\n'
        '  "keywords": ["fifa"]\n'
        "}"
    )
    
    response = client.post("/api/narration/generate-metadata", json={
        "projectId": test_project,
        "script": "Script text.",
        "provider": "openai"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["titles"]) == 2
    assert data["titles"][0] == "Controversy 1"
    assert data["description"] == "Short description."
    assert "shorts" in data["tags"]

@patch("backend.app.routers.narration.kokoro_provider")
@patch("backend.app.routers.narration.get_video_metadata")
def test_generate_voiceover_kokoro_success(mock_metadata, mock_kokoro, test_project):
    mock_metadata.return_value = {"duration": 10.0, "width": 0, "height": 0}
    
    # Simulate kokoro_provider.generate_speech creating the final file
    def side_effect(text, voice, speed, output_path):
        with open(output_path, "w") as f:
            f.write("mock audio data")
            
    mock_kokoro.generate_speech.side_effect = side_effect
    
    # WAV format test
    response = client.post("/api/narration/generate-voiceover", json={
        "projectId": test_project,
        "script": "Hello from local Kokoro",
        "provider": "kokoro",
        "voice": "af_heart",
        "speed": 1.2,
        "outputFormat": "wav"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "audio"
    assert data["duration"] == 10.0
    assert "audio/narration_" in data["path"]
    assert data["path"].endswith(".wav")
    
    # Cleanup created audio file
    filename = data["path"].split("/")[-1]
    audio_path = AUDIO_DIR / filename
    if audio_path.exists():
        audio_path.unlink()

