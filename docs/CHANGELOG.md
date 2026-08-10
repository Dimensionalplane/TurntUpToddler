# Changelog

All notable changes to this project will be documented in this file.

## [5.41.0] - Current

### Added

- **Suno Cover Pipeline (tut_run.py)**: CDP-based automated cover generation for top 5 children's songs.
  - 5 songs × 10 genres × 4 speeds × 2 vocal modes = 400 tracks
  - React portal modal detection via querySelectorAll (Suno UI updated 2026)
  - Upload flow: Add Audio → Browse → File chooser → Full Song → Describe → Continue
  - Feed polling with old/new clip diff for cover detection
  - Navigation timeout resilience with retry
- **Kling AI Video Generator (tut_kling.py)**: Text-to-video integration for children's music videos
  - Free tier API: create → poll (15min timeout) → download
  - Batch generation for all MP3s
- **YouTube Uploader (tut_upload.py)**: OAuth-based batch upload to TurntUpToddler channel
  - Auto-parses song/genre/speed/vocal from filename conventions
  - Batch mode for all videos in videos/
- **Missing Song Renderer (render_missing_songs.py)**: Sine-wave WAV rendering for row_row_boat + itsy_bitsy at all speeds
- **Branch Merges**: Merged feat-editor-endpoints-tooltips into main

## [5.39.0] - 2026

### Added

- **Editor Metadata API**: Implemented `/api/v1/editor/metadata` endpoint in `hymn_remaker/api.py` to extract note-by-note synchronization from MusicXML files.
- **Cluster Rendering API**: Implemented `/api/v1/editor/cluster` endpoint in `hymn_remaker/api.py` to submit generation jobs to a RabbitMQ render cluster.
- **Editor Frontend Integration**: Updated `frontend/src/app/editor/page.tsx` to include interactive UI elements for Metadata Extraction and Cluster Rendering jobs, including descriptive tooltips.

## [1.26.1] - Previous

### Changed

- **Submodule Renaming**: Renamed the submodule directory and all internal/external configurations from `hymnmania` to `TUT` to match the new naming scheme.
- **Branch Merging**: Fast-forwarded and merged all development branches (including `origin/master`) into the `main` branch.
- **Reference Updates**: Renamed all instances of `hymnmania` in docs and inventory manifests to `TUT`.

## [1.26.0] - 2026-05-20

### Added

- **Multi-Voice Spatial Expansion via PyRubberband**: Upgraded the ElevenLabs choral harmony algorithm. By replacing crude framerate shifting with high-fidelity `pyrubberband` pitch-shifting, parallel vocal tracks are now perfectly pitch-shifted (+4 and +7 semitones) without altering their temporal duration. This results in significantly clearer, crisper multi-part harmonies.

## [1.25.1] - Previous

### Added

- **Redis Render Polling System**: Connected the Streamlit UI to a Redis state store to actively poll and reflect the status of tasks queued in the RabbitMQ render cluster.
- **Headless Worker Microservice**: Added `worker.py` daemon capable of pulling from RabbitMQ and updating Redis.
- **Exhaustive Documentation Pivot**: Massively expanded `VISION.md`, `ROADMAP.md`, `TODO.md`, `LIBRARIES.md`, and `HANDOFF.md` to capture the new microservices architecture and absolute autonomous generation goals.
- **Universal LLM Agent Rules**: Prepared rollout of universal instruction sets (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `GPT.md`, `copilot-instructions.md`) to standardize documentation, versioning, and feature progression across all future AI agent sessions.
