from pathlib import Path
from typing import Dict, Any, Optional
from backend.app.providers.base import SpeechToTextProvider
from backend.app.config import WHISPER_MODELS_DIR

class WhisperLocalProvider(SpeechToTextProvider):
    """Speech-to-Text provider running OpenAI Whisper locally."""

    def __init__(self, model_name: str = "tiny"):
        self.model_name = model_name

    def transcribe(self, file_path: Path, language: str = None) -> Dict[str, Any]:
        """Transcribes the target file using local Whisper.
        
        Args:
            file_path: Path to the target audio/video file.
            language: Optional language name or code. If None, auto-detects.
        """
        import whisper
        
        # Load model from local storage download root
        model = whisper.load_model(self.model_name, download_root=str(WHISPER_MODELS_DIR))
        
        # Build transcription arguments
        kwargs = {}
        if language:
            # Normalize language (e.g. Persian/Farsi to 'fa', English to 'en')
            lang_lower = language.lower()
            if "persian" in lang_lower or "farsi" in lang_lower or lang_lower == "fa":
                kwargs["language"] = "fa"
            elif "english" in lang_lower or lang_lower == "en":
                kwargs["language"] = "en"
            else:
                kwargs["language"] = language
                
        result = model.transcribe(str(file_path), **kwargs)
        
        return {
            "text": result.get("text", ""),
            "segments": result.get("segments", [])
        }
