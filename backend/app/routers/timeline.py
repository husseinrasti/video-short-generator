from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from backend.app.utils.render import start_render_task, get_render_status

router = APIRouter(prefix="/api/timeline", tags=["timeline"])

class RenderRequest(BaseModel):
    projectId: str
    aspectRatio: str = Field("9:16", description="Aspect ratio: 9:16, 16:9, 1:1")
    resolution: str = Field("1080p", description="Resolution: 720p, 1080p, 1440p")

class RenderResponse(BaseModel):
    taskId: str
    status: str

@router.post("/render", response_model=RenderResponse, status_code=status.HTTP_202_ACCEPTED)
def render_timeline(request: RenderRequest):
    """Triggers a background rendering task to compile the project timeline into a single MP4."""
    try:
        task_id = start_render_task(request.projectId, request.aspectRatio, request.resolution)
        return RenderResponse(taskId=task_id, status="pending")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start timeline rendering: {e}"
        )

@router.get("/render/{task_id}")
def check_render_status(task_id: str):
    """Polls the status of a background timeline render task."""
    task = get_render_status(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Render task {task_id} not found"
        )
    return task

@router.post("/render/{task_id}/cancel")
def cancel_timeline_render(task_id: str):
    """Cancels a background timeline render task."""
    from backend.app.utils.render import cancel_render_task
    success = cancel_render_task(task_id)
    return {"taskId": task_id, "status": "cancelled", "success": success}
