# IDEAS & Brainstorming

This document serves as a repository for future features, radical pivots, refactoring suggestions, and general brainstorms to continue evolving the Hymn Remaker Omni-Workspace.

## 1. Multi-Node Cluster Rendering (Architecture Pivot)
**Rationale:** Currently, the entire pipeline (OMR -> MIDI -> C++ Render -> AI Gen -> AI Stem Sep -> FFmpeg) runs on a single node (even with Docker and multithreading).
**Idea:** Decouple the pipeline into microservices using a message broker (RabbitMQ/Redis).
- Node A handles UI and queueing.
- Node B (GPU-heavy) handles Demucs stem separation and OMR.
- Node C handles C++ rendering and FFmpeg video encoding.
This allows massive horizontal scaling for a "Hymn Factory" capable of generating hundreds of tracks simultaneously.

## 2. WebRTC Live Studio (Feature)
**Rationale:** The `RadioStreamer` works perfectly for pushing to RTMP. However, for internal previewing, downloading a generated MP4 or clicking "Render Preview" is slow.
**Idea:** Implement WebRTC in the Streamlit UI to stream the native C++ `HymnPlayer` output directly to the browser with ultra-low latency, effectively creating a live "DJ Deck" in the browser where users can tweak settings and hear the changes instantly without rendering a file.

## 3. Specialized AI Stem Extraction (Improvement)
**Rationale:** `demucs` is fantastic but generalizes separation into `drums`, `bass`, `vocals`, `other`.
**Idea:** Since this is focused heavily on classical/hymn to deep house transformations, integrate a specialized model that can isolate `choir`, `organ`, `piano`, and `strings` to allow incredibly granular EQing and ducking in the final mix.

## 4. Hardware-Accelerated Video Encoders (Optimization)
**Rationale:** We added multithreading (`-threads 0`) and `-preset veryfast` for x264, but it still relies on CPU.
**Idea:** Dynamically detect the host system's GPU capabilities (`h264_nvenc` for NVIDIA, `h264_qsv` / `hevc_videotoolbox` for Apple Silicon) and inject the appropriate FFmpeg encoder flags to reduce rendering time by 500-1000%.

## 5. Direct Spotify / Apple Music Distribution (Pivot)
**Rationale:** We currently auto-publish to YouTube, TikTok, and Instagram.
**Idea:** Integrate a distributor API (like DistroKid or TuneCore) to auto-generate album releases and push the final, mastered audio directly to Spotify and Apple Music, treating the pipeline as an autonomous record label.

## 6. Real-time Lyrics Translation (Feature)
**Rationale:** We currently use `music21` to rip exact syllable timings from MusicXML.
**Idea:** Before generating TTS vocals, run the extracted lyrics through an LLM to translate them into 10 different languages, generate 10 vocal tracks, and output 10 separate videos, making the hymn universally accessible globally in a single click.
