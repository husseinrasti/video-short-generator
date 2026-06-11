import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"

# Storage Subdirectories
VIDEOS_DIR = STORAGE_DIR / "videos"
AUDIO_DIR = STORAGE_DIR / "audio"
IMAGES_DIR = STORAGE_DIR / "images"
SUBTITLES_DIR = STORAGE_DIR / "subtitles"
PROJECTS_DIR = STORAGE_DIR / "projects"
RENDERS_DIR = STORAGE_DIR / "renders"
TEMP_DIR = STORAGE_DIR / "temp"
MODELS_DIR = STORAGE_DIR / "models"
WHISPER_MODELS_DIR = MODELS_DIR / "whisper"
KOKORO_MODELS_DIR = MODELS_DIR / "kokoro"

# Ensure all directories exist
for directory in [
    STORAGE_DIR,
    VIDEOS_DIR,
    AUDIO_DIR,
    IMAGES_DIR,
    SUBTITLES_DIR,
    PROJECTS_DIR,
    RENDERS_DIR,
    TEMP_DIR,
    MODELS_DIR,
    WHISPER_MODELS_DIR,
    KOKORO_MODELS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# Application Config
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
