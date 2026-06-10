import os
import uuid
import subprocess
import re
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from backend.app.config import VIDEOS_DIR, AUDIO_DIR, RENDERS_DIR, TEMP_DIR
from backend.app.models.project import Project, VideoTrackItem, AudioTrackItem
from backend.app.utils.storage import load_project
from backend.app.utils.ffmpeg import FFMPEG_PATH

# Thread-safe in-memory task tracker
RENDER_TASKS: Dict[str, Dict[str, Any]] = {}
renders_lock = threading.Lock()

# Process tracking for task cancellation
RENDER_PROCESSES: Dict[str, subprocess.Popen] = {}
processes_lock = threading.Lock()

RESOLUTIONS = {
    "9:16": {
        "720p": (720, 1280),
        "1080p": (1080, 1920),
        "1440p": (1440, 2560)
    },
    "16:9": {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "1440p": (2560, 1440)
    },
    "1:1": {
        "720p": (720, 720),
        "1080p": (1080, 1080),
        "1440p": (1440, 1440)
    }
}

def update_render_status(task_id: str, updates: Dict[str, Any]):
    with renders_lock:
        if task_id in RENDER_TASKS:
            RENDER_TASKS[task_id].update(updates)

def get_render_status(task_id: str) -> Optional[Dict[str, Any]]:
    with renders_lock:
        return RENDER_TASKS.get(task_id)

def _parse_time(time_str: str) -> float:
    """Parses FFmpeg time output HH:MM:SS.ms into seconds."""
    try:
        parts = time_str.split(":")
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return 0.0

def _render_worker(task_id: str, project_id: str, aspect_ratio: str, resolution: str):
    """FFmpeg video timeline rendering background task."""
    try:
        project = load_project(project_id)
        if not project:
            update_render_status(task_id, {"status": "failed", "error": "Project not found"})
            return

        # Target dimensions
        dimensions = RESOLUTIONS.get(aspect_ratio, {}).get(resolution)
        if not dimensions:
            update_render_status(task_id, {"status": "failed", "error": f"Invalid aspect ratio or resolution: {aspect_ratio} {resolution}"})
            return
            
        width, height = dimensions
        
        # Sort video track items
        video_items = sorted(project.timeline.tracks.video, key=lambda x: x.start)
        audio_items = sorted(project.timeline.tracks.audio, key=lambda x: x.start)
        
        if not video_items:
            update_render_status(task_id, {"status": "failed", "error": "Video track is empty. Add clips to the timeline."})
            return
            
        # Calculate total project duration based on video track items
        total_duration = sum(item.duration for item in video_items)
        if total_duration <= 0:
            update_render_status(task_id, {"status": "failed", "error": "Project duration must be greater than 0"})
            return

        # Gather unique assets to map as inputs
        # We need to map assetId -> input index
        # Let's map unique asset files to prevent loading the same file multiple times
        unique_assets_map = {}  # assetPath -> input index
        inputs_list = []
        
        # Helper to get local filesystem path for asset
        def get_asset_file_path(path: str) -> Path:
            # path is relative to storage folder, e.g. "videos/xxx.mp4"
            return VIDEOS_DIR.parent / path

        # Add video track assets
        for item in video_items:
            asset = next((a for a in project.assets if a.id == item.assetId), None)
            if not asset:
                update_render_status(task_id, {"status": "failed", "error": f"Asset {item.assetId} not found in project"})
                return
            
            asset_path = str(get_asset_file_path(asset.path))
            if asset_path not in unique_assets_map:
                unique_assets_map[asset_path] = len(inputs_list)
                inputs_list.append(asset_path)
                
        # Add audio track assets
        for item in audio_items:
            asset = next((a for a in project.assets if a.id == item.assetId), None)
            if not asset:
                update_render_status(task_id, {"status": "failed", "error": f"Asset {item.assetId} not found in project"})
                return
            
            asset_path = str(get_asset_file_path(asset.path))
            if asset_path not in unique_assets_map:
                unique_assets_map[asset_path] = len(inputs_list)
                inputs_list.append(asset_path)

        # Build FFmpeg command inputs
        cmd = [FFMPEG_PATH, "-y"]
        for inp in inputs_list:
            cmd.extend(["-i", inp])

        # Build filter_complex graph
        filter_parts = []
        
        # 1. Process Video Clips: Trim, Scale, Pad, and set PTS
        video_concat_nodes = []
        audio_concat_nodes = []
        
        for idx, item in enumerate(video_items):
            asset = next((a for a in project.assets if a.id == item.assetId), None)
            asset_path = str(get_asset_file_path(asset.path))
            input_idx = unique_assets_map[asset_path]
            
            # Label nodes
            v_node = f"v{idx}"
            a_node = f"a{idx}"
            
            # Trim and format video to target dimensions (with padding/letterboxing)
            filter_parts.append(
                f"[{input_idx}:v]trim=start={item.sourceStart}:duration={item.duration},setpts=PTS-STARTPTS,"
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1[{v_node}]"
            )
            
            # Trim audio and adjust volume
            audio_vol = item.volume if not item.muted else 0.0
            filter_parts.append(
                f"[{input_idx}:a]atrim=start={item.sourceStart}:duration={item.duration},asetpts=PTS-STARTPTS,"
                f"volume={audio_vol}[{a_node}]"
            )
            
            video_concat_nodes.append(f"[{v_node}]")
            audio_concat_nodes.append(f"[{a_node}]")
            
        # 2. Concatenate video segments
        num_segments = len(video_items)
        concat_v_out = "v_concat"
        concat_a_out = "a_concat"
        
        # Join all segment nodes
        segment_nodes = ""
        for i in range(num_segments):
            segment_nodes += f"{video_concat_nodes[i]}{audio_concat_nodes[i]}"
            
        filter_parts.append(f"{segment_nodes}concat=n={num_segments}:v=1:a=1[{concat_v_out}][{concat_a_out}]")

        # 3. Handle separate Audio Tracks (e.g. background music)
        final_audio_out = concat_a_out
        
        if audio_items:
            # We want to mix the background audio track on top of our video audio
            # Process each audio timeline item
            audio_mix_nodes = [f"[{concat_a_out}]"]
            
            for idx, item in enumerate(audio_items):
                asset = next((a for a in project.assets if a.id == item.assetId), None)
                asset_path = str(get_asset_file_path(asset.path))
                input_idx = unique_assets_map[asset_path]
                
                mix_node = f"bg_a{idx}"
                
                # Trim and offset/delay background audio to match its timeline start
                # We use 'adelay' to position it on the timeline
                delay_ms = int(item.start * 1000)
                
                # We trim it first
                filter_parts.append(
                    f"[{input_idx}:a]atrim=start={item.sourceStart}:duration={item.duration},asetpts=PTS-STARTPTS,"
                    f"volume={item.volume},adelay={delay_ms}|{delay_ms}[{mix_node}]"
                )
                audio_mix_nodes.append(f"[{mix_node}]")
                
            # Mix all audio nodes together
            mixed_audio_out = "a_mixed"
            mix_inputs_str = "".join(audio_mix_nodes)
            filter_parts.append(f"{mix_inputs_str}amix=inputs={len(audio_mix_nodes)}:duration=first[{mixed_audio_out}]")
            final_audio_out = mixed_audio_out

        # Complete the filter_complex graph
        filter_graph = ";".join(filter_parts)
        
        # Resolve output file
        render_id = str(uuid.uuid4())
        output_filename = f"render_{render_id}.mp4"
        output_path = RENDERS_DIR / output_filename
        
        # Append filter graph and encoder settings to command
        cmd.extend([
            "-filter_complex", filter_graph,
            "-map", f"[{concat_v_out}]",
            "-map", f"[{final_audio_out}]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(output_path)
        ])
        
        # Boot FFmpeg process and capture stderr to track progress
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        with processes_lock:
            task = RENDER_TASKS.get(task_id)
            if task and task.get("status") == "cancelled":
                try:
                    process.kill()
                except Exception:
                    pass
                return
            RENDER_PROCESSES[task_id] = process

        try:
            # Regex to match time=HH:MM:SS.ms
            time_regex = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")
            
            # Read stderr line-by-line to parse progress
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                    
                match = time_regex.search(line)
                if match:
                    elapsed_time = _parse_time(match.group(1))
                    progress = min(round((elapsed_time / total_duration) * 100, 1), 99.0)
                    with renders_lock:
                        t = RENDER_TASKS.get(task_id)
                        if t and t.get("status") == "cancelled":
                            break
                    update_render_status(task_id, {
                        "status": "rendering",
                        "progress": progress
                    })
                    
            process.wait()
            
            with renders_lock:
                t = RENDER_TASKS.get(task_id)
                if t and t.get("status") == "cancelled":
                    return

            if process.returncode == 0:
                update_render_status(task_id, {
                    "status": "completed",
                    "progress": 100.0,
                    "outputPath": f"renders/{output_filename}"
                })
            else:
                stderr_out = process.stderr.read()
                update_render_status(task_id, {
                    "status": "failed",
                    "error": f"FFmpeg failed with exit code {process.returncode}. {stderr_out}"
                })
        finally:
            with processes_lock:
                if task_id in RENDER_PROCESSES:
                    RENDER_PROCESSES.pop(task_id)
            
    except Exception as e:
        print(f"Error rendering project: {e}")
        update_render_status(task_id, {
            "status": "failed",
            "error": str(e)
        })

def start_render_task(project_id: str, aspect_ratio: str, resolution: str) -> str:
    """Spawns background thread to compile the project video timeline."""
    task_id = str(uuid.uuid4())
    
    with renders_lock:
        RENDER_TASKS[task_id] = {
            "id": task_id,
            "projectId": project_id,
            "aspectRatio": aspect_ratio,
            "resolution": resolution,
            "status": "pending",
            "progress": 0.0,
            "error": None,
            "outputPath": None
        }
        
    thread = threading.Thread(
        target=_render_worker,
        args=(task_id, project_id, aspect_ratio, resolution),
        daemon=True
    )
    thread.start()
    return task_id

def cancel_render_task(task_id: str) -> bool:
    """Cancels a timeline rendering task and terminates the FFmpeg process."""
    with renders_lock:
        task = RENDER_TASKS.get(task_id)
        if task:
            task["status"] = "cancelled"
    
    with processes_lock:
        process = RENDER_PROCESSES.get(task_id)
        if process:
            try:
                process.terminate()
                process.wait(timeout=1.0)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
            RENDER_PROCESSES.pop(task_id, None)
            return True
    return False
