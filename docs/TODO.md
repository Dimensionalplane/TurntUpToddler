# TODO

This list tracks immediate, actionable tasks, bug fixes, and minor feature requests necessary to push the project toward its roadmap goals.

## High Priority
- [ ] **Pybind11 Integration:** Create a `pybind11` wrapper for the `HymnPlayer` C++ class. Ensure the Python orchestrator can instantiate the player, load a MIDI, and extract the rendered audio buffer directly into a `numpy` array or `pydub.AudioSegment`.
- [ ] **Dependency Audit:** Verify all Python dependencies in `requirements.txt` have explicit versions pinned to prevent upstream breaking changes.
- [ ] **Streamlit UI Expansion:** Expose the FFmpeg subtitle styling options (font size, color, background box) to the Streamlit UI. Currently, they are hardcoded in `video_uploader.py`.

## Medium Priority
- [ ] **MusicXML Parser:** Research and implement a Python parser (e.g., `music21`) to extract tempo, key signature, and existing lyrics from `.mxl` files before falling back to ChatGPT generation.
- [ ] **TTS Alignment Smoothing:** Sometimes the ElevenLabs TTS audio is slightly longer or shorter than the instrumental track. Implement a dynamic time-stretching function using `pydub` (or `librosa`) to slightly speed up or slow down the vocals to match the exact duration of the instrumental.
- [ ] **Centralized Config File:** Move all hardcoded fallback paths (like `/usr/share/sounds/sf2/FluidR3_GM.sf2` and `.cache/art/`) into a central `config.yaml` or `settings.py` file.

## Low Priority / Polish
- [ ] **Docker Optimization:** Multi-stage Dockerfile build to compile the C++ engine in a build container, resulting in a smaller final runtime image.
- [ ] **UI Loading States:** Add Streamlit `st.spinner` or progress bars to the DALL-E and ElevenLabs API calls to improve user experience during long network requests.
