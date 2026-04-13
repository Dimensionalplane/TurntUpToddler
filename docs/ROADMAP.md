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
- [ ] Automated short-form clip extraction from the main video.
- [ ] Integration with advanced video generation AI (e.g., Runway Gen-2, Sora) to replace static DALL-E album art with dynamic, reactive music videos.

## Phase 4: Autonomy
- [x] "Always-on" daemon mode that monitors an inbox, generates content overnight, and schedules uploads without user invocation.
