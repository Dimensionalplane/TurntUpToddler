# Hymn Remaker Vision
**Goal:** Build the ultimate automated pipeline for converting public-domain MIDI files into modern, YouTube-ready music videos with AI-generated audio remakes, synced subtitles, and professional synthesized vocals.

**Core Principles:**
- **Frictionless:** Zero manual configuration required to generate an asset.
- **Robustness:** Fallbacks for every dependency (FFmpeg errors, Replicate rate limits, OpenAI outages).
- **Scalable:** Process huge numbers of files in parallel via ThreadPoolExecutors.

**Intended Workflow:**
Upload `.mid` files -> Configure preset styling -> Output High-Quality 4K video mixed with 0dBFS normalized audio, auto-subbed lyrics, and singing/spoken word generation from ElevenLabs.
