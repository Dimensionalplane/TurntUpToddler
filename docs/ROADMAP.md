# Comprehensive Roadmap

This document outlines the high-level trajectory of the Hymn Remaker project, moving from core automation to advanced analytical features and native performance optimizations.

## Phase 1: Core Automation Pipeline (Completed)
- [x] Basic MIDI to Audio rendering using Python wrappers (`midi2audio`).
- [x] Replicate MusicGen integration for stylistic Deep House transformation.
- [x] OpenAI integration for metadata, lyrics, and DALL-E cover art.
- [x] ElevenLabs TTS integration for generative vocals.
- [x] Audio mixing (ducking) and FFmpeg subtitle/video assembly.
- [x] Basic Streamlit web interface for monitoring.

## Phase 2: Robustness, Scale & Cost Optimization (Completed)
- [x] Daemon mode (`--daemon`) for continuous, automated directory watching.
- [x] Short-form video extraction (`--create-shorts`) for TikTok/Reels.
- [x] Local DALL-E image caching via MD5 hashing to reduce API overhead.
- [x] Idempotency flags (`--skip-render`, `--skip-remake`) for pipeline resumption.
- [x] FFmpeg subtitle burn retry and sanitization loops.
- [x] Seeding of the native C++ `HymnPlayer` engine.

## Phase 3: Advanced Input & Native Integration (Current Focus)
- [ ] **MusicXML Support:** Extend the input parser to accept MusicXML files, allowing for richer metadata (lyrics, dynamics, tempo changes) compared to standard MIDI files.
- [ ] **OMR (Optical Music Recognition):** Integrate libraries (e.g., Audiveris) to allow users to scan physical sheet music PDFs and convert them directly into MIDI/MusicXML for processing.
- [ ] **Native C++ Python Bindings:** Replace the `midi2audio` shell-wrapper dependency by bridging the `src/engine/HymnPlayer` C++ engine into Python using `pybind11` or `ctypes`. This will allow for granular, sample-accurate audio rendering and manipulation directly within the Python pipeline.
- [ ] **Advanced Lyric Timing:** Implement forced alignment tools (e.g., Montreal Forced Aligner or Whisper) to synchronize the ElevenLabs TTS audio with the generated beat with millisecond precision, creating flawless karaoke-style subtitle files (.ass/.vtt).

## Phase 4: Creative Expansion & Live Features
- [ ] **Live DJ Mode / Infinite Radio:** Build a continuously running web stream (e.g., Icecast/HLS) that dynamically queues and remixes hymns in real-time, functioning as a 24/7 Deep House internet radio station.
- [ ] **Multi-Voice Harmonization:** Utilize multiple ElevenLabs voice models simultaneously to generate choral or harmonized vocal tracks.
- [ ] **Dynamic Visualizers:** Replace static DALL-E cover art with dynamic, audio-reactive visualizers generated via FFmpeg or native OpenGL shaders.
