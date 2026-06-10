import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Resolve FFmpeg / FFprobe executables
FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"
FFPROBE_PATH = "/opt/homebrew/bin/ffprobe" if os.path.exists("/opt/homebrew/bin/ffprobe") else "ffprobe"

def get_video_metadata(video_path: str) -> Dict[str, Any]:
    """Queries details about a video file using ffprobe."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-show_entries", "format=duration:stream=width,height,codec_name,r_frame_rate",
        "-of", "json",
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        streams = data.get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_name") != "audio"), {})
        format_info = data.get("format", {})
        
        # Calculate frame rate
        fps = 30.0
        r_frame_rate = video_stream.get("r_frame_rate", "30/1")
        if "/" in r_frame_rate:
            num, den = map(int, r_frame_rate.split("/"))
            if den != 0:
                fps = round(num / den, 2)
                
        duration = float(format_info.get("duration", 0))
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        
        return {
            "duration": duration,
            "width": width,
            "height": height,
            "fps": fps,
            "codec": video_stream.get("codec_name")
        }
    except Exception as e:
        print(f"Error executing ffprobe for {video_path}: {e}")
        return {
            "duration": 0.0,
            "width": 0,
            "height": 0,
            "fps": 30.0,
            "codec": "unknown"
        }

def extract_thumbnail(video_path: str, thumbnail_path: str, timestamp: float = 1.0) -> bool:
    """Extracts a thumbnail frame from the video at the given timestamp."""
    if not os.path.exists(video_path):
        return False
        
    # Build output directory if needed
    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
    
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        thumbnail_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error extracting thumbnail: {e.stderr}")
        # Try at 0.0 timestamp as fallback
        if timestamp != 0.0:
            return extract_thumbnail(video_path, thumbnail_path, 0.0)
        return False
    except Exception as e:
        print(f"General error extracting thumbnail: {e}")
        return False

def trim_video(video_path: str, output_path: str, start: float, duration: float) -> bool:
    """Extracts a clip from video with high temporal precision using libx264 re-encoding."""
    if not os.path.exists(video_path):
        return False
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Accurate trimming uses seek BEFORE the input, but we also specify -ss/t for re-encoding
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-ss", str(start),
        "-t", str(duration),
        "-i", video_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "fast",
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error trimming video: {e.stderr}")
        return False
    except Exception as e:
        print(f"General error trimming video: {e}")
        return False

def extract_audio(video_path: str, output_path: str, out_format: str = "mp3") -> bool:
    """Extracts audio track from video file to MP3 or WAV format."""
    if not os.path.exists(video_path):
        return False
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cmd = [FFMPEG_PATH, "-y", "-i", video_path, "-vn"]
    
    if out_format.lower() == "mp3":
        cmd.extend(["-acodec", "libmp3lame", "-q:a", "2"])
    elif out_format.lower() == "wav":
        cmd.extend(["-acodec", "pcm_s16le", "-ar", "44100"])
    else:
        # Generic copy/extract
        cmd.extend(["-acodec", "copy"])
        
    cmd.append(output_path)
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error extracting audio: {e.stderr}")
        return False
    except Exception as e:
        print(f"General error extracting audio: {e}")
        return False

def detect_silence(file_path: str, noise_threshold: float = -30.0, min_duration: float = 0.5) -> list:
    """Detects periods of silence in an audio/video file using FFmpeg's silencedetect filter."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    cmd = [
        FFMPEG_PATH,
        "-i", file_path,
        "-af", f"silencedetect=noise={noise_threshold}dB:d={min_duration}",
        "-f", "null",
        "-"
    ]
    
    try:
        # Silence output goes to stderr
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        stderr_content = result.stderr
        
        silences = []
        current_silence = {}
        
        for line in stderr_content.splitlines():
            if "silence_start:" in line:
                try:
                    val = line.split("silence_start:")[1].strip().split()[0]
                    current_silence["start"] = float(val)
                except (IndexError, ValueError):
                    pass
            elif "silence_end:" in line:
                try:
                    end_part = line.split("silence_end:")[1].strip()
                    end_val = end_part.split("|")[0].strip()
                    current_silence["end"] = float(end_val)
                    
                    if "silence_duration:" in line:
                        dur_val = line.split("silence_duration:")[1].strip()
                        current_silence["duration"] = float(dur_val)
                    else:
                        current_silence["duration"] = current_silence["end"] - current_silence.get("start", 0.0)
                    
                    if "start" in current_silence:
                        silences.append(current_silence)
                    current_silence = {}
                except (IndexError, ValueError):
                    pass
        return silences
    except Exception as e:
        print(f"Error executing silencedetect: {e}")
        return []


