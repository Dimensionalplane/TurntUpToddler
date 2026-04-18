# Roadmap

## Phase 1: Core Automation (Completed)
- [x] Basic MIDI to Audio rendering.
- [x] Replicate MusicGen integration.
- [x] ElevenLabs TTS integration.
- [x] FFmpeg subtitle and video generation.

## Phase 2: Robustness & Scale (Completed)
- [x] Daemon mode (`--daemon`).
- [x] Short-form video extraction (`--create-shorts`).
- [x] DALL-E image caching.
- [x] Idempotency (skip flags).
- [x] C++ `HymnPlayer` scaffolding and tests.

## Phase 3: Advanced Input & Analysis (Next)
- [ ] MusicXML / OMR (Optical Music Recognition) support.
- [ ] Advanced lyric timing analysis.
- [ ] Integration of the C++ `HymnPlayer` engine into the Python orchestrator via pybind11 or ctypes.
- [ ] Full UI representation for all CLI parameters.
