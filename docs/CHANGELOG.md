# Changelog

All notable changes to this project will be documented in this file.

## [1.31.0] - 2026-06-14
### Added
- **Radio Streamer Web Integration**: Ported live RTMP broadcast controls to the distributed web stack.
- **Broadcast API**: Implemented endpoints for starting, stopping, and skipping tracks on the `RadioStreamer` background thread.
- **Real-time Radio Monitoring**: Developed the `RadioControls` Next.js component to monitor "Now Playing" tracks and streaming status via polling.

## [1.30.0] - 2026-06-14
### Added
- **Hymn Editor Web Port**: Successfully ported all backend rendering and extraction tools from the original Streamlit "Hymn Editor" tab to the FastAPI/Next.js stack.
- **Native Audio Preview API**: Implemented `/api/v1/editor/preview` to allow real-time C++ based audio synthesis from the web UI.
- **MusicXML Metadata Extraction**: Implemented `/api/v1/editor/extract` for note-synced lyric and title extraction.
- **Cluster Submission**: Integrated RabbitMQ job queueing directly into the FastAPI backend and Next.js frontend.

## [1.29.0] - 2026-06-14
### Added
- **Interactive Next.js Dashboard**: Developed the first functional iteration of the decoupled frontend, including a generation form with full v1.28.0 parameter support and automated history polling.
- **Dynamic Job Tracking**: Implemented session-based job tracking on the frontend to monitor background processing status in real-time.

## [1.28.0] - 2026-06-14
### Added
- **Phase 7 Initiation: Next.js Frontend Scaffold**: Created the `frontend/` directory and scaffolded a Next.js application to replace the Streamlit monolith.
- **API CORS Support**: Added `CORSMiddleware` to the FastAPI backend to support cross-origin requests from the Next.js frontend.
- **Job Status API**: Implemented `/api/v1/jobs/{job_id}` endpoint to expose background job status from Redis.

## [1.27.0] - 2026-06-14
### Added
- **Multi-Stage Docker Optimization**: Refactored `Dockerfile` to implement an optimized multi-stage build, separating heavy ML dependencies (PyTorch, oemer, demucs) from the lightweight runtime stage.
- **Repository Consolidation**: Merged multiple outstanding feature branches (`feat/comprehensive-docs-and-tts-params`, `feature/web-ui-and-parallelization`) into the main branch to unify the codebase.

## [1.26.2] - 2026-06-11
### Added
- **Kids Mode**: Implemented a dedicated Kids Mode pipeline with automated nursery rhyme downloads, child-friendly styling, and YouTube COPPA compliance.

## [1.26.0] - 2026-05-20
### Added
- **Multi-Voice Spatial Expansion via PyRubberband**: Upgraded the ElevenLabs choral harmony algorithm. By replacing crude framerate shifting with high-fidelity `pyrubberband` pitch-shifting, parallel vocal tracks are now perfectly pitch-shifted (+4 and +7 semitones) without altering their temporal duration. This results in significantly clearer, crisper multi-part harmonies.

## [1.25.1] - Previous
### Added
- **Redis Render Polling System**: Connected the Streamlit UI to a Redis state store to actively poll and reflect the status of tasks queued in the RabbitMQ render cluster.
- **Headless Worker Microservice**: Added `worker.py` daemon capable of pulling from RabbitMQ and updating Redis.
- **Exhaustive Documentation Pivot**: Massively expanded `VISION.md`, `ROADMAP.md`, `TODO.md`, `LIBRARIES.md`, and `HANDOFF.md` to capture the new microservices architecture and absolute autonomous generation goals.
- **Universal LLM Agent Rules**: Prepared rollout of universal instruction sets (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `GPT.md`, `copilot-instructions.md`) to standardize documentation, versioning, and feature progression across all future AI agent sessions.
