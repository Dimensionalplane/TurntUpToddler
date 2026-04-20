# Handoff Document

## Session Summary
- **Multi-Voice Harmonization**: Upgraded the ElevenLabs `tts_generator.py` to parse comma-separated `voice_ids` from the Streamlit UI. The system generates discrete audio files per voice, algorithmically pitch-shifts secondary voices (using `pydub` frame-rate overrides) to create a major triad chord (+4, +7 semitones), pans them to create spatial width, and mixes them onto the primary melody track.
- **Dynamic Tempo Extraction**: Leveraged `mido` inside `src/midi_renderer.py` to parse the global `set_tempo` BPM from the raw `.mid` or `.mxl` files. The orchestrator now injects this precise numeric BPM (e.g., `120.0 BPM`) directly into the Replicate/MusicGen style prompt to prevent AI tempo-drifting from the original sheet music.
- **Hymn Editor Toolbar**: Addressed the UI incompleteness by refactoring `app.py` into a robust, multi-tab Streamlit dashboard. The new "Hymn Editor" tab acts as a standalone sandbox exposing raw backend utilities (MusicXML lyric extraction to `.txt`, lightning-fast native C++ audio preview rendering via Pybind11) without firing the full pipeline.
- **Documentation Update**: Extensively updated `ROADMAP.md`, `TODO.md`, `CHANGELOG.md`, and bumped the global `VERSION` to **1.10.0**, officially marking the completion of Phase 4 (Creative Expansion).

## State of the Project
- Features dense, highly autonomous AI orchestration capabilities (Lyrics, Metdata, Art, Remix, Harmonized TTS Vocals, Video Muxing).
- Extensively containerized, thread-safe, native C++ audio playback, and OMR image reading.
- Fully documented and versioned aligned with the Omni-Workspace guidelines.

## Next Steps for the Next Agent
- **Roadmap Phase 5:** Start exploring the **Live DJ Radio Stream** architecture. Investigate spinning up an `icecast` server via Docker, configuring `ffmpeg` to continuously push the generated `.mp4` chunks to the HLS/RTMP endpoint to create a 24/7 internet radio station experience.
- Look into **Stem Separation Integration** using `spleeter`. By isolating the generated Deep House drums, the TTS vocals could be mixed to duck *only* the melodic stems, preventing the heavy house beat from dropping in volume during singing.
