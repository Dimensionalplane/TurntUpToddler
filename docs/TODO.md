# TODO

This list tracks immediate, actionable tasks, bug fixes, and minor feature requests necessary to push the project toward its roadmap goals.

## High Priority
- [ ] **OMR Proof of Concept:** Research Python wrappers for Audiveris or similar Optical Music Recognition tools. The goal is to allow users to drop a `.pdf` sheet music file into the `input/` folder and have the daemon automatically convert it to MusicXML for processing.
- [ ] **Multi-Voice Harmonization Proof of Concept:** Update `tts_generator.py` to optionally accept a list of `voice_ids`. Generate separate audio tracks for each voice, pitch-shift them (e.g., using `librosa` or `pydub`) to create chords, and mix them before overlaying onto the instrumental.
- [ ] **Live DJ Radio Stream Research:** Investigate FFmpeg's `icecast` or HLS streaming capabilities. The goal is to pipe the output of `video_uploader.py` directly to a continuous RTMP/HLS stream endpoint.

## Medium Priority
- [ ] **Dynamic Time-Stretching Refinement:** Currently, `src/utils.py` uses a simple `atempo` stretch ratio for the entire vocal track. Investigate using forced alignment (like Whisper timestamps) to stretch individual words or phrases to fall perfectly on the downbeat.
- [ ] **Advanced Subtitle Parsing:** The current MusicXML parser aggressively strips hyphens from extracted lyrics. Implement a smarter parsing algorithm that preserves syllables and outputs a valid `.srt` or `.ass` file with precise note-by-note timing extracted from the `.mxl` file.

## Low Priority / Polish
- [ ] **UI Loading States:** Add Streamlit `st.spinner` or progress bars to the DALL-E and ElevenLabs API calls to improve user experience during long network requests.
