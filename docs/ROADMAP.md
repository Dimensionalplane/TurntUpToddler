# Hymn Remaker Roadmap

## Phase 1: Core Functionality (Completed)
- [x] Basic MIDI to WAV rendering using FluidSynth.
- [x] Integration with Replicate's MusicGen for style-conditioned audio generation.
- [x] Integration with OpenAI for video metadata, dynamic lyrics generation, and DALL-E 3 album art.
- [x] Basic video assembly with FFmpeg.
- [x] Built-in Streamlit Web UI.

## Phase 2: Polish & Completeness (In Progress)
- [x] ElevenLabs TTS Vocal generation and audio mixing.
- [x] Robust YouTube uploading via OAuth.
- [x] Dynamic generation of synchronized subtitles (SRT) burned into the video.
- [x] Exposing deep TTS parameters (voice_id, model selection) to the frontend CLI and UI.
- [x] Implement global, file-based version tracking referencing the omni-workspace `VERSION` file.

## Phase 3: Scaling & Platform Expansion
- [ ] Support for multiple input formats beyond MIDI (MusicXML, sheet music PDFs via OMR).
- [x] TikTok/Instagram Reels native vertical video formatting.
- [x] Automated short-form clip extraction from the main video.
- [ ] Integration with advanced video generation AI (e.g., Runway Gen-2, Sora) to replace static DALL-E album art with dynamic, reactive music videos.

## Phase 4: Autonomy
- [x] "Always-on" daemon mode that monitors an inbox, generates content overnight, and schedules uploads without user invocation.
# Comprehensive Roadmap

This document outlines the high-level trajectory of the Hymn Remaker project, tracking its evolution from a basic Python wrapper pipeline into a high-performance native C++ Audio/Visual/AI broadcasting engine.

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
- [x] **Multi-Voice Spatial Expansion:** Utilize multiple ElevenLabs voice models simultaneously. Use high-fidelity pitch-shifting (`pyrubberband`) on parallel vocal tracks (e.g., +4 and +7 semitones) to create clear, 3-part or 4-part lush choral harmonies without altering audio speed, mixing them before overlaying onto the instrumental.
- [x] **Dynamic Tempo Matching:** Analyze the BPM of the original MIDI/MXL file natively using `mido`, feeding that precise integer directly into the Replicate MusicGen prompt to ensure output remixes strictly adhere to the source tempo.

## Phase 5: Distribution, Visuals & Infinite Streaming (Completed)
- [x] **Stem Separation:** Utilize an AI stem separator (`demucs`) post-MusicGen to isolate the drum and bass tracks. This allows the TTS vocals to precisely duck *only* the melodic instruments (`other`, `bass`) without reducing the energy of the driving house `drums` beat.
- [x] **Dynamic Visualizers:** Replace static DALL-E cover art with dynamic, audio-reactive visualizers generated via FFmpeg complex filters. Options include `showwaves` (`cline`, `line`, `p2p`) and `avectorscope` Lissajous curves.
- [x] **Live DJ Mode / Infinite Radio:** Build a continuously running background thread (`src/radio_streamer.py`) that dynamically queues, shuffles, and streams the `.mp4` video output folder to a live RTMP endpoint (e.g., YouTube Live) operating as a 24/7 internet radio station.
- [x] **Advanced Subtitle Parsing:** Extract the exact, note-by-note synchronization arrays natively from `.mxl` files (via `music21`), concatenating syllables (`begin`, `middle`, `end`) and timing durations to completely bypass GPT timing hallucinations, mapping exact `.srt` files directly to the sheet music.

## Phase 6: Cloud Native Polish & App Ecosystem (Current Focus)
- [x] **Interactive Radio Controls:** Expose the `RadioStreamer` background thread to the Streamlit UI's sidebar, allowing users to start broadcasts, view the current playing song, and manually "Skip Track" or "Kill Stream" via robust Python `Event` flags.
- [ ] **Distroless/Alpine Docker Image:** The massive dependencies of PyTorch (`demucs`), OpenCV, and ONNX Runtime (`oemer`) bloat the `hymn_remaker:latest` container. A multi-stage Docker build separating the AI inference models from the Streamlit UI web container will drastically cut deployment size.