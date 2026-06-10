from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Asset(BaseModel):
    id: str
    name: str
    type: str  # "video", "audio", "image", "subtitle"
    path: str  # relative path within storage directory
    duration: Optional[float] = None
    resolution: Optional[str] = None
    createdAt: str

class TimelineItem(BaseModel):
    id: str
    assetId: Optional[str] = None
    name: str
    start: float  # Start time on timeline (in seconds)
    duration: float  # Duration on timeline (in seconds)
    sourceStart: float = 0.0  # Start time in source file (in seconds)

class VideoTrackItem(TimelineItem):
    volume: float = 1.0
    muted: bool = False

class AudioTrackItem(TimelineItem):
    volume: float = 1.0

class SubtitleTrackItem(TimelineItem):
    text: str

class TextStyle(BaseModel):
    fontFamily: str = "Inter"
    fontSize: int = 40
    fontWeight: str = "normal"
    color: str = "#ffffff"
    backgroundColor: str = "transparent"
    borderWidth: int = 0
    borderColor: str = "#000000"
    shadowColor: str = "transparent"
    shadowBlur: int = 0
    opacity: float = 1.0
    x: float = 0.5  # Relative normalized x position (0.0 to 1.0)
    y: float = 0.8  # Relative normalized y position (0.0 to 1.0)
    rotation: float = 0.0  # Rotation in degrees

class TextAnimation(BaseModel):
    inType: str = "none"  # "none", "fade", "scale", "slide-up", "slide-down"
    outType: str = "none"  # "none", "fade"
    inDuration: float = 0.3
    outDuration: float = 0.3

class TextTrackItem(TimelineItem):
    text: str
    style: TextStyle = Field(default_factory=TextStyle)
    animation: TextAnimation = Field(default_factory=TextAnimation)

class ImageStyle(BaseModel):
    width: float = 0.3  # Relative width (0.0 to 1.0)
    height: float = 0.3  # Relative height (0.0 to 1.0)
    x: float = 0.5
    y: float = 0.5
    rotation: float = 0.0
    opacity: float = 1.0
    layerOrder: int = 0

class ImageTrackItem(TimelineItem):
    style: ImageStyle = Field(default_factory=ImageStyle)

class TimelineTracks(BaseModel):
    video: List[VideoTrackItem] = Field(default_factory=list)
    audio: List[AudioTrackItem] = Field(default_factory=list)
    subtitle: List[SubtitleTrackItem] = Field(default_factory=list)
    text: List[TextTrackItem] = Field(default_factory=list)
    image: List[ImageTrackItem] = Field(default_factory=list)

class Timeline(BaseModel):
    tracks: TimelineTracks = Field(default_factory=TimelineTracks)

class Project(BaseModel):
    id: str
    name: str
    createdAt: str
    updatedAt: str
    timeline: Timeline = Field(default_factory=Timeline)
    assets: List[Asset] = Field(default_factory=list)
