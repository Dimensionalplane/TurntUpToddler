# TODO

## High Priority

- [x] Implement robust documentation structure across `docs/`.
- [x] Modify `hymn_remaker/app.py` to display the global version number in the sidebar.
- [x] Modify `hymn_remaker/app.py` to allow user selection of ElevenLabs Voice ID and Model.
- [x] Update `process_single_midi` in `main.py` to accept and pass the Voice ID and Model parameters.

## Medium Priority

- [x] Improve error handling and retry logic around FFmpeg subtitle burning.
- [x] Add caching for DALL-E 3 image generation so re-running the same pipeline doesn't burn credits.
- [x] Add a progress bar specifically for the YouTube upload chunking process.

## Low Priority / Polish

- [x] Clean up temporary files more aggressively if a pipeline step fails mid-way.
- [x] Add unit tests specifically mocking the ElevenLabs API responses.
This list tracks immediate, actionable tasks, bug fixes, and minor feature requests necessary to push the project toward its Roadmap Phase 6 goals.

## High Priority

- [x] **Docker Alpine / Distroless Base:** The addition of `oemer` and its heavy ML dependencies (ONNX Runtime, OpenCV) significantly bloated the multi-stage Docker build. Investigate shrinking the final runtime stage container by using a minimal base image (like Alpine or Distroless) and pre-compiled OpenCV binaries, moving the heavy ML inference to an external microservice if necessary.

## Medium Priority

- [x] **Multi-Voice Spatial Expansion:** The current Multi-Voice Harmonization algorithm linearly shifts pitch by `+4` and `+7` semitones. Research using `librosa` instead of `pydub`'s crude framerate-stretching to apply high-fidelity pitch-shifting (e.g. `pyrubberband`) without altering the audio speed, ensuring clearer, crisper harmonies.

## Low Priority / Polish

- [x] **UI Loading States:** Add Streamlit `st.spinner` or progress bars to the DALL-E, Demucs, and ElevenLabs API calls to improve user experience during long processing stages in the interactive UI wizard.

## Future Exploration

- [x] Port `app.py` UI to a Next.js frontend with FastAPI backend.
- [x] Implement Metadata Extraction and Cluster Rendering APIs in the Next.js editor.

---

## Kids Mode: Turntable Toddler

- [ ] **Rewrite classic nursery rhymes with modern DJ/producer lyrics** — modify the most popular children's songs to teach kids about DJing, music production, and AI tools.
  - E.g. "The turntable goes wigga-wigga-wig" vibes — crossfaders, beat matching, samples, looping.
  - Target audience: preschool/early elementary, fun + educational.
- [ ] Decide: Suno-generated vocals or TTS + human-written lyrics?
- [ ] Create a curriculum/ladder: basic (parts of a turntable) → advanced (beat grids, FX chains, AI stem separation).
- [ ] Generate audio tracks via Suno cover pipeline (melody-preserving Remix→Cover flow).
