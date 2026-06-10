import os
import httpx
from pathlib import Path
from backend.app.utils.ai import load_api_keys

async def generate_openai_tts(text: str, voice: str, speed: float, model: str, output_path: Path):
    """Calls OpenAI TTS API to generate speech."""
    keys = load_api_keys()
    api_key = keys.get("openai", "").strip()
    if not api_key:
        raise ValueError("OpenAI API key is not configured.")
        
    async with httpx.AsyncClient(timeout=60.0) as client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or "tts-1",
            "input": text,
            "voice": voice or "alloy",
            "speed": speed
        }
        res = await client.post("https://api.openai.com/v1/audio/speech", headers=headers, json=payload)
        res.raise_for_status()
        
        # Write binary content to file
        with open(output_path, "wb") as f:
            f.write(res.content)

async def generate_elevenlabs_tts(text: str, voice: str, model: str, output_path: Path):
    """Calls ElevenLabs Text-to-Speech API to generate speech."""
    keys = load_api_keys()
    api_key = keys.get("elevenlabs", "").strip()
    if not api_key:
        raise ValueError("ElevenLabs API key is not configured.")
        
    voice_id = voice or "21m00Tcm4TlvDq8ikWAM"
    model_id = model or "eleven_monolingual_v1"
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        res = await client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        
        with open(output_path, "wb") as f:
            f.write(res.content)
