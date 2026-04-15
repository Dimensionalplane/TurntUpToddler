# System Memory & Context

*   **Project Context**: Part of the Robert Pelloni Omni-Workspace.
*   **Current Focus**: Polishing the pipeline by exposing advanced TTS settings and enforcing global version tracking.
*   **Observations**:
    *   The Streamlit UI uses concurrent threads. The `add_script_run_ctx` patch is critical and must not be removed.
    *   FFmpeg occasionally fails when burning subtitles if paths aren't escaped properly. The current fallback (run without subtitles) is necessary.
    *   The system relies on a local installation of FluidSynth and a SoundFont, which makes Docker the strongly preferred deployment method.
