# Vision

Hymn Remaker is an automated pipeline that converts local MIDI files into Deep House music videos. It combines FluidSynth rendering, Replicate's MusicGen for remixing, OpenAI for metadata and lyric generation, ElevenLabs for TTS vocal tracking, and FFmpeg for video synthesis. The ultimate goal is a fully robust, "1-click" pipeline capable of autonomously generating endless high-quality modern remixes of classic hymns with dynamic lyric videos.

## Core Features
- Full autonomous processing via Daemon Mode (`--daemon`).
- Intelligent TTS synchronization.
- Automatic shorts generation (`--create-shorts`).
- DALL-E image caching for cost-efficiency.
- Extensible C++ audio engine (`HymnPlayer`) for fast native playback.
