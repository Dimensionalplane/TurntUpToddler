# Handoff Document

**Date:** 2024-04-10
**Version:** 1.7.1
**Session Summary & Architecture Analysis:**

During this extensive session, the AI autonomously analyzed the project architecture, mapped out missing/incomplete features from the roadmap, and established a comprehensive suite of Omni-Workspace documentation (`VISION.md`, `ROADMAP.md`, `CHANGELOG.md`, etc.). The project version is now globally tracked via a central `VERSION` file, which is dynamically parsed and displayed by the Streamlit UI.

The following major architectural enhancements were successfully implemented and wired through both the CLI (`main.py`) and Web UI (`app.py`):
1. **Automated Short-form Clip Extraction:** Utilizing FFmpeg's segment muxer to automatically split the final rendered video into engaging 15-second clips for social media distribution.
2. **Daemon Mode (`--daemon`):** Integration of the `watchdog` library to allow continuous, "always-on" monitoring of the input directory for new MIDI files.
3. **Vertical Video Support:** Native 9:16 aspect ratio formatting using advanced FFmpeg scale and pad filter complex logic, catering directly to TikTok/Instagram Reels.
4. **DALL-E 3 Local Caching:** Implemented MD5 hashing on prompts to save generated album art locally (`.cache/art/`), saving redundant API calls and credits on pipeline re-runs.
5. **ElevenLabs Deep Parameter Exposure:** The underlying `voice_id` and `model` arguments for TTS generation are now configurable by the user instead of hardcoded defaults.
6. **Robust Failure Handling:**
   - **FFmpeg Subtitle Retries:** If FFmpeg fails to burn SRTs due to weird lyric encodings, the pipeline catches the error, sanitizes the text (ASCII-only), and retries, eventually falling back to no-subtitles if needed.
   - **Aggressive Cleanup:** A `try-except` block in the main orchestrator ensures that mid-flight crashes clean up partially rendered WAVs/MP4s to prevent disk bloat.

**Next Steps (Phase 3+):**
- The pipeline is incredibly robust. Future models should focus on input expansion: specifically adding support for MusicXML or Optical Music Recognition (OMR) to convert sheet music PDFs directly into the pipeline.
