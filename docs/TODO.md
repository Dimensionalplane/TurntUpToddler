# TODO

This list tracks immediate, actionable tasks, bug fixes, and minor feature requests necessary to push the project toward its roadmap goals.

## High Priority
- [ ] **Advanced Subtitle Parsing:** The current `MusicXMLParser` aggressively strips hyphens from extracted lyrics to create a flat string for OpenAI to consume. Implement a smarter parsing algorithm that preserves the original syllable breaks and leverages the actual `.mxl` note timings to output a valid `.srt` or `.ass` file with precise, note-by-note synchronization, entirely bypassing the need for GPT to guess subtitle timings.

## Medium Priority
- [ ] **Oemer Docker Optimization:** `oemer` relies on ONNX Runtime and OpenCV, significantly increasing the Docker image footprint. Investigate creating a highly optimized, trimmed base image (e.g., via `alpine` or `distroless`) for the runtime stage to reduce final container size.
- [ ] **Expanded Visualizer Options:** Currently, the FFmpeg filter uses `showwaves=mode=cline`. Expose more parameters to the Streamlit UI to allow the user to select between different modes (e.g., `p2p`, `line`, `cline`) or try `avectorscope` for Lissajous curves.

## Low Priority / Polish
- [ ] **Live Stream Status UI:** The `--stream-rtmp` flag currently operates in the background of the CLI `main.py` daemon. Create a dedicated module in `app.py`'s sidebar that displays the status of the RTMP stream, currently playing song, and allows the user to manually "Skip Track" on the broadcast thread.
