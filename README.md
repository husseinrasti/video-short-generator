# video-short-generator

AI-Assisted Local Video Editor for Shorts Creation

**video-short-generator** is a desktop-first, local-first productivity tool designed to help creators download videos, extract audio, detect silence, generate AI narration scripts, overlay text/images, and export optimized short-form videos (YouTube Shorts, TikTok, Instagram Reels) under custom aspect ratios—all directly on their local machines.

---

## 🚀 Key Features

### 1. Multi-Track Timeline & Workspace
* **Sticky Track Headers**: Easy track identification (Video, Audio, Subtitles, Text, Image) even when scrolled.
* **Horizontal Navigation**: Trackpad horizontal swiping and `Shift + Scrollwheel` gestures to pan large timelines smoothly.
* **Timeline Ruler & Playhead Scrubbing**: Absolute ruler with tick marks and dynamic time divisions; click and drag to scrub/seek the playhead.
* **Timeline Edit Toolbar**: Action buttons for **Cut (Split)**, **Delete**, **Mute/Unmute**, and **Duplicate** targeting selected clips.
* **Real-time Volume & Mute Sync**: Preview playhead dynamically respects muted track clips during playback simulation.

### 2. Audio Silence Detection
* **Silence Scanner**: Dynamic threshold (dB) and minimum duration parameters to scan video/audio tracks for silent sections.
* **Automatic Ripple Cut**: Delete silent gaps instantly and shift remaining timeline items leftward to preserve rhythm.

### 3. AI Narration Studio
* **AI Script Generator**: LLM-powered assistant (OpenAI, Anthropic Claude, Gemini) with preset rewrite modifiers (*Shorter*, *Longer*, *More Exciting*, *More Professional*).
* **AI Model Selection**: Selector dropdown populated dynamically from the backend provider listing, showing name, provider, and context window metrics.
* **Local TTS Engine**: Synthesis using OpenAI or ElevenLabs, with precise speed controls processed via the FFmpeg `atempo` filter.
* **Auto-Subtitles**: Fast, local speech-to-text alignment powered by Whisper.
* **Sync Assistant**: Real-time validation checking speech duration against video footage coverage, pointing out gaps and offering repair suggestions.

### 4. Overlays & Rendering
* **Overlay Controls**: Add layered text and image overlays with coordinates, size, weight, shadow, and background styles.
* **FFmpeg Pipeline**: Scales, pads/letterboxes, and overlays tracks according to desired aspect ratios (`9:16`, `16:9`, `1:1`) and resolutions (`720p`, `1080p`, `1440p`).
* **Active Cancellation**: Terminate background downloads, transcribe tasks, and FFmpeg render compiles instantly.

---

## 🛠️ Tech Stack

* **Backend**: FastAPI (Python), FFmpeg, `yt-dlp`, Pydantic database models.
* **Frontend**: Next.js, React, TypeScript, Tailwind CSS, Lucide icons.
* **State Management**: Local JSON persistence for projects, assets, and rendering tasks, paired with a React state undo/redo stack.

---

## ⚙️ Setup & Installation

### Prerequisites
1. **Python 3.10+**
2. **Node.js 18+** & **npm**
3. **FFmpeg** & **FFprobe** installed and available in your system `PATH`.
   * *Mac*: `brew install ffmpeg`
   * *Ubuntu*: `sudo apt install ffmpeg`

---

### 1. Backend Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run uvicorn local development server:
   ```bash
   PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --port 8000 --reload
   ```

The FastAPI Swagger interactive documentation will be available at `http://localhost:8000/docs`.

---

### 2. Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install Node modules:
   ```bash
   npm install
   ```
3. Run Next.js dev server:
   ```bash
   npm run dev
   ```
Open `http://localhost:3000` in your browser to interact with the web app.

---

## 🚀 Running the Application

You can run both the Backend and Frontend components simultaneously or individually.

### Quick Start (Recommended)
A root-level helper script `run.sh` is provided to check dependencies, handle port conflicts, run both servers in parallel, and cleanly terminate them on exit.

1. Ensure the setup steps for both backend and frontend are completed.
2. Run the helper script from the root directory:
   ```bash
   ./run.sh
   ```
3. Open [http://localhost:3000](http://localhost:3000) in your browser.
4. Press `Ctrl + C` in the terminal to stop both servers at any time.

### Manual Startup

If you prefer starting each service individually in separate terminal sessions:

#### 1. Start Backend Server
```bash
# From the root directory
PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --port 8000 --reload
```
Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

#### 2. Start Frontend Server
```bash
# From the root directory
npm run dev --prefix frontend
```
Web client interface: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Running Tests

A comprehensive test suite covering project operations, mock FFmpeg trims, metadata queries, silence detection, render compiler graphs, and narration utilities is available under `backend/tests/`.

To execute tests, navigate to the project root and run:
```bash
PYTHONPATH=. .venv/bin/pytest
```

---

## 📦 Project Directory Layout

```
.
├── backend
│   ├── app
│   │   ├── main.py              # FastAPI application entrypoint
│   │   ├── config.py            # Local storage initialization & CORS
│   │   ├── models               # Pydantic schemas (Project, Assets, Tracks)
│   │   ├── routers              # API controllers (AI, Audio, Narration, Videos, Timeline)
│   │   └── utils                # Core modules (FFmpeg engine, yt-dlp downloader, Whisper STT)
│   └── tests                    # Backend pytest suite
├── frontend
│   ├── src
│   │   └── app
│   │       ├── layout.tsx       # Root Next.js layout
│   │       └── page.tsx         # Main Video Editor workspace dashboard
│   ├── package.json
│   └── tailwind.config.ts
├── storage                      # Local database repository (videos, audio, renders, cached metadata)
└── README.md                    # Project documentation
```
