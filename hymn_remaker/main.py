import os
import sys
import glob
import logging
import argparse
import json
import requests
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from hymn_remaker import settings

# Add the project root to sys.path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.midi_renderer import MidiRenderer
from src.remaker import MusicRemaker
from src.content_generator import ContentGenerator
from src.video_uploader import VideoProducer
from src.tts_generator import TTSGenerator
from src.musicxml_parser import MusicXMLParser
from src.omr_processor import OMRProcessor
from src.utils import process_audio

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("hymn_remaker.log") # Commented out to avoid permission issues if run in weird places
    ]
)
logger = logging.getLogger("HymnRemaker")

def main():
    parser = argparse.ArgumentParser(description="Hymn Remaker Pipeline")
    parser.add_argument("--input-dir", default="hymn_remaker/input", help="Directory containing input MIDI files")
    parser.add_argument("--output-dir", default="hymn_remaker/output", help="Directory for output files")
    parser.add_argument("--soundfont", help="Path to custom soundfont")
    parser.add_argument("--style", default="Deep House, high quality, electronic", help="Musical style prompt for the remake")
    parser.add_argument("--upload", action="store_true", help="Upload to YouTube after generation")
    parser.add_argument("--skip-render", action="store_true", help="Skip MIDI rendering if WAV exists")
    parser.add_argument("--skip-remake", action="store_true", help="Skip music generation if output audio exists")
    parser.add_argument("--voice-id", default="21m00Tcm4TlvDq8ikWAM", help="ElevenLabs Voice ID")
    parser.add_argument("--model", default="eleven_multilingual_v2", help="ElevenLabs Model")
    parser.add_argument("--video-format", default="Standard 16:9", choices=["Standard 16:9", "Vertical 9:16 (TikTok/Reels)"], help="Output video format")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode, watching the input directory for new files continuously.")
    parser.add_argument("--create-shorts", action="store_true", help="Extract 15-second short clips from the final video.")

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize modules
    try:
        base_audio_path = remake_audio_path = metadata_path = vocal_track_path = None
        renderer = MidiRenderer(soundfont_path=args.soundfont)
        remaker = MusicRemaker()
        content_gen = ContentGenerator()
        video_producer = VideoProducer()
        mxl_parser = MusicXMLParser()
        omr_processor = OMRProcessor()
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        sys.exit(1)

    import concurrent.futures

    def run_pipeline(midi_file_list):
        if not midi_file_list:
            return

        max_workers = min(4, len(midi_file_list))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    process_single_midi,
                    midi_path,
                    args.output_dir,
                    args.style,
                    args.skip_render,
                    args.skip_remake,
                    args.upload,
                    renderer,
                    remaker,
                    content_gen,
                    video_producer,
                    mxl_parser,
                    omr_processor,
                    voice_id=args.voice_id,
                    model=args.model,
                    video_format=args.video_format,
                    create_shorts=args.create_shorts
                ): midi_path for midi_path in midi_file_list
            }

            for future in concurrent.futures.as_completed(futures):
                midi_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing {midi_path} through executor: {e}")

    # Process initial files
    initial_midi_files = glob.glob(os.path.join(args.input_dir, "*.mid")) +                          glob.glob(os.path.join(args.input_dir, "*.mxl")) +                          glob.glob(os.path.join(args.input_dir, "*.xml"))
    if initial_midi_files:
        logger.info(f"Found {len(initial_midi_files)} initial MIDI files to process.")
        run_pipeline(initial_midi_files)
    else:
        logger.warning(f"No initial MIDI files found in {args.input_dir}")

    # Daemon Mode Logic
    if args.daemon:
        logger.info(f"Starting Daemon Mode. Monitoring {args.input_dir} for new MIDI files...")

        class MidiHandler(FileSystemEventHandler):
            def on_created(self, event):
                valid_exts = (".mid", ".mxl", ".xml", ".png", ".jpg", ".pdf")
                if not event.is_directory and any(event.src_path.lower().endswith(ext) for ext in valid_exts):
                    logger.info(f"Detected new Input file: {event.src_path}")
                    # Give the file a moment to finish copying/downloading
                    time.sleep(1)
                    run_pipeline([event.src_path])

            def on_moved(self, event):
                valid_exts = (".mid", ".mxl", ".xml", ".png", ".jpg", ".pdf")
                if not event.is_directory and any(event.dest_path.lower().endswith(ext) for ext in valid_exts):
                    logger.info(f"Detected moved MIDI file: {event.dest_path}")
                    time.sleep(1)
                    run_pipeline([event.dest_path])

        observer = Observer()
        observer.schedule(MidiHandler(), args.input_dir, recursive=False)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping Daemon Mode...")
            observer.stop()
        observer.join()
    else:
        if not initial_midi_files:
            sys.exit(0)

def process_single_midi(
    midi_path, output_dir, style, skip_render, skip_remake, upload,
    renderer, remaker, content_gen, video_producer, mxl_parser=None, omr_processor=None, tts_generator=None,
    normalize_audio=True, fade_in_ms=0, fade_out_ms=0, generate_vocals=False,
    voice_id=settings.DEFAULT_ELEVENLABS_VOICE_ID, model=settings.DEFAULT_ELEVENLABS_MODEL, video_format=settings.DEFAULT_VIDEO_FORMAT, create_shorts=False, status_callback=None,
    sub_font_size=24, sub_primary_color="#FFFFFF", sub_outline_color="#000000", sub_back_color="#000000", sub_box=True,
    interactive_callback=None
):
    base_audio_path = remake_audio_path = metadata_path = vocal_track_path = None
    try:
        filename = os.path.basename(midi_path)
        name_no_ext = os.path.splitext(filename)[0]

        def update_status(msg, progress):
            logger.info(msg)
            if status_callback:
                status_callback(msg, progress)

        update_status(f"Processing {filename}...", 10)

        pre_extracted_metadata = {}
        target_midi_path = midi_path

        # -1. Check if input is an image/PDF (OMR)
        if filename.lower().endswith('.png') or filename.lower().endswith('.jpg') or filename.lower().endswith('.pdf'):
            update_status(f"Step 0/4: Running OMR on sheet music ({filename})...", 12)
            if omr_processor and omr_processor.is_available():
                target_mxl_path = omr_processor.process(midi_path, output_dir)
                filename = os.path.basename(target_mxl_path)
                midi_path = target_mxl_path
                name_no_ext = os.path.splitext(filename)[0]
            else:
                logger.error("OMR processor is not available or oemer is not installed.")
                raise RuntimeError("Cannot process image/PDF without an active OMR processor.")

        # 0. Check if input is MusicXML and extract/convert
        if filename.lower().endswith('.mxl') or filename.lower().endswith('.xml'):
            update_status(f"Step 0/4: Parsing MusicXML and converting to MIDI ({filename})...", 15)
            target_midi_path = os.path.join(output_dir, f"{name_no_ext}_converted.mid")
            if mxl_parser:
                pre_extracted_metadata = mxl_parser.process(midi_path, target_midi_path)
            else:
                logger.warning("MusicXML parser not available, skipping XML parsing.")

        # 1. Render MIDI to Audio (WAV)
        update_status(f"Step 1/4: Rendering MIDI ({filename})...", 20)
        base_audio_path = os.path.join(output_dir, f"{name_no_ext}_base.wav")

        # Extract precise BPM to prevent AI tempo drift
        target_bpm = 120.0
        if os.path.exists(target_midi_path):
            target_bpm = renderer.get_midi_bpm(target_midi_path)
            update_status(f"Extracted dynamic tempo: {target_bpm:.1f} BPM", 25)

        if not skip_render or not os.path.exists(base_audio_path):
            renderer.render(target_midi_path, base_audio_path)
        else:
            update_status(f"Skipping render for {filename}, {base_audio_path} exists.", 30)

        # 2. Generate Remake (MusicGen)
        update_status(f"Step 2/4: Remaking Audio via Replicate ({filename})...", 40)
        remake_audio_path = os.path.join(output_dir, f"{name_no_ext}_remake.wav")

        if not skip_remake or not os.path.exists(remake_audio_path):
            # Enforce exact tempo in the style prompt
            tempo_enforced_style = f"{style}. The track must be exactly {target_bpm:.1f} BPM. Keep this exact tempo."

            # Call Replicate
            remake_url = remaker.remake(base_audio_path, tempo_enforced_style)

            # Download the remake
            update_status(f"Downloading remake from {remake_url}...", 50)
            response = requests.get(remake_url)
            response.raise_for_status()
            with open(remake_audio_path, "wb") as f:
                f.write(response.content)

            # Apply audio processing (Normalization & Fades)
            update_status(f"Applying advanced audio processing to {filename}...", 60)
            process_audio(remake_audio_path, remake_audio_path, normalize=normalize_audio, fade_in_ms=fade_in_ms, fade_out_ms=fade_out_ms)

        else:
             update_status(f"Skipping remake for {filename}, {remake_audio_path} exists.", 60)

        # 3. Generate Content (Metadata, Lyrics & Art)
        update_status(f"Step 3/4: Generating Lyrics, Art & Metadata ({filename})...", 70)

        metadata_path = os.path.join(output_dir, f"{name_no_ext}_metadata.json")

        # Check if we already generated (and potentially edited) this data
        if os.path.exists(metadata_path):
            update_status(f"Loading existing metadata and lyrics from {metadata_path}...", 72)
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            lyrics = metadata.get("lyrics", [])
            art_prompt = metadata.get("art_prompt", f"Abstract album art for {metadata.get('title', name_no_ext)}, {style} style, high quality, 4k")

            # If in interactive mode, we still need to yield back to UI to approve/edit
            if interactive_callback:
                update_status(f"Pausing for interactive review...", 76)
                edited_data = interactive_callback({
                    'metadata': metadata,
                    'lyrics': lyrics,
                    'art_prompt': art_prompt
                })
                if edited_data:
                    metadata = edited_data.get('metadata', metadata)
                    lyrics = edited_data.get('lyrics', lyrics)
                    art_prompt = edited_data.get('art_prompt', art_prompt)

                # Save edits
                with open(metadata_path, "w") as f:
                    metadata["lyrics"] = lyrics
                    metadata["art_prompt"] = art_prompt
                    json.dump(metadata, f, indent=4)
                update_status(f"Resuming pipeline...", 78)
        else:
            # First time generation
            # Incorporate pre-extracted MusicXML metadata
            if pre_extracted_metadata and pre_extracted_metadata.get("title"):
                metadata = content_gen.generate_metadata(pre_extracted_metadata["title"], style=style)
            else:
                metadata = content_gen.generate_metadata(name_no_ext, style=style)

            # Use extracted lyrics if available, otherwise generate
            if pre_extracted_metadata and pre_extracted_metadata.get("lyrics"):
                update_status("Formatting extracted MusicXML lyrics...", 75)
                title_context = pre_extracted_metadata.get("title") or name_no_ext
                lyrics = content_gen.generate_lyrics(title_context)
            else:
                lyrics = content_gen.generate_lyrics(metadata.get("title", name_no_ext))

            art_prompt = f"Abstract album art for {metadata.get('title', name_no_ext)}, {style} style, high quality, 4k"

            # Save initial generation before review so it's cached for the Streamlit rerun
            with open(metadata_path, "w") as f:
                metadata["lyrics"] = lyrics
                metadata["art_prompt"] = art_prompt
                json.dump(metadata, f, indent=4)

            # If in interactive mode, yield execution back to the UI to allow the user to edit metadata/lyrics/art_prompt
            if interactive_callback:
                update_status(f"Pausing for interactive review...", 76)
                edited_data = interactive_callback({
                    'metadata': metadata,
                    'lyrics': lyrics,
                    'art_prompt': art_prompt
                })
                if edited_data:
                    metadata = edited_data.get('metadata', metadata)
                    lyrics = edited_data.get('lyrics', lyrics)
                    art_prompt = edited_data.get('art_prompt', art_prompt)

                # Save edits
                with open(metadata_path, "w") as f:
                    metadata["lyrics"] = lyrics
                    metadata["art_prompt"] = art_prompt
                    json.dump(metadata, f, indent=4)
                update_status(f"Resuming pipeline...", 78)

        # Generate the actual image using the (potentially edited) prompt
        art_url = content_gen.generate_art(art_prompt)

        # Optional: Generate Vocals via ElevenLabs
        vocal_track_path = None
        if generate_vocals and tts_generator and lyrics:
            update_status(f"Step 3.5/4: Generating Vocals via ElevenLabs ({filename})...", 80)
            vocal_track_path = os.path.join(output_dir, f"{name_no_ext}_vocals.wav")
            try:
                tts_generator.generate_vocals(lyrics, vocal_track_path, voice_id=voice_id, model=model)
            except Exception as e:
                logger.error(f"Failed to generate vocals: {e}")
                vocal_track_path = None # Fallback to no vocals

        # If vocals were generated, we need to mix them into the remake_audio_path now
        if vocal_track_path:
            update_status(f"Mixing Vocals into Instrumental ({filename})...", 82)
            # Re-process the audio to mix the vocals (process_audio handles mixing if vocal_track_path is provided)
            process_audio(
                remake_audio_path,
                remake_audio_path,
                normalize=normalize_audio,
                fade_in_ms=fade_in_ms,
                fade_out_ms=fade_out_ms,
                vocal_track_path=vocal_track_path
            )

        # 4. Create Video (with subtitles if lyrics exist)
        update_status(f"Step 4/4: Creating Video with Subtitles ({filename})...", 85)
        video_path = os.path.join(output_dir, f"{name_no_ext}.mp4")
        video_producer.create_video(remake_audio_path, art_url, video_path, lyrics=lyrics, video_format=video_format, sub_font_size=sub_font_size, sub_primary_color=sub_primary_color, sub_outline_color=sub_outline_color, sub_back_color=sub_back_color, sub_box=sub_box)

        # 4.5 Create Shorts
        if create_shorts:
            update_status(f"Extracting Short Clips ({filename})...", 90)
            try:
                video_producer.create_shorts(video_path, output_dir)
                update_status(f"Short clips generated in output/shorts/", 92)
            except Exception as e:
                logger.error(f"Failed to generate shorts: {e}")

        # 5. Upload to YouTube (Optional)
        if upload:
            update_status(f"Uploading {filename} to YouTube...", 95)
            def upload_progress_cb(pct):
                scaled_pct = int(95 + (pct * 0.05))
                update_status(f"Uploading {filename} to YouTube... {pct}%", scaled_pct)

            video_id = video_producer.upload_to_youtube(video_path, metadata, progress_callback=upload_progress_cb)
            update_status(f"Video uploaded: https://youtu.be/{video_id}", 100)
        else:
            update_status(f"Finished processing {filename}", 100)

    except Exception as e:
        logger.error(f"Error processing {midi_path}: {e}")
        logger.info(f"Cleaning up temporary files for {filename} due to failure...")

        # Cleanup files if they were created during this failed run
        for path in [base_audio_path, remake_audio_path, metadata_path, vocal_track_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Cleaned up {path}")
                except OSError:
                    pass
        raise e

if __name__ == "__main__":
    main()
