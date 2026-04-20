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

## Phase 3: Advanced Input, Interactivity & Native Integration (Completed)
- [x] **MusicXML Support:** Extend the input parser to accept MusicXML files (`.mxl` / `.xml`), extracting richer metadata (lyrics, titles) compared to standard MIDI files.
- [x] **Native C++ Python Bindings:** Replace the `midi2audio` shell-wrapper dependency by bridging the `src/engine/HymnPlayer` C++ engine into Python using `pybind11`.
- [x] **TTS Alignment Smoothing:** Implemented FFmpeg `atempo` time-stretching to synchronize the ElevenLabs TTS audio duration with the generated instrumental beat.
- [x] **Interactive UI Review Mode:** Implemented a mid-pipeline Streamlit pause, allowing users to manually edit generated metadata, lyrics, and DALL-E prompts before final rendering.
- [x] **Hymn Editor UI:** Provide a fully functional manual sandbox tab for raw file operations, `.txt` lyrics extraction, and real-time native audio previewing.

## Phase 4: Creative Expansion & OMR (Completed)
- [x] **OMR (Optical Music Recognition):** Integrated `oemer` to allow users to scan physical sheet music PDFs and PNGs, automatically converting them into MusicXML files for downstream processing.
- [x] **Multi-Voice Harmonization:** Utilize multiple ElevenLabs voice models simultaneously. Pitch-shift parallel vocal tracks to create 3-part or 4-part harmonies, mixing them before overlaying onto the instrumental.
- [x] **Dynamic Tempo Matching:** Analyze the BPM of the original MIDI file using `mido` or `librosa`, and feed that precise BPM into the Replicate MusicGen prompt to ensure output remixes strictly adhere to the source tempo.

## Phase 5: Distribution, Visuals & Infinite Streaming (Current Focus)
- [x] **Stem Separation:** Utilize an AI stem separator (`demucs`) post-MusicGen to isolate the drum and bass tracks. This allows the TTS vocals to precisely duck *only* the melodic instruments without reducing the energy of the driving house beat.
- [x] **Dynamic Visualizers:** Replace static DALL-E cover art with dynamic, audio-reactive visualizers generated via FFmpeg complex filters (`showwaves`).
- [x] **Live DJ Mode / Infinite Radio:** Build a continuously running background thread that dynamically queues, shuffles, and streams the `.mp4` video output folder to a live RTMP endpoint (e.g., YouTube Live) operating as a 24/7 internet radio station.
- [ ] **Advanced Subtitle Parsing:** Move away from forcing GPT to guess subtitle timings by extracting the exact, note-by-note synchronization arrays natively from `.mxl` files.
