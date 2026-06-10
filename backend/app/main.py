from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.config import STORAGE_DIR, CORS_ORIGINS
from backend.app.routers import projects, videos, timeline, audio, ai, narration

app = FastAPI(
    title="video-short-generator API",
    description="Local backend API for video-short-generator application",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the local storage directory for static file access (video, audio, thumbnail, renders, etc.)
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

# Include Routers
app.include_router(projects.router)
app.include_router(videos.router)
app.include_router(timeline.router)
app.include_router(audio.router)
app.include_router(ai.router)
app.include_router(narration.router)

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "app": "video-short-generator",
        "version": "0.1.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
