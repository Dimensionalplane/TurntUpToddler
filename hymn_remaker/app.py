import streamlit as st
import os
import sys
import glob
import concurrent.futures

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
    "Deep House, high quality, electronic",
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

output_dir = st.sidebar.text_input("Output Directory", value="hymn_remaker/output", help="Where the final audio, video, and metadata files will be saved.")
max_workers = st.sidebar.slider("Concurrent Tasks", min_value=1, max_value=4, value=1, help="Process multiple MIDI files at the same time. Warning: High concurrency may hit API rate limits or use significant local resources.")

st.sidebar.markdown("### Advanced Audio Processing")
with st.sidebar.expander("Audio Settings", expanded=False):
    normalize_audio = st.checkbox("Normalize Volume", value=True, help="Automatically adjust the volume of the generated audio to a standard level.")
    fade_in_ms = st.number_input("Fade-In (ms)", min_value=0, max_value=10000, value=0, step=500, help="Apply a gradual volume increase at the start of the audio.")
    fade_out_ms = st.number_input("Fade-Out (ms)", min_value=0, max_value=10000, value=0, step=500, help="Apply a gradual volume decrease at the end of the audio.")

st.sidebar.markdown("### Pipeline Options")
video_format = st.sidebar.selectbox("Video Format", ["Standard 16:9", "Vertical 9:16 (TikTok/Reels)"], index=0, help="Output video aspect ratio.")
generate_vocals = st.sidebar.checkbox("Generate Vocals (ElevenLabs)", value=False, help="Automatically generate singing/spoken word vocals for the lyrics and mix them into the final track.")

elevenlabs_voice_id = "21m00Tcm4TlvDq8ikWAM"
elevenlabs_model = "eleven_multilingual_v2"

if generate_vocals:
    if not os.environ.get("ELEVENLABS_API_KEY"):
        st.sidebar.error("Cannot generate vocals without an ELEVENLABS_API_KEY.")
    else:
        with st.sidebar.expander("ElevenLabs Settings", expanded=True):
            elevenlabs_voice_id = st.text_input("Voice ID", value="21m00Tcm4TlvDq8ikWAM", help="The ElevenLabs Voice ID to use.")
            elevenlabs_model = st.selectbox("Model", ["eleven_multilingual_v2", "eleven_monolingual_v1", "eleven_turbo_v2"], index=0, help="The ElevenLabs model to use.")


skip_render = st.sidebar.checkbox("Skip Render if exists", value=False, help="If the intermediate base WAV file already exists, don't re-render it from MIDI.")
skip_remake = st.sidebar.checkbox("Skip Remake if exists", value=False, help="If the remade audio already exists, don't call the MusicGen API again.")
upload = st.sidebar.checkbox("Upload to YouTube", value=False, help="Automatically upload the finished video to YouTube (requires OAuth credentials setup).")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear Workspace", help="Delete all files in the input and output directories."):
    import shutil
    try:
        if os.path.exists("hymn_remaker/input"):
            shutil.rmtree("hymn_remaker/input")
            os.makedirs("hymn_remaker/input")
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)
        st.sidebar.success("Workspace cleared successfully.")
    except Exception as e:
        st.sidebar.error(f"Failed to clear workspace: {e}")

uploaded_files = st.file_uploader("Upload MIDI files", type=["mid", "midi"], accept_multiple_files=True, help="Select one or more public domain hymn MIDI files to process.")

if st.button("Start Processing", type="primary"):
    if not uploaded_files:
        st.warning("Please upload at least one MIDI file.")
    elif renderer is None:
        st.error("Pipeline modules failed to load.")
    else:
        # Ensure input/output dirs exist
        os.makedirs("hymn_remaker/input", exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Save uploaded files to input directory
        saved_files = []
        for uf in uploaded_files:
            file_path = os.path.join("hymn_remaker/input", uf.name)
            with open(file_path, "wb") as f:
                f.write(uf.getbuffer())
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

        # Process function with UI updates
        def ui_process_wrapper(file_path):
            filename = os.path.basename(file_path)
            try:
                status_texts[file_path].info(f"Step 1/4: Rendering MIDI ({filename})...")
                progress_bars[file_path].progress(15)

                # We need to monkey-patch or intercept logging if we want to show exact internal steps,
                # but for now we just wrap the whole call and update progress after it's done.
                # Alternatively, we pass a callback, but we will modify process_single_midi slightly to accept a callback later.
                # For now, let's pass a progress callback or simply execute the function.

                # To make this truly granular, we should update process_single_midi to take a status_callback.
                # Since we haven't yet, we'll just run it. We will update `process_single_midi` in main.py.

                process_single_midi(
                    file_path,
                    output_dir,
                    style,
                    skip_render,
                    skip_remake,
                    upload,
                    renderer,
                    remaker,
                    content_gen,
                    video_producer,
                    tts_generator=tts_generator,
                    normalize_audio=normalize_audio,
                    fade_in_ms=fade_in_ms,
                    fade_out_ms=fade_out_ms,
                    generate_vocals=generate_vocals,
                    voice_id=elevenlabs_voice_id,
                    model=elevenlabs_model,
                    video_format=video_format,
                    status_callback=lambda msg, prog: (status_texts[file_path].info(msg), progress_bars[file_path].progress(prog))
                )

                status_texts[file_path].success(f"Completed! ✅ ({filename})")
                progress_bars[file_path].progress(100)

                # Try to display the video if it exists
                name_no_ext = os.path.splitext(filename)[0]
                video_path = os.path.join(output_dir, f"{name_no_ext}.mp4")
                audio_path = os.path.join(output_dir, f"{name_no_ext}_remake.wav")
                metadata_path = os.path.join(output_dir, f"{name_no_ext}_metadata.json")

                if os.path.exists(video_path):
                    st.video(video_path)

                    # Create columns for download buttons
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

        # Run concurrently, passing Streamlit script run context to the threads
        from streamlit.runtime.scriptrunner import add_script_run_ctx

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for fp in saved_files:
                future = executor.submit(ui_process_wrapper, fp)
                add_script_run_ctx(future)
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                pass

        st.balloons()
        st.success("All processing complete!")
