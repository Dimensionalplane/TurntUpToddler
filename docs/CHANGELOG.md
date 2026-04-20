# Changelog

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog.

## [1.11.0] - Current
### Added
- **AI Stem Separation**: Integrated Facebook's `demucs` library (`src/stem_separator.py`) into the pipeline. After Replicate generates the Deep House instrumental, the system now autonomously isolates the `drums`, `bass`, `vocals`, and `other` (melody) tracks.
- **Smart Audio Ducking**: Rewrote `process_audio` in `src/utils.py` to utilize the new AI stems. When mixing the generated ElevenLabs vocal tracks, the system now exclusively "ducks" (lowers the volume of) the melodic (`other`) stems and slightly ducks the `bass` stem to create frequency room for the vocal. Crucially, the `drums` stem is left completely untouched at full volume, ensuring the driving dance beat retains its maximum impact without pumping or dropping out during singing.

## [1.10.0] - Previous
### Added
- **Multi-Voice Harmonization**: Upgraded the ElevenLabs TTS integration to generate 3-part or 4-part lush choral harmonies.
- **Dynamic Tempo Matching**: Updated `midi_renderer.py` to extract exact BPM and inject it into the Replicate style prompt.
- **Hymn Editor UI Toolbar**: Rebuilt `app.py` into a multi-tab Streamlit dashboard offering discrete manual utilities (Native Audio preview, MusicXML metadata extraction).
