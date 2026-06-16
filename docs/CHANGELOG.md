# CHANGELOG - HYMN REMAKER

## [1.41.0] - 2024-05-24
### Added
- **Job Retry Mechanism:** Users can now re-trigger failed generation jobs with a single click from the dashboard.
- **Enhanced UI Telemetry:** Status cards now show job completion percentage and sub-step messages more prominently.
- **Adaptive Progress Bars:** Progress bar color changes to amber (warning) when a job is awaiting user review.

### Changed
- Refactored `api.py` to store job configurations in Redis for persistence.
- Updated Next.js dashboard with improved task visibility and underscored status formatting.

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
