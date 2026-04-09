import streamlit as st
import os
import sys
import glob
import concurrent.futures

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.midi_renderer import MidiRenderer
from src.remaker import MusicRemaker
from src.content_generator import ContentGenerator
from src.video_uploader import VideoProducer
from src.tts_generator import TTSGenerator
from main import process_single_midi
from src.db import init_db, get_history

st.set_page_config(page_title="Hymn Remaker UI", page_icon="🎵", layout="wide")

# Initialize SQLite database
init_db()

# Try to load the version number from VERSION.md
try:
    with open(os.path.join(os.path.dirname(__file__), "VERSION.md"), "r") as f:
        __version__ = f.read().strip()
except Exception:
    __version__ = "Unknown"

st.title("🎵 Hymn Remaker Pipeline")
st.write(f"Convert MIDI files into modern music videos with AI! **(v{__version__})**")

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

st.sidebar.markdown(f"---")
st.sidebar.write(f"<small>Hymn Remaker Version: {__version__}</small>", unsafe_allow_html=True)

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
generate_vocals = st.sidebar.checkbox("Generate Vocals (ElevenLabs)", value=False, help="Automatically generate singing/spoken word vocals for the lyrics and mix them into the final track.")
if generate_vocals and not os.environ.get("ELEVENLABS_API_KEY"):
    st.sidebar.error("Cannot generate vocals without an ELEVENLABS_API_KEY.")

use_visualizer = st.sidebar.checkbox("Use Audio Visualizer", value=False, help="Generate a dynamic ffmpeg waveform video instead of downloading static DALL-E 3 artwork.")

# Replicate Hash Configuration
replicate_model_hash = st.sidebar.text_input(
    "Replicate Model Hash",
    value=os.environ.get("REPLICATE_MODEL", "meta/musicgen:671ac904629c9798ddc38d7747750e2f54e63d179aa2e84786d1a2d6cc7809a6"),
    help="The specific MusicGen model hash to use. Advanced users can swap this if Meta releases updates."
)
os.environ["REPLICATE_MODEL"] = replicate_model_hash

use_dynamic_prompt = st.sidebar.checkbox("Use AI Dynamic Prompting", value=True, help="Automatically analyze the MIDI structure (BPM, Time Signature) and use OpenAI to craft an expert-level prompt for Replicate, rather than just passing the generic style text.")

skip_render = st.sidebar.checkbox("Skip Render if exists", value=False, help="If the intermediate base WAV file already exists, don't re-render it from MIDI.")
skip_remake = st.sidebar.checkbox("Skip Remake if exists", value=False, help="If the remade audio already exists, don't call the MusicGen API again.")
upload = st.sidebar.checkbox("Upload to YouTube", value=False, help="Automatically upload the finished video to YouTube (requires OAuth credentials setup).")

st.sidebar.markdown("### Cloud & Notifications")
with st.sidebar.expander("S3 & Webhooks", expanded=False):
    s3_bucket = st.text_input("AWS S3 Bucket Name", value=os.environ.get("AWS_S3_BUCKET", ""), help="Upload generated assets to this S3 bucket automatically. Requires AWS credentials in .env.")
    webhook_url = st.text_input("Discord/Slack Webhook URL", value=os.environ.get("WEBHOOK_URL", ""), help="Send a notification to this webhook when generation completes.")

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

tab1, tab2, tab3 = st.tabs(["🚀 Generate", "📁 Gallery & History", "⚙️ System Dashboard"])

with tab1:
    st.subheader("Create New Hymn")
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

            # Save uploaded files to input directory with strict validation
            saved_files = []
            invalid_files = []
            for uf in uploaded_files:
                # Validate MIDI header (MThd)
                file_bytes = uf.getbuffer()
                if len(file_bytes) < 4 or file_bytes[:4] != b'MThd':
                    invalid_files.append(uf.name)
                    continue

                file_path = os.path.join("hymn_remaker/input", uf.name)
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                saved_files.append(file_path)

            if invalid_files:
                st.error(f"Failed to load {len(invalid_files)} invalid files (not standard MIDI format): {', '.join(invalid_files)}")

            if not saved_files:
                st.stop()

            st.success(f"Saved {len(saved_files)} valid MIDI files to input directory.")

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
                        use_visualizer=use_visualizer,
                        use_dynamic_prompt=use_dynamic_prompt,
                        s3_bucket=s3_bucket if s3_bucket else None,
                        webhook_url=webhook_url if webhook_url else None,
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
                                st.write(f"**Actual AI Prompt Used:** _{metadata.get('ai_generation_prompt', 'N/A')}_")
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

with tab2:
    st.subheader("Generation History")
    history_records = get_history()

    if not history_records:
        st.info("No generations found in history yet.")
    else:
        for idx, record in enumerate(history_records):
            with st.expander(f"{record['date_created'][:16]} - {record['hymn_name']} ({record['style']})", expanded=(idx==0)):
                if os.path.exists(record['video_path']):
                    st.video(record['video_path'])

                    col1, col2 = st.columns(2)
                    with open(record['video_path'], "rb") as f:
                        col1.download_button("Download Video", f, file_name=os.path.basename(record['video_path']), mime="video/mp4", key=f"dl_vid_{idx}")

                    if os.path.exists(record['audio_path']):
                        with open(record['audio_path'], "rb") as f:
                            col2.download_button("Download Audio", f, file_name=os.path.basename(record['audio_path']), mime="audio/wav", key=f"dl_aud_{idx}")

                    if os.path.exists(record['metadata_path']):
                        try:
                            import json
                            with open(record['metadata_path'], "r") as f:
                                meta = json.load(f)
                            st.write(f"**Title:** {meta.get('title')}")
                            st.write(f"**Description:** {meta.get('description')}")
                        except Exception:
                            st.write("Metadata file unavailable.")
                else:
                    if record.get('remote_video_url'):
                        st.info("Local file deleted, but cloud backups are available.")
                        st.markdown(f"[Watch/Download Video from S3]({record['remote_video_url']})")
                        if record.get('remote_audio_url'):
                            st.markdown(f"[Download Audio from S3]({record['remote_audio_url']})")
                    else:
                        st.warning("Video file has been deleted or moved from output directory, and no cloud backup exists.")

with tab3:
    st.subheader("System & Dependencies Dashboard")
    st.write("Track the version compatibility of the underlying project submodules and system binaries. Useful for debugging Docker environments.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### System Binaries")
        import subprocess
        # Check FFmpeg
        try:
            ffmpeg_version = subprocess.check_output(["ffmpeg", "-version"]).decode().split('\n')[0]
            st.success(f"✅ FFmpeg: `{ffmpeg_version}`")
        except Exception:
            st.error("❌ FFmpeg: Not Installed or Not in PATH")

        # Check FluidSynth
        try:
            fluidsynth_version = subprocess.check_output(["fluidsynth", "--version"]).decode().split('\n')[0]
            st.success(f"✅ FluidSynth: `{fluidsynth_version}`")
        except Exception:
            st.error("❌ FluidSynth: Not Installed or Not in PATH")

    with col2:
        st.markdown("#### Python Submodules (`requirements.txt`)")
        try:
            req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
            if os.path.exists(req_path):
                with open(req_path, "r") as f:
                    reqs = f.read().splitlines()

                # Fetch installed versions
                import importlib.metadata
                for req in reqs:
                    if not req.strip() or req.startswith('#'): continue
                    pkg_name = req.split('==')[0].split('>=')[0].split('<')[0].strip()
                    try:
                        version = importlib.metadata.version(pkg_name)
                        st.write(f"- **{pkg_name}**: `v{version}`")
                    except importlib.metadata.PackageNotFoundError:
                        st.write(f"- **{pkg_name}**: `Not Installed` ❌")
            else:
                st.warning("`requirements.txt` not found.")
        except Exception as e:
            st.error(f"Could not load requirements: {e}")

    st.markdown("---")
    st.markdown("#### Project Directory Structure")
    st.code("""
hymn_remaker/
├── app.py                  # Streamlit Web UI
├── main.py                 # Core parallel processing pipeline
├── src/                    # Submodules & API Integrations
│   ├── content_generator.py # OpenAI GPT-4 / DALL-E
│   ├── midi_analyzer.py     # Mido BPM/Time Signature Parsing
│   ├── tts_generator.py     # ElevenLabs Voice Synthesis
│   ├── s3_uploader.py       # Boto3 AWS S3 Backup
│   ├── video_uploader.py    # FFmpeg & YouTube Data API
│   ├── webhook_notifier.py  # Discord/Slack Integrations
│   └── utils.py             # Pydub Audio Ducking/Mixing
├── input/                  # MIDI drop folder
└── output/                 # Final MP4/WAV/JSON destination
    """)
