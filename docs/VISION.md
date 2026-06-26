# Project Vision: Hymn Remaker

The ultimate goal of the Hymn Remaker Pipeline is to seamlessly automate the conversion of public-domain classical and religious MIDI files into high-quality, modern, stylized music videos (e.g., Deep House, Synthwave) suitable for algorithmic distribution on platforms like YouTube and TikTok.

## Core Foundational Ideas:
1.  **Fully Automated Pipeline**: The process from `input.mid` to `output.mp4` on YouTube must require zero human intervention once initiated.
2.  **State-of-the-art AI Integration**: Leverage the latest generative AI (GPT-4 for lyrics and metadata, DALL-E 3 for art, ElevenLabs for vocal synthesis, MusicGen for audio styling) to produce highly polished, commercial-quality content.
3.  **Modular and Extensible**: Each step (Rendering, Remaking, Content Generation, TTS, Video Production) must be loosely coupled so that new models or APIs can be hot-swapped as technology advances.
4.  **Omni-Workspace Compatibility**: The project is a core piece of the larger robertpelloni ecosystem. It must adhere strictly to global versioning and cross-repo intelligence sharing via standard LLM instructions and scripts.
5.  **User Delight**: The Streamlit interface must provide a magical, one-click experience while simultaneously offering granular "power user" controls (voice models, ducking, normalization) for audio engineers.
# Vision

## Project Overview
Hymn Remaker is a highly automated, end-to-end pipeline designed to transform traditional, local MIDI hymn files, MusicXML sheets, and raw physical sheet music (via OMR) into modern, high-fidelity Deep House music videos. It seamlessly blends classical compositions with contemporary electronic music production techniques, leveraging state-of-the-art AI to automate the entire creative process from audio synthesis to video assembly, and ultimately broadcasting to a 24/7 internet radio stream.

## Ultimate Goal
The ultimate goal of Hymn Remaker is to provide a "1-click", fully robust, and infinitely scalable content creation factory. It autonomously generates endless, high-quality, modern remixes of classic hymns accompanied by dynamic, visually stunning, audio-reactive lyric videos, suitable for seamless distribution across platforms like YouTube, TikTok, and Instagram Reels. The system operates with zero human intervention in Daemon mode, handling errors gracefully while optimizing for cost (API caching) and performance.

## Core Design Philosophy
- **Autonomy & Momentum:** The system runs continuously via Daemon Mode (`--daemon`) or a dedicated Live Stream broadcaster (`--stream-rtmp`), eagerly processing new inputs without manual triggers. Errors must be caught, logged, and bypassed to keep the pipeline moving ("Don't stop the party").
- **Cost Efficiency & Idempotency:** Utilizing external APIs (OpenAI, Replicate, ElevenLabs) requires strict caching mechanisms (DALL-E MD5 hash caches) and idempotency flags (`--skip-render`, `--skip-remake`) to ensure failed pipelines can resume without incurring redundant API costs.
- **Modularity & Extensibility:** The architecture is decoupled into distinct stages: OMR scanning, MusicXML extraction, C++ audio synthesis, AI remixing, stem separation, multi-voice TTS generation, audio mixing, and video rendering. This allows individual components to be swapped or upgraded independently.
- **Comprehensive Observability & Interactivity:** Every feature, setting, and error state is heavily documented and comprehensively represented in the Streamlit UI, providing users with absolute control and transparency. The "Interactive Review Mode" and the "Hymn Editor Toolbar" provide explicit interfaces for humans to augment AI-generated lyrics, extract precise timing metadata, and render C++ audio previews without disrupting the daemon flow.

## Technological Pillars
1. **Raw Input Translation (Oemer & Music21):** Users can supply `.mid`, `.mxl`, or raw `.pdf`/`.png` sheet music scans. The pipeline autonomously runs Optical Music Recognition (OMR) using the ONNX-backed `oemer` library to translate physical sheets into MusicXML, parsing it via `music21` for exact syllable timing metadata before converting it to MIDI for the audio engine.
2. **Audio Synthesis (FluidSynth & Native C++):** Fast, sample-accurate offline rendering of MIDI data. The pipeline leverages a robust, thread-safe Pybind11 wrapper (`HymnPlayer`) around the FluidSynth C API for native Python orchestration.
3. **AI Audio Transformation (Replicate/MusicGen):** Intelligently converting raw, synthetic MIDI renders into stylistically appropriate Deep House tracks, enforcing global tempos (`mido`) to prevent AI drifting.
4. **AI Stem Separation (Demucs):** Splitting the generated Replicate track into `drums`, `bass`, `vocals`, and `other` (melody) to enable granular frequency ducking in the master mix.
5. **Generative Voice (ElevenLabs TTS):** Producing human-like, emotive vocal tracks. High-fidelity pitch-shifted multi-voice spatial harmonies (via `librosa` and `pyrubberband` algorithm) and precise FFmpeg `atempo` time-stretching guarantee perfect beat alignment and crisp vocal presence.
6. **Generative Art & Metadata (OpenAI GPT-4 & DALL-E 3):** Crafting unique visual identities, titles, descriptions, and SEO tags for every generated video.
7. **Video Assembly & Streaming (FFmpeg):** Programmatically composing stems, vocals, audio-reactive `showwaves` visualizers, and exact karaoke-style subtitles into final MP4 artifacts, supporting both 16:9 and 9:16 aspect ratios. It then streams these directly to RTMP servers.