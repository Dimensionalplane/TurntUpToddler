# MEMORY - HYMN REMAKER

## ARCHITECTURAL OBSERVATIONS
- **3-Stage Builds:** Essential for managing the 10GB+ ML footprint. Site-packages must be copied carefully to avoid overwriting during pip installs.
- **FFmpeg Bottlenecks:** Rendering is the slowest step. GPU-accelerated FFmpeg (NVENC) should be prioritized in K8s node selectors.
- **Interactive Review:** The blocking polling pattern in `worker.py` is robust but requires reliable Redis connectivity. Jobs should have a timeout to prevent permanent worker stalls.
- **Distributed Microservices:** Transition from Streamlit to FastAPI/Next.js and RabbitMQ/Redis task clustering has significantly improved scalability and reliability.
- **Kubernetes Orchestration:** Deploying via Kustomize manifests allows for granular control over resources and volume mounts (sharing `input`/`output` between API and workers).

## DESIGN PREFERENCES
- **Decoupled API:** The move from Streamlit to FastAPI/Next.js was critical for scalability.
- **Dynamic Backgrounds:** Video backgrounds (via Sora/Runway) are significantly more engaging than static DALL-E images. Looping logic via `-stream_loop -1` is the preferred implementation.
- **Kids Mode:** Styling should favor high-contrast vector art and clear, large subtitles.
- **Polymorphic Asset Handling:** `VideoProducer` automatically detects asset types (image vs video) and applies the correct FFmpeg filters.

## DISCOVERED OPTIMIZATIONS
- **Tempo Drift:** Enforcing BPM in AI prompts (Suno/MusicGen) is necessary to keep generated audio in sync with original MIDI timings.
- **Subtitles:** ASS/SRT burning is more flexible than hardcoded overlays. Unicode NFKD normalization ensures accented characters are preserved as ASCII equivalents.
- **Background Handling:** `VideoProducer` now handles polymorphic background assets. Extension-based detection is used to switch between `-loop 1` (images) and `-stream_loop -1` (videos).
- **AI Video Caching:** Redis-based caching of AI video URLs significantly reduces API costs and improves response times for repeated prompts.
- **RTMP Streaming:** Specific FLV flags (`-flvflags no_duration_filesize`) are required for stable streaming to YouTube Live.
