# Handoff Document

## Session Summary
- **Advanced Subtitle Parsing**: Addressed the highest priority item from `TODO.md`. The `MusicXMLParser` (`src/musicxml_parser.py`) was deeply refactored using `music21`'s `.flatten().notes` and tempo mapping tools. Instead of flattening a score into a raw string and asking GPT to "guess" subtitle timestamps, the pipeline now calculates the exact start and end time (in seconds) of every individual syllable and recursively joins `begin` and `middle` syllables into whole words.
- **Pipeline Integration**: Modified `main.py`'s Content Generation step. If the parser detects structured array dicts inside the `lyrics` metadata, it completely skips the GPT prompt phase and passes the native sheet music timings down the pipeline to the ElevenLabs TTS generator and FFmpeg SRT burner, ensuring millisecond-accurate lip-syncing relative to the FluidSynth instrumental track.
- **UI Expansion**: Updated the `app.py` "Hymn Editor" tab to cleanly display the nested JSON object containing these precise offsets alongside the raw text for manual user validation.
- **Documentation Update**: Extensively updated `ROADMAP.md`, `TODO.md`, `CHANGELOG.md`, and bumped the global `VERSION` to **1.14.0**. This officially marks the completion of the entirety of Phase 5 of the roadmap.

## State of the Project
- The project's generative core is completely finished, highly polished, fully containerized, and extremely documented.
- All functional roadmap phases (Phase 1 through 5) are 100% complete.
- The pipeline now natively synchronizes lyrics to notes directly from the input `.mxl` source without relying on AI hallucination for timestamps, resulting in vastly improved karaoke-style SRT burns on the final MP4.

## Next Steps for the Next Agent
- **Docker Optimization**: The addition of `oemer` (ONNX Runtime, OpenCV) and `demucs` (PyTorch) has severely bloated the multi-stage Docker build. The top priority in `TODO.md` is investigating a minimal base image (like Alpine or Distroless) and pre-compiled libraries for the runtime stage to radically shrink the final container size and reduce deployment friction.
- **Stream Control UI**: Create a dedicated control panel in `app.py`'s sidebar that interacts with the `RadioStreamer` thread to display the currently broadcasting RTMP song and allow the user to manually trigger a "Skip Track" event.
