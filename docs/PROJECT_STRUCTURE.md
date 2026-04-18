# Project Structure & External Libraries

This document provides a comprehensive overview of the Hymn Remaker directory layout, the purpose of each component, and the external libraries and APIs utilized.

## Directory Layout

```text
hymnmania/
├── VERSION                     # Global version source of truth (e.g., 1.7.2).
├── Makefile                    # Build script for the native C++ HymnPlayer engine.
├── requirements.txt            # Python dependencies.
├── docs/                       # Comprehensive Omni-Workspace documentation suite.
│   ├── AGENTS.md               # Overview of AI agent roles and workflows.
│   ├── UNIVERSAL_LLM_INSTRUCTIONS.md # Core instructions that all models must obey.
│   ├── CLAUDE.md / GPT.md      # Model-specific overrides and prompts.
│   ├── VISION.md               # Ultimate project goals and design philosophy.
│   ├── ROADMAP.md              # Long-term phases and architectural goals.
│   ├── TODO.md                 # Immediate, actionable developer tasks.
│   ├── IDEAS.md                # Creative brainstorms and feature expansions.
│   ├── MEMORY.md               # Technical observations and workflow preferences.
│   ├── DEPLOY.md               # Instructions for system prep, Docker, and API keys.
│   ├── CHANGELOG.md            # Version history following "Keep a Changelog".
│   ├── HANDOFF.md              # State summary passed between AI sessions.
│   ├── VERSION.md              # Mirrored version file for documentation links.
│   └── PROJECT_STRUCTURE.md    # This file.
├── hymn_remaker/               # Primary Python application package.
│   ├── main.py                 # The core orchestrator and daemon loop.
│   ├── app.py                  # The Streamlit Web UI entry point.
│   ├── input/                  # Directory monitored by watchdog for incoming MIDI/MXL files.
│   ├── output/                 # Destination for final .mp4 videos and Shorts.
│   └── tests/                  # Pytest suite for the Python pipeline.
│       └── test_*.py           # Mocks and unit tests for pipeline components.
├── src/                        # Cross-language source files and utilities.
│   ├── engine/                 # Native C++ Audio Engine.
│   │   ├── HymnPlayer.h        # Header defining the FluidSynth wrapper class.
│   │   └── HymnPlayer.cpp      # Implementation of native audio loading and rendering.
│   └── video_uploader.py       # Python module for FFmpeg assembly and YouTube OAuth.
├── tests/                      # Native C++ tests.
│   └── HymnPlayerTests.cpp     # Unit tests for the C++ engine (builds to `run_tests`).
└── .cache/                     # Local caching directory.
    └── art/                    # Stores DALL-E generated images (hashed by prompt).
```

## External Libraries & System Dependencies

The project relies on a mix of native system libraries, Python packages, and cloud APIs.

### System Libraries (Native)
*   **FluidSynth** (`libfluidsynth-dev`): Required for the C++ `HymnPlayer` engine to parse MIDI data and render audio buffers using SoundFonts.
*   **FFmpeg**: An absolute prerequisite for the Python pipeline. Utilized extensively in `video_uploader.py` for audio mixing, video scaling (16:9 vs 9:16), hardcoding subtitles, and muxing.

### Python Libraries (Internal)
*   `pydub`: Used heavily for audio manipulation, specifically for mixing the generated instrumental with the TTS vocal track and applying "ducking" (lowering instrumental volume when vocals play).
*   `midi2audio`: A lightweight Python wrapper around the `fluidsynth` command-line tool. (Targeted for replacement by the native `HymnPlayer` via Pybind11).
*   `streamlit`: Powers the interactive web dashboard (`app.py`), allowing users to configure ElevenLabs voices, video formats, and monitor daemon progress.
*   `watchdog`: Provides the file-system monitoring capabilities required for the `--daemon` mode in `main.py`.
*   `pytest` & `pytest-mock`: Used exclusively in the `hymn_remaker/tests/` directory to ensure pipeline orchestrator reliability without triggering expensive API calls.

### Cloud APIs
*   **OpenAI (`gpt-4-turbo`, `dall-e-3`)**: Used to generate SEO-optimized titles, descriptions, contextual lyrics based on the hymn's mood, and unique cover art.
*   **Replicate (`musicgen-melody`)**: Used to transform the raw FluidSynth audio render into a stylized Deep House track.
*   **ElevenLabs**: Used to generate hyper-realistic, emotive vocal tracks from the GPT-generated lyrics.
*   **YouTube Data API v3**: Used within `video_uploader.py` to automatically publish completed videos to the user's channel.
