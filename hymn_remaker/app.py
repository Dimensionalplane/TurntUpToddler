import streamlit as st
import os
import sys
import glob
import concurrent.futures
from hymn_remaker import settings

# Load global version
VERSION = "Unknown"
try:
    # Try reading from root VERSION file or docs/VERSION.md
    import os
    version_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION")
    if os.path.exists(version_path):
        with open(version_path, "r") as vf:
            VERSION = vf.read().strip()
    else:
        version_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "VERSION.md")
        if os.path.exists(version_path):
             with open(version_path, "r") as vf:
                 VERSION = vf.read().strip()
except Exception:
    pass

st.sidebar.markdown(f"**Version: {VERSION}**")
st.sidebar.markdown("---")


# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.midi_renderer import MidiRenderer
from src.remaker import MusicRemaker
from src.content_generator import ContentGenerator
from src.video_uploader import VideoProducer
from src.tts_generator import TTSGenerator
from main import process_single_midi

st.set_page_config(page_title="Hymn Remaker UI", page_icon="🎵", layout="wide")

st.title("🎵 Hymn Remaker Pipeline")
st.write("Convert MIDI files into modern music videos with AI!")

# Initialize objects
@st.cache_resource
def load_modules():
    try:
        return (
            MidiRenderer(),
            MusicRemaker(),
            ContentGenerator(),
            VideoProducer(),
            TTSGenerator()
        )
    except Exception as e:
        st.error(f"Failed to initialize modules: {e}")
        return None, None, None, None, None

renderer, remaker, content_gen, video_producer, tts_generator = load_modules()

st.sidebar.header("Environment & API")
missing_keys = []
if not os.environ.get("OPENAI_API_KEY"):
    missing_keys.append("OPENAI_API_KEY")
if not os.environ.get("REPLICATE_API_TOKEN"):
    missing_keys.append("REPLICATE_API_TOKEN")

if missing_keys:
    st.sidebar.error(f"Missing Essential API Keys: {', '.join(missing_keys)}. The pipeline may fail. Please set them in your `.env` file.")
else:
    st.sidebar.success("Essential API Keys configured! ✅")

if not os.environ.get("ELEVENLABS_API_KEY"):
    st.sidebar.warning("Missing ELEVENLABS_API_KEY. Vocal generation will be disabled.")

st.sidebar.header("Settings")

# Style Preset Selection
preset_styles = [
    settings.DEFAULT_STYLE,
    "Lofi hip hop, chill, relaxing",
    "Synthwave, retro 80s, neon",
    "Epic Orchestral, cinematic, Hans Zimmer",
    "Acoustic Folk, warm, intimate",
    "Custom..."
]
selected_style = st.sidebar.selectbox("Musical Style Preset", preset_styles, help="Select a predefined style or choose 'Custom...' to write your own.")

if selected_style == "Custom...":
    style = st.sidebar.text_input("Custom Style", value="Your custom prompt here", help="Describe the exact musical style, instruments, and mood you want.")
else:
    style = selected_style

output_dir = st.sidebar.text_input("Output Directory", value=settings.OUTPUT_DIR, help="Where the final audio, video, and metadata files will be saved.")
max_workers = st.sidebar.slider("Concurrent Tasks", min_value=1, max_value=4, value=1, help="Process multiple MIDI files at the same time. Warning: High concurrency may hit API rate limits or use significant local resources.")

st.sidebar.markdown("### Advanced Audio Processing")
with st.sidebar.expander("Audio Settings", expanded=False):
    normalize_audio = st.checkbox("Normalize Volume", value=True, help="Automatically adjust the volume of the generated audio to a standard level.")
    fade_in_ms = st.number_input("Fade-In (ms)", min_value=0, max_value=10000, value=0, step=500, help="Apply a gradual volume increase at the start of the audio.")
    fade_out_ms = st.number_input("Fade-Out (ms)", min_value=0, max_value=10000, value=0, step=500, help="Apply a gradual volume decrease at the end of the audio.")


st.sidebar.markdown("### Subtitle Styling")
with st.sidebar.expander("Subtitle Style Settings", expanded=False):
    sub_font_size = st.number_input("Font Size", min_value=12, max_value=72, value=24, step=2, help="Font size for burned-in subtitles.")
    sub_primary_color = st.color_picker("Primary Color", value="#FFFFFF", help="Main text color for subtitles.")
    sub_outline_color = st.color_picker("Outline Color", value="#000000", help="Outline color for subtitles.")
    sub_back_color = st.color_picker("Background Box Color", value="#000000", help="Background box color (if enabled).")
    sub_box = st.checkbox("Show Background Box", value=True, help="Draw a semi-transparent box behind subtitle text for readability.")

st.sidebar.markdown("### Pipeline Options")

interactive_mode = st.sidebar.checkbox("Interactive Review Mode", value=False, help="Pause the pipeline after metadata/lyrics generation to manually edit the lyrics, title, and art prompt before rendering the final audio and video.")

video_format = st.sidebar.selectbox("Video Format", ["Standard 16:9", "Vertical 9:16 (TikTok/Reels)"], index=0, help="Output video aspect ratio.")
enable_visualizer = st.sidebar.checkbox("Audio-Reactive Visualizer", value=False, help="Overlay a dynamic audio waveform on the generated video.")
generate_vocals = st.sidebar.checkbox("Generate Vocals (ElevenLabs)", value=False, help="Automatically generate singing/spoken word vocals for the lyrics and mix them into the final track.")
create_shorts = st.sidebar.checkbox("Create 15s Shorts", value=False, help="Extract 15-second clips from the final video into the output/shorts directory.")

elevenlabs_voice_id = settings.DEFAULT_ELEVENLABS_VOICE_ID
elevenlabs_model = settings.DEFAULT_ELEVENLABS_MODEL

if generate_vocals:
    if not os.environ.get("ELEVENLABS_API_KEY"):
        st.sidebar.error("Cannot generate vocals without an ELEVENLABS_API_KEY.")
    else:
        with st.sidebar.expander("ElevenLabs Settings", expanded=True):
            elevenlabs_voice_id = st.text_input("Voice IDs (Comma-separated for Harmony)", value=settings.DEFAULT_ELEVENLABS_VOICE_ID, help="Enter a single ElevenLabs Voice ID for solo, or multiple comma-separated IDs to generate a multi-voice harmonized choir.")
            elevenlabs_model = st.selectbox("Model", ["eleven_multilingual_v2", "eleven_monolingual_v1", "eleven_turbo_v2"], index=0, help="The ElevenLabs model to use.")


skip_render = st.sidebar.checkbox("Skip Render if exists", value=False, help="If the intermediate base WAV file already exists, don't re-render it from MIDI.")
skip_remake = st.sidebar.checkbox("Skip Remake if exists", value=False, help="If the remade audio already exists, don't call the MusicGen API again.")
upload = st.sidebar.checkbox("Upload to YouTube", value=False, help="Automatically upload the finished video to YouTube (requires OAuth credentials setup).")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear Workspace", help="Delete all files in the input and output directories."):
    import shutil
    try:
        if os.path.exists(settings.INPUT_DIR):
            shutil.rmtree(settings.INPUT_DIR)
            os.makedirs(settings.INPUT_DIR)
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)
        st.sidebar.success("Workspace cleared successfully.")
    except Exception as e:
        st.sidebar.error(f"Failed to clear workspace: {e}")

tab1, tab2 = st.tabs(["🚀 Automated Pipeline", "🎹 Hymn Editor (Beta)"])

with tab1:
    uploaded_files = st.file_uploader("Upload MIDI, MusicXML, or Sheet Music images (OMR)", type=["mid", "midi", "mxl", "xml", "png", "jpg", "pdf"], accept_multiple_files=True, help="Select one or more public domain hymn MIDI, MusicXML, or Sheet Music image files to process.")

    if st.button("Start Processing", type="primary"):
        st.session_state["is_processing"] = True
        st.session_state["completed_files"] = []
        st.session_state["uploaded_files_data"] = []
        if uploaded_files:
            for uf in uploaded_files:
                st.session_state["uploaded_files_data"].append({
                    "name": uf.name,
                    "data": uf.getbuffer().tobytes()
                })

    if st.session_state.get("is_processing", False):
        if not st.session_state.get("uploaded_files_data"):
            st.warning("Please upload at least one MIDI file.")
            st.session_state["is_processing"] = False
        elif renderer is None:
            st.error("Pipeline modules failed to load.")
        else:
            # Ensure input/output dirs exist
            os.makedirs(settings.INPUT_DIR, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            # Save uploaded files to input directory
            saved_files = []
            for uf_data in st.session_state["uploaded_files_data"]:
                file_path = os.path.join(settings.INPUT_DIR, uf_data["name"])
                with open(file_path, "wb") as f:
                    f.write(uf_data["data"])
                saved_files.append(file_path)

            st.success(f"Saved {len(saved_files)} files to input directory.")

            # Create placeholders for progress
        progress_bars = {}
        status_texts = {}
        for file_path in saved_files:
            filename = os.path.basename(file_path)
            st.write(f"### {filename}")
            progress_bars[file_path] = st.progress(0)
            status_texts[file_path] = st.empty()
            status_texts[file_path].text("Queued...")

        def ui_process_wrapper(file_path):
            filename = os.path.basename(file_path)
            try:
                status_texts[file_path].info(f"Step 1/4: Rendering MIDI ({filename})...")
                progress_bars[file_path].progress(15)

                # Default callback for non-interactive
                callback = None

                if interactive_mode:
                    def interactive_callback_sync(data):
                        st.info("Pipeline Paused: Review generated content before final rendering.")
                        state_key = f"interactive_{filename}"
                        if state_key not in st.session_state:
                            st.session_state[state_key] = data

                        curr_data = st.session_state[state_key]

                        if st.session_state.get(f"interactive_done_{filename}"):
                            return st.session_state[state_key]

                        with st.form(key=f"form_{filename}"):
                            st.subheader(f"Edit Metadata & Art Prompt: {filename}")
                            new_title = st.text_input("Title", value=curr_data['metadata'].get('title', ''))
                            new_desc = st.text_area("Description", value=curr_data['metadata'].get('description', ''))
                            new_art = st.text_area("Art Prompt (DALL-E)", value=curr_data['art_prompt'])
                            st.subheader("Edit Lyrics")
                            raw_text = "\n".join([l['text'] for l in curr_data['lyrics']])
                            new_lyrics_text = st.text_area("Lyrics (One line per subtitle block)", value=raw_text, height=300)
                            submit = st.form_submit_button("Approve & Continue Rendering")

                        if submit:
                            new_lyrics = []
                            for idx, line in enumerate(new_lyrics_text.strip().split('\n')):
                                if line.strip():
                                    if idx < len(curr_data['lyrics']):
                                        new_line = curr_data['lyrics'][idx].copy()
                                        new_line['text'] = line.strip()
                                        new_lyrics.append(new_line)
                                    else:
                                        new_lyrics.append({'start': 0, 'end': 5, 'text': line.strip()})
                            curr_data['metadata']['title'] = new_title
                            curr_data['metadata']['description'] = new_desc
                            curr_data['art_prompt'] = new_art
                            curr_data['lyrics'] = new_lyrics
                            st.session_state[f"interactive_done_{filename}"] = True
                            st.session_state[state_key] = curr_data
                            st.rerun()
                        st.stop()
                    callback = interactive_callback_sync

                force_skip_render = skip_render
                force_skip_remake = skip_remake
                if interactive_mode and st.session_state.get(f"interactive_done_{filename}"):
                    force_skip_render = True
                    force_skip_remake = True

                process_single_midi(
                    file_path, output_dir, style, force_skip_render, force_skip_remake, upload,
                    renderer, remaker, content_gen, video_producer, mxl_parser=mxl_parser, omr_processor=omr_processor, tts_generator=tts_generator, stem_separator=stem_separator,
                    normalize_audio=normalize_audio, fade_in_ms=fade_in_ms, fade_out_ms=fade_out_ms,
                    generate_vocals=generate_vocals, voice_id=elevenlabs_voice_id, model=elevenlabs_model,
                    video_format=video_format, create_shorts=create_shorts, sub_font_size=sub_font_size,
                    sub_primary_color=sub_primary_color, sub_outline_color=sub_outline_color, sub_back_color=sub_back_color, sub_box=sub_box,
                    status_callback=lambda msg, prog: (status_texts[file_path].info(msg), progress_bars[file_path].progress(prog)),
                    interactive_callback=callback
                )

                status_texts[file_path].success(f"Completed! ✅ ({filename})")
                progress_bars[file_path].progress(100)

                name_no_ext = os.path.splitext(filename)[0]
                video_path = os.path.join(output_dir, f"{name_no_ext}.mp4")
                audio_path = os.path.join(output_dir, f"{name_no_ext}_remake.wav")
                metadata_path = os.path.join(output_dir, f"{name_no_ext}_metadata.json")

                if os.path.exists(video_path):
                    st.video(video_path)
                    col1, col2, col3 = st.columns(3)
                    with open(video_path, "rb") as f:
                        col1.download_button("Download Video 🎥", f, file_name=f"{name_no_ext}.mp4", mime="video/mp4")
                    if os.path.exists(audio_path):
                        with open(audio_path, "rb") as f:
                            col2.download_button("Download Audio 🎵", f, file_name=f"{name_no_ext}_remake.wav", mime="audio/wav")
                    if os.path.exists(metadata_path):
                        with open(metadata_path, "r") as f:
                            import json
                            metadata = json.load(f)
                            col3.download_button("Download Metadata 📄", json.dumps(metadata, indent=4), file_name=f"{name_no_ext}_metadata.json", mime="application/json")
                        with st.expander(f"Metadata & Lyrics for {name_no_ext}"):
                            st.write(f"**Title:** {metadata.get('title', 'N/A')}")
                            st.write(f"**Description:** {metadata.get('description', 'N/A')}")
                            st.write(f"**Tags:** {', '.join(metadata.get('tags', []))}")
                            if metadata.get("lyrics"):
                                st.write("**Lyrics:**")
                                for line in metadata["lyrics"]:
                                    st.write(f"[{line.get('start')}s -> {line.get('end')}s] {line.get('text')}")

            except Exception as e:
                status_texts[file_path].text(f"Error: {e} ❌")
                st.error(f"Error processing {filename}: {e}")

        st.write("---")
        st.write("Processing log:")

        if interactive_mode:
            st.warning("Interactive mode enabled: processing files sequentially.")
            for fp in saved_files:
                filename = os.path.basename(fp)
                if filename in st.session_state.get("completed_files", []):
                    continue
                ui_process_wrapper(fp)
                if "completed_files" not in st.session_state:
                    st.session_state["completed_files"] = []
                st.session_state["completed_files"].append(filename)
        else:
            import concurrent.futures
            from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
            ctx = get_script_run_ctx()

            def thread_func(fp, context):
                add_script_run_ctx(ctx=context)
                ui_process_wrapper(fp)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for fp in saved_files:
                    future = executor.submit(thread_func, fp, ctx)
                    futures.append(future)
                for future in concurrent.futures.as_completed(futures):
                    pass

        st.balloons()
        st.success("All processing complete!")
        st.session_state["is_processing"] = False
        st.session_state.pop("uploaded_files_data", None)



with tab2:
    st.header("Hymn Editor Toolbar")
    st.info("This section exposes raw backend rendering tools for manual experimentation without running the full generative pipeline.")

    st.subheader("1. File Operations")
    editor_file = st.file_uploader("Load MIDI or MusicXML file for editing", type=["mid", "midi", "mxl", "xml"], key="editor_uploader")

    if editor_file:
        file_path = os.path.join(settings.INPUT_DIR, f"edit_{editor_file.name}")
        with open(file_path, "wb") as f:
            f.write(editor_file.getbuffer())
        st.success(f"Loaded: {editor_file.name}")

        st.subheader("2. Native Audio Preview")
        st.write("Use the native C++ engine to render a fast audio preview of the raw file.")

        col1, col2 = st.columns(2)
        with col1:
            preview_soundfont = st.selectbox("Select SoundFont", settings.DEFAULT_SOUNDFONT_PATHS)
        with col2:
            st.write(" ")
            st.write(" ")
            if st.button("Render Preview 🔊"):
                with st.spinner("Rendering audio via C++ engine..."):
                    try:
                        # Re-instantiate the renderer with the specific selected soundfont just for the preview
                        temp_renderer = MidiRenderer(soundfont_path=preview_soundfont)

                        # Handle MXL conversion if needed
                        target_path = file_path
                        if file_path.lower().endswith('.mxl') or file_path.lower().endswith('.xml'):
                            target_path = os.path.join(settings.OUTPUT_DIR, f"edit_preview.mid")
                            mxl_parser.process(file_path, target_path)

                        out_audio = os.path.join(settings.OUTPUT_DIR, "edit_preview.wav")
                        temp_renderer.render(target_path, out_audio)
                        st.audio(out_audio)
                        st.success("Render complete.")
                    except Exception as e:
                        st.error(f"Failed to render preview: {e}")

        st.subheader("3. Metadata Extraction")
        if st.button("Extract Sheet Metadata 📄"):
            if file_path.lower().endswith('.mxl') or file_path.lower().endswith('.xml'):
                with st.spinner("Parsing MusicXML..."):
                    try:
                        dummy_mid = os.path.join(settings.OUTPUT_DIR, "dummy_extract.mid")
                        metadata = mxl_parser.process(file_path, dummy_mid)

                        st.text_input("Extracted Title", value=metadata.get("title", "Unknown"))
                        st.text_input("Extracted Composer", value=metadata.get("composer", "Unknown"))

                        if metadata.get("lyrics"):
                            edited_lyrics = st.text_area("Extracted Lyrics", value=metadata.get("lyrics"), height=200)

                            if st.button("Save Edited Lyrics to .txt 💾"):
                                out_txt_path = os.path.join(settings.OUTPUT_DIR, f"{editor_file.name}_lyrics.txt")
                                with open(out_txt_path, "w") as lf:
                                    lf.write(edited_lyrics)
                                st.success(f"Lyrics saved to {out_txt_path}")

                                with open(out_txt_path, "rb") as lf:
                                    st.download_button("Download .txt", lf, file_name=f"{editor_file.name}_lyrics.txt", mime="text/plain")
                        else:
                            st.warning("No lyrics found in this file.")
                    except Exception as e:
                        st.error(f"Failed to parse MusicXML: {e}")
            else:
                st.warning("Metadata extraction is currently only supported for MusicXML (.mxl, .xml) files, not standard MIDI.")
