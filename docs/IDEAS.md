# CREATIVE IDEAS - HYMN REMAKER

## PIVOTS & EXPANSIONS
1. **AI Choir Generator:** Beyond solo TTS, use Multi-speaker models to generate full choral harmonies based on SATB MIDI tracks.
2. **Interactive VR/AR Church:** Stream the generated audio/video into a VR environment where users can "attend" a virtual service.
3. **Mobile App:** A lightweight "Hymn-in-your-pocket" app for generating personalized calming music on the go.
4. **Interactive Radio DJ:** Use an LLM to generate "DJ banter" between tracks in the radio streamer, introducing the next song with generated metadata.

## RE-ARCHITECTING
- **Rust Port:** Rewrite the `midi_renderer` in Rust for even better performance and safety.
- **Serverless Workers:** Move render workers to AWS Lambda (using EFS for scratch space) for true pay-as-you-go scaling.
- **WebGPU Visualizers:** Offload audio-reactive visualizers to the client's browser using WebGPU for real-time interactivity.

## AGGRESSIVE REFACTORING
- **Standardized Plugin System:** Allow developers to write "Style Plugins" that encapsulate specific Prompt/Video/Audio parameters.
- **On-Device ML:** Attempt to run smaller MusicGen variants (small/melody) directly in the browser via ONNX Runtime Web.
