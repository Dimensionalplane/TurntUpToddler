# TODO

This list tracks immediate, actionable tasks, bug fixes, and minor feature requests necessary to push the project toward its roadmap goals.

## High Priority
- [ ] **Docker Alpine / Distroless Base:** The addition of `oemer` and its dependencies (ONNX Runtime, OpenCV) significantly bloated the multi-stage Docker build. Investigate shrinking the final runtime stage container by using a minimal base image (like Alpine) and pre-compiled OpenCV binaries.

## Medium Priority
- [ ] **Live Stream Status UI:** The `--stream-rtmp` flag currently operates seamlessly in the background of the CLI `main.py` daemon. Create a dedicated module in `app.py`'s sidebar that displays the status of the RTMP stream, currently playing song, and allows the user to manually "Skip Track" on the broadcast thread using thread-safe events.

## Low Priority / Polish
- [ ] **Expanded Visualizer Options:** Currently, the FFmpeg filter uses `showwaves=mode=cline`. Expose more parameters to the Streamlit UI to allow the user to select between different modes (e.g., `p2p`, `line`, `cline`) or try `avectorscope` for Lissajous curves.
