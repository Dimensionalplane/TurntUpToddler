# CHANGELOG - HYMN REMAKER

## [1.47.0] - 2024-05-30
### Added
- **Algorithmic Style Transfer:** Integrated `Music21` into `OMRProcessor` to allow for score-level modifications. Supports initial 'Swing' and 'Lullaby' arrangement styles.
- **Arrangement Selection:** Added "Arrangement (OMR)" dropdown to the Next.js dashboard.

### Fixed
- Improved file extension handling during score modification to support both `.mxl` and `.musicxml` reliably.

## [1.46.0] - 2024-05-29
### Added
- **Multi-Channel Webhooks:** `WebhookNotifier` now supports multiple Discord/Slack channels via a configuration dictionary.
- **Style-Transfer Placeholder:** Added hook in `OMRProcessor` for future algorithmic score modifications.

### Fixed
- **Frontend URL Wiring:** Fixed a hardcoded backend URL in the dashboard to support dynamic deployment environments.

## [1.45.0] - 2024-05-28
### Added
- **YouTube Live Radio:** Added full support for streaming to YouTube Live RTMP endpoints.
- **Improved Stream Monitoring:** The radio worker now verifies the health of the streaming thread before reporting status to Redis.

### Fixed
- **RTMP Compatibility:** Added `-flvflags no_duration_filesize` to `RadioStreamer` for better compatibility with YouTube's RTMP ingest servers.
- **UI UX:** Improved radio control labels and added loading states to the dashboard.

## [1.44.0] - 2024-05-27
### Added
- **AI Video Caching:** Implemented Redis-based caching for AI-generated video URLs (Sora/Runway) to prevent redundant generation costs.
- **Enhanced Lyric Normalization:** Added Unicode NFKD normalization to `VideoProducer` to preserve accented characters by converting them to their ASCII equivalents (e.g., ñ -> n) rather than deleting them.

### Changed
- Distributed workers and API now share the same Redis-backed module state for `ContentGenerator`.

## [1.43.0] - 2024-05-26
### Added
- **4K UHD Rendering:** Added support for ultra-high-definition 4K video output (3840x2160) across the pipeline.
- **Resolution Selection:** New dropdown in Next.js dashboard to toggle between 1080p and 4K.
- **Improved AI Video Looping:** Enhanced Sora/Runway prompting logic to encourage seamless infinite background loops.

### Fixed
- **API Modularization:** Fixed a gap where `SunoRemaker` was missing from the backend module registry, improving task reliability.

## [1.42.0] - 2024-05-25
### Added
- **Musical Style Presets:** Introduced a system for genre presets (Deep House, Lofi, Synthwave, etc.) to simplify generation.
- **Config API:** New `/api/v1/config/presets` endpoint to serve dynamic configuration to the frontend.
- **Style Dropdown:** Added a searchable preset dropdown to the Next.js `GenerateForm`.

### Fixed
- **Lyric Sanitization:** Implemented regex filtering for non-standard characters in SRT generation to prevent FFmpeg burning failures.
- **SRT Encoding:** Enforced UTF-8 encoding for subtitle files.

### Changed
- Refactored `settings.py` to centralize style configurations.

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
