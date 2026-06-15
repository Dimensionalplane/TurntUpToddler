# CHANGELOG - HYMN REMAKER

## [1.40.0] - 2024-05-23
### Added
- **Dynamic AI Video Overlay:** Support for dynamic video backgrounds (Sora/Runway) in the rendering pipeline.
- **Looped Video Support:** Implemented `-stream_loop -1` FFmpeg filtering for seamless background looping.
- **Frontend Toggles:** Added "Dynamic AI Video Overlay" checkbox to `GenerateForm.js`.
- **Enhanced Review:** Added `video_prompt` editing to the `ReviewModal.js` interactive loop.

### Fixed
- FFmpeg command generation for video-based background assets.
- Temporary file extension preservation for background assets.

### Changed
- Integrated video generation step into `process_single_midi` pipeline.
- Updated project documentation (VISION, MEMORY, ROADMAP, TODO, DEPLOY, IDEAS).

## [1.39.0] - 2024-05-22
### Added
- **Interactive Review System:** Distributed blocking/approval loop via Redis.
- **Kubernetes Orchestration:** Complete Kustomize manifests for cluster deployment.
- **FastAPI Migration:** Decomposed monolith into microservices.
