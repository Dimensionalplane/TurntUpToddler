# System Memory & Context

*   **Project Context**: Part of the Robert Pelloni Omni-Workspace.
*   **Current Focus**: Polishing the pipeline by exposing advanced TTS settings and enforcing global version tracking.
*   **Observations**:
    *   The Streamlit UI uses concurrent threads. The `add_script_run_ctx` patch is critical and must not be removed.
    *   FFmpeg occasionally fails when burning subtitles if paths aren't escaped properly. The current fallback (run without subtitles) is necessary.
    *   The system relies on a local installation of FluidSynth and a SoundFont, which makes Docker the strongly preferred deployment method.
# Project Memory & Analysis

This document serves as an ongoing record of codebase observations, architectural decisions, and design preferences, ensuring continuity across development sessions and AI agents.

## Architectural Observations
- **External Dependencies:** The project relies heavily on system-level installations of `ffmpeg` (for video assembly, scaling, subtitle styling, and time-stretching) and `fluidsynth` (for MIDI to audio rendering).
- **SoundFont Configuration:** Default SoundFont locations are managed centrally in `hymn_remaker/settings.py`. The native C++ engine gracefully falls back to silence if missing.
- **Concurrency in Streamlit:** Background processing within the Streamlit UI utilizes `concurrent.futures.ThreadPoolExecutor`. Crucially, the context hook `add_script_run_ctx` must be passed the actual thread context from the main thread (retrieved via `get_script_run_ctx()`) *inside* the executing worker function. Passing a `Future` object causes crashes.
- **Thread Safety in Audio Rendering:** The native C++ `HymnPlayer` engine (via `pybind11`) is stateful and maintains pointers to FluidSynth's core memory. Consequently, `MidiRenderer.render` must instantiate a *new* instance of `HymnPlayer` internally for every concurrent job; making it a singleton class attribute will cause catastrophic multithreading data races and segmentation faults.
- **Idempotency Controls:** The pipeline relies on CLI flags like `--skip-render` and `--skip-remake`. These are critical for debugging and resuming failed jobs without repeating expensive API calls to OpenAI, Replicate, or ElevenLabs. When the Streamlit "Interactive Review Mode" triggers a script re-run upon user approval, these flags are automatically overridden to `True` for the specific file to prevent redundant Replicate/OpenAI charges.
- **Video Assembly:** Video generation, formatting (Standard 16:9 vs. Vertical 9:16), subtitle hex-to-ASS color parsing, and YouTube uploading (via OAuth2) are centralized in `src/video_uploader.py`. The Shorts extraction feature (`--create-shorts`) uses FFmpeg's `segment` muxer to chop videos into 15-second intervals.
- **Advanced Input Parsing:** `hymn_remaker/src/musicxml_parser.py` utilizes the `music21` package to ingest `.mxl` and `.xml` files, extracting native lyrics, titles, and composer metadata. It outputs a standard `.mid` file to continue down the normal rendering path, allowing the metadata to optionally bypass the GPT generative step.
- **TTS Alignment Smoothing:** `hymn_remaker/src/utils.py` computes the duration of the instrumental remix and time-stretches the generated ElevenLabs vocal track to identically match it using FFmpeg's `atempo` filter (capped strictly between ratios 0.5x and 2.0x to prevent crashes).

## Robustness & Error Handling
- **Temporary File Cleanup:** The `main.py` orchestrator implements aggressive cleanup logic for temporary files generated mid-pipeline. Variables representing file paths must be initialized to `None` at the scope's start to prevent `UnboundLocalError` during exception handling.
- **Subtitle Sanitization:** FFmpeg's subtitle burning filter is notoriously fragile. The pipeline includes a retry loop that strips non-ASCII characters from lyrics if the initial subtitle burn crashes, falling back to a textless video if all retries fail.
- **Asset Caching:** DALL-E 3 generated images are cached locally in `settings.ART_CACHE_DIR` using an MD5 hash of the prompt. The video uploader intelligently handles local file paths using `shutil.copy2` when a cached image is used instead of an HTTP URL.

## Design & Workflow Preferences
- **Omni-Workspace Alignment:** This repository is part of a massive, 100+ nested repository workspace. AI agents must rigidly adhere to global instructions found in `UNIVERSAL_LLM_INSTRUCTIONS.md` and `AGENTS.md`.
- **Extreme Detail:** The user mandates comprehensive, highly detailed documentation for every feature, input, and architectural decision. Summaries are discouraged; exhaustive descriptions are required.
- **Autonomous Momentum:** The system and the development agents should strive for continuous, uninterrupted operation. Fix bugs on the fly, commit frequently, and immediately proceed to the next roadmap item.
- **Code Commenting:** Explain the "why" and "how" of complex logic, side effects, optimizations, and workarounds. Leave self-evident code bare to avoid noise.
- **Global Versioning:** A single version of truth exists for the application version (`VERSION` and `docs/VERSION.md`). It is dynamically parsed by the Streamlit UI and must be referenced in all commit messages.