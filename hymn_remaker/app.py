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
from main import process_single_midi

st.set_page_config(page_title="Hymn Remaker UI", page_icon="🎵")

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
            VideoProducer()
        )
    except Exception as e:
        st.error(f"Failed to initialize modules: {e}")
        return None, None, None, None

renderer, remaker, content_gen, video_producer = load_modules()

st.sidebar.header("Settings")
style = st.sidebar.text_input("Musical Style", value="Deep House, high quality, electronic")
output_dir = st.sidebar.text_input("Output Directory", value="hymn_remaker/output")
max_workers = st.sidebar.slider("Concurrent Tasks", min_value=1, max_value=4, value=1)
skip_render = st.sidebar.checkbox("Skip Render if exists", value=False)
skip_remake = st.sidebar.checkbox("Skip Remake if exists", value=False)
upload = st.sidebar.checkbox("Upload to YouTube", value=False)

uploaded_files = st.file_uploader("Upload MIDI files", type=["mid", "midi"], accept_multiple_files=True)

if st.button("Start Processing"):
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
                status_texts[file_path].text("Processing...")
                progress_bars[file_path].progress(10)

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
                    video_producer
                )

                status_texts[file_path].text("Completed! ✅")
                progress_bars[file_path].progress(100)

                # Try to display the video if it exists
                name_no_ext = os.path.splitext(filename)[0]
                video_path = os.path.join(output_dir, f"{name_no_ext}.mp4")
                if os.path.exists(video_path):
                    st.video(video_path)

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
