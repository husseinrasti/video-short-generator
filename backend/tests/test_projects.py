import os
import shutil
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import PROJECTS_DIR, STORAGE_DIR

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown_test_env():
    """Sets up a clean temporary projects directory and cleans up after."""
    # Back up existing projects if any (should be empty for new project workspace)
    temp_backup_dir = STORAGE_DIR / "projects_backup"
    has_backup = False
    
    if PROJECTS_DIR.exists():
        # Temporarily rename it to not interfere with tests
        shutil.move(str(PROJECTS_DIR), str(temp_backup_dir))
        has_backup = True
        
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Clean up test files
    if PROJECTS_DIR.exists():
        shutil.rmtree(str(PROJECTS_DIR))
        
    # Restore backup
    if has_backup:
        shutil.move(str(temp_backup_dir), str(PROJECTS_DIR))
    else:
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_and_list_projects():
    # List should be empty initially
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert response.json() == []

    # Create a project
    response = client.post("/api/projects", json={"name": "Test Short Video"})
    assert response.status_code == 201
    project_data = response.json()
    assert project_data["name"] == "Test Short Video"
    assert "id" in project_data
    assert len(project_data["timeline"]["tracks"]["video"]) == 0

    # List should now contain one project
    response = client.get("/api/projects")
    assert response.status_code == 200
    meta_list = response.json()
    assert len(meta_list) == 1
    assert meta_list[0]["id"] == project_data["id"]
    assert meta_list[0]["name"] == "Test Short Video"

def test_get_project_not_found():
    response = client.get("/api/projects/does-not-exist")
    assert response.status_code == 404

def test_update_project():
    # Create project
    response = client.post("/api/projects", json={"name": "To Be Updated"})
    project = response.json()
    project_id = project["id"]

    # Modify name and add an asset
    project["name"] = "Updated Name"
    project["assets"].append({
        "id": "asset-1",
        "name": "clip.mp4",
        "type": "video",
        "path": "videos/clip.mp4",
        "duration": 10.5,
        "createdAt": "2026-06-10T12:00:00Z"
    })

    # Update
    response = client.put(f"/api/projects/{project_id}", json=project)
    assert response.status_code == 200
    updated_project = response.json()
    assert updated_project["name"] == "Updated Name"
    assert len(updated_project["assets"]) == 1
    assert updated_project["assets"][0]["id"] == "asset-1"

    # Get from API to confirm persistence
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    fetched_project = response.json()
    assert fetched_project["name"] == "Updated Name"
    assert len(fetched_project["assets"]) == 1

def test_delete_project():
    # Create project
    response = client.post("/api/projects", json={"name": "To Be Deleted"})
    project_id = response.json()["id"]

    # Delete project
    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204

    # Verify not found
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 404
