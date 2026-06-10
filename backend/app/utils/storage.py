import json
import os
from typing import List, Dict, Any, Optional
from backend.app.config import PROJECTS_DIR
from backend.app.models.project import Project

def save_project(project: Project) -> Project:
    """Saves a project object to storage as a JSON file."""
    file_path = PROJECTS_DIR / f"{project.id}.json"
    project_dict = project.model_dump()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(project_dict, f, indent=2, ensure_ascii=False)
    return project

def load_project(project_id: str) -> Optional[Project]:
    """Loads a project from storage by its ID."""
    file_path = PROJECTS_DIR / f"{project_id}.json"
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Project(**data)
    except Exception as e:
        # If there's an error parsing (e.g. schema changes), handle/log it or return None
        print(f"Error loading project {project_id}: {e}")
        return None

def delete_project(project_id: str) -> bool:
    """Deletes a project's JSON file from storage."""
    file_path = PROJECTS_DIR / f"{project_id}.json"
    if file_path.exists():
        file_path.unlink()
        return True
    return False

def list_projects() -> List[Dict[str, Any]]:
    """Lists summary details of all saved projects."""
    projects = []
    for filename in os.listdir(PROJECTS_DIR):
        if filename.endswith(".json"):
            file_path = PROJECTS_DIR / filename
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    projects.append({
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "createdAt": data.get("createdAt"),
                        "updatedAt": data.get("updatedAt"),
                    })
            except Exception as e:
                print(f"Error parsing metadata for {filename}: {e}")
    # Sort projects by updatedAt descending
    projects.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
    return projects
