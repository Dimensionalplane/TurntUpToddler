# TODO

This list tracks immediate, actionable tasks, bug fixes, and minor feature requests necessary to push the project toward its roadmap goals.

## High Priority
- [ ] **Live DJ Radio Stream Research:** Investigate FFmpeg's `icecast` or HLS streaming capabilities. The goal is to pipe the output of `video_uploader.py` directly to a continuous RTMP/HLS stream endpoint for a 24/7 internet radio station feature.

## Medium Priority
- [ ] **Advanced Subtitle Parsing:** The current `MusicXMLParser` aggressively strips hyphens from extracted lyrics. Implement a smarter parsing algorithm that preserves syllables and leverages the actual note timings in the `.mxl` file to output a valid `.srt` or `.ass` file with precise, note-by-note synchronization, bypassing the need for GPT to guess timings.
- [ ] **Oemer Docker Optimization:** `oemer` relies on ONNX Runtime and OpenCV, significantly increasing the Docker image footprint. Investigate creating a highly optimized, trimmed base image (e.g., via `alpine` or `distroless`) for the runtime stage to reduce final container size.

## Low Priority / Polish
- [ ] **Audio-Reactive Visualizer:** Research FFmpeg's `avectorscope` or `showwaves` filters. Add a Streamlit toggle to overlay a waveform visualizer on top of the DALL-E generated album art.
- [ ] **UI Loading States:** Add Streamlit `st.spinner` or progress bars to the DALL-E, Demucs, and ElevenLabs API calls to improve user experience during long processing stages in the interactive UI wizard.
