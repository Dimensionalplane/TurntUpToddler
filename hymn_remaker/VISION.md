# Hymn Remaker Vision
**Goal:** Build the ultimate automated pipeline for converting public-domain MIDI files into modern, YouTube-ready music videos with AI-generated audio remakes, synced subtitles, and professional synthesized vocals.

**Core Principles:**
- **Frictionless:** Zero manual configuration required to generate an asset.
- **Robustness:** Fallbacks for every dependency (FFmpeg errors, Replicate rate limits, OpenAI outages).
- **Scalable:** Orchestrated via Kubernetes and RabbitMQ, allowing for infinite horizontal scaling of render workers.
- **Human-in-the-Loop:** Interactive review checkpoints for high-precision metadata and lyric curation.

**Intended Workflow:**
Upload `.mid` / `.mxl` / Sheet Music -> Select Style & Features -> Interactive Review (Optional) -> Distributed Render Worker -> S3 Storage -> YouTube / Radio Stream.
