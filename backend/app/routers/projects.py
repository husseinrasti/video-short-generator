from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone
from backend.app.models.project import Project, Timeline
from backend.app.utils.storage import (
    save_project,
    load_project,
    delete_project,
    list_projects,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectCreateRequest(BaseModel):
    name: Optional[str] = Field(default="Untitled Project", description="Name of the new project")

class ProjectMetaResponse(BaseModel):
    id: str
    name: str
    createdAt: str
    updatedAt: str

@router.get("", response_model=List[ProjectMetaResponse])
def get_all_projects():
    """List metadata for all existing projects."""
    return list_projects()

@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(request: ProjectCreateRequest):
    """Create a new project with defaults and save it."""
    project_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    project = Project(
        id=project_id,
        name=request.name or "Untitled Project",
        createdAt=timestamp,
        updatedAt=timestamp,
        timeline=Timeline(),
        assets=[],
    )
    save_project(project)
    return project

@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str):
    """Get detailed state of a single project."""
    project = load_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return project

@router.put("/{project_id}", response_model=Project)
def update_project(project_id: str, updated_project: Project):
    """Overwrite the state of an existing project, updating the updatedAt timestamp."""
    existing = load_project(project_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Ensure the ID from path matches the project ID
    if updated_project.id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID in path does not match project ID in body"
        )
        
    # Update timestamp
    updated_project.updatedAt = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    save_project(updated_project)
    return updated_project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project(project_id: str):
    """Delete a project file."""
    deleted = delete_project(project_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return
