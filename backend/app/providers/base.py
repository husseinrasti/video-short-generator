import abc
from pathlib import Path
from typing import Dict, Any, List

class SpeechToTextProvider(abc.ABC):
    """Abstract base class for all Speech-to-Text providers."""

    @abc.abstractmethod
    def transcribe(self, file_path: Path, language: str = None) -> Dict[str, Any]:
        """Transcribes the video or audio file at file_path.
        
        Args:
            file_path: Absolute Path to the target audio/video file.
            language: Optional language code (e.g. 'en', 'fa'). If None, should auto-detect.
            
        Returns:
            Dict containing:
                - "text": The full concatenated transcription text.
                - "segments": A list of dicts, each with keys:
                    - "start": float start time in seconds
                    - "end": float end time in seconds
                    - "text": str segment text
        """
        pass


class TextToSpeechProvider(abc.ABC):
    """Abstract base class for all Text-to-Speech providers."""

    @abc.abstractmethod
    def generate_speech(self, text: str, voice: str, speed: float, output_path: Path) -> Path:
        """Generates speech audio from text and saves it to output_path.
        
        Args:
            text: The text script to read.
            voice: The voice ID/name to use.
            speed: Speaking speed factor (e.g. 1.0, 1.2).
            output_path: Target output path (supporting WAV or MP3).
            
        Returns:
            Path to the final output file.
        """
        pass

    @abc.abstractmethod
    def get_available_voices(self) -> List[Dict[str, str]]:
        """Returns the list of voices supported by this provider.
        
        Returns:
            List of dicts, e.g. [{"id": "af_heart", "name": "Heart (US Female)"}]
        """
        pass
