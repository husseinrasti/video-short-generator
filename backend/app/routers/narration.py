from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path

from backend.app.config import STORAGE_DIR, AUDIO_DIR
from backend.app.utils.storage import load_project, save_project
from backend.app.utils.ai import call_llm
from backend.app.utils.tts import generate_openai_tts, generate_elevenlabs_tts
from backend.app.utils.ffmpeg import adjust_audio_speed, get_video_metadata
from backend.app.utils.whisper_transcribe import get_whisper_model
from backend.app.models.project import Asset, SubtitleTrackItem
from backend.app.providers.tts import KokoroLocalProvider

# Instantiate local TTS provider
kokoro_provider = KokoroLocalProvider()

router = APIRouter(prefix="/api/narration", tags=["narration"])

# Request/Response schemas
class ScriptGenerateRequest(BaseModel):
    projectId: str
    provider: str = Field("openai", description="openai, anthropic, or gemini")
    mode: str = Field("topic", description="topic, notes, or raw")
    inputValue: str
    modifier: Optional[str] = Field(None, description="shorter, longer, exciting, professional, reduce-20, reduce-50, expand, etc.")

class ScriptGenerateResponse(BaseModel):
    script: str

class VoiceoverGenerateRequest(BaseModel):
    projectId: str
    script: str
    provider: str = Field("openai", description="openai, elevenlabs, or kokoro")
    voice: str
    speed: float = 1.0
    model: Optional[str] = None
    outputFormat: Optional[str] = Field("mp3", description="mp3 or wav")

class SubtitlesGenerateRequest(BaseModel):
    projectId: str
    audioAssetId: str
    script: str

class MetadataGenerateRequest(BaseModel):
    projectId: str
    script: str
    provider: str = Field("openai", description="openai, anthropic, or gemini")

class MetadataGenerateResponse(BaseModel):
    titles: List[str]
    description: str
    tags: List[str]
    keywords: List[str]

@router.post("/generate-script", response_model=ScriptGenerateResponse)
async def generate_narration_script(request: ScriptGenerateRequest):
    """Generates or rewrites a voiceover narration script using the selected LLM provider."""
    system_instruction = (
        "You are a professional scriptwriter specializing in viral short-form content (YouTube Shorts, TikTok, Instagram Reels).\n"
        "Generate an engaging voiceover script. Requirements:\n"
        "- Start with a powerful 3-second hook to grab attention.\n"
        "- Keep the tone conversational, fast-paced, and natural for speech.\n"
        "- Use simple, clear sentence structures.\n"
        "- Do NOT include any markdown, formatting, bullet points, headers, or emojis.\n"
        "- Do NOT output any stage directions, narration cues, or background notes (e.g. do not write '[sound effects]' or '[Voiceover:]').\n"
        "- Aim for between 30 and 90 seconds of total speaking time (around 75 to 225 words).\n"
        "- Output ONLY the spoken narration text itself."
    )

    if request.modifier:
        mod = request.modifier.lower()
        if mod == "shorter":
            prompt = f"Make the following script shorter (reduce length by about 20% to 30%):\n\n{request.inputValue}"
        elif mod == "longer":
            prompt = f"Expand the following script with more detail and depth while maintaining high engagement:\n\n{request.inputValue}"
        elif mod == "exciting":
            prompt = f"Make the following script significantly more exciting, energetic, and dramatic:\n\n{request.inputValue}"
        elif mod == "professional":
            prompt = f"Make the following script sound more professional, authoritative, and educational:\n\n{request.inputValue}"
        elif mod == "reduce-20":
            prompt = f"Rewrite the following script to make it exactly 20% shorter, keeping the hook and key points:\n\n{request.inputValue}"
        elif mod == "reduce-50":
            prompt = f"Rewrite the following script to make it exactly 50% shorter, trimming it down to only the most vital points:\n\n{request.inputValue}"
        elif mod in ["expand", "add-detail"]:
            prompt = f"Expand the following script with more details and depth:\n\n{request.inputValue}"
        elif mod == "increase-duration":
            prompt = f"Make the following script longer to increase speaking duration:\n\n{request.inputValue}"
        else:
            prompt = f"Modify the following script as follows: {request.modifier}\n\nScript:\n{request.inputValue}"
    else:
        # Initial script generation
        mode = request.mode.lower()
        if mode == "topic":
            prompt = f"Generate a highly engaging voiceover script about this topic:\n{request.inputValue}"
        elif mode == "notes":
            prompt = f"Generate a highly engaging voiceover script based on these bullet points or notes:\n{request.inputValue}"
        else:
            # Raw text input
            prompt = f"Polish and rewrite this draft text into a high-engagement, spoken narration script:\n{request.inputValue}"

    try:
        script = await call_llm(request.provider, prompt, system_instruction)
        return ScriptGenerateResponse(script=script.strip())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate script: {e}"
        )

@router.post("/generate-voiceover", response_model=Asset, status_code=status.HTTP_201_CREATED)
async def generate_narration_voiceover(request: VoiceoverGenerateRequest):
    """Invokes TTS (OpenAI, ElevenLabs, or local Kokoro) to generate narration voiceover, saves it locally as a project asset."""
    project = load_project(request.projectId)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.projectId} not found"
        )

    # Output file settings
    asset_id = str(uuid.uuid4())
    ext = "wav" if request.outputFormat and request.outputFormat.lower() == "wav" else "mp3"
    filename = f"narration_{asset_id}.{ext}"
    audio_path = AUDIO_DIR / filename
    temp_path = AUDIO_DIR / f"temp_{filename}"

    try:
        provider = request.provider.lower()
        if provider == "kokoro":
            # Kokoro is a fully local offline TTS pipeline
            kokoro_provider.generate_speech(
                text=request.script,
                voice=request.voice,
                speed=request.speed,
                output_path=audio_path
            )
        else:
            if provider == "openai":
                await generate_openai_tts(
                    text=request.script,
                    voice=request.voice,
                    speed=request.speed,
                    model=request.model or "tts-1",
                    output_path=temp_path
                )
            elif provider == "elevenlabs":
                await generate_elevenlabs_tts(
                    text=request.script,
                    voice=request.voice,
                    model=request.model or "eleven_monolingual_v1",
                    output_path=temp_path
                )
            else:
                raise ValueError(f"Unsupported TTS provider: {request.provider}")

            # Apply speed adjustment or format conversion via FFmpeg if necessary
            # OpenAI handles speed natively on API side, ElevenLabs requires post-processing for speed
            needs_processing = (provider == "elevenlabs" and request.speed != 1.0) or ext == "wav"
            if needs_processing:
                success = adjust_audio_speed(str(temp_path), str(audio_path), 1.0 if provider == "openai" else request.speed)
                if not success:
                    raise RuntimeError("FFmpeg speed adjustment/format conversion failed")
                if temp_path.exists():
                    temp_path.unlink()
            else:
                if temp_path.exists():
                    os.rename(temp_path, audio_path)

        # Retrieve audio duration
        metadata = get_video_metadata(str(audio_path))
        duration = metadata.get("duration", 0.0)

        # Create asset
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        new_asset = Asset(
            id=asset_id,
            name=f"Narration Voiceover ({duration:.1f}s)",
            type="audio",
            path=f"audio/{filename}",
            duration=duration,
            resolution=None,
            createdAt=timestamp
        )

        # Save to project
        project.assets.append(new_asset)
        save_project(project)

        return new_asset

    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        if audio_path.exists():
            audio_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS Voiceover generation failed: {e}"
        )

@router.post("/generate-subtitles", response_model=List[SubtitleTrackItem])
def generate_narration_subtitles(request: SubtitlesGenerateRequest):
    """Runs local Whisper synchronously on the generated voiceover audio file to create subtitle segments."""
    project = load_project(request.projectId)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.projectId} not found"
        )

    asset = next((a for a in project.assets if a.id == request.audioAssetId), None)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio asset {request.audioAssetId} not found in project"
        )

    file_path = STORAGE_DIR / asset.path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voiceover audio file not found on disk"
        )

    try:
        # Load whisper and transcribe synchronously
        model = get_whisper_model("tiny")
        result = model.transcribe(str(file_path))
        
        segments = result.get("segments", [])
        subtitles: List[SubtitleTrackItem] = []
        for seg in segments:
            start_time = float(seg.get("start", 0))
            end_time = float(seg.get("end", 0))
            duration = end_time - start_time
            if duration <= 0:
                continue
                
            sub_id = str(uuid.uuid4())
            sub_item = SubtitleTrackItem(
                id=sub_id,
                assetId=request.audioAssetId,
                name=f"Sub {seg.get('id', 0)}",
                start=start_time,
                duration=duration,
                sourceStart=start_time,
                text=seg.get("text", "").strip()
            )
            subtitles.append(sub_item)
            
        return subtitles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Whisper transcript alignment failed: {e}"
        )

@router.post("/generate-metadata", response_model=MetadataGenerateResponse)
async def generate_narration_youtube_metadata(request: MetadataGenerateRequest):
    """Generates Title ideas, description, hashtags, and keywords from the narration script using an LLM."""
    system_instruction = (
        "You are an expert social media manager optimizing YouTube Shorts.\n"
        "Analyze the provided narration script and return a JSON payload with optimized details.\n"
        "Return ONLY a raw JSON object matching this schema:\n"
        "{\n"
        "  \"titles\": [\"title 1\", \"title 2\", \"title 3\", \"title 4\", \"title 5\"],\n"
        "  \"description\": \"engaging youtube description text with keywords\",\n"
        "  \"tags\": [\"tag1\", \"tag2\", \"tag3\"],\n"
        "  \"keywords\": [\"keyword1\", \"keyword2\"]\n"
        "}\n"
        "Do not wrap the response in markdown code blocks like ```json."
    )
    
    prompt = f"Narration script:\n\n{request.script}"
    
    try:
        import json
        raw_response = await call_llm(request.provider, prompt, system_instruction)
        clean_json = raw_response.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            if clean_json.startswith("json"):
                clean_json = clean_json[4:].strip()
                
        data = json.loads(clean_json)
        return MetadataGenerateResponse(
            titles=data.get("titles", [])[:5],
            description=data.get("description", ""),
            tags=data.get("tags", []),
            keywords=data.get("keywords", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI metadata generation failed: {e}"
        )
