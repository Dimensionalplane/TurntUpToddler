# Vision

## Project Overview
Hymn Remaker is a highly automated, end-to-end pipeline designed to transform traditional, local MIDI hymn files, MusicXML sheets, and raw physical sheet music (via OMR) into modern, high-fidelity Deep House music videos. It seamlessly blends classical compositions with contemporary electronic music production techniques, leveraging state-of-the-art AI to automate the entire creative process from audio synthesis to video assembly.

## Ultimate Goal
The ultimate goal of Hymn Remaker is to provide a "1-click", fully robust, and infinitely scalable content creation factory. It aims to autonomously generate endless, high-quality, modern remixes of classic hymns accompanied by dynamic, visually stunning lyric videos, suitable for seamless distribution across platforms like YouTube, TikTok, and Instagram Reels. The system must operate with zero human intervention once configured, handling errors gracefully and optimizing for cost (e.g., API caching) and performance.

## Core Design Philosophy
- **Autonomy & Momentum:** The system should run continuously (e.g., via Daemon Mode), eagerly processing new inputs without manual triggers. Errors must be caught, logged, and bypassed to keep the pipeline moving ("Don't stop the party").
- **Cost Efficiency & Idempotency:** Utilizing external APIs (OpenAI, Replicate, ElevenLabs) requires strict caching mechanisms (like the DALL-E MD5 hash cache) and idempotency flags (`--skip-render`, `--skip-remake`) to ensure failed pipelines can resume without incurring redundant API costs.
- **Modularity & Extensibility:** The architecture is decoupled into distinct stages: synthesis, AI remixing, TTS generation, audio mixing, and video rendering. This allows individual components to be swapped or upgraded independently (e.g., migrating from shell wrappers to native C++ engine pybindings).
- **Comprehensive Observability & Interactivity:** Every feature, setting, and error state must be heavily documented and comprehensively represented in the Streamlit UI, providing users with absolute control and transparency over the pipeline. The "Interactive Review Mode" provides an explicit mid-point for humans to augment AI-generated lyrics and prompts without disrupting the daemon flow.

## Technological Pillars
1. **Raw Input Translation (Oemer & Music21):** Users can supply MIDI files, MusicXML files, or scanned images of physical sheet music. The pipeline autonomously runs Optical Music Recognition (OMR) to translate physical sheet music into MusicXML, parsing it for raw data before converting it to MIDI for the audio engine.
2. **Audio Synthesis (FluidSynth & Native C++):** Fast, accurate rendering of MIDI data using SoundFonts. The pipeline leverages a robust, thread-safe Pybind11 wrapper (`HymnPlayer`) around the FluidSynth C API.
3. **AI Audio Transformation (Replicate/MusicGen):** Intelligently converting raw, synthetic MIDI renders into stylistically appropriate Deep House tracks.
4. **Generative Voice (ElevenLabs TTS):** Producing human-like, emotive vocal tracks from dynamically generated lyrics.
5. **Generative Art & Metadata (OpenAI GPT-4 & DALL-E 3):** Crafting unique visual identities, titles, descriptions, and SEO tags for every generated video.
6. **Video & Subtitle Assembly (FFmpeg):** Programmatically composing audio tracks, cover art, and hardcoded subtitles into final video artifacts, supporting both 16:9 and 9:16 (Shorts) aspect ratios with full subtitle styling exposure.
7. **User Interface (Streamlit):** A robust, interactive web dashboard for real-time monitoring, configuration, and manual overrides.
