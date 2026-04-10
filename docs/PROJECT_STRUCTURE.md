# Project Structure

## Directory Layout
```
/
├── docs/                   # Omni-Workspace and project-specific documentation.
├── hymn_remaker/           # Core application folder.
│   ├── input/              # Drop MIDI files here.
│   ├── output/             # Generated WAVs, MP4s, and JSON metadata.
│   ├── src/                # Pipeline modules.
│   │   ├── content_generator.py # OpenAI GPT/DALL-E logic.
│   │   ├── midi_renderer.py     # FluidSynth logic.
│   │   ├── remaker.py           # Replicate MusicGen logic.
│   │   ├── tts_generator.py     # ElevenLabs logic.
│   │   ├── utils.py             # Audio mixing and retries.
│   │   └── video_uploader.py    # FFmpeg and YouTube API logic.
│   ├── app.py              # Streamlit Web UI.
│   ├── main.py             # CLI Entrypoint.
│   └── tests/              # Pytest suite.
├── scripts/                # Utility scripts (e.g., test midi generation).
└── VERSION                 # Global Single Source of Truth for the version.
```

## Submodules / External Dependencies
-   **OpenAI**: API (gpt-4-turbo, dall-e-3)
-   **Replicate**: API (meta/musicgen-melody)
-   **ElevenLabs**: API
-   **FluidSynth**: System Dependency
-   **FFmpeg**: System Dependency
