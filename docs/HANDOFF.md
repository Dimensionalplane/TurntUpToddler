# Handoff Document

## Session Summary
- **Concurrency & UI Fixes**: Audited and fixed a severe threading bug in `MidiRenderer` where the single native C++ engine (`HymnPlayer`) was being accessed by multiple Streamlit threads simultaneously, causing segmentation faults. We also repaired the "Interactive Review Mode" UI bug where `st.rerun()` would drop the user's uploaded file queue. The multi-file processing queue is now safely stored in `st.session_state`.
- **Dependency Audit**: Unpinned `requirements.txt` dependencies. Previous attempts to rigidly pin versions caused cross-platform build failures due to environment-specific packages.
- **OMR Implementation**: Built `src/omr_processor.py` utilizing the `oemer` library. The pipeline (both the UI and the Watchdog daemon) now accepts raw physical sheet music scans (`.pdf`, `.jpg`, `.png`). It autonomously runs the image through an ONNX/OpenCV neural net, converts the page to a MusicXML file, and bridges it back into the existing parsing pipeline seamlessly.
- **Documentation Update**: Extensively updated `ROADMAP.md`, `TODO.md`, `CHANGELOG.md`, and bumped the global `VERSION` to **1.9.0**, marking the completion of the first major feature in Phase 4 (Creative Expansion, Live Features & OMR).

## State of the Project
- Extremely robust. The project now successfully ingests all formats (MIDI, MusicXML, PDF, PNG/JPG) entirely natively.
- The C++ audio engine is safely threaded per-call.
- The Streamlit interactive wizard is stable across multi-file processing queues.

## Next Steps for the Next Agent
- **Roadmap Phase 4:** The immediate next priority is **Multi-Voice Harmonization**. Investigate updating `hymn_remaker/src/tts_generator.py` to optionally accept a list of `voice_ids` (e.g., Soprano, Alto, Tenor). Generate separate audio tracks for each voice, pitch-shift the harmony tracks (using `pydub` or `librosa`), and pan them (left/right) before mixing them down into a single master vocal track.
- Implement **Dynamic Tempo Extraction** by extracting the BPM from the MIDI or MusicXML file and passing it directly into the Replicate MusicGen prompt.
- **Docker Optimization**: The addition of `oemer`, `onnxruntime`, and `opencv-python-headless` significantly increases the container footprint. Look into creating a more trimmed, multi-stage runtime build or a dedicated "lite" version of the Dockerfile.
