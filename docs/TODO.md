# TODO

This list tracks immediate, actionable tasks, bug fixes, and minor feature requests necessary to push the project toward its Roadmap Phase 8 goals.

## High Priority
- [x] **Full Render Worker Refactor:** Move the heavy machine learning inference (`demucs`, `oemer`, ElevenLabs TTS, MusicGen, FFmpeg video generation) fully into the `services/renderer.py` pipeline. The `hymn_remaker` Streamlit node should act purely as a fast, lightweight UI/API gateway, publishing structured JSON jobs to RabbitMQ.
