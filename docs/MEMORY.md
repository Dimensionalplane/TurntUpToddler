# Project Memory & Analysis

This document serves as an ongoing record of codebase observations, architectural decisions, and design preferences, ensuring continuity across development sessions and AI agents.

## Architectural Observations
- **External Dependencies:** The project relies heavily on system-level installations of `ffmpeg` (for video assembly, scaling, and subtitle burning) and `fluidsynth` (for MIDI to audio rendering).
- **SoundFont Configuration:** The default SoundFont location is hardcoded as `/usr/share/sounds/sf2/FluidR3_GM.sf2`. The native C++ engine gracefully falls back to silence if this is missing.
- **Concurrency in Streamlit:** Background processing within the Streamlit UI utilizes `concurrent.futures.ThreadPoolExecutor`. Crucially, `add_script_run_ctx` from `streamlit.runtime.scriptrunner` must be attached to each submitted future. Failing to do so breaks the UI context and prevents real-time updates.
- **Idempotency Controls:** The pipeline relies on CLI flags like `--skip-render` and `--skip-remake`. These are vital for debugging and resuming failed jobs without repeating expensive API calls to OpenAI, Replicate, or ElevenLabs.
- **Video Assembly:** Video generation, formatting (Standard 16:9 vs. Vertical 9:16), and YouTube uploading (via OAuth2) are centralized in `src/video_uploader.py`. The Shorts extraction feature (`--create-shorts`) uses FFmpeg's `segment` muxer to chop videos into 15-second intervals.
- **C++ Engine:** A native C++ core (`src/engine/HymnPlayer`) has been seeded. It wraps FluidSynth for playback and audio buffer rendering. It currently lives alongside the Python codebase and compiles via a standard `Makefile`.

## Robustness & Error Handling
- **Temporary File Cleanup:** The `main.py` orchestrator implements aggressive cleanup logic for temporary files generated mid-pipeline. Variables representing file paths must be initialized to `None` at the scope's start to prevent `UnboundLocalError` during exception handling.
- **Subtitle Sanitization:** FFmpeg's subtitle burning filter is notoriously fragile. The pipeline includes a retry loop that strips non-ASCII characters from lyrics if the initial subtitle burn crashes, falling back to a textless video if all retries fail.
- **Asset Caching:** DALL-E 3 generated images are cached locally in `.cache/art/` using an MD5 hash of the prompt. The video uploader intelligently handles local file paths using `shutil.copy2` when a cached image is used instead of an HTTP URL.

## Design & Workflow Preferences
- **Omni-Workspace Alignment:** This repository is part of a massive, 100+ nested repository workspace. AI agents must rigidly adhere to global instructions found in `UNIVERSAL_LLM_INSTRUCTIONS.md` and `AGENTS.md`.
- **Extreme Detail:** The user mandates comprehensive, highly detailed documentation for every feature, input, and architectural decision. Summaries are discouraged; exhaustive descriptions are required.
- **Autonomous Momentum:** The system and the development agents should strive for continuous, uninterrupted operation. Fix bugs on the fly, commit frequently, and immediately proceed to the next roadmap item.
- **Code Commenting:** Explain the "why" and "how" of complex logic, side effects, optimizations, and workarounds. Leave self-evident code bare to avoid noise.
- **Global Versioning:** A single version of truth exists for the application version (`VERSION` and `docs/VERSION.md`). It is dynamically parsed by the Streamlit UI and must be referenced in all commit messages.
