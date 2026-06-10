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
        return {"openai": "", "anthropic": "", "gemini": "", "elevenlabs": ""}
    try:
        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "openai": data.get("openai", ""),
                "anthropic": data.get("anthropic", ""),
                "gemini": data.get("gemini", ""),
                "elevenlabs": data.get("elevenlabs", "")
            }
    except Exception:
        return {"openai": "", "anthropic": "", "gemini": "", "elevenlabs": ""}

async def call_llm(provider: str, prompt: str, system_instruction: str = "", model: Optional[str] = None) -> str:
    """Invokes the selected LLM provider via REST calls, using the specified model if provided."""
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
                "model": model or "gpt-4o-mini",
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
            model_name = model or "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
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
                "model": model or "claude-3-5-haiku-20241022",
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

# Curated lists of recommended models
CURATED_MODELS = {
    "openai": [
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "contextWindow": 128000},
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "contextWindow": 128000},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "openai", "contextWindow": 128000},
        {"id": "o3-mini", "name": "o3-mini", "provider": "openai", "contextWindow": 200000}
    ],
    "anthropic": [
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "provider": "anthropic", "contextWindow": 200000},
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "anthropic", "contextWindow": 200000},
        {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "provider": "anthropic", "contextWindow": 200000}
    ],
    "gemini": [
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "provider": "gemini", "contextWindow": 1048576},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "provider": "gemini", "contextWindow": 1048576},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "gemini", "contextWindow": 2097152}
    ]
}

MODEL_CACHE_FILE = STORAGE_DIR / "cached_models.json"

def load_cached_models() -> dict:
    if MODEL_CACHE_FILE.exists():
        try:
            with open(MODEL_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return CURATED_MODELS

def save_cached_models(models_dict: dict):
    try:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(models_dict, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

async def fetch_provider_models(provider: str, api_key: str) -> List[Dict[str, Any]]:
    """Fetches currently available models for a provider or falls back to curated models."""
    prov = provider.lower()
    if not api_key:
        cached = load_cached_models()
        return cached.get(prov, CURATED_MODELS.get(prov, []))

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if prov == "openai":
                headers = {"Authorization": f"Bearer {api_key}"}
                res = await client.get("https://api.openai.com/v1/models", headers=headers)
                res.raise_for_status()
                models = res.json().get("data", [])
                chat_models = []
                for m in models:
                    mid = m["id"]
                    if mid.startswith("gpt-") or mid.startswith("o1") or mid.startswith("o3"):
                        if any(x in mid for x in ["-instruct", "-realtime", "-audio", "-embedding", "-moderation", "-edit", "dall-e"]):
                            continue
                        context = 128000
                        if "o1" in mid or "o3" in mid:
                            context = 200000
                        chat_models.append({
                            "id": mid,
                            "name": mid.replace("-", " ").title(),
                            "provider": "openai",
                            "contextWindow": context
                        })
                if chat_models:
                    # Sort to bring minis / recommended ones first
                    chat_models.sort(key=lambda x: x["id"])
                    # Save to local cache
                    cached = load_cached_models()
                    cached[prov] = chat_models
                    save_cached_models(cached)
                    return chat_models

            elif prov == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                res = await client.get(url)
                res.raise_for_status()
                models = res.json().get("models", [])
                gemini_models = []
                for m in models:
                    name = m.get("name", "")
                    mid = name.split("/")[-1] if "/" in name else name
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        if "embedding" in mid:
                            continue
                        context = 1048576
                        if "pro" in mid:
                            context = 2097152
                        gemini_models.append({
                            "id": mid,
                            "name": m.get("displayName", mid),
                            "provider": "gemini",
                            "contextWindow": context
                        })
                if gemini_models:
                    cached = load_cached_models()
                    cached[prov] = gemini_models
                    save_cached_models(cached)
                    return gemini_models

            elif prov == "anthropic":
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
                res = await client.get("https://api.anthropic.com/v1/models", headers=headers)
                res.raise_for_status()
                models = res.json().get("data", [])
                anth_models = []
                for m in models:
                    mid = m.get("model", m.get("id", ""))
                    if mid:
                        anth_models.append({
                            "id": mid,
                            "name": mid.replace("-", " ").title(),
                            "provider": "anthropic",
                            "contextWindow": 200000
                        })
                if anth_models:
                    cached = load_cached_models()
                    cached[prov] = anth_models
                    save_cached_models(cached)
                    return anth_models

    except Exception as e:
        print(f"Error dynamically fetching models for {provider}: {e}")

    # Fallback to cache or curated lists
    cached = load_cached_models()
    return cached.get(prov, CURATED_MODELS.get(prov, []))
