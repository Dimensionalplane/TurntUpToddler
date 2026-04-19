# TODO

This list tracks immediate, actionable tasks, bug fixes, and minor feature requests necessary to push the project toward its roadmap goals.

## High Priority
- [ ] **Multi-Voice Harmonization Function:** Update `hymn_remaker/src/tts_generator.py` to optionally accept a list of `voice_ids` (e.g., Soprano, Alto, Tenor). Generate separate audio tracks for each voice, pitch-shift the harmony tracks (using `pydub` or `librosa`), and pan them (left/right) before mixing them down into a single master vocal track.
- [ ] **Dynamic Tempo Extraction:** In `hymn_remaker/src/musicxml_parser.py` and `midi_renderer.py`, extract the global BPM/Tempo from the `.mid` or `.mxl` file using `mido`. Pass this exact BPM string into the `MusicRemaker` (Replicate) prompt (e.g., `"... at exactly 120 BPM"`) to prevent the AI from generating mismatched tempos.

## Medium Priority
- [ ] **Advanced Subtitle Parsing:** The current `MusicXMLParser` aggressively strips hyphens from extracted lyrics. Implement a smarter parsing algorithm that preserves syllables and leverages the actual note timings in the `.mxl` file to output a valid `.srt` or `.ass` file with precise, note-by-note synchronization, bypassing the need for GPT to guess timings.
- [ ] **Live DJ Radio Stream Research:** Investigate FFmpeg's `icecast` or HLS streaming capabilities. The goal is to pipe the output of `video_uploader.py` directly to a continuous RTMP/HLS stream endpoint for a 24/7 internet radio station feature.
- [ ] **Oemer Docker Optimization:** `oemer` relies on ONNX Runtime and OpenCV, significantly increasing the Docker image footprint. Investigate creating a highly optimized, trimmed base image (e.g., via `alpine` or `distroless`) for the runtime stage to reduce final container size.

## Low Priority / Polish
- [ ] **Audio-Reactive Visualizer:** Research FFmpeg's `avectorscope` or `showwaves` filters. Add a Streamlit toggle to overlay a waveform visualizer on top of the DALL-E generated album art.
- [ ] **UI Loading States:** Add Streamlit `st.spinner` or progress bars to the DALL-E and ElevenLabs API calls to improve user experience during long network requests in the interactive UI wizard.
