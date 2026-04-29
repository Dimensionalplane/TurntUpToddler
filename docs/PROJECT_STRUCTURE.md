# Project Structure & Architecture Map

## Overview
The **Hymn Remaker** uses a decoupled, microservice-based architecture orchestrated by Docker Compose. The environment relies on native C++ rendering for audio alongside heavy Python ML libraries for generation.

## Directory Tree
```
/hymn_remaker
├── /docs                 # Exhaustive documentation (VISION, ROADMAP, IDEAS, HANDOFF)
├── /input                # Shared mounted volume for raw user input (.mid, .mxl, .pdf)
├── /output               # Shared mounted volume for final artifacts (.mp4)
├── /services             # Microservice daemon nodes
│   └── /renderer         # Headless worker daemon pulling from RabbitMQ
├── /src                  # Core business logic
│   └── /engine           # Native Pybind11 / C++ FluidSynth wrapper (HymnPlayer)
├── /tests                # Pytest suite
├── app.py                # Main Streamlit web gateway / UI
├── main.py               # Legacy / Alternative CLI entrypoint
├── docker-compose.yml    # 3-node orchestration map
├── Dockerfile            # Multi-stage Alpine container for Web/Renderer
├── Makefile              # C++ Pybind11 extension compilation commands
├── requirements.txt      # Global dependency map
└── VERSION               # Single source of truth for global versioning
```

## Core Submodules / Services
1. **Web Gateway (`app.py`)**
   - Streamlit interface for human-in-the-loop interaction and job configuration.
   - Pushes tasks to RabbitMQ.
   - Maintains WebRTC loop for low-latency live preview.
2. **RabbitMQ Broker**
   - Standard `rabbitmq:3-management` alpine container. Routes jobs between UI and Renderer.
3. **Renderer Worker (`services/renderer`)**
   - Headless consumer daemon.
   - Instantiates heavy ML models in memory to avoid spin-up latency on a per-job basis.

## Essential Libraries & Dependencies

### System Packages (Alpine)
- `fluidsynth` & `fluid-soundfont-gm`: Core C libraries for sample-accurate MIDI rendering.
- `ffmpeg`: Video encoding and audio-reactive visualization.
- `build-base`, `linux-headers`: Required for compiling the C++ `pybind11` extension.

### Python ML & Audio Stack (`requirements.txt`)
- `pybind11`: Bridges the native C++ `HymnPlayer` engine to Python.
- `mido` & `music21`: Parses MIDI timing, MusicXML syllables, and tempo maps.
- `oemer`: ONNX-backed Optical Music Recognition (Sheet Music -> XML).
- `demucs` (v4.0.1): High-fidelity AI stem separation.
- `pydub`, `librosa`, `soundfile`: Audio manipulation, spatial expansion, and phase-vocoder pitch shifting.
- `elevenlabs`: High-fidelity multi-voice Generative TTS.
- `replicate` / `openai`: API wrappers for MusicGen style transfer, DALL-E art, and GPT metadata generation.
- `streamlit-webrtc`: Bidirectional RTC streaming for the Live Studio feature.
- `pika` (v1.3.2): RabbitMQ message brokering client.
