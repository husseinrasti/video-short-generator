from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import threading
import httpx
import shutil
from pathlib import Path
from backend.app.utils.ai import save_api_keys, load_api_keys, call_llm
from backend.app.utils.storage import load_project
from backend.app.config import WHISPER_MODELS_DIR, KOKORO_MODELS_DIR

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


# --- Local AI Models Setup & Status State ---

INSTALL_LOCK = threading.Lock()
INSTALL_THREAD = None

INSTALL_STATUS: Dict[str, Any] = {
    "status": "not_installed",      # "not_installed", "installing", "ready", "error", "cancelled"
    "progress": 0.0,
    "error": None,
    "current_file": "",
    "whisper": "not_installed",     # "not_installed", "ready"
    "kokoro": "not_installed"       # "not_installed", "ready"
}

def check_local_models_status() -> Dict[str, str]:
    """Checks the local file storage to see if Whisper and Kokoro models are present."""
    whisper_file = WHISPER_MODELS_DIR / "tiny.pt"
    kokoro_model = KOKORO_MODELS_DIR / "kokoro-v1.0.onnx"
    kokoro_voices = KOKORO_MODELS_DIR / "voices-v1.0.bin"
    
    whisper_ready = whisper_file.exists() and whisper_file.stat().st_size > 70 * 1024 * 1024
    kokoro_ready = (
        kokoro_model.exists() and kokoro_model.stat().st_size > 300 * 1024 * 1024
        and kokoro_voices.exists() and kokoro_voices.stat().st_size > 20 * 1024 * 1024
    )
    
    return {
        "whisper": "ready" if whisper_ready else "not_installed",
        "kokoro": "ready" if kokoro_ready else "not_installed"
    }

def update_initial_status():
    """Reads filesystem status and initializes the global installer state."""
    status = check_local_models_status()
    INSTALL_STATUS["whisper"] = status["whisper"]
    INSTALL_STATUS["kokoro"] = status["kokoro"]
    
    if status["whisper"] == "ready" and status["kokoro"] == "ready":
        INSTALL_STATUS["status"] = "ready"
        INSTALL_STATUS["progress"] = 100.0
    else:
        INSTALL_STATUS["status"] = "not_installed"
        INSTALL_STATUS["progress"] = 0.0

# Initialize status on module load
update_initial_status()

def download_file_with_progress(url: str, dest_path: Path, start_prog: float, end_prog: float):
    """Downloads a file streaming chunks and updating progress."""
    global INSTALL_STATUS
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp")
    
    # Clean up any leftover temporary file
    if temp_path.exists():
        temp_path.unlink()
        
    with httpx.Client(timeout=60.0) as client:
        with client.stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(temp_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=1024 * 64):
                    if INSTALL_STATUS["status"] == "cancelled":
                        raise RuntimeError("Installation cancelled by user")
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        file_prog = downloaded / total_size
                        overall_prog = start_prog + (end_prog - start_prog) * file_prog
                        with INSTALL_LOCK:
                            INSTALL_STATUS["progress"] = round(overall_prog * 100, 1)
                            INSTALL_STATUS["current_file"] = dest_path.name

            if dest_path.exists():
                dest_path.unlink()
            shutil.move(str(temp_path), str(dest_path))

def _install_worker():
    """Background worker for downloading Whisper and Kokoro local models."""
    global INSTALL_STATUS
    try:
        # Download URLs
        whisper_url = "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"
        kokoro_onnx_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
        kokoro_voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

        # 1. Download Whisper tiny.pt (0% to 20%)
        whisper_path = WHISPER_MODELS_DIR / "tiny.pt"
        if INSTALL_STATUS["whisper"] != "ready":
            download_file_with_progress(whisper_url, whisper_path, 0.0, 0.20)
            with INSTALL_LOCK:
                INSTALL_STATUS["whisper"] = "ready"
        else:
            with INSTALL_LOCK:
                INSTALL_STATUS["progress"] = 20.0

        # 2. Download Kokoro ONNX model (20% to 95%)
        kokoro_path = KOKORO_MODELS_DIR / "kokoro-v1.0.onnx"
        kokoro_status = check_local_models_status()["kokoro"]
        
        if kokoro_status != "ready" or not kokoro_path.exists():
            download_file_with_progress(kokoro_onnx_url, kokoro_path, 0.20, 0.95)
            
        # 3. Download Kokoro voices data bin (95% to 100%)
        voices_path = KOKORO_MODELS_DIR / "voices-v1.0.bin"
        if kokoro_status != "ready" or not voices_path.exists():
            download_file_with_progress(kokoro_voices_url, voices_path, 0.95, 1.00)
            
        with INSTALL_LOCK:
            INSTALL_STATUS["kokoro"] = "ready"
            
        # Integrity verification
        status = check_local_models_status()
        if status["whisper"] == "ready" and status["kokoro"] == "ready":
            with INSTALL_LOCK:
                INSTALL_STATUS["status"] = "ready"
                INSTALL_STATUS["progress"] = 100.0
                INSTALL_STATUS["current_file"] = ""
                INSTALL_STATUS["error"] = None
        else:
            raise RuntimeError("Integrity verification failed: files are incomplete or incorrect size.")

    except Exception as e:
        # Delete any temporary files on failure or cancellation
        for folder in [WHISPER_MODELS_DIR, KOKORO_MODELS_DIR]:
            for temp_file in folder.glob("*.tmp"):
                try:
                    temp_file.unlink()
                except Exception:
                    pass
        with INSTALL_LOCK:
            if INSTALL_STATUS["status"] == "cancelled":
                update_initial_status()
            else:
                INSTALL_STATUS["status"] = "error"
                INSTALL_STATUS["error"] = str(e)


@router.get("/local-status")
def get_local_models_status_api():
    """Returns the current status of local AI models installation."""
    if INSTALL_STATUS["status"] in ["ready", "not_installed", "error"]:
        update_initial_status()
    return INSTALL_STATUS


@router.post("/install-local", status_code=status.HTTP_202_ACCEPTED)
def trigger_install_local_models():
    """Spawns the background installer thread for local Whisper and Kokoro models."""
    global INSTALL_THREAD
    with INSTALL_LOCK:
        if INSTALL_STATUS["status"] == "installing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Installation is already in progress."
            )
        
        INSTALL_STATUS["status"] = "installing"
        INSTALL_STATUS["progress"] = 0.0
        INSTALL_STATUS["error"] = None
        INSTALL_STATUS["current_file"] = ""
        
        INSTALL_THREAD = threading.Thread(target=_install_worker, daemon=True)
        INSTALL_THREAD.start()
        
    return {"message": "Installation started"}


@router.post("/cancel-install")
def cancel_install_local_models():
    """Cancels any active local AI models installation in progress."""
    global INSTALL_STATUS
    with INSTALL_LOCK:
        if INSTALL_STATUS["status"] != "installing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No installation in progress to cancel."
            )
        INSTALL_STATUS["status"] = "cancelled"
    return {"message": "Cancellation request submitted"}

