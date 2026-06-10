"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Play,
  Pause,
  Plus,
  Trash2,
  Download,
  Film,
  Music,
  FileText,
  Sparkles,
  Settings,
  Scissors,
  Volume2,
  RefreshCw,
  FolderOpen,
  ArrowRight,
  Maximize2,
  CheckCircle,
  AlertCircle,
  Loader2,
  Tv,
  Merge,
  Split,
  Edit2,
  Eye,
  Type,
  Image as ImageIcon,
  Key,
  Copy,
  Scissors as TrimIcon,
  VolumeX
} from "lucide-react";

// API Base URL config
const API_BASE = "http://localhost:8000";

interface Asset {
  id: string;
  name: string;
  type: string;
  path: string;
  duration?: number;
  resolution?: string;
  createdAt: string;
}

interface TimelineItem {
  id: string;
  assetId?: string;
  name: string;
  start: number;
  duration: number;
  sourceStart: number;
}

interface VideoTrackItem extends TimelineItem {
  volume: number;
  muted: boolean;
}

interface AudioTrackItem extends TimelineItem {
  volume: number;
}

interface SubtitleTrackItem extends TimelineItem {
  text: string;
}

interface TextStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: string;
  color: string;
  backgroundColor: string;
  borderWidth: number;
  borderColor: string;
  shadowColor: string;
  shadowBlur: number;
  opacity: number;
  x: number;
  y: number;
  rotation: number;
}

interface TextTrackItem extends TimelineItem {
  text: string;
  style: TextStyle;
}

interface ImageStyle {
  width: number;
  height: number;
  x: number;
  y: number;
  rotation: number;
  opacity: number;
  layerOrder: number;
}

interface ImageTrackItem extends TimelineItem {
  style: ImageStyle;
}

interface TimelineTracks {
  video: VideoTrackItem[];
  audio: AudioTrackItem[];
  subtitle: SubtitleTrackItem[];
  text: TextTrackItem[];
  image: ImageTrackItem[];
}

interface Project {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  timeline: {
    tracks: TimelineTracks;
  };
  assets: Asset[];
}

interface ProjectMeta {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

interface DownloadTask {
  id: string;
  url: string;
  projectId: string;
  status: string;
  progress: number;
  error?: string;
  asset?: Asset;
}

interface RenderTask {
  id: string;
  projectId: string;
  aspectRatio: string;
  resolution: string;
  status: string;
  progress: number;
  error?: string;
  outputPath?: string;
}

interface TranscribeTask {
  id: string;
  projectId: string;
  assetId: string;
  status: string;
  progress: number;
  error?: string;
  transcriptPath?: string;
  subtitlesCount?: number;
}

interface AIKeyStatus {
  openai: boolean;
  anthropic: boolean;
  gemini: boolean;
}

interface AIMetadata {
  titles: string[];
  description: string;
  tags: string[];
  keywords: string[];
}

interface AIHighlight {
  start: number;
  end: number;
  reason: string;
}

interface SilenceSegment {
  start: number;
  end: number;
  duration: number;
}

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 10);
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}.${ms}`;
};

export default function VideoEditorWorkspace() {
  // Projects state
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [newProjectName, setNewProjectName] = useState("");
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);

  // Video download state
  const [downloadUrl, setDownloadUrl] = useState("");
  const [activeDownloads, setActiveDownloads] = useState<Record<string, DownloadTask>>({});

  // Media Player playback state
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playerDuration, setPlayerDuration] = useState(0);
  
  // Timeline playback mode
  const [isTimelinePlayback, setIsTimelinePlayback] = useState(false);
  const [timelineDuration, setTimelineDuration] = useState(0);
  
  // Render / Export state
  const [exportAspectRatio, setExportAspectRatio] = useState("9:16");
  const [exportResolution, setExportResolution] = useState("1080p");
  const [activeRender, setActiveRender] = useState<RenderTask | null>(null);
  const [showRenderModal, setShowRenderModal] = useState(false);

  // Transcription state
  const [activeTranscribe, setActiveTranscribe] = useState<TranscribeTask | null>(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [selectedSubtitleId, setSelectedSubtitleId] = useState<string | null>(null);
  const [subtitleStyle, setSubtitleStyle] = useState<"tiktok" | "shorts" | "minimal">("tiktok");

  // AI Panel & API Keys state (Phase 7)
  const [apiKeysStatus, setApiKeysStatus] = useState<AIKeyStatus>({ openai: false, anthropic: false, gemini: false });
  const [showKeysModal, setShowKeysModal] = useState(false);
  const [openaiKeyInput, setOpenaiKeyInput] = useState("");
  const [anthropicKeyInput, setAnthropicKeyInput] = useState("");
  const [geminiKeyInput, setGeminiKeyInput] = useState("");
  const [aiProvider, setAiProvider] = useState("openai");
  const [isGeneratingMetadata, setIsGeneratingMetadata] = useState(false);
  const [aiMetadata, setAiMetadata] = useState<AIMetadata | null>(null);
  const [isDetectingHighlights, setIsDetectingHighlights] = useState(false);
  const [aiHighlights, setAiHighlights] = useState<AIHighlight[]>([]);

  // Silence Detection state
  const [detectedSilences, setDetectedSilences] = useState<SilenceSegment[]>([]);
  const [isDetectingSilence, setIsDetectingSilence] = useState(false);
  const [noiseThreshold, setNoiseThreshold] = useState(-30.0);
  const [minSilenceDuration, setMinSilenceDuration] = useState(0.5);

  // Text / Image Overlay Editor state (Phase 7)
  const [selectedTextId, setSelectedTextId] = useState<string | null>(null);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [textInputVal, setTextInputVal] = useState("");
  const [textX, setTextX] = useState(0.5);
  const [textY, setTextY] = useState(0.5);
  const [textSize, setTextSize] = useState(40);
  const [textColor, setTextColor] = useState("#ffffff");
  const [textBgColor, setTextBgColor] = useState("transparent");
  const [textFont, setTextFont] = useState("Inter");
  const [textWeight, setTextWeight] = useState("bold");
  const [textShadowColor, setTextShadowColor] = useState("transparent");
  const [textShadowBlur, setTextShadowBlur] = useState(0);

  const [imgX, setImgX] = useState(0.5);
  const [imgY, setImgY] = useState(0.5);
  const [imgWidth, setImgWidth] = useState(0.3);
  const [imgHeight, setImgHeight] = useState(0.3);
  
  // Visual workspace state
  const [activeTab, setActiveTab] = useState<"assets" | "subtitles" | "ai" | "settings">("assets");
  const [zoomLevel, setZoomLevel] = useState(20);
  
  // Trimming tool state (Feature 3)
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(10);
  const [isTrimming, setIsTrimming] = useState(false);
  const [isExtractingAudio, setIsExtractingAudio] = useState(false);
  
  // References
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const timelineContainerRef = useRef<HTMLDivElement | null>(null);
  const playbackIntervalRef = useRef<any>(null);
  
  // Undo/Redo state stack
  const [past, setPast] = useState<Project[]>([]);
  const [future, setFuture] = useState<Project[]>([]);
  const lastHistoryTime = useRef<number>(0);

  // Load project list and API keys status on startup
  useEffect(() => {
    fetchProjects();
    fetchKeysStatus();
  }, []);

  // Poll downloads
  useEffect(() => {
    const activeTaskIds = Object.keys(activeDownloads).filter(
      (id) => activeDownloads[id].status === "pending" || activeDownloads[id].status === "downloading" || activeDownloads[id].status === "processing"
    );

    if (activeTaskIds.length === 0) return;

    const interval = setInterval(() => {
      activeTaskIds.forEach((taskId) => {
        checkDownloadStatus(taskId);
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [activeDownloads]);

  // Poll render task
  useEffect(() => {
    if (!activeRender) return;
    if (activeRender.status === "completed" || activeRender.status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/timeline/render/${activeRender.id}`);
        if (res.ok) {
          const task = await res.json();
          setActiveRender(task);
        }
      } catch (err) {
        console.error(err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeRender]);

  // Poll Whisper transcription
  useEffect(() => {
    if (!activeTranscribe) return;
    if (activeTranscribe.status === "completed" || activeTranscribe.status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/audio/transcribe/${activeTranscribe.id}`);
        if (res.ok) {
          const task = await res.json();
          setActiveTranscribe(task);
          if (task.status === "completed") {
            setIsTranscribing(false);
            if (activeProject) loadProjectDetails(activeProject.id);
          } else if (task.status === "failed") {
            setIsTranscribing(false);
            alert(`Transcription failed: ${task.error}`);
          }
        }
      } catch (err) {
        console.error(err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeTranscribe, activeProject]);

  // Sync trimEnd
  useEffect(() => {
    if (selectedAsset && selectedAsset.duration) {
      setTrimStart(0);
      setTrimEnd(Math.min(selectedAsset.duration, 10));
    }
  }, [selectedAsset]);

  // Compute timeline duration
  useEffect(() => {
    if (activeProject) {
      const vDuration = activeProject.timeline.tracks.video.reduce((max, item) => Math.max(max, item.start + item.duration), 0);
      const aDuration = activeProject.timeline.tracks.audio.reduce((max, item) => Math.max(max, item.start + item.duration), 0);
      const tDuration = activeProject.timeline.tracks.text.reduce((max, item) => Math.max(max, item.start + item.duration), 0);
      setTimelineDuration(Math.max(vDuration, aDuration, tDuration));
    } else {
      setTimelineDuration(0);
    }
  }, [activeProject]);

  // Auto-save every 30 seconds (Feature 14)
  useEffect(() => {
    if (!activeProject) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/projects/${activeProject.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(activeProject),
        });
        if (res.ok) {
          console.log("Project auto-saved successfully.");
        }
      } catch (err) {
        console.error("Auto-save failed", err);
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [activeProject]);

  // Keyboard Shortcuts (Nice-to-Have)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const active = document.activeElement;

      // Undo/Redo Shortcuts (Allow native text inputs to handle undo/redo when focused)
      const isMac = typeof window !== "undefined" && navigator.platform.toUpperCase().indexOf("MAC") >= 0;
      const isUndo = (isMac ? e.metaKey : e.ctrlKey) && e.key === "z" && !e.shiftKey;
      const isRedo = (isMac ? e.metaKey : e.ctrlKey) && (e.key === "y" || (e.key === "z" && e.shiftKey));

      if (
        active &&
        (active.tagName === "INPUT" ||
          active.tagName === "TEXTAREA" ||
          active.getAttribute("contenteditable") === "true")
      ) {
        if (isUndo || isRedo) return; // Native input behavior
      }

      if (isUndo) {
        e.preventDefault();
        handleUndo();
        return;
      }
      if (isRedo) {
        e.preventDefault();
        handleRedo();
        return;
      }

      if (
        active &&
        (active.tagName === "INPUT" ||
          active.tagName === "TEXTAREA" ||
          active.getAttribute("contenteditable") === "true")
      ) {
        return;
      }

      if (e.code === "Space") {
        e.preventDefault();
        handlePlayPause();
      } else if (e.code === "KeyS") {
        e.preventDefault();
        if (selectedSubtitleId) {
          handleSplitSubtitle(selectedSubtitleId);
        } else if (activeProject) {
          const activeVideo = activeProject.timeline.tracks.video.find(
            (v) => currentTime >= v.start && currentTime < v.start + v.duration
          );
          if (activeVideo) handleSplitTimelineItem("video", activeVideo.id);
        }
      } else if (e.code === "Delete" || e.code === "Backspace") {
        e.preventDefault();
        if (selectedTextId) {
          handleRemoveTimelineItemWrapper("text", selectedTextId);
        } else if (selectedImageId) {
          handleRemoveTimelineItemWrapper("image", selectedImageId);
        } else if (selectedSubtitleId) {
          handleRemoveTimelineItemWrapper("subtitle", selectedSubtitleId);
        } else if (activeProject) {
          const activeVideo = activeProject.timeline.tracks.video.find(
            (v) => currentTime >= v.start && currentTime < v.start + v.duration
          );
          if (activeVideo) handleRemoveTimelineItemWrapper("video", activeVideo.id);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeProject, currentTime, selectedTextId, selectedImageId, selectedSubtitleId, past, future]);

  // Sync player progress
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      if (!isTimelinePlayback) {
        setCurrentTime(video.currentTime);
      }
    };

    const handleLoadedMetadata = () => {
      if (!isTimelinePlayback) setPlayerDuration(video.duration);
    };

    const handleEnded = () => {
      if (!isTimelinePlayback) setIsPlaying(false);
    };

    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("loadedmetadata", handleLoadedMetadata);
    video.addEventListener("ended", handleEnded);

    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("loadedmetadata", handleLoadedMetadata);
      video.removeEventListener("ended", handleEnded);
    };
  }, [selectedAsset, isTimelinePlayback]);

  // Timeline simulated playback logic
  useEffect(() => {
    if (isTimelinePlayback && isPlaying) {
      const step = 0.1;
      playbackIntervalRef.current = setInterval(() => {
        setCurrentTime((prevTime) => {
          const nextTime = prevTime + step;
          if (nextTime >= timelineDuration) {
            setIsPlaying(false);
            return timelineDuration;
          }
          
          if (activeProject) {
            const activeItem = activeProject.timeline.tracks.video.find(
              (item) => nextTime >= item.start && nextTime < item.start + item.duration
            );
            
            if (activeItem) {
              const asset = activeProject.assets.find((a) => a.id === activeItem.assetId);
              if (asset) {
                if (selectedAsset?.id !== asset.id) {
                  setSelectedAsset(asset);
                }
                const relativeTime = nextTime - activeItem.start + activeItem.sourceStart;
                if (videoRef.current) {
                  if (Math.abs(videoRef.current.currentTime - relativeTime) > 0.3) {
                    videoRef.current.currentTime = relativeTime;
                  }
                  if (videoRef.current.paused) {
                    videoRef.current.play().catch(err => {});
                  }
                }
              }
            } else {
              if (videoRef.current && !videoRef.current.paused) {
                videoRef.current.pause();
              }
            }
          }
          return nextTime;
        });
      }, 100);
    } else {
      if (playbackIntervalRef.current) clearInterval(playbackIntervalRef.current);
      if (videoRef.current && isTimelinePlayback) videoRef.current.pause();
    }

    return () => {
      if (playbackIntervalRef.current) clearInterval(playbackIntervalRef.current);
    };
  }, [isTimelinePlayback, isPlaying, timelineDuration, activeProject, selectedAsset]);

  // Sync state values when selected text item changes
  useEffect(() => {
    if (activeProject && selectedTextId) {
      const textItem = activeProject.timeline.tracks.text.find(t => t.id === selectedTextId);
      if (textItem) {
        setTextInputVal(textItem.text);
        setTextX(textItem.style.x);
        setTextY(textItem.style.y);
        setTextSize(textItem.style.fontSize);
        setTextColor(textItem.style.color);
        setTextBgColor(textItem.style.backgroundColor);
        setTextFont(textItem.style.fontFamily);
        setTextWeight(textItem.style.fontWeight);
        setTextShadowColor(textItem.style.shadowColor);
        setTextShadowBlur(textItem.style.shadowBlur);
      }
    }
  }, [selectedTextId, activeProject]);

  // Sync state values when selected image item changes
  useEffect(() => {
    if (activeProject && selectedImageId) {
      const imgItem = activeProject.timeline.tracks.image.find(i => i.id === selectedImageId);
      if (imgItem) {
        setImgX(imgItem.style.x);
        setImgY(imgItem.style.y);
        setImgWidth(imgItem.style.width);
        setImgHeight(imgItem.style.height);
      }
    }
  }, [selectedImageId, activeProject]);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
        if (data.length > 0 && !activeProject) loadProjectDetails(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadProjectDetails = async (projectId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}`);
      if (res.ok) {
        const project = await res.json();
        setActiveProject(project);
        setPast([]);
        setFuture([]);
        
        const videoAssets = project.assets.filter((a: Asset) => a.type === "video");
        if (videoAssets.length > 0 && !selectedAsset) {
          setSelectedAsset(videoAssets[0]);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const updateProjectState = async (updatedProject: Project) => {
    if (!activeProject) return null;
    try {
      const res = await fetch(`${API_BASE}/api/projects/${activeProject.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedProject)
      });
      if (res.ok) {
        const saved = await res.json();
        const now = Date.now();
        // Debounce history recording to group fast consecutive changes (like slider drags)
        if (!lastHistoryTime.current || (now - lastHistoryTime.current >= 1500)) {
          setPast((prev) => [...prev, activeProject]);
          setFuture([]); // Clear redo stack on new action
        }
        lastHistoryTime.current = now;
        setActiveProject(saved);
        return saved;
      }
    } catch (err) {
      console.error("Failed to update project state", err);
    }
    return null;
  };

  const handleUndo = async () => {
    if (past.length === 0 || !activeProject) return;
    const previous = past[past.length - 1];
    const newPast = past.slice(0, past.length - 1);

    try {
      const res = await fetch(`${API_BASE}/api/projects/${activeProject.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(previous)
      });
      if (res.ok) {
        const saved = await res.json();
        setPast(newPast);
        setFuture((prev) => [activeProject, ...prev]);
        setActiveProject(saved);
      }
    } catch (err) {
      console.error("Undo failed", err);
    }
  };

  const handleRedo = async () => {
    if (future.length === 0 || !activeProject) return;
    const nextState = future[0];
    const newFuture = future.slice(1);

    try {
      const res = await fetch(`${API_BASE}/api/projects/${activeProject.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextState)
      });
      if (res.ok) {
        const saved = await res.json();
        setPast((prev) => [...prev, activeProject]);
        setFuture(newFuture);
        setActiveProject(saved);
      }
    } catch (err) {
      console.error("Redo failed", err);
    }
  };

  const fetchKeysStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/ai/keys`);
      if (res.ok) {
        const data = await res.json();
        setApiKeysStatus(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveKeys = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/ai/keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          openai: openaiKeyInput,
          anthropic: anthropicKeyInput,
          gemini: geminiKeyInput
        })
      });
      if (res.ok) {
        setShowKeysModal(false);
        fetchKeysStatus();
        alert("API keys successfully saved locally.");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to save API keys.");
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/api/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newProjectName })
      });
      if (res.ok) {
        const newProj = await res.json();
        setActiveProject(newProj);
        setPast([]);
        setFuture([]);
        setNewProjectName("");
        setShowNewProjectModal(false);
        fetchProjects();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm("Are you sure you want to delete this project?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}`, { method: "DELETE" });
      if (res.ok) {
        if (activeProject?.id === projectId) {
          setActiveProject(null);
          setSelectedAsset(null);
        }
        fetchProjects();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDownloadVideo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!downloadUrl.trim() || !activeProject) return;
    try {
      const res = await fetch(`${API_BASE}/api/videos/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: downloadUrl, projectId: activeProject.id })
      });
      if (res.ok) {
        const data = await res.json();
        setActiveDownloads((prev) => ({
          ...prev,
          [data.taskId]: {
            id: data.taskId,
            url: downloadUrl,
            projectId: activeProject.id,
            status: data.status,
            progress: 0
          }
        }));
        setDownloadUrl("");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const checkDownloadStatus = async (taskId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/videos/download/${taskId}`);
      if (res.ok) {
        const task = await res.json();
        setActiveDownloads((prev) => ({ ...prev, [taskId]: task }));
        if (task.status === "completed") {
          if (activeProject && task.projectId === activeProject.id) loadProjectDetails(activeProject.id);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;
    if (isPlaying) {
      if (!isTimelinePlayback) video.pause();
      setIsPlaying(false);
    } else {
      if (isTimelinePlayback) {
        setIsPlaying(true);
      } else {
        video.play().then(() => setIsPlaying(true)).catch(err => {});
      }
    }
  };

  const handleScrubberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    
    if (isTimelinePlayback) {
      if (activeProject) {
        const activeItem = activeProject.timeline.tracks.video.find(
          (item) => newTime >= item.start && newTime < item.start + item.duration
        );
        if (activeItem) {
          const asset = activeProject.assets.find((a) => a.id === activeItem.assetId);
          if (asset) {
            if (selectedAsset?.id !== asset.id) setSelectedAsset(asset);
            const relativeTime = newTime - activeItem.start + activeItem.sourceStart;
            if (videoRef.current) {
              videoRef.current.currentTime = relativeTime;
            }
          }
        }
      }
    } else {
      if (videoRef.current) {
        videoRef.current.currentTime = newTime;
      }
    }
  };

  // Timeline Addition
  const handleAddToTimeline = async (asset: Asset) => {
    if (!activeProject) return;
    const trackType = asset.type === "video" ? "video" : "audio";
    const track = activeProject.timeline.tracks[trackType] as TimelineItem[];
    const lastItemEnd = track.reduce((max, item) => Math.max(max, item.start + item.duration), 0);
    
    const itemId = Math.random().toString(36).substring(2, 9);
    const newItem: any = {
      id: itemId,
      assetId: asset.id,
      name: asset.name,
      start: lastItemEnd,
      duration: asset.duration || 5.0,
      sourceStart: 0.0,
      volume: 1.0,
      muted: false
    };

    const updatedProject = { ...activeProject };
    if (trackType === "video") updatedProject.timeline.tracks.video.push(newItem);
    else updatedProject.timeline.tracks.audio.push(newItem);

    await updateProjectState(updatedProject);
  };

  // Add Visual Text overlay block (Feature 7)
  const handleAddTextOverlay = async () => {
    if (!activeProject) return;
    const track = activeProject.timeline.tracks.text;
    const lastItemEnd = track.reduce((max, item) => Math.max(max, item.start + item.duration), 0);
    
    const textId = Math.random().toString(36).substring(2, 9);
    const newTextItem: TextTrackItem = {
      id: textId,
      name: "Text Overlay",
      start: lastItemEnd,
      duration: 4.0, // Default 4 seconds
      sourceStart: 0.0,
      text: "Double-click to edit text",
      style: {
        fontFamily: "Inter",
        fontSize: 42,
        fontWeight: "bold",
        color: "#ffffff",
        backgroundColor: "transparent",
        borderWidth: 0,
        borderColor: "#000000",
        shadowColor: "#000000",
        shadowBlur: 4,
        opacity: 1.0,
        x: 0.5,
        y: 0.5,
        rotation: 0.0
      }
    };

    const updatedProject = { ...activeProject };
    updatedProject.timeline.tracks.text.push(newTextItem);

    const saved = await updateProjectState(updatedProject);
    if (saved) {
      setSelectedTextId(textId);
      setSelectedImageId(null);
    }
  };

  // Add Visual Image overlay block (Feature 8)
  const handleAddImageOverlay = async (imageAsset: Asset) => {
    if (!activeProject) return;
    const track = activeProject.timeline.tracks.image;
    const lastItemEnd = track.reduce((max, item) => Math.max(max, item.start + item.duration), 0);
    
    const imgId = Math.random().toString(36).substring(2, 9);
    const newImgItem: ImageTrackItem = {
      id: imgId,
      assetId: imageAsset.id,
      name: imageAsset.name,
      start: lastItemEnd,
      duration: 5.0,
      sourceStart: 0.0,
      style: {
        width: 0.3,
        height: 0.3,
        x: 0.5,
        y: 0.5,
        rotation: 0.0,
        opacity: 1.0,
        layerOrder: 1
      }
    };

    const updatedProject = { ...activeProject };
    updatedProject.timeline.tracks.image.push(newImgItem);

    const saved = await updateProjectState(updatedProject);
    if (saved) {
      setSelectedImageId(imgId);
      setSelectedTextId(null);
    }
  };

  // Update Text styles properties
  const handleUpdateTextProperties = async () => {
    if (!activeProject || !selectedTextId) return;
    const updatedProject = { ...activeProject };
    updatedProject.timeline.tracks.text = updatedProject.timeline.tracks.text.map((t) => {
      if (t.id === selectedTextId) {
        return {
          ...t,
          text: textInputVal,
          style: {
            fontFamily: textFont,
            fontSize: textSize,
            fontWeight: textWeight,
            color: textColor,
            backgroundColor: textBgColor,
            borderWidth: 0,
            borderColor: "#000000",
            shadowColor: textShadowColor,
            shadowBlur: textShadowBlur,
            opacity: 1.0,
            x: textX,
            y: textY,
            rotation: 0.0
          }
        };
      }
      return t;
    });

    await updateProjectState(updatedProject);
  };

  // Update Image placement styles
  const handleUpdateImageProperties = async () => {
    if (!activeProject || !selectedImageId) return;
    const updatedProject = { ...activeProject };
    updatedProject.timeline.tracks.image = updatedProject.timeline.tracks.image.map((i) => {
      if (i.id === selectedImageId) {
        return {
          ...i,
          style: {
            width: imgWidth,
            height: imgHeight,
            x: imgX,
            y: imgY,
            rotation: 0.0,
            opacity: 1.0,
            layerOrder: 1
          }
        };
      }
      return i;
    });

    await updateProjectState(updatedProject);
  };

  // Remove item from timeline (core helper)
  const handleRemoveTimelineItem = async (trackType: "video" | "audio" | "subtitle", itemId: string) => {
    if (!activeProject) return;

    const updatedProject = { ...activeProject };
    if (trackType === "video") {
      updatedProject.timeline.tracks.video = updatedProject.timeline.tracks.video.filter(
        (i) => i.id !== itemId
      );
    } else if (trackType === "audio") {
      updatedProject.timeline.tracks.audio = updatedProject.timeline.tracks.audio.filter(
        (i) => i.id !== itemId
      );
    } else if (trackType === "subtitle") {
      updatedProject.timeline.tracks.subtitle = updatedProject.timeline.tracks.subtitle.filter(
        (i) => i.id !== itemId
      );
      if (selectedSubtitleId === itemId) setSelectedSubtitleId(null);
    }

    const savedProject = await updateProjectState(updatedProject);
    if (savedProject) {
      if (savedProject.timeline.tracks.video.length === 0 && trackType === "video") {
        setCurrentTime(0);
        setIsPlaying(false);
      }
    }
  };

  // Remove item from timeline wrapper
  const handleRemoveTimelineItemWrapper = async (trackType: "video" | "audio" | "subtitle" | "text" | "image", itemId: string) => {
    if (!activeProject) return;
    
    if (trackType === "text" || trackType === "image") {
      const updatedProject = { ...activeProject };
      if (trackType === "text") {
        updatedProject.timeline.tracks.text = updatedProject.timeline.tracks.text.filter(t => t.id !== itemId);
        if (selectedTextId === itemId) setSelectedTextId(null);
      } else {
        updatedProject.timeline.tracks.image = updatedProject.timeline.tracks.image.filter(i => i.id !== itemId);
        if (selectedImageId === itemId) setSelectedImageId(null);
      }
      await updateProjectState(updatedProject);
    } else {
      await handleRemoveTimelineItem(trackType, itemId);
    }
  };

  // Split clip at current playhead
  const handleSplitTimelineItem = async (trackType: "video" | "audio", itemId: string) => {
    if (!activeProject) return;
    
    const track = activeProject.timeline.tracks[trackType] as TimelineItem[];
    const item = track.find((i) => i.id === itemId);
    if (!item) return;

    // Check if playhead intersects item
    const relativeTime = currentTime - item.start;
    if (relativeTime <= 0.2 || relativeTime >= item.duration - 0.2) {
      alert("Split point is too close to the borders of the clip.");
      return;
    }

    const item1 = {
      ...item,
      id: Math.random().toString(36).substring(2, 9),
      duration: relativeTime
    };

    const item2 = {
      ...item,
      id: Math.random().toString(36).substring(2, 9),
      start: currentTime,
      duration: item.duration - relativeTime,
      sourceStart: item.sourceStart + relativeTime
    };

    const updatedProject = { ...activeProject };
    if (trackType === "video") {
      updatedProject.timeline.tracks.video = updatedProject.timeline.tracks.video.flatMap(
        (i) => (i.id === itemId ? [item1 as VideoTrackItem, item2 as VideoTrackItem] : [i])
      );
    } else {
      updatedProject.timeline.tracks.audio = updatedProject.timeline.tracks.audio.flatMap(
        (i) => (i.id === itemId ? [item1 as AudioTrackItem, item2 as AudioTrackItem] : [i])
      );
    }

    await updateProjectState(updatedProject);
  };

  // AI Metadata Generator call (Feature 12)
  const handleGenerateAIMetadata = async () => {
    if (!activeProject) return;
    setIsGeneratingMetadata(true);
    setAiMetadata(null);
    try {
      const res = await fetch(`${API_BASE}/api/ai/generate-metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          provider: aiProvider
        })
      });
      if (res.ok) {
        const data = await res.json();
        setAiMetadata(data);
      } else {
        const err = await res.json();
        alert(`AI Metadata call failed: ${err.detail || "Unknown error"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Connection failed.");
    } finally {
      setIsGeneratingMetadata(false);
    }
  };

  // AI Highlights Detector call (Feature 12)
  const handleDetectAIHighlights = async () => {
    if (!activeProject) return;
    setIsDetectingHighlights(true);
    setAiHighlights([]);
    try {
      const res = await fetch(`${API_BASE}/api/ai/detect-highlights`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          provider: aiProvider
        })
      });
      if (res.ok) {
        const data = await res.json();
        setAiHighlights(data.highlights || []);
      } else {
        const err = await res.json();
        alert(`AI Highlight call failed: ${err.detail || "Unknown error"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Connection failed.");
    } finally {
      setIsDetectingHighlights(false);
    }
  };

  // Apply suggested highlight clip directly (trim & add to asset library)
  const handleApplySuggestedHighlight = async (hl: AIHighlight) => {
    if (!activeProject || !selectedAsset) return;
    setIsTrimming(true);
    try {
      const duration = hl.end - hl.start;
      const res = await fetch(`${API_BASE}/api/videos/trim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          assetId: selectedAsset.id,
          start: hl.start,
          duration: duration
        })
      });
      if (res.ok) {
        const newAsset = await res.json();
        await loadProjectDetails(activeProject.id);
        setSelectedAsset(newAsset);
        alert(`Trimmed suggested moment (${hl.start.toFixed(1)}s - ${hl.end.toFixed(1)}s) and added to library.`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsTrimming(false);
    }
  };

  // Whisper transcription trigger
  const handleTranscribeAsset = async () => {
    if (!selectedAsset || !activeProject) return;
    setIsTranscribing(true);
    try {
      const res = await fetch(`${API_BASE}/api/audio/transcribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          assetId: selectedAsset.id
        })
      });
      if (res.ok) {
        const task = await res.json();
        setActiveTranscribe(task);
      } else {
        const err = await res.json();
        alert(`Failed to transcribe: ${err.detail || "Unknown error"}`);
        setIsTranscribing(false);
      }
    } catch (err) {
      console.error("Transcription trigger failed", err);
      alert("Connection error launching transcription.");
      setIsTranscribing(false);
    }
  };

  const handleTranscribeAssetWrapper = async () => {
    await handleTranscribeAsset();
  };

  // Silence Detection API call
  const handleDetectSilence = async () => {
    if (!selectedAsset || !activeProject) return;
    setIsDetectingSilence(true);
    setDetectedSilences([]);
    try {
      const res = await fetch(`${API_BASE}/api/audio/detect-silence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          assetId: selectedAsset.id,
          noiseThreshold,
          minDuration: minSilenceDuration
        })
      });
      if (res.ok) {
        const data = await res.json();
        setDetectedSilences(data);
        if (data.length === 0) {
          alert("No silences detected with the current parameters.");
        }
      } else {
        const err = await res.json();
        alert(`Silence detection failed: ${err.detail || "Unknown error"}`);
      }
    } catch (err) {
      console.error("Silence detection failed", err);
      alert("Connection error executing silence detection.");
    } finally {
      setIsDetectingSilence(false);
    }
  };

  // Remove silence from timeline track item (ripple edit)
  const handleRemoveSilenceFromTimeline = async (trackType: "video" | "audio", itemId: string) => {
    if (!activeProject) return;

    const track = activeProject.timeline.tracks[trackType] as TimelineItem[];
    const item = track.find((i) => i.id === itemId);
    if (!item || !item.assetId) {
      alert("No asset associated with this timeline item.");
      return;
    }

    let silences = detectedSilences;
    setIsDetectingSilence(true);
    try {
      const res = await fetch(`${API_BASE}/api/audio/detect-silence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          assetId: item.assetId,
          noiseThreshold,
          minDuration: minSilenceDuration
        })
      });
      if (res.ok) {
        silences = await res.json();
        setDetectedSilences(silences);
      } else {
        const err = await res.json();
        alert(`Silence detection failed: ${err.detail || "Unknown error"}`);
        setIsDetectingSilence(false);
        return;
      }
    } catch (err) {
      console.error(err);
      alert("Failed to connect to silence detection service.");
      setIsDetectingSilence(false);
      return;
    } finally {
      setIsDetectingSilence(false);
    }

    if (silences.length === 0) {
      alert("No silences detected in this item's asset.");
      return;
    }

    const clipStart = item.sourceStart;
    const clipEnd = item.sourceStart + item.duration;
    const sortedSilences = [...silences].sort((a, b) => a.start - b.start);
    
    const activeNonSilentRanges: { sourceStart: number; duration: number }[] = [];
    let currentSrc = clipStart;
    
    for (const sil of sortedSilences) {
      if (sil.start >= clipEnd) break;
      if (sil.end <= clipStart) continue;
      
      const overlapStart = Math.max(clipStart, sil.start);
      const overlapEnd = Math.min(clipEnd, sil.end);
      
      if (overlapStart > currentSrc) {
        activeNonSilentRanges.push({
          sourceStart: currentSrc,
          duration: overlapStart - currentSrc
        });
      }
      currentSrc = overlapEnd;
    }
    
    if (currentSrc < clipEnd) {
      activeNonSilentRanges.push({
        sourceStart: currentSrc,
        duration: clipEnd - currentSrc
      });
    }
    
    if (activeNonSilentRanges.length === 0) {
      alert("This clip is entirely silent based on the current threshold!");
      return;
    }
    
    const newItems: any[] = [];
    let currentTimelineStart = item.start;
    
    for (const range of activeNonSilentRanges) {
      newItems.push({
        ...item,
        id: Math.random().toString(36).substring(2, 9),
        start: currentTimelineStart,
        duration: range.duration,
        sourceStart: range.sourceStart
      });
      currentTimelineStart += range.duration;
    }
    
    const originalEnd = item.start + item.duration;
    const newEnd = currentTimelineStart;
    const durationDelta = newEnd - originalEnd;
    
    const updatedProject = { ...activeProject };
    const trackItems = updatedProject.timeline.tracks[trackType] as TimelineItem[];
    
    const trackBefore = trackItems.filter(i => i.start < item.start);
    const trackAfter = trackItems.filter(i => i.start > item.start).map(i => ({
      ...i,
      start: i.start + durationDelta
    }));
    
    if (trackType === "video") {
      updatedProject.timeline.tracks.video = [
        ...trackBefore as VideoTrackItem[],
        ...newItems as VideoTrackItem[],
        ...trackAfter as VideoTrackItem[]
      ];
    } else {
      updatedProject.timeline.tracks.audio = [
        ...trackBefore as AudioTrackItem[],
        ...newItems as AudioTrackItem[],
        ...trackAfter as AudioTrackItem[]
      ];
    }
    
    await updateProjectState(updatedProject);
    alert(`Successfully removed silences: split clip into ${newItems.length} segments.`);
  };

  // Subtitle Editing updates
  const handleUpdateSubtitleText = async (subId: string, newText: string) => {
    if (!activeProject) return;
    const updatedProject = { ...activeProject };
    updatedProject.timeline.tracks.subtitle = updatedProject.timeline.tracks.subtitle.map(
      (sub) => (sub.id === subId ? { ...sub, text: newText } : sub)
    );
    await updateProjectState(updatedProject);
  };

  const handleUpdateSubtitleTextWrapper = async (subId: string, newText: string) => {
    await handleUpdateSubtitleText(subId, newText);
  };

  const handleMergeSubtitles = async (subId: string) => {
    if (!activeProject) return;
    const subs = activeProject.timeline.tracks.subtitle;
    const index = subs.findIndex((s) => s.id === subId);
    if (index === -1 || index === subs.length - 1) {
      alert("No subsequent subtitle segment to merge with.");
      return;
    }

    const current = subs[index];
    const nextSub = subs[index + 1];

    const mergedText = `${current.text} ${nextSub.text}`.trim();
    const mergedDuration = (nextSub.start + nextSub.duration) - current.start;

    const updatedProject = { ...activeProject };
    updatedProject.timeline.tracks.subtitle = [
      ...subs.slice(0, index),
      { ...current, text: mergedText, duration: mergedDuration },
      ...subs.slice(index + 2)
    ];

    const saved = await updateProjectState(updatedProject);
    if (saved) {
      if (selectedSubtitleId === nextSub.id) setSelectedSubtitleId(current.id);
    }
  };

  const handleSplitSubtitle = async (subId: string) => {
    if (!activeProject) return;
    const subs = activeProject.timeline.tracks.subtitle;
    const sub = subs.find((s) => s.id === subId);
    if (!sub) return;

    const words = sub.text.split(" ");
    if (words.length <= 1) {
      alert("Not enough words in this subtitle segment to split.");
      return;
    }

    const midPoint = Math.floor(words.length / 2);
    const text1 = words.slice(0, midPoint).join(" ");
    const text2 = words.slice(midPoint).join(" ");

    const halfDuration = sub.duration / 2;
    const sub1 = {
      ...sub,
      id: Math.random().toString(36).substring(2, 9),
      text: text1,
      duration: halfDuration
    };
    const sub2 = {
      ...sub,
      id: Math.random().toString(36).substring(2, 9),
      name: `Sub Split`,
      start: sub.start + halfDuration,
      text: text2,
      duration: halfDuration,
      sourceStart: sub.sourceStart + halfDuration
    };

    const updatedProject = { ...activeProject };
    updatedProject.timeline.tracks.subtitle = subs.flatMap(
      (s) => (s.id === subId ? [sub1, sub2] : [s])
    );

    const saved = await updateProjectState(updatedProject);
    if (saved) {
      setSelectedSubtitleId(sub1.id);
    }
  };

  // Trimming API call
  const handleExtractClip = async () => {
    if (!selectedAsset || !activeProject) return;
    setIsTrimming(true);
    try {
      const res = await fetch(`${API_BASE}/api/videos/trim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          assetId: selectedAsset.id,
          start: trimStart,
          duration: trimEnd - trimStart
        })
      });
      if (res.ok) {
        const newAsset = await res.json();
        await loadProjectDetails(activeProject.id);
        setSelectedAsset(newAsset);
      } else {
        const err = await res.json();
        alert(`Failed to extract clip: ${err.detail || "Unknown error"}`);
      }
    } catch (err) {
      console.error("Failed to extract clip", err);
      alert("Connection error. Failed to extract clip.");
    } finally {
      setIsTrimming(false);
    }
  };

  const handleExtractClipWrapper = async () => {
    await handleExtractClip();
  };

  // Audio extraction API call
  const handleExtractAudio = async () => {
    if (!selectedAsset || !activeProject) return;
    setIsExtractingAudio(true);
    try {
      const res = await fetch(`${API_BASE}/api/videos/extract-audio`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          assetId: selectedAsset.id,
          format: "mp3"
        })
      });
      if (res.ok) {
        const newAsset = await res.json();
        await loadProjectDetails(activeProject.id);
        alert(`Successfully extracted audio: ${newAsset.name}`);
      } else {
        const err = await res.json();
        alert(`Failed to extract audio: ${err.detail || "Unknown error"}`);
      }
    } catch (err) {
      console.error("Failed to extract audio", err);
      alert("Connection error. Failed to extract audio.");
    } finally {
      setIsExtractingAudio(false);
    }
  };

  const handleExtractAudioWrapper = async () => {
    await handleExtractAudio();
  };

  // Render trigger
  const handleRenderTimeline = async () => {
    if (!activeProject) return;
    try {
      const res = await fetch(`${API_BASE}/api/timeline/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: activeProject.id,
          aspectRatio: exportAspectRatio,
          resolution: exportResolution
        })
      });
      
      if (res.ok) {
        const task = await res.json();
        setActiveRender(task);
        setShowRenderModal(true);
      } else {
        const err = await res.json();
        alert(`Failed to render: ${err.detail || "Unknown error"}`);
      }
    } catch (err) {
      console.error("Error triggering render", err);
      alert("Connection error triggering render.");
    }
  };

  const handleRenderTimelineWrapper = async () => {
    await handleRenderTimeline();
  };

  // Find active subtitle, text overlays, and image overlays at currentTime
  const activeSubtitle = activeProject?.timeline.tracks.subtitle.find(
    (sub) => currentTime >= sub.start && currentTime < sub.start + sub.duration
  );

  const activeTextOverlays = activeProject?.timeline.tracks.text.filter(
    (t) => currentTime >= t.start && currentTime < t.start + t.duration
  ) || [];

  const activeImageOverlays = activeProject?.timeline.tracks.image.filter(
    (img) => currentTime >= img.start && currentTime < img.start + img.duration
  ) || [];

  return (
    <div className="flex flex-col h-full bg-[#0b0b0f] text-[#f4f4f6]">
      {/* HEADER / NAVIGATION BAR */}
      <header className="flex items-center justify-between px-6 py-4 bg-[#12121a] border-b border-[#22222f] shadow-lg">
        <div className="flex items-center space-x-3">
          <div className="bg-gradient-to-tr from-indigo-600 to-purple-600 p-2 rounded-lg text-white">
            <Maximize2 className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-[#a3a3c2] bg-clip-text text-transparent">
              video-short-generator
            </h1>
            <p className="text-xs text-indigo-400 font-medium">AI-Assisted Desktop Editor</p>
          </div>
        </div>

        {/* Project Selector bar */}
        <div className="flex items-center space-x-3">
          {/* API Keys Configuration indicator */}
          <button
            onClick={() => {
              setOpenaiKeyInput("");
              setAnthropicKeyInput("");
              setGeminiKeyInput("");
              setShowKeysModal(true);
            }}
            className="flex items-center space-x-1 px-3 py-1.5 bg-[#181824] hover:bg-[#252535] border border-[#222238] rounded-lg text-xs text-indigo-300 font-semibold cursor-pointer shadow active:scale-95"
          >
            <Key className="w-3.5 h-3.5" />
            <span>API Keys Settings</span>
          </button>

          <div className="relative">
            <select
              className="bg-[#1c1c28] border border-[#22222f] text-sm text-[#f4f4f6] px-4 py-2 rounded-lg outline-none cursor-pointer focus:border-[#6366f1] transition-all"
              value={activeProject?.id || ""}
              onChange={(e) => {
                if (e.target.value) {
                  loadProjectDetails(e.target.value);
                  setIsPlaying(false);
                  setCurrentTime(0);
                  setSelectedSubtitleId(null);
                  setSelectedTextId(null);
                  setSelectedImageId(null);
                }
              }}
            >
              {projects.length === 0 && <option value="">No Projects Available</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setShowNewProjectModal(true)}
            className="flex items-center space-x-1.5 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-2 rounded-lg text-xs font-semibold transition-all shadow-md active:scale-95 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>

          {activeProject && (
            <button
              onClick={() => handleDeleteProject(activeProject.id)}
              className="p-2 text-red-400 hover:text-red-300 bg-[#25171e] hover:bg-[#3d1a29] border border-[#3b1a29] rounded-lg transition-all active:scale-95 cursor-pointer"
              title="Delete Project"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </header>

      {/* WORKSPACE CONTENT SHELL */}
      <main className="flex-1 flex overflow-hidden p-4 gap-4">
        {/* LEFT COLUMN: Asset Library & Downloads */}
        <div className="w-[380px] flex flex-col gap-4 overflow-hidden">
          {/* Section: Download Video */}
          <div className="editor-panel p-4 flex flex-col gap-3">
            <h2 className="text-sm font-semibold flex items-center gap-2 text-indigo-300">
              <Download className="w-4 h-4" /> Import Video from URL
            </h2>
            <form onSubmit={handleDownloadVideo} className="flex gap-2">
              <input
                type="text"
                placeholder="Paste YouTube or Pinterest URL..."
                value={downloadUrl}
                onChange={(e) => setDownloadUrl(e.target.value)}
                disabled={!activeProject}
                className="flex-1 text-xs bg-[#1c1c28] border border-[#22222f] rounded-lg px-3 py-2 text-white placeholder-gray-500 outline-none focus:border-[#6366f1] transition-all"
              />
              <button
                type="submit"
                disabled={!activeProject || !downloadUrl.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white px-3 py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center cursor-pointer"
              >
                Download
              </button>
            </form>

            {/* Active Downloads List */}
            {Object.keys(activeDownloads).length > 0 && (
              <div className="flex flex-col gap-2 max-h-[120px] overflow-y-auto mt-1 border-t border-[#22222f] pt-2">
                {Object.values(activeDownloads).map((task) => (
                  <div key={task.id} className="text-[11px] bg-[#1a1a24] p-2 rounded border border-[#22222f]">
                    <div className="flex justify-between items-center mb-1">
                      <span className="truncate max-w-[180px] text-gray-400 font-mono">{task.url}</span>
                      <span className="font-semibold text-indigo-400 uppercase text-[9px] tracking-wider">
                        {task.status}
                      </span>
                    </div>
                    {task.status === "downloading" || task.status === "processing" ? (
                      <div className="w-full bg-[#2a2a38] h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-indigo-500 h-full rounded-full transition-all duration-300"
                          style={{ width: `${task.progress}%` }}
                        ></div>
                      </div>
                    ) : task.status === "completed" ? (
                      <div className="text-emerald-400 flex items-center gap-1 mt-0.5">
                        <CheckCircle className="w-3.5 h-3.5" /> Ready for Timeline
                      </div>
                    ) : task.status === "failed" ? (
                      <div className="text-red-400 flex items-center gap-1 mt-0.5" title={task.error}>
                        <AlertCircle className="w-3.5 h-3.5" /> Download Failed
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section: Asset Library */}
          <div className="editor-panel flex-1 flex flex-col overflow-hidden">
            <div className="flex border-b border-[#22222f] bg-[#12121a]">
              <button
                onClick={() => setActiveTab("assets")}
                className={`flex-1 text-center py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                  activeTab === "assets" ? "border-indigo-500 text-[#f4f4f6]" : "border-transparent text-gray-500 hover:text-gray-300"
                }`}
              >
                Asset Library
              </button>
              <button
                onClick={() => setActiveTab("settings")}
                className={`flex-1 text-center py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                  activeTab === "settings" ? "border-indigo-500 text-[#f4f4f6]" : "border-transparent text-gray-500 hover:text-gray-300"
                }`}
              >
                Project Assets ({activeProject?.assets.length || 0})
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3">
              {!activeProject ? (
                <div className="h-full flex items-center justify-center text-xs text-gray-500">
                  Create or select a project to get started
                </div>
              ) : activeProject.assets.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-xs text-gray-500 p-6 text-center gap-2">
                  <Film className="w-8 h-8 text-[#22222f] animate-bounce" />
                  <span>No assets imported yet. Paste a URL above to download videos.</span>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {activeProject.assets.map((asset) => (
                    <div
                      key={asset.id}
                      onClick={() => {
                        setSelectedAsset(asset);
                        setIsTimelinePlayback(false);
                      }}
                      className={`group cursor-pointer relative rounded-lg overflow-hidden border transition-all ${
                        selectedAsset?.id === asset.id && !isTimelinePlayback
                          ? "border-indigo-500 bg-[#161622]"
                          : "border-[#22222f] bg-[#12121a] hover:border-[#3f3f50]"
                      }`}
                    >
                      <div className="aspect-video w-full bg-black relative">
                        {asset.type === "video" ? (
                          <img
                            src={`${API_BASE}/storage/images/${asset.id}_thumb.jpg`}
                            alt={asset.name}
                            onError={(e) => {
                              e.currentTarget.src = "data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 24 24'%3E%3Cpath fill='%23222' d='M0 0h24v24H0z'/%3E%3C/svg%3E";
                            }}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center bg-[#181824]">
                            <Music className="w-8 h-8 text-indigo-400" />
                          </div>
                        )}
                        <span className="absolute bottom-1 right-1 bg-black/85 text-[10px] px-1 rounded font-mono">
                          {asset.duration ? formatTime(asset.duration).split(".")[0] : "--:--"}
                        </span>
                      </div>
                      <div className="p-2">
                        <p className="text-[11px] font-semibold truncate group-hover:text-indigo-400 transition-colors" title={asset.name}>
                          {asset.name}
                        </p>
                        <p className="text-[9px] text-gray-500 uppercase mt-0.5">{asset.resolution || asset.type}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* MIDDLE COLUMN: Video Player */}
        <div className="flex-1 flex flex-col gap-4 overflow-hidden">
          {/* Preview Video Player */}
          <div className="editor-panel flex-1 flex flex-col overflow-hidden relative">
            <div className="bg-[#12121a] px-4 py-2 border-b border-[#22222f] flex justify-between items-center">
              <span className="text-xs font-semibold text-gray-400 flex items-center gap-1.5">
                <Tv className="w-3.5 h-3.5 text-indigo-400" />
                {isTimelinePlayback ? "Timeline simulated preview" : selectedAsset ? selectedAsset.name : "Preview Monitor"}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setIsTimelinePlayback(!isTimelinePlayback);
                    setIsPlaying(false);
                    setCurrentTime(0);
                    setSelectedTextId(null);
                    setSelectedImageId(null);
                  }}
                  disabled={!activeProject || activeProject.timeline.tracks.video.length === 0}
                  className={`px-3 py-1 text-[10px] font-bold rounded border transition-all active:scale-95 cursor-pointer disabled:opacity-40 ${
                    isTimelinePlayback
                      ? "bg-indigo-600/40 text-indigo-300 border-indigo-500/70"
                      : "bg-[#181824] text-gray-400 border-[#222238] hover:text-white"
                  }`}
                >
                  {isTimelinePlayback ? "Viewing: Timeline" : "View Timeline"}
                </button>
              </div>
            </div>

            {/* Video Canvas Container (Feature 7 & 8) */}
            <div className="flex-1 bg-black flex items-center justify-center overflow-hidden relative">
              {selectedAsset ? (
                <div className="relative max-h-full max-w-full flex items-center justify-center aspect-video bg-black select-none">
                  <video
                    ref={videoRef}
                    src={`${API_BASE}/storage/${selectedAsset.path}`}
                    className="max-h-full max-w-full object-contain"
                  />
                  
                  {/* Dynamic Subtitle overlay simulation (Feature 10) */}
                  {activeSubtitle && (
                    <div className="absolute inset-x-0 bottom-8 flex justify-center pointer-events-none px-4 select-none z-10">
                      {subtitleStyle === "tiktok" && (
                        <div className="bg-yellow-400 text-black px-3 py-1.5 rounded font-black text-sm uppercase shadow-2xl scale-110 tracking-wider">
                          {activeSubtitle.text}
                        </div>
                      )}
                      {subtitleStyle === "shorts" && (
                        <div className="bg-black/85 text-[#f4f4f6] px-4 py-2 border border-indigo-500 rounded-lg font-bold text-sm text-center shadow-lg">
                          {activeSubtitle.text}
                        </div>
                      )}
                      {subtitleStyle === "minimal" && (
                        <div className="text-white font-semibold text-sm tracking-wide text-shadow-md text-center max-w-[80%] bg-black/45 px-2 py-0.5 rounded">
                          {activeSubtitle.text}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Active TEXT Overlays Canvas (Feature 7) */}
                  {activeTextOverlays.map((t) => (
                    <div
                      key={t.id}
                      style={{
                        position: "absolute",
                        left: `${t.style.x * 100}%`,
                        top: `${t.style.y * 100}%`,
                        transform: "translate(-50%, -50%)",
                        color: t.style.color,
                        backgroundColor: t.style.backgroundColor,
                        fontFamily: t.style.fontFamily,
                        fontSize: `${t.style.fontSize}px`,
                        fontWeight: t.style.fontWeight as any,
                        textShadow: t.style.shadowColor !== "transparent" ? `0px 2px ${t.style.shadowBlur}px ${t.style.shadowColor}` : "none",
                        opacity: t.style.opacity,
                        border: selectedTextId === t.id ? "1.5px dashed #6366f1" : "none",
                        padding: "4px 8px",
                        borderRadius: "4px",
                        zIndex: 20
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTextId(t.id);
                        setSelectedImageId(null);
                        setActiveTab("assets");
                      }}
                      className="cursor-pointer hover:border hover:border-dashed hover:border-indigo-400 transition-all text-center"
                    >
                      {t.text}
                    </div>
                  ))}

                  {/* Active IMAGE Overlays Canvas (Feature 8) */}
                  {activeImageOverlays.map((img) => {
                    const imgAsset = activeProject?.assets.find((a) => a.id === img.assetId);
                    if (!imgAsset) return null;
                    return (
                      <div
                        key={img.id}
                        style={{
                          position: "absolute",
                          left: `${img.style.x * 100}%`,
                          top: `${img.style.y * 100}%`,
                          width: `${img.style.width * 100}%`,
                          height: `${img.style.height * 100}%`,
                          transform: "translate(-50%, -50%)",
                          opacity: img.style.opacity,
                          border: selectedImageId === img.id ? "1.5px dashed #6366f1" : "none",
                          zIndex: 15
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedImageId(img.id);
                          setSelectedTextId(null);
                          setActiveTab("assets");
                        }}
                        className="cursor-pointer hover:border hover:border-dashed hover:border-indigo-400 transition-all"
                      >
                        <img
                          src={`${API_BASE}/storage/${imgAsset.path}`}
                          alt={img.name}
                          className="w-full h-full object-contain pointer-events-none"
                        />
                      </div>
                    );
                  })}

                </div>
              ) : (
                <div className="text-xs text-gray-500 flex flex-col items-center gap-2">
                  <Film className="w-12 h-12 text-[#22222f]" />
                  <span>Select a video or toggle "View Timeline" to preview</span>
                </div>
              )}
            </div>

            {/* Player Controls & Scrubber */}
            {(selectedAsset || isTimelinePlayback) && (
              <div className="bg-[#12121a] border-t border-[#22222f] p-3 flex flex-col gap-2">
                {/* Scrubber slider */}
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono text-indigo-400 w-12">{formatTime(currentTime)}</span>
                  <input
                    type="range"
                    min="0"
                    max={isTimelinePlayback ? timelineDuration : playerDuration || 0}
                    step="0.05"
                    value={currentTime}
                    onChange={handleScrubberChange}
                    className="flex-1 h-1 bg-[#22222f] rounded-lg cursor-pointer"
                  />
                  <span className="text-[10px] font-mono text-gray-500 w-12">
                    {formatTime(isTimelinePlayback ? timelineDuration : playerDuration)}
                  </span>
                </div>

                {/* Control buttons */}
                <div className="flex justify-between items-center px-2">
                  <div className="flex items-center gap-1.5">
                    {selectedAsset && !isTimelinePlayback && (
                      <button
                        onClick={() => handleAddToTimeline(selectedAsset)}
                        className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-bold transition-all shadow active:scale-95"
                      >
                        <Plus className="w-3.5 h-3.5" /> Add to Timeline
                      </button>
                    )}
                  </div>

                  <button
                    onClick={handlePlayPause}
                    className="p-2.5 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center shadow-md active:scale-90 transition-all cursor-pointer"
                  >
                    {isPlaying ? <Pause className="w-4 h-4 fill-white" /> : <Play className="w-4 h-4 fill-white ml-0.5" />}
                  </button>

                  <div className="w-20"></div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Tool Panel & Subtitle/AI Editor */}
        <div className="w-[320px] flex flex-col gap-4 overflow-hidden">
          <div className="editor-panel flex-1 flex flex-col overflow-hidden">
            <div className="flex border-b border-[#22222f] bg-[#12121a] overflow-x-auto shrink-0">
              <button
                onClick={() => setActiveTab("assets")}
                className={`flex-1 text-center py-2.5 px-2 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                  activeTab === "assets" ? "border-indigo-500 text-[#f4f4f6]" : "border-transparent text-gray-500 hover:text-gray-300"
                }`}
              >
                Tools
              </button>
              <button
                onClick={() => setActiveTab("subtitles")}
                className={`flex-1 text-center py-2.5 px-2 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                  activeTab === "subtitles" ? "border-indigo-500 text-[#f4f4f6]" : "border-transparent text-gray-500 hover:text-gray-300"
                }`}
              >
                Subtitles
              </button>
              <button
                onClick={() => setActiveTab("ai")}
                className={`flex-1 text-center py-2.5 px-2 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
                  activeTab === "ai" ? "border-indigo-500 text-[#f4f4f6]" : "border-transparent text-gray-500 hover:text-gray-300"
                }`}
              >
                AI Panel
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
              {activeTab === "assets" && (
                <div className="flex flex-col gap-4">
                  {/* Phase 7 Layer Properties */}
                  {selectedTextId ? (
                    <div className="flex flex-col gap-3 bg-[#13131e] p-3 rounded-lg border border-[#22223c]">
                      <div className="flex justify-between items-center border-b border-[#22222f] pb-1.5 mb-1.5">
                        <span className="text-xs font-bold text-indigo-400 flex items-center gap-1">
                          <Type className="w-3.5 h-3.5" /> Text Overlay Style
                        </span>
                        <button
                          onClick={() => handleRemoveTimelineItemWrapper("text", selectedTextId)}
                          className="text-red-400 hover:text-red-300 p-0.5 rounded"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <span className="text-[9px] text-gray-500 font-bold uppercase">Text Value</span>
                        <input
                          type="text"
                          value={textInputVal}
                          onChange={(e) => setTextInputVal(e.target.value)}
                          onBlur={handleUpdateTextProperties}
                          className="bg-[#1c1c28] border border-[#22222f] text-xs px-2.5 py-1.5 rounded outline-none text-white focus:border-indigo-500"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">X Pos ({textX.toFixed(2)})</span>
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.01"
                            value={textX}
                            onChange={(e) => {
                              setTextX(parseFloat(e.target.value));
                              handleUpdateTextProperties();
                            }}
                            className="w-full h-1 bg-gray-700 rounded"
                          />
                        </div>
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">Y Pos ({textY.toFixed(2)})</span>
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.01"
                            value={textY}
                            onChange={(e) => {
                              setTextY(parseFloat(e.target.value));
                              handleUpdateTextProperties();
                            }}
                            className="w-full h-1 bg-gray-700 rounded"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">Text Color</span>
                          <input
                            type="color"
                            value={textColor}
                            onChange={(e) => {
                              setTextColor(e.target.value);
                              handleUpdateTextProperties();
                            }}
                            className="w-full h-7 bg-transparent border-0 rounded cursor-pointer"
                          />
                        </div>
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">Font Size</span>
                          <input
                            type="number"
                            value={textSize}
                            onChange={(e) => {
                              setTextSize(parseInt(e.target.value) || 20);
                              handleUpdateTextProperties();
                            }}
                            className="bg-[#1c1c28] border border-[#22222f] text-xs px-2 py-1 rounded outline-none"
                          />
                        </div>
                      </div>

                      <div className="flex flex-col gap-1">
                        <span className="text-[9px] text-gray-500 font-bold uppercase">Shadow Color</span>
                        <select
                          value={textShadowColor}
                          onChange={(e) => {
                            setTextShadowColor(e.target.value);
                            setTextShadowBlur(e.target.value === "transparent" ? 0 : 5);
                            handleUpdateTextProperties();
                          }}
                          className="bg-[#1c1c28] border border-[#22222f] text-xs px-2 py-1.5 rounded outline-none"
                        >
                          <option value="transparent">No Shadow</option>
                          <option value="#000000">Black Shadow</option>
                          <option value="#ff0000">Red Shadow</option>
                          <option value="#6366f1">Indigo Glow</option>
                        </select>
                      </div>

                      <button
                        onClick={() => setSelectedTextId(null)}
                        className="w-full py-1 text-center bg-[#212132] hover:bg-[#2c2c43] text-gray-400 hover:text-white rounded text-[10px] transition-all font-semibold"
                      >
                        Deselect Overlay
                      </button>
                    </div>
                  ) : selectedImageId ? (
                    <div className="flex flex-col gap-3 bg-[#13131e] p-3 rounded-lg border border-[#22223c]">
                      <div className="flex justify-between items-center border-b border-[#22222f] pb-1.5 mb-1.5">
                        <span className="text-xs font-bold text-indigo-400 flex items-center gap-1">
                          <ImageIcon className="w-3.5 h-3.5" /> Image Overlay Style
                        </span>
                        <button
                          onClick={() => handleRemoveTimelineItemWrapper("image", selectedImageId)}
                          className="text-red-400 hover:text-red-300 p-0.5 rounded"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">Width ({Math.round(imgWidth * 100)}%)</span>
                          <input
                            type="range"
                            min="0.05"
                            max="1"
                            step="0.01"
                            value={imgWidth}
                            onChange={(e) => {
                              setImgWidth(parseFloat(e.target.value));
                              handleUpdateImageProperties();
                            }}
                            className="w-full h-1 bg-gray-700 rounded"
                          />
                        </div>
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">Height ({Math.round(imgHeight * 100)}%)</span>
                          <input
                            type="range"
                            min="0.05"
                            max="1"
                            step="0.01"
                            value={imgHeight}
                            onChange={(e) => {
                              setImgHeight(parseFloat(e.target.value));
                              handleUpdateImageProperties();
                            }}
                            className="w-full h-1 bg-gray-700 rounded"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">X Pos ({imgX.toFixed(2)})</span>
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.01"
                            value={imgX}
                            onChange={(e) => {
                              setImgX(parseFloat(e.target.value));
                              handleUpdateImageProperties();
                            }}
                            className="w-full h-1 bg-gray-700 rounded"
                          />
                        </div>
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">Y Pos ({imgY.toFixed(2)})</span>
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.01"
                            value={imgY}
                            onChange={(e) => {
                              setImgY(parseFloat(e.target.value));
                              handleUpdateImageProperties();
                            }}
                            className="w-full h-1 bg-gray-700 rounded"
                          />
                        </div>
                      </div>

                      <button
                        onClick={() => setSelectedImageId(null)}
                        className="w-full py-1 text-center bg-[#212132] hover:bg-[#2c2c43] text-gray-400 hover:text-white rounded text-[10px] transition-all font-semibold"
                      >
                        Deselect Overlay
                      </button>
                    </div>
                  ) : null}

                  {/* Standard Trimming and Audio Tools */}
                  <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1">
                    <Scissors className="w-3.5 h-3.5" /> Clip Trimming
                  </h2>
                  {selectedAsset && selectedAsset.type === "video" && !isTimelinePlayback ? (
                    <div className="flex flex-col gap-3">
                      <div className="flex justify-between text-[10px] font-mono text-gray-400">
                        <span>Start: {formatTime(trimStart)}</span>
                        <span>End: {formatTime(trimEnd)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min="0"
                          max={selectedAsset.duration || 10}
                          step="0.1"
                          value={trimStart}
                          onChange={(e) => setTrimStart(Math.min(parseFloat(e.target.value), trimEnd))}
                          className="w-1/2 h-1 bg-[#22222f] rounded"
                        />
                        <input
                          type="range"
                          min="0"
                          max={selectedAsset.duration || 10}
                          step="0.1"
                          value={trimEnd}
                          onChange={(e) => setTrimEnd(Math.max(parseFloat(e.target.value), trimStart))}
                          className="w-1/2 h-1 bg-[#22222f] rounded"
                        />
                      </div>
                      <button
                        onClick={handleExtractClipWrapper}
                        disabled={isTrimming}
                        className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded text-xs font-bold transition-all shadow cursor-pointer text-center"
                      >
                        {isTrimming ? "Extracting..." : "Extract Clip"}
                      </button>
                    </div>
                  ) : (
                    <p className="text-[11px] text-gray-500 italic">Select a video asset to trim.</p>
                  )}

                  <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1 mt-2">
                    <Volume2 className="w-3.5 h-3.5" /> Audio Extraction
                  </h2>
                  {selectedAsset && selectedAsset.type === "video" && !isTimelinePlayback ? (
                    <button
                      onClick={handleExtractAudioWrapper}
                      disabled={isExtractingAudio}
                      className="w-full py-1.5 bg-[#1b1b28] hover:bg-[#252538] border border-[#222238] text-indigo-300 rounded text-xs font-bold transition-all cursor-pointer text-center"
                    >
                      {isExtractingAudio ? "Extracting Audio..." : "Extract Audio track (MP3)"}
                    </button>
                  ) : (
                    <p className="text-[11px] text-gray-500 italic">Select a video asset to extract audio.</p>
                  )}

                  {/* Add Overlay buttons */}
                  <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1 mt-2">
                    <Type className="w-3.5 h-3.5" /> Overlays Integration
                  </h2>
                  {activeProject ? (
                    <div className="flex flex-col gap-2">
                      <button
                        onClick={handleAddTextOverlay}
                        className="w-full py-1.5 bg-[#1b1b28] hover:bg-[#252538] border border-[#222238] text-indigo-300 rounded text-xs font-bold transition-all cursor-pointer text-center flex items-center justify-center gap-1.5"
                      >
                        <Plus className="w-3.5 h-3.5" /> Add Text Layer
                      </button>

                      {/* Image Overlay selection from Asset Library */}
                      <div className="flex flex-col gap-1">
                        <span className="text-[9px] text-gray-500 font-bold uppercase">Image Overlay Sources</span>
                        <div className="max-h-24 overflow-y-auto border border-[#22222f] rounded p-1.5 flex flex-col gap-1 bg-black/25">
                          {activeProject.assets.filter(a => a.type === "image" || a.type === "video" && a.id.startsWith("image-")).length === 0 ? (
                            <span className="text-[9px] text-gray-500 italic">No image assets uploaded yet.</span>
                          ) : (
                            activeProject.assets.filter(a => a.type === "image").map(a => (
                              <button
                                key={a.id}
                                onClick={() => handleAddImageOverlay(a)}
                                className="w-full text-left p-1 text-[10px] hover:bg-indigo-950/20 text-indigo-300 flex justify-between items-center"
                              >
                                <span className="truncate max-w-[80%]">{a.name}</span>
                                <Plus className="w-3 h-3" />
                              </button>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {/* Speech-to-Text block */}
                  <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1 mt-2">
                    <FileText className="w-3.5 h-3.5" /> Speech-to-Text
                  </h2>
                  {selectedAsset && selectedAsset.type === "video" ? (
                    <div className="flex flex-col gap-2">
                      <p className="text-[11px] text-gray-500">Generate auto-captions locally with OpenAI Whisper.</p>
                      <button
                        onClick={handleTranscribeAssetWrapper}
                        disabled={isTranscribing}
                        className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-1"
                      >
                        {isTranscribing ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>Transcribing...</span>
                          </>
                        ) : (
                          <>
                            <RefreshCw className="w-3.5 h-3.5" />
                            <span>Run Local Auto-Subtitles</span>
                          </>
                        )}
                      </button>
                    </div>
                  ) : (
                    <p className="text-[11px] text-gray-500 italic">Select a video to run transcription.</p>
                  )}

                  {/* Silence Detection block */}
                  <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1 mt-3">
                    <VolumeX className="w-3.5 h-3.5" /> Silence Detection
                  </h2>
                  {selectedAsset && selectedAsset.type === "video" ? (
                    <div className="flex flex-col gap-2 bg-[#13131e]/50 border border-[#22223c]/40 p-2.5 rounded-lg">
                      <div className="grid grid-cols-2 gap-2">
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">Threshold ({noiseThreshold} dB)</span>
                          <input
                            type="range"
                            min="-60"
                            max="0"
                            step="1"
                            value={noiseThreshold}
                            onChange={(e) => setNoiseThreshold(parseInt(e.target.value))}
                            className="w-full h-1 bg-[#22222f] rounded"
                          />
                        </div>
                        <div className="flex flex-col gap-1">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">Min Dur ({minSilenceDuration}s)</span>
                          <input
                            type="number"
                            min="0.1"
                            max="5"
                            step="0.1"
                            value={minSilenceDuration}
                            onChange={(e) => setMinSilenceDuration(parseFloat(e.target.value) || 0.5)}
                            className="bg-[#1c1c28] border border-[#22222f] text-[10px] px-2 py-0.5 rounded outline-none text-white focus:border-indigo-500"
                          />
                        </div>
                      </div>

                      <button
                        onClick={handleDetectSilence}
                        disabled={isDetectingSilence}
                        className="w-full py-1 bg-[#1b1b28] hover:bg-[#252538] border border-[#222238] text-indigo-300 rounded text-[11px] font-bold transition-all cursor-pointer flex items-center justify-center gap-1"
                      >
                        {isDetectingSilence ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" />
                            <span>Analyzing...</span>
                          </>
                        ) : (
                          <>
                            <VolumeX className="w-3 h-3" />
                            <span>Scan for Silence</span>
                          </>
                        )}
                      </button>

                      {detectedSilences.length > 0 && (
                        <div className="flex flex-col gap-1.5 mt-1 border-t border-[#22222f]/60 pt-2">
                          <span className="text-[9px] text-gray-500 font-bold uppercase">Detected Silences ({detectedSilences.length})</span>
                          <div className="max-h-24 overflow-y-auto border border-[#22222f] rounded p-1 flex flex-col gap-1 bg-black/10">
                            {detectedSilences.map((s, idx) => (
                              <div key={idx} className="text-[9px] font-mono text-gray-400 flex justify-between px-1 py-0.5 hover:bg-white/5">
                                <span>{s.start.toFixed(2)}s - {s.end.toFixed(2)}s</span>
                                <span className="text-red-400/80">-{s.duration.toFixed(2)}s</span>
                              </div>
                            ))}
                          </div>

                          {/* Quick Trim Option */}
                          {activeProject && (
                            <div className="flex flex-col gap-1.5 mt-1">
                              {/* Video item at playhead */}
                              {(() => {
                                const activeVideo = activeProject.timeline.tracks.video.find(
                                  (v) => currentTime >= v.start && currentTime < v.start + v.duration
                                );
                                if (activeVideo && activeVideo.assetId === selectedAsset.id) {
                                  return (
                                    <button
                                      onClick={() => handleRemoveSilenceFromTimeline("video", activeVideo.id)}
                                      className="w-full py-1 bg-red-950/30 hover:bg-red-900/40 border border-red-900/50 text-red-300 rounded text-[10px] font-bold transition-all cursor-pointer text-center"
                                    >
                                      Ripple-Cut Silence from Active Video Clip
                                    </button>
                                  );
                                }
                                return null;
                              })()}

                              {/* Audio item at playhead */}
                              {(() => {
                                const activeAudio = activeProject.timeline.tracks.audio.find(
                                  (a) => currentTime >= a.start && currentTime < a.start + a.duration
                                );
                                if (activeAudio && activeAudio.assetId === selectedAsset.id) {
                                  return (
                                    <button
                                      onClick={() => handleRemoveSilenceFromTimeline("audio", activeAudio.id)}
                                      className="w-full py-1 bg-red-950/30 hover:bg-red-900/40 border border-red-900/50 text-red-300 rounded text-[10px] font-bold transition-all cursor-pointer text-center"
                                    >
                                      Ripple-Cut Silence from Active Audio Clip
                                    </button>
                                  );
                                }
                                return null;
                              })()}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-[11px] text-gray-500 italic">Select a video asset to analyze silence.</p>
                  )}
                </div>
              )}

              {activeTab === "subtitles" && (
                <div className="flex flex-col gap-3 h-full overflow-hidden">
                  <div className="flex flex-col gap-1 border-b border-[#22222f] pb-3 shrink-0">
                    <span className="text-[10px] text-gray-500 font-bold uppercase">Subtitle Style Presets</span>
                    <div className="grid grid-cols-3 gap-1.5">
                      {["tiktok", "shorts", "minimal"].map((style) => (
                        <button
                          key={style}
                          onClick={() => setSubtitleStyle(style as any)}
                          className={`py-1 text-[10px] capitalize rounded font-semibold transition-all border cursor-pointer ${
                            subtitleStyle === style
                              ? "bg-indigo-600/30 border-indigo-500 text-indigo-300"
                              : "bg-[#181824] border-[#222238] text-gray-400 hover:text-white"
                          }`}
                        >
                          {style}
                        </button>
                      ))}
                    </div>
                  </div>

                  {!activeProject || activeProject.timeline.tracks.subtitle.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-center text-xs text-gray-500 gap-2 py-8">
                      <FileText className="w-8 h-8 text-[#22222f]" />
                      <span>No subtitles generated yet. Go to "Tools" to run speech-to-text.</span>
                    </div>
                  ) : (
                    <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-1">
                      {activeProject.timeline.tracks.subtitle.map((sub) => (
                        <div
                          key={sub.id}
                          onClick={() => {
                            setSelectedSubtitleId(sub.id);
                            setCurrentTime(sub.start);
                            if (videoRef.current && !isTimelinePlayback) {
                              videoRef.current.currentTime = sub.sourceStart;
                            }
                          }}
                          className={`p-2.5 rounded-lg border text-xs flex flex-col gap-2 transition-all cursor-pointer ${
                            selectedSubtitleId === sub.id
                              ? "bg-indigo-950/20 border-indigo-500"
                              : "bg-[#12121a] border-[#22222f] hover:border-[#3f3f50]"
                          }`}
                        >
                          <div className="flex justify-between items-center text-[10px] text-gray-500 font-mono">
                            <span>
                              {formatTime(sub.start).split(".")[0]}s → {formatTime(sub.start + sub.duration).split(".")[0]}s
                            </span>
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleSplitSubtitle(sub.id);
                                }}
                                className="hover:text-indigo-400"
                                title="Split segment in half"
                              >
                                <Split className="w-3 h-3" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleMergeSubtitles(sub.id);
                                }}
                                className="hover:text-indigo-400"
                                title="Merge with next subtitle segment"
                              >
                                <Merge className="w-3 h-3" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRemoveTimelineItemWrapper("subtitle", sub.id);
                                }}
                                className="hover:text-red-400 text-red-500/70"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </div>

                          <textarea
                            value={sub.text}
                            rows={2}
                            onClick={(e) => e.stopPropagation()}
                            onChange={(e) => handleUpdateSubtitleTextWrapper(sub.id, e.target.value)}
                            className="bg-[#1c1c28] border border-[#22222f] rounded p-1.5 text-xs text-white outline-none focus:border-indigo-500 resize-none font-sans"
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === "ai" && (
                <div className="flex flex-col gap-4">
                  {/* Select LLM model provider */}
                  <div className="flex flex-col gap-1.5">
                    <span className="text-[10px] text-gray-500 font-bold uppercase">LLM Provider Selection</span>
                    <select
                      value={aiProvider}
                      onChange={(e) => setAiProvider(e.target.value)}
                      className="bg-[#1c1c28] border border-[#22222f] text-xs text-white px-3 py-2 rounded-lg outline-none cursor-pointer"
                    >
                      <option value="openai" disabled={!apiKeysStatus.openai}>OpenAI (gpt-4o-mini)</option>
                      <option value="anthropic" disabled={!apiKeysStatus.anthropic}>Claude (claude-3-5-haiku)</option>
                      <option value="gemini" disabled={!apiKeysStatus.gemini}>Google Gemini (1.5-flash)</option>
                    </select>
                  </div>

                  {/* Actions buttons */}
                  <div className="grid grid-cols-2 gap-2 mt-1 shrink-0">
                    <button
                      onClick={handleGenerateAIMetadata}
                      disabled={isGeneratingMetadata || !activeProject}
                      className="py-2 bg-indigo-600/25 border border-indigo-500/50 hover:bg-indigo-600/50 disabled:opacity-40 rounded text-[11px] font-bold text-indigo-300 flex items-center justify-center gap-1.5 cursor-pointer shadow active:scale-95"
                    >
                      {isGeneratingMetadata ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                      <span>Metadata Gen</span>
                    </button>
                    
                    <button
                      onClick={handleDetectAIHighlights}
                      disabled={isDetectingHighlights || !activeProject}
                      className="py-2 bg-yellow-600/25 border border-yellow-500/50 hover:bg-yellow-600/50 disabled:opacity-40 rounded text-[11px] font-bold text-yellow-300 flex items-center justify-center gap-1.5 cursor-pointer shadow active:scale-95"
                    >
                      {isDetectingHighlights ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <TrimIcon className="w-3.5 h-3.5" />}
                      <span>Find Moments</span>
                    </button>
                  </div>

                  {/* Results: Suggested Highlights */}
                  {aiHighlights.length > 0 && (
                    <div className="flex flex-col gap-2 mt-2 border-t border-[#22222f] pt-3">
                      <span className="text-[10px] text-gray-500 font-bold uppercase flex items-center gap-1">
                        <Sparkles className="w-3.5 h-3.5 text-yellow-400 animate-pulse" /> AI Highlight Detection
                      </span>
                      <div className="flex flex-col gap-2 max-h-44 overflow-y-auto">
                        {aiHighlights.map((hl, i) => (
                          <div key={i} className="bg-[#12121e] border border-[#222238] p-2.5 rounded-lg text-xs flex flex-col gap-1">
                            <div className="flex justify-between items-center font-mono text-[10px] text-yellow-400">
                              <span>Range: {hl.start.toFixed(1)}s - {hl.end.toFixed(1)}s</span>
                              <span>({(hl.end - hl.start).toFixed(1)}s)</span>
                            </div>
                            <p className="text-[11px] text-gray-400 italic font-sans">"{hl.reason}"</p>
                            <button
                              onClick={() => handleApplySuggestedHighlight(hl)}
                              className="mt-1 py-1 w-full bg-[#1b1b28] hover:bg-[#252538] border border-[#3f3f5a] text-yellow-400 rounded text-[10px] font-bold transition-all cursor-pointer flex items-center justify-center gap-1"
                            >
                              <Scissors className="w-3 h-3" /> Trim & Save Clip
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Results: Metadata generator */}
                  {aiMetadata && (
                    <div className="flex flex-col gap-3 mt-2 border-t border-[#22222f] pt-3 max-h-96 overflow-y-auto pr-1">
                      <span className="text-[10px] text-gray-500 font-bold uppercase">AI Suggestions</span>
                      
                      <div className="flex flex-col gap-1.5">
                        <span className="text-[9px] text-[#8c8cb2] font-bold uppercase">Video Title Ideas</span>
                        <div className="flex flex-col gap-1">
                          {aiMetadata.titles.map((title, i) => (
                            <div key={i} className="bg-[#12121a] border border-[#22222f] p-2 rounded text-[11px] flex justify-between items-center gap-2">
                              <span className="font-semibold text-white truncate">{title}</span>
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(title);
                                  alert("Title copied to clipboard!");
                                }}
                                className="text-gray-400 hover:text-indigo-400"
                              >
                                <Copy className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="flex flex-col gap-1">
                        <span className="text-[9px] text-[#8c8cb2] font-bold uppercase">YouTube Description</span>
                        <div className="bg-[#12121a] border border-[#22222f] p-2.5 rounded text-[11px] text-gray-400 relative">
                          <p className="max-h-24 overflow-y-auto whitespace-pre-wrap font-sans leading-relaxed">{aiMetadata.description}</p>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(aiMetadata.description);
                              alert("Description copied!");
                            }}
                            className="absolute top-2 right-2 text-gray-400 hover:text-indigo-400"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      <div className="flex flex-col gap-1">
                        <span className="text-[9px] text-[#8c8cb2] font-bold uppercase">Tags / Hashtags</span>
                        <div className="flex flex-wrap gap-1 bg-[#12121a] border border-[#22222f] p-2 rounded max-h-16 overflow-y-auto">
                          {aiMetadata.tags.map((tag, i) => (
                            <span key={i} className="text-[9px] bg-indigo-950/40 border border-indigo-900/40 text-indigo-300 px-1.5 py-0.5 rounded font-mono">
                              #{tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* BOTTOM PANEL: Multi-track Timeline */}
      <section className="h-[260px] bg-[#12121a] border-t border-[#22222f] flex flex-col overflow-hidden">
        {/* Timeline Header controls */}
        <div className="flex items-center justify-between px-6 py-2 bg-[#0d0d12] border-b border-[#22222f] text-xs">
          <div className="flex items-center space-x-4">
            <span className="font-mono text-indigo-400">Playhead: {formatTime(currentTime)}</span>
            <div className="flex items-center space-x-1.5">
              <span className="text-[10px] text-gray-500">Timeline Zoom</span>
              <input
                type="range"
                min="5"
                max="50"
                value={zoomLevel}
                onChange={(e) => setZoomLevel(parseInt(e.target.value))}
                className="w-24 h-1 bg-[#22222f] rounded"
              />
            </div>
          </div>

          {activeProject && (
            <div className="flex items-center space-x-2">
              <select
                value={exportAspectRatio}
                onChange={(e) => setExportAspectRatio(e.target.value)}
                className="bg-[#1c1c28] border border-[#22222f] text-[10px] px-2 py-1 rounded text-gray-400 outline-none"
              >
                <option value="9:16">Aspect: 9:16 (Shorts/TikTok)</option>
                <option value="16:9">Aspect: 16:9 (YouTube)</option>
                <option value="1:1">Aspect: 1:1 (Instagram)</option>
              </select>

              <select
                value={exportResolution}
                onChange={(e) => setExportResolution(e.target.value)}
                className="bg-[#1c1c28] border border-[#22222f] text-[10px] px-2 py-1 rounded text-gray-400 outline-none"
              >
                <option value="720p">Quality: 720p</option>
                <option value="1080p">Quality: 1080p</option>
                <option value="1440p">Quality: 1440p</option>
              </select>

              <button
                onClick={handleRenderTimelineWrapper}
                disabled={activeProject.timeline.tracks.video.length === 0}
                className="flex items-center gap-1 px-3 py-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded text-[11px] font-bold transition-all shadow-md active:scale-95 cursor-pointer"
              >
                Export/Render MP4
              </button>
            </div>
          )}
        </div>

        {/* Timeline Tracks container */}
        <div ref={timelineContainerRef} className="flex-1 overflow-x-auto overflow-y-auto p-4 flex flex-col gap-2">
          {/* Video Track */}
          <div className="flex items-center gap-3 min-w-[800px]">
            <div className="w-24 flex items-center gap-1.5 shrink-0 select-none border-r border-[#22222f] pr-2">
              <Film className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Video</span>
            </div>
            <div className="flex-1 bg-[#15151f] h-11 rounded border border-[#222238] relative flex items-center p-1 overflow-hidden">
              {activeProject && activeProject.timeline.tracks.video.length === 0 && (
                <span className="text-[10px] text-gray-600 italic px-2">Timeline video track is empty</span>
              )}
              {activeProject?.timeline.tracks.video.map((item) => (
                <div
                  key={item.id}
                  style={{
                    left: `${item.start * zoomLevel}px`,
                    width: `${item.duration * zoomLevel}px`
                  }}
                  className="absolute h-9 bg-indigo-900/40 hover:bg-indigo-950/60 border border-indigo-500 rounded px-2.5 flex items-center justify-between text-[10px] overflow-hidden select-none cursor-pointer group"
                >
                  <span className="truncate font-semibold max-w-[80%]">{item.name}</span>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSplitTimelineItem("video", item.id);
                      }}
                      className="text-indigo-400 hover:text-indigo-300 p-0.5 rounded hover:bg-[#12121a]"
                      title="Split clip at playhead"
                    >
                      <Scissors className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveTimelineItemWrapper("video", item.id);
                      }}
                      className="text-red-400 hover:text-red-300 p-0.5 rounded hover:bg-[#12121a]"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}

              {/* Playhead visualization */}
              <div
                style={{ left: `${currentTime * zoomLevel}px` }}
                className="absolute top-0 bottom-0 w-0.5 bg-yellow-500 pointer-events-none z-10"
              >
                <div className="w-2.5 h-2.5 bg-yellow-500 -ml-1 rounded-full border border-black shadow"></div>
              </div>
            </div>
          </div>

          {/* Audio Track */}
          <div className="flex items-center gap-3 min-w-[800px]">
            <div className="w-24 flex items-center gap-1.5 shrink-0 select-none border-r border-[#22222f] pr-2">
              <Music className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Audio</span>
            </div>
            <div className="flex-1 bg-[#15151f] h-11 rounded border border-[#222238] relative flex items-center p-1 overflow-hidden">
              {activeProject && activeProject.timeline.tracks.audio.length === 0 && (
                <span className="text-[10px] text-gray-600 italic px-2">Timeline audio track is empty</span>
              )}
              {activeProject?.timeline.tracks.audio.map((item) => (
                <div
                  key={item.id}
                  style={{
                    left: `${item.start * zoomLevel}px`,
                    width: `${item.duration * zoomLevel}px`
                  }}
                  className="absolute h-9 bg-emerald-950/40 hover:bg-emerald-950/60 border border-emerald-500 rounded px-2.5 flex items-center justify-between text-[10px] overflow-hidden select-none cursor-pointer group"
                >
                  <span className="truncate font-semibold max-w-[80%] text-emerald-300">{item.name}</span>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSplitTimelineItem("audio", item.id);
                      }}
                      className="text-emerald-400 hover:text-emerald-300 p-0.5 rounded hover:bg-[#12121a]"
                      title="Split audio at playhead"
                    >
                      <Scissors className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveTimelineItemWrapper("audio", item.id);
                      }}
                      className="text-red-400 hover:text-red-300 p-0.5 rounded hover:bg-[#12121a]"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
              <div
                style={{ left: `${currentTime * zoomLevel}px` }}
                className="absolute top-0 bottom-0 w-0.5 bg-yellow-500 pointer-events-none z-10"
              ></div>
            </div>
          </div>

          {/* Subtitle Track */}
          <div className="flex items-center gap-3 min-w-[800px]">
            <div className="w-24 flex items-center gap-1.5 shrink-0 select-none border-r border-[#22222f] pr-2">
              <FileText className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Subtitles</span>
            </div>
            <div className="flex-1 bg-[#15151f] h-11 rounded border border-[#222238] relative flex items-center p-1 overflow-hidden">
              {activeProject && activeProject.timeline.tracks.subtitle.length === 0 && (
                <span className="text-[10px] text-gray-600 italic px-2">Subtitle track is empty</span>
              )}
              {activeProject?.timeline.tracks.subtitle.map((item) => (
                <div
                  key={item.id}
                  style={{
                    left: `${item.start * zoomLevel}px`,
                    width: `${item.duration * zoomLevel}px`
                  }}
                  onClick={() => setSelectedSubtitleId(item.id)}
                  className={`absolute h-9 rounded px-2 flex items-center justify-between text-[10px] overflow-hidden select-none cursor-pointer border group ${
                    selectedSubtitleId === item.id
                      ? "bg-indigo-900/60 border-indigo-400 text-white"
                      : "bg-[#181824] border-[#222238] text-gray-400 hover:border-gray-500"
                  }`}
                >
                  <span className="truncate font-semibold max-w-[85%]">{item.text}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveTimelineItemWrapper("subtitle", item.id);
                    }}
                    className="text-red-400 hover:text-red-300 opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))}
              <div
                style={{ left: `${currentTime * zoomLevel}px` }}
                className="absolute top-0 bottom-0 w-0.5 bg-yellow-500 pointer-events-none z-10"
              ></div>
            </div>
          </div>

          {/* TEXT Overlay Track (Phase 7) */}
          <div className="flex items-center gap-3 min-w-[800px]">
            <div className="w-24 flex items-center gap-1.5 shrink-0 select-none border-r border-[#22222f] pr-2">
              <Type className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Text Track</span>
            </div>
            <div className="flex-1 bg-[#15151f] h-11 rounded border border-[#222238] relative flex items-center p-1 overflow-hidden">
              {activeProject && activeProject.timeline.tracks.text.length === 0 && (
                <span className="text-[10px] text-gray-600 italic px-2">Click "Add Text Layer" in tools</span>
              )}
              {activeProject?.timeline.tracks.text.map((item) => (
                <div
                  key={item.id}
                  style={{
                    left: `${item.start * zoomLevel}px`,
                    width: `${item.duration * zoomLevel}px`
                  }}
                  onClick={() => {
                    setSelectedTextId(item.id);
                    setSelectedImageId(null);
                  }}
                  className={`absolute h-9 rounded px-2.5 flex items-center justify-between text-[10px] overflow-hidden select-none cursor-pointer border group ${
                    selectedTextId === item.id
                      ? "bg-indigo-900/60 border-indigo-400 text-white"
                      : "bg-[#181824] border-[#222238] text-gray-400 hover:border-gray-500"
                  }`}
                >
                  <span className="truncate font-semibold max-w-[80%]">{item.text}</span>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveTimelineItemWrapper("text", item.id);
                      }}
                      className="text-red-400 hover:text-red-300 p-0.5 rounded"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
              <div
                style={{ left: `${currentTime * zoomLevel}px` }}
                className="absolute top-0 bottom-0 w-0.5 bg-yellow-500 pointer-events-none z-10"
              ></div>
            </div>
          </div>

          {/* IMAGE Overlay Track (Phase 7) */}
          <div className="flex items-center gap-3 min-w-[800px]">
            <div className="w-24 flex items-center gap-1.5 shrink-0 select-none border-r border-[#22222f] pr-2">
              <ImageIcon className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Image Track</span>
            </div>
            <div className="flex-1 bg-[#15151f] h-11 rounded border border-[#222238] relative flex items-center p-1 overflow-hidden">
              {activeProject && activeProject.timeline.tracks.image.length === 0 && (
                <span className="text-[10px] text-gray-600 italic px-2">Import an image and add to timeline</span>
              )}
              {activeProject?.timeline.tracks.image.map((item) => (
                <div
                  key={item.id}
                  style={{
                    left: `${item.start * zoomLevel}px`,
                    width: `${item.duration * zoomLevel}px`
                  }}
                  onClick={() => {
                    setSelectedImageId(item.id);
                    setSelectedTextId(null);
                  }}
                  className={`absolute h-9 rounded px-2.5 flex items-center justify-between text-[10px] overflow-hidden select-none cursor-pointer border group ${
                    selectedImageId === item.id
                      ? "bg-indigo-900/60 border-indigo-400 text-white"
                      : "bg-[#181824] border-[#222238] text-gray-400 hover:border-gray-500"
                  }`}
                >
                  <span className="truncate font-semibold max-w-[80%]">{item.name}</span>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveTimelineItemWrapper("image", item.id);
                      }}
                      className="text-red-400 hover:text-red-300 p-0.5 rounded"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
              <div
                style={{ left: `${currentTime * zoomLevel}px` }}
                className="absolute top-0 bottom-0 w-0.5 bg-yellow-500 pointer-events-none z-10"
              ></div>
            </div>
          </div>

        </div>
      </section>

      {/* MODAL: Create New Project */}
      {showNewProjectModal && (
        <div className="fixed inset-0 bg-black/75 flex items-center justify-center z-50 animate-fade-in">
          <form
            onSubmit={handleCreateProject}
            className="bg-[#12121a] border border-[#22222f] p-6 rounded-xl w-[400px] shadow-2xl flex flex-col gap-4"
          >
            <div>
              <h3 className="text-sm font-bold text-white">Create New Project</h3>
              <p className="text-[11px] text-gray-400">Enter a descriptive name for your video short project.</p>
            </div>
            <input
              type="text"
              placeholder="e.g. Football Highlights Short..."
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              className="bg-[#1c1c28] border border-[#22222f] text-xs text-white px-3 py-2 rounded-lg outline-none focus:border-[#6366f1] transition-all"
              autoFocus
            />
            <div className="flex justify-end gap-2 text-xs">
              <button
                type="button"
                onClick={() => {
                  setShowNewProjectModal(false);
                  setNewProjectName("");
                }}
                className="px-4 py-2 border border-[#22222f] text-gray-400 rounded-lg hover:bg-[#1a1a24] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg cursor-pointer"
              >
                Create Project
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL: API Keys Configuration (Phase 7) */}
      {showKeysModal && (
        <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-50">
          <form
            onSubmit={handleSaveKeys}
            className="bg-[#12121a] border border-[#22222f] p-6 rounded-xl w-[440px] shadow-2xl flex flex-col gap-4"
          >
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Key className="w-4 h-4 text-indigo-400" /> AI API Provider Credentials
              </h3>
              <p className="text-[11px] text-gray-400">Keys are saved 100% locally on your machine (`storage/api_keys.json`). Never hardcoded or sent to third-party SaaS cloud servers.</p>
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-gray-500 font-bold uppercase">OpenAI Key (sk-...)</label>
                <input
                  type="password"
                  placeholder={apiKeysStatus.openai ? "Configured (Overwrite...)" : "Enter OpenAI key"}
                  value={openaiKeyInput}
                  onChange={(e) => setOpenaiKeyInput(e.target.value)}
                  className="bg-[#1c1c28] border border-[#22222f] text-xs px-2.5 py-1.5 rounded outline-none text-white focus:border-indigo-500"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-gray-500 font-bold uppercase">Claude Anthropic Key (sk-ant-...)</label>
                <input
                  type="password"
                  placeholder={apiKeysStatus.anthropic ? "Configured (Overwrite...)" : "Enter Claude key"}
                  value={anthropicKeyInput}
                  onChange={(e) => setAnthropicKeyInput(e.target.value)}
                  className="bg-[#1c1c28] border border-[#22222f] text-xs px-2.5 py-1.5 rounded outline-none text-white focus:border-indigo-500"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-gray-500 font-bold uppercase">Google Gemini Key (AIzaSy...)</label>
                <input
                  type="password"
                  placeholder={apiKeysStatus.gemini ? "Configured (Overwrite...)" : "Enter Gemini key"}
                  value={geminiKeyInput}
                  onChange={(e) => setGeminiKeyInput(e.target.value)}
                  className="bg-[#1c1c28] border border-[#22222f] text-xs px-2.5 py-1.5 rounded outline-none text-white focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 text-xs pt-2">
              <button
                type="button"
                onClick={() => setShowKeysModal(false)}
                className="px-4 py-2 border border-[#22222f] text-gray-400 rounded-lg hover:bg-[#1a1a24] cursor-pointer"
              >
                Close Settings
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg cursor-pointer"
              >
                Save Credentials
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL: Rendering Progress */}
      {showRenderModal && activeRender && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-[#12121a] border border-[#22222f] p-6 rounded-xl w-[420px] shadow-2xl flex flex-col gap-5">
            <div className="flex items-center justify-between border-b border-[#22222f] pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-yellow-400" /> Exporting Timeline Video
              </h3>
              <button
                onClick={() => {
                  if (activeRender.status === "completed" || activeRender.status === "failed") {
                    setShowRenderModal(false);
                  }
                }}
                disabled={activeRender.status === "rendering" || activeRender.status === "pending"}
                className="text-xs text-gray-500 hover:text-white disabled:opacity-30 cursor-pointer"
              >
                Close
              </button>
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex justify-between text-xs text-gray-400">
                <span>Aspect: {activeRender.aspectRatio}</span>
                <span>Quality: {activeRender.resolution}</span>
              </div>
              
              <div className="bg-[#181824] p-3 rounded-lg border border-[#222238] flex flex-col gap-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-indigo-400 uppercase tracking-wide text-[10px]">
                    Status: {activeRender.status}
                  </span>
                  <span className="font-mono font-bold text-white">{activeRender.progress}%</span>
                </div>
                
                {activeRender.status === "rendering" || activeRender.status === "pending" ? (
                  <div className="w-full bg-[#2a2a38] h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-indigo-500 to-purple-500 h-full rounded-full transition-all duration-300"
                      style={{ width: `${activeRender.progress}%` }}
                    ></div>
                  </div>
                ) : null}
              </div>

              {activeRender.status === "completed" && activeRender.outputPath && (
                <div className="bg-emerald-950/30 border border-emerald-500/40 p-4 rounded-lg flex flex-col gap-3 text-xs text-[#a3dcb2]">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold">
                    <CheckCircle className="w-4 h-4" /> Render Complete!
                  </div>
                  <p>Your short video is ready. You can play it or download it directly using the button below.</p>
                  <a
                    href={`${API_BASE}/storage/${activeRender.outputPath}`}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full flex items-center justify-center gap-2 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded font-bold transition-all shadow-md active:scale-95"
                  >
                    <Download className="w-4 h-4" /> Download Final Video (MP4)
                  </a>
                </div>
              )}

              {activeRender.status === "failed" && (
                <div className="bg-red-950/30 border border-red-500/40 p-4 rounded-lg flex flex-col gap-1.5 text-xs text-[#f4a2a2]">
                  <div className="flex items-center gap-2 text-red-400 font-bold">
                    <AlertCircle className="w-4 h-4" /> Export Failed
                  </div>
                  <p className="font-mono text-[10px] max-h-24 overflow-y-auto mt-1 bg-black/40 p-2 rounded">
                    {activeRender.error}
                  </p>
                </div>
              )}
            </div>

            {activeRender.status === "rendering" && (
              <div className="flex items-center gap-2 text-[10px] text-gray-500 italic justify-center">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Compiling segments with FFmpeg. Do not close the window.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
