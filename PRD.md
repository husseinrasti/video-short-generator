Prompt: Build the project incrementally. Complete each phase fully before moving to the next phase. Do not scaffold unfinished features. Deliver a working MVP first, then add advanced functionality.

# Product Requirements Document (PRD)

## video-short-generator

AI-Assisted Local Video Editor for Shorts Creation

---

# Overview

Build a desktop-first web application that allows a single user to download videos from supported URLs, trim clips, arrange them on a timeline, generate subtitles, and render short-form videos (YouTube Shorts, TikTok, Instagram Reels).

This is a personal productivity tool and NOT a multi-user SaaS product.

The application should run locally on the user's machine.

No authentication, user accounts, billing, subscriptions, or cloud infrastructure are required.

The focus is speed, simplicity, and local-first workflows.

---

# Core Requirements

## Goal

Enable a user to:

1. Import videos from URLs.
2. Extract clips from videos.
3. Arrange clips on a timeline.
4. Extract audio.
5. Generate and edit subtitles.
6. Add text overlays.
7. Add images.
8. Render final videos.
9. Use AI features with their own API keys.

---

# Technical Requirements

## Backend

Use Python.

Preferred stack:

* Python 3.13+
* FastAPI
* FFmpeg
* yt-dlp
* OpenAI Whisper (local)
* Pydantic
* Uvicorn

No database.

All project data should be stored as JSON files.

---

## Frontend

Use:

* Next.js (latest stable version)
* React (latest stable version)
* TypeScript
* Tailwind CSS
* shadcn/ui

The UI should resemble a lightweight video editor.

---

# Important Development Rule

Always use the latest stable version of every library, framework, and dependency at implementation time.

Do not use deprecated packages.

Do not use abandoned packages.

Verify compatibility before selecting dependencies.

---

# Storage Architecture

Use local filesystem storage only.

Example:

workspace/
├── videos/
├── audio/
├── images/
├── subtitles/
├── projects/
├── renders/
└── temp/

Project state should be saved in JSON.

Example:

{
"name": "world-cup-short",
"timeline": [],
"assets": []
}

No SQL database.

No Redis.

No Celery.

No Docker requirement for MVP.

---

# Feature 1: Video Import

Supported sources:

* YouTube URLs
* Pinterest video URLs

Requirements:

* Download video locally
* Show download progress
* Store downloaded assets locally
* Generate thumbnail preview

Implementation recommendation:

* yt-dlp

---

# Feature 2: Video Preview

Requirements:

* Preview video in browser
* Display current timestamp
* Play
* Pause
* Seek

---

# Feature 3: Clip Extraction

Requirements:

User can:

* Select start time
* Select end time

Using:

* Timeline scrubber
* Range slider

Example:

Start: 00:04
End: 00:10

Create clip:

clip_001.mp4

Requirements:

* Non-destructive editing
* Original file remains unchanged

---

# Feature 4: Asset Library

Display imported assets:

## Videos

* Thumbnail
* Duration
* Resolution

## Audio

* Waveform preview
* Duration

## Images

* Preview

## Subtitles

* Transcript preview

---

# Feature 5: Audio Extraction

Requirements:

Extract audio from any video.

Output:

* mp3
* wav

User can:

* Add extracted audio to timeline
* Mute original clip audio
* Adjust volume

---

# Feature 6: Multi-Track Timeline

Create a professional timeline system.

Tracks:

Video Track

Audio Track

Subtitle Track

Text Track

Image Track

Capabilities:

* Drag and drop
* Reorder
* Resize clips
* Split clips
* Delete clips
* Move clips
* Zoom timeline

Timeline should feel similar to Premiere Pro, CapCut, or Descript.

---

# Feature 7: Text Overlay Editor

User can add text anywhere.

Properties:

* Font family
* Font size
* Font weight
* Color
* Background color
* Border
* Shadow
* Opacity
* Position
* Rotation

Animation support:

* Fade In
* Fade Out
* Scale In
* Slide Up
* Slide Down

---

# Feature 8: Image Overlay

Supported formats:

* PNG
* JPG
* WEBP

Capabilities:

* Resize
* Rotate
* Opacity
* Layer ordering

Images can be placed anywhere on timeline.

---

# Feature 9: Speech-to-Text

Requirements:

Use local Whisper.

User selects video.

System generates:

Transcript

Example:

00:00 Hello everyone
00:02 Welcome back

Store transcript locally.

No cloud dependency required.

---

# Feature 10: Subtitle Generation

Convert transcript into subtitle blocks.

Capabilities:

* Edit subtitle text
* Delete subtitle
* Merge subtitle
* Split subtitle
* Change timing

Styles:

* TikTok style
* YouTube Shorts style
* Minimal style

Support word highlighting.

---

# Feature 11: AI Panel

Right sidebar.

User provides API keys.

Supported providers:

* OpenAI
* Anthropic
* Google Gemini

Architecture should allow adding future providers.

Store API keys locally.

Never hardcode keys.

---

# Feature 12: AI Features

## Generate Video Description

Input:

* Transcript
* Video title

Output:

* YouTube description
* Hashtags
* Keywords

---

## Generate Video Title

Input:

* Transcript

Output:

* Multiple title suggestions

---

## Generate Captions

Input:

* Transcript

Output:

Engaging text overlays.

Example:

"WHAT A GOAL!"

---

## Highlight Detection

Input:

Transcript only.

Do NOT send video files to AI.

Output:

Suggested clip ranges.

Example:

[
{
"start": 52,
"end": 60,
"reason": "Exciting moment"
}
]

Token usage should remain minimal.

---

# Feature 13: Rendering

Requirements:

Use FFmpeg.

Export formats:

* MP4

Aspect ratios:

* 9:16
* 16:9
* 1:1

Quality:

* 720p
* 1080p
* 1440p

Render progress must be visible.

---

# Feature 14: Project Persistence

Save project.

Load project.

Auto-save every 30 seconds.

Everything stored locally.

No server-side persistence.

---

# Nice-to-Have Features

## Silence Detection

Detect silent sections.

Suggest removal.

---

## Auto Subtitle Styling

Automatically highlight active spoken words.

---

## Keyboard Shortcuts

Space = Play/Pause

S = Split

Delete = Remove

Ctrl+Z = Undo

Ctrl+Shift+Z = Redo

---

## AI Command Assistant

Examples:

"Create subtitles"

"Find best highlights"

"Generate YouTube description"

The assistant should translate requests into application actions.

---

# Non-Goals

Do NOT build:

* Authentication
* Multi-user support
* SaaS billing
* Team collaboration
* Cloud rendering
* Database infrastructure
* Enterprise features

This is a local-first personal productivity application.

---

# Success Criteria

A user can:

1. Paste multiple YouTube/Pinterest URLs.
2. Download videos.
3. Trim clips.
4. Arrange clips on a timeline.
5. Extract audio.
6. Generate subtitles.
7. Add text and images.
8. Use AI assistance.
9. Generate YouTube metadata.
10. Export a complete YouTube Short in MP4 format.

The application should be fully functional locally without requiring any database or cloud infrastructure.

# Feature Request: AI Narration Studio

## Important Constraint

Do NOT refactor the existing application architecture.

Do NOT modify existing timeline functionality.

Do NOT redesign existing UI.

Do NOT introduce a database.

Do NOT introduce authentication.

Implement this as an additive feature that integrates with the existing editor.

The current application must continue working exactly as it does now.

---

# Goal

Add an AI Narration Studio that allows the user to:

1. Enter a topic, notes, or raw text.
2. Generate an engaging narration script using an LLM.
3. Edit the generated script.
4. Convert the script into speech using a TTS provider.
5. Automatically generate subtitles from the narration.
6. Insert the generated audio and subtitles directly into the existing timeline.

This feature should be optional and not affect users who do not use AI features.

---

# New UI Section

Add a new panel:

AI Narration Studio

The panel may be placed:

* Right sidebar
  OR
* Separate modal

Do not modify existing editor layout significantly.

---

# Step 1: AI Provider Configuration

Allow user to configure API keys.

Supported providers:

* OpenAI
* Anthropic
* Google Gemini

Store keys locally.

Do not hardcode keys.

Do not send keys to any external service except the selected provider.

---

# Step 2: Narration Input

Allow three input modes.

## Mode A: Topic

Example:

World Cup Controversies

---

## Mode B: Notes

Example:

* Hand of God
* Zidane headbutt
* Suarez handball

---

## Mode C: Raw Text

User provides full text manually.

---

# Step 3: Script Generation

Add button:

Generate Narration

Prompt Requirements:

Generate a highly engaging narration script for a YouTube Short.

Requirements:

* Attention-grabbing hook in first 3 seconds
* Conversational tone
* Fast-paced
* Suitable for voice narration
* Clear sentence structure
* No markdown
* No bullet points
* No emojis
* Between 30 and 90 seconds of speaking time

Return only narration text.

---

# Step 4: Script Editor

After generation:

Show editable text area.

User can:

* Edit script
* Rewrite manually
* Copy script
* Save script

Add buttons:

* Regenerate
* Shorter
* Longer
* More Exciting
* More Professional

These actions should use the selected LLM.

---

# Step 5: Text-to-Speech

Add section:

Generate Voiceover

Supported providers:

* OpenAI TTS
* ElevenLabs

Architecture should allow future providers.

User selects:

* Voice
* Speed
* Model

Output:

voiceover.mp3

Store locally.

---

# Step 6: Subtitle Generation

After TTS generation:

Automatically create subtitle entries.

Use either:

* Generated script text
  OR
* Whisper alignment

Preferred:

Generate timestamped subtitles using Whisper alignment.

Output:

SRT format

Store locally.

---

# Step 7: Timeline Integration

Add button:

Insert Into Timeline

When clicked:

Automatically:

1. Add generated audio to Audio Track.
2. Add generated subtitles to Subtitle Track.

Do not overwrite existing tracks.

Append as new timeline assets.

---

# Step 8: YouTube Metadata Generator

Add section:

Generate Metadata

Input:

* Narration Script

Output:

1. Title Suggestions (5 options)

2. YouTube Description

3. Hashtags

4. SEO Keywords

Prompt Requirements:

Generate:

* 5 click-worthy titles
* A YouTube Shorts description
* Relevant hashtags
* SEO keywords

Return structured JSON.

---

# Step 9: Token Optimization

IMPORTANT

Minimize token usage.

Never send:

* Video files
* Audio files
* Images

Only send:

* Topic
* Notes
* Narration text
* Transcript text

All AI features must be text-only.

---

# Step 10: Future Extensibility

Design the feature using provider abstractions.

Example:

AIProvider

* OpenAIProvider
* GeminiProvider
* AnthropicProvider

TTSProvider

* OpenAITTSProvider
* ElevenLabsProvider

Future providers should be easy to add.

---

# Success Criteria

A user can:

1. Enter a topic.
2. Generate narration.
3. Edit narration.
4. Generate voiceover audio.
5. Generate subtitles.
6. Insert both into the existing timeline.
7. Generate YouTube titles and descriptions.

All without changing the current editor workflow.


# Additional Feature: Narration Duration Estimation

## Goal

Help users determine whether a generated narration is suitable for short-form video before generating audio.

This feature should require no AI calls and should work instantly.

---

# Estimated Speaking Duration

After a narration script is generated or edited:

Automatically calculate:

* Estimated speaking duration
* Estimated word count

Display:

Word Count: 128 words

Estimated Duration: 46 seconds

---

# Calculation Logic

Use average speaking speed.

Default:

150 words per minute

Formula:

duration_seconds = (word_count / 150) * 60

---

# Voice-Aware Estimation

If a TTS voice is selected:

Adjust estimation based on voice speed.

Examples:

0.8x speed

1.0x speed

1.2x speed

Recalculate duration automatically.

---

# Shorts Compatibility Indicator

Display a visual indicator.

Examples:

🟢 Ideal Short
0–60 seconds

🟡 Long Short
60–90 seconds

🔴 Too Long
90+ seconds

---

# Timeline Compatibility

Display:

Current Timeline Length

Narration Length

Difference

Example:

Timeline Length: 52 seconds

Narration Length: 47 seconds

Status: Good Match

---

# Auto Optimization Suggestions

If narration exceeds target duration:

Display quick actions:

* Make Shorter
* Reduce by 20%
* Reduce by 50%

If narration is too short:

Display:

* Expand Script
* Add More Detail
* Increase Duration

These actions may use the selected LLM.

---

# Live Updates

Whenever the user edits the script manually:

Recalculate instantly.

No API calls required.

No backend processing required.

Should feel real-time.

---

# Success Criteria

Before generating audio, the user can immediately see:

* Word count
* Estimated speaking duration
* Shorts compatibility status
* Timeline compatibility

This helps prevent generating voiceovers that are too long or too short for the intended video.

# Additional Feature: Narration & Timeline Sync Assistant

## Goal

Help users ensure that narration duration and available footage are aligned before rendering.

This feature should work locally and require no AI calls.

The purpose is to prevent situations where:

* Narration is longer than available footage.
* Footage is significantly longer than narration.
* Large gaps exist in the final video.

---

# Sync Analysis Panel

Add a panel:

Narration Sync Analysis

Display:

* Narration Duration
* Timeline Duration
* Total Video Footage
* Total Audio Duration
* Total Subtitle Duration

---

# Duration Comparison

Example:

Narration Duration: 47 seconds

Timeline Duration: 52 seconds

Difference: +5 seconds

Status: Good Match

---

Another example:

Narration Duration: 65 seconds

Timeline Duration: 42 seconds

Difference: -23 seconds

Status: Insufficient Footage

---

# Status Categories

## Perfect Match

Difference less than 3 seconds

Display:

🟢 Perfect Match

---

## Good Match

Difference between 3 and 10 seconds

Display:

🟢 Good Match

---

## Warning

Difference between 10 and 20 seconds

Display:

🟡 Review Timeline

---

## Poor Match

Difference greater than 20 seconds

Display:

🔴 Significant Mismatch

---

# Coverage Analysis

Analyze whether footage covers the full narration.

Example:

Narration:

45 seconds

Available clips:

Clip 1 = 10s

Clip 2 = 15s

Clip 3 = 8s

Total = 33s

Display:

Missing Coverage: 12 seconds

---

# Excess Footage Detection

Example:

Narration:

45 seconds

Available clips:

70 seconds

Display:

Unused Footage: 25 seconds

---

# Gap Detection

Analyze timeline structure.

Detect:

* Empty spaces
* Missing media segments
* Subtitle gaps
* Audio gaps

Display warnings.

Example:

Gap Detected:
00:18 → 00:22

Duration:
4 seconds

---

# Auto Suggestions

Provide suggestions.

Examples:

Add More Footage

Trim Narration

Extend Existing Clips

Insert Image Slides

Add B-Roll

Generate Additional Narration

Suggestions should be generated using local calculations whenever possible.

No AI required.

---

# Narration Placement Preview

Display estimated synchronization:

Segment 1:
0s–10s

Segment 2:
10s–22s

Segment 3:
22s–35s

This allows the user to visually understand how narration aligns with clips before rendering.

---

# Real-Time Updates

Whenever:

* Narration changes
* Clips are added
* Clips are trimmed
* Timeline order changes

The analysis should automatically refresh.

No manual refresh required.

---

# Optional Future AI Enhancement

Future version may include:

"Auto Match Narration To Clips"

The system can suggest which clips best fit each narration segment.

This should not be implemented now.

Only prepare the architecture for future support.

---

# Success Criteria

Before rendering, users can immediately see:

* Whether narration fits available footage.
* Whether footage is too short.
* Whether footage is too long.
* Whether gaps exist.
* Whether additional assets are needed.

This should significantly reduce failed renders and improve short-form video production workflow.
