import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import httpx
from backend.app.config import STORAGE_DIR

API_KEYS_FILE = STORAGE_DIR / "api_keys.json"

def save_api_keys(keys: Dict[str, str]):
    """Saves API keys to a secure local JSON file."""
    # Ensure folder exists
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

def load_api_keys() -> Dict[str, str]:
    """Loads API keys from the local JSON file."""
    if not API_KEYS_FILE.exists():
        return {"openai": "", "anthropic": "", "gemini": ""}
    try:
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "openai": data.get("openai", ""),
                "anthropic": data.get("anthropic", ""),
                "gemini": data.get("gemini", "")
            }
    except Exception:
        return {"openai": "", "anthropic": "", "gemini": ""}

async def call_llm(provider: str, prompt: str, system_instruction: str = "") -> str:
    """Invokes the selected LLM provider via REST calls."""
    keys = load_api_keys()
    api_key = keys.get(provider.lower(), "").strip()
    
    if not api_key:
        raise ValueError(f"API key for provider {provider} is not configured.")
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        if provider.lower() == "openai":
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
            res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"].strip()
            
        elif provider.lower() == "gemini":
            # Gemini v1beta model call
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            
            # Combine system instruction and prompt for Gemini
            contents = []
            if system_instruction:
                contents.append({"role": "user", "parts": [{"text": f"Instructions: {system_instruction}\n\nTask:\n"}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})
            
            payload = {
                "contents": contents,
                "generationConfig": {"temperature": 0.3}
            }
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            
            candidates = res.json().get("candidates", [])
            if candidates:
                return candidates[0]["content"]["parts"][0]["text"].strip()
            raise ValueError("No text output received from Gemini API")
            
        elif provider.lower() == "anthropic":
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 1024,
                "system": system_instruction,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
            res = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            res.raise_for_status()
            return res.json()["content"][0]["text"].strip()
            
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
