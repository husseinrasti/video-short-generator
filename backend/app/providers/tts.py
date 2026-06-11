import os
import threading
from pathlib import Path
from typing import Dict, Any, List
from backend.app.providers.base import TextToSpeechProvider
from backend.app.config import KOKORO_MODELS_DIR

class KokoroLocalProvider(TextToSpeechProvider):
    """Text-to-Speech provider running Kokoro-82M locally via ONNX Runtime."""

    def __init__(self):
        self._kokoro = None
        self._lock = threading.Lock()

    def _get_kokoro(self):
        """Lazy-loads the Kokoro model in a thread-safe manner."""
        from kokoro_onnx import Kokoro
        
        if self._kokoro is None:
            with self._lock:
                if self._kokoro is None:
                    model_path = KOKORO_MODELS_DIR / "kokoro-v1.0.onnx"
                    voices_path = KOKORO_MODELS_DIR / "voices-v1.0.bin"
                    
                    if not model_path.exists() or not voices_path.exists():
                        raise FileNotFoundError(
                            "Kokoro local model files (kokoro-v1.0.onnx / voices-v1.0.bin) are not installed. "
                            "Please install them via the Local AI Setup first."
                        )
                    
                    print(f"Loading local Kokoro TTS model (ONNX: {model_path}, Voices: {voices_path})...")
                    self._kokoro = Kokoro(str(model_path), str(voices_path))
                    print("Kokoro TTS model loaded successfully.")
                    
        return self._kokoro

    def generate_speech(self, text: str, voice: str, speed: float, output_path: Path) -> Path:
        """Generates speech audio using Kokoro TTS and processes speed/formats via FFmpeg.
        
        Args:
            text: The narration text.
            voice: The selected voice ID (e.g. 'af_heart').
            speed: Playback speed (0.5 to 2.0).
            output_path: Target path (e.g. output.mp3 or output.wav).
        """
        import soundfile as sf
        import uuid
        from backend.app.config import TEMP_DIR
        from backend.app.utils.ffmpeg import adjust_audio_speed
        
        # Default voice if not specified
        voice_id = voice or "af_heart"
        
        # Determine language code based on voice prefix:
        # af_* / am_* -> US English (en-us)
        # bf_* / bm_* -> UK English (en-gb)
        # jf_* / jm_* -> Japanese (ja)
        # zh_*        -> Chinese (zh)
        lang = "en-us"
        if voice_id.startswith("bf_") or voice_id.startswith("bm_"):
            lang = "en-gb"
        elif voice_id.startswith("jf_") or voice_id.startswith("jm_"):
            lang = "ja"
        elif voice_id.startswith("zh_"):
            lang = "zh"

        kokoro = self._get_kokoro()
        
        # 1. Synthesize audio samples at base speed (1.0)
        # We will use FFmpeg's `atempo` for speed adjustments to maintain pitch consistency.
        samples, sample_rate = kokoro.create(
            text,
            voice=voice_id,
            speed=1.0,
            lang=lang
        )
        
        # 2. Save base audio samples to temporary WAV file
        temp_wav_path = TEMP_DIR / f"kokoro_{uuid.uuid4().hex}.wav"
        
        try:
            sf.write(str(temp_wav_path), samples, sample_rate)
            
            # 3. Apply speed adjustment and final format encoding via FFmpeg
            success = adjust_audio_speed(str(temp_wav_path), str(output_path), speed)
            if not success:
                raise RuntimeError("FFmpeg audio post-processing (speed / format conversion) failed.")
        finally:
            # Cleanup temp file
            if temp_wav_path.exists():
                temp_wav_path.unlink()
                
        return output_path

    def get_available_voices(self) -> List[Dict[str, str]]:
        """Returns the list of voices included in Kokoro-82M."""
        return [
            {"id": "af_heart", "name": "Heart (US Female - Recommended)"},
            {"id": "af_bella", "name": "Bella (US Female)"},
            {"id": "af_sarah", "name": "Sarah (US Female)"},
            {"id": "af_nicole", "name": "Nicole (US Female)"},
            {"id": "af_sky", "name": "Sky (US Female)"},
            {"id": "am_adam", "name": "Adam (US Male)"},
            {"id": "am_michael", "name": "Michael (US Male)"},
            {"id": "bf_emma", "name": "Emma (UK Female)"},
            {"id": "bf_isabella", "name": "Isabella (UK Female)"},
            {"id": "bm_george", "name": "George (UK Male)"},
            {"id": "bm_lewis", "name": "Lewis (UK Male)"}
        ]
