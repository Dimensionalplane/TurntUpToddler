# TODO

This list tracks immediate, actionable tasks, bug fixes, and minor feature requests necessary to push the project toward its Roadmap Phase 6 goals.

## High Priority
- [ ] **Docker Alpine / Distroless Base:** The addition of `oemer` and its heavy ML dependencies (ONNX Runtime, OpenCV) significantly bloated the multi-stage Docker build. Investigate shrinking the final runtime stage container by using a minimal base image (like Alpine or Distroless) and pre-compiled OpenCV binaries, moving the heavy ML inference to an external microservice if necessary.

## Medium Priority
- [ ] **Multi-Voice Spatial Expansion:** The current Multi-Voice Harmonization algorithm linearly shifts pitch by `+4` and `+7` semitones. Research using `librosa` instead of `pydub`'s crude framerate-stretching to apply high-fidelity pitch-shifting (e.g. `pyrubberband`) without altering the audio speed, ensuring clearer, crisper harmonies.
- [ ] **Expanded Visualizer Options:** Currently, the FFmpeg filter uses `showwaves=mode=cline`. Expose more parameters to the Streamlit UI to allow the user to select between different modes (e.g., `p2p`, `line`, `cline`) or try `avectorscope` for Lissajous curves.

## Low Priority / Polish
- [ ] **UI Loading States:** Add Streamlit `st.spinner` or progress bars to the DALL-E, Demucs, and ElevenLabs API calls to improve user experience during long processing stages in the interactive UI wizard.
