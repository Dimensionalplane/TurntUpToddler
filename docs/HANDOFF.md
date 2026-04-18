# Handoff Document

## Session Summary
- **Pybind11 Integration**: Wired the native C++ `HymnPlayer` engine into the Python orchestrator via `MidiRenderer`. It now natively renders audio buffers into NumPy arrays and exports them via `soundfile`, falling back to `midi2audio` only if compilation fails.
- **Centralized Settings**: Created `hymn_remaker/settings.py` to consolidate all hardcoded paths (SoundFonts, caching, I/O) and default parameters across `main.py`, `app.py`, and the source modules.
- **TTS Alignment**: Modified `hymn_remaker/src/utils.py` to include an FFmpeg `atempo` time-stretching function that perfectly aligns the duration of the ElevenLabs vocal track with the Replicate instrumental track before mixing.

## State of the Project
- The pipeline is now significantly less reliant on shell-wrapper hacks for its core audio synthesis, leveraging a direct memory bridge to FluidSynth.
- Codebase maintainability is vastly improved with centralized configurations.
- Audio fidelity is improved due to exact duration matching during vocal ducking.

## Next Steps for the Next Agent
- **Roadmap Phase 3:** Begin looking into MusicXML / OMR (Optical Music Recognition) integration, perhaps using `music21` to parse `.mxl` metadata prior to GPT analysis.
- **Dependency Audit:** Audit `requirements.txt` to ensure strict version pinning for production stability.
- Investigate multi-stage Dockerfile builds to compile the Pybind11 extension natively within the deployment container.
