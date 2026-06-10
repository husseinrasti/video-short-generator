from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
from backend.app.utils.ai import save_api_keys, load_api_keys, call_llm
from backend.app.utils.storage import load_project

router = APIRouter(prefix="/api/ai", tags=["ai"])

class KeysSaveRequest(BaseModel):
    openai: str = ""
    anthropic: str = ""
    gemini: str = ""
    elevenlabs: str = ""

class KeysStatusResponse(BaseModel):
    openai: bool
    anthropic: bool
    gemini: bool
    elevenlabs: bool

class AIRequest(BaseModel):
    projectId: str
    provider: str = Field("openai", description="openai, anthropic, or gemini")
    model: Optional[str] = None

class Highlight(BaseModel):
    start: float
    end: float
    reason: str

class HighlightsResponse(BaseModel):
    highlights: List[Highlight]

class MetadataResponse(BaseModel):
    titles: List[str]
    description: str
    tags: List[str]
    keywords: List[str]

@router.get("/keys", response_model=KeysStatusResponse)
def get_keys_status():
    """Returns whether the API keys are configured (without exposing values)."""
    keys = load_api_keys()
    return KeysStatusResponse(
        openai=bool(keys.get("openai", "").strip()),
        anthropic=bool(keys.get("anthropic", "").strip()),
        gemini=bool(keys.get("gemini", "").strip()),
        elevenlabs=bool(keys.get("elevenlabs", "").strip())
    )

@router.post("/keys", status_code=status.HTTP_204_NO_CONTENT)
def configure_keys(request: KeysSaveRequest):
    """Saves API keys locally in the storage directory."""
    save_api_keys(request.model_dump())
    return

@router.get("/models")
async def get_provider_models(provider: str):
    """Returns available model lists for the specified provider."""
    keys = load_api_keys()
    api_key = keys.get(provider.lower(), "").strip()
    from backend.app.utils.ai import fetch_provider_models
    models = await fetch_provider_models(provider, api_key)
    return models

def _get_timeline_transcript(project_id: str) -> str:
    """Combines timeline subtitles into a formatted script with timestamps."""
    project = load_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
        
    subs = sorted(project.timeline.tracks.subtitle, key=lambda x: x.start)
    if not subs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subtitle track is empty. Please generate auto-subtitles first."
        )
        
    script_lines = []
    for s in subs:
        script_lines.append(f"[{s.start:.1f}s - {s.start + s.duration:.1f}s]: {s.text}")
    return "\n".join(script_lines)

@router.post("/generate-metadata", response_model=MetadataResponse)
async def generate_video_metadata(request: AIRequest):
    """Generates optimized YouTube Short metadata (Titles, Description, Tags) from transcript."""
    transcript = _get_timeline_transcript(request.projectId)
    
    system_instruction = (
        "You are an expert social media manager optimizing short-form videos (YouTube Shorts, TikTok, Instagram Reels).\n"
        "Analyze the provided timestamped transcript and return a JSON payload with optimized video details.\n"
        "Return ONLY a raw JSON object matching this schema:\n"
        "{\n"
        "  \"titles\": [\"title 1\", \"title 2\", \"title 3\"],\n"
        "  \"description\": \"engaging youtube shorts description text with call-to-action\",\n"
        "  \"tags\": [\"tag1\", \"tag2\", \"tag3\"],\n"
        "  \"keywords\": [\"keyword1\", \"keyword2\"]\n"
        "}\n"
        "Do not wrap the response in markdown code blocks like ```json."
    )
    
    prompt = f"Here is the video transcript:\n\n{transcript}"
    
    try:
        raw_response = await call_llm(request.provider, prompt, system_instruction, request.model)
        # Attempt to strip code blocks if model ignored instructions
        clean_json = raw_response.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            if clean_json.startswith("json"):
                clean_json = clean_json[4:].strip()
                
        data = json.loads(clean_json)
        return MetadataResponse(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI call failed: {e}"
        )

@router.post("/detect-highlights", response_model=HighlightsResponse)
async def detect_highlights_api(request: AIRequest):
    """Detects engaging highlight ranges (start, end, reason) using transcript timestamps."""
    transcript = _get_timeline_transcript(request.projectId)
    
    system_instruction = (
        "You are an expert video editor finding viral moments for Shorts/TikToks.\n"
        "Analyze the timestamped transcript and suggest 1 to 3 engaging clip ranges.\n"
        "Return ONLY a raw JSON object matching this schema:\n"
        "{\n"
        "  \"highlights\": [\n"
        "    {\n"
        "      \"start\": 12.5,\n"
        "      \"end\": 20.0,\n"
        "      \"reason\": \"Hook explanation or peak interest statement\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Ensure start and end timestamps match the range boundaries in the transcript. Do not wrap in markdown."
    )
    
    prompt = f"Transcript segments:\n\n{transcript}"
    
    try:
        raw_response = await call_llm(request.provider, prompt, system_instruction, request.model)
        clean_json = raw_response.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            if clean_json.startswith("json"):
                clean_json = clean_json[4:].strip()
                
        data = json.loads(clean_json)
        return HighlightsResponse(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI call failed: {e}"
        )
