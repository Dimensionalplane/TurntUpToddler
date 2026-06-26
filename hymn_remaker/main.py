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

from hymn_remaker.src.midi_renderer import MidiRenderer
from hymn_remaker.src.remaker import MusicRemaker
from hymn_remaker.src.suno_remaker import SunoRemaker
from hymn_remaker.src.content_generator import ContentGenerator
from hymn_remaker.src.video_uploader import VideoProducer
from hymn_remaker.src.tts_generator import TTSGenerator
from hymn_remaker.src.musicxml_parser import MusicXMLParser
from hymn_remaker.src.omr_processor import OMRProcessor
from hymn_remaker.src.stem_separator import StemSeparator
from hymn_remaker.src.radio_streamer import RadioStreamer
from hymn_remaker.src.utils import process_audio
from hymn_remaker.src.children_song_finder import ChildrenSongFinder

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("HymnRemaker")


def main():
    parser = argparse.ArgumentParser(description="Hymn Remaker Pipeline")
    parser.add_argument("--input-dir", default="hymn_remaker/input", help="Directory containing input MIDI files")
    parser.add_argument("--output-dir", default="hymn_remaker/output", help="Directory for output files")
    parser.add_argument("--soundfont", help="Path to custom soundfont")
    parser.add_argument("--style", default=settings.DEFAULT_STYLE, help="Musical style prompt for the remake")
    parser.add_argument("--upload", action="store_true", help="Upload to YouTube after generation")
    parser.add_argument("--skip-render", action="store_true", help="Skip MIDI rendering if WAV exists")
    parser.add_argument("--skip-remake", action="store_true", help="Skip music generation if output audio exists")
    parser.add_argument("--remake-priority", default=settings.REMAKE_PRIORITY, choices=["suno", "replicate"], help="AI service priority for Step 2 remake (default: suno)")
    parser.add_argument("--suno-session", default=None, help="Suno AI session token (overrides SUNO_SESSION_TOKEN env var)")
    parser.add_argument("--convert-mp3", action="store_true", help="Batch convert all base WAV files to MP3 and exit")
    parser.add_argument("--voice-id", default=settings.DEFAULT_ELEVENLABS_VOICE_ID, help="ElevenLabs Voice ID")
    parser.add_argument("--model", default=settings.DEFAULT_ELEVENLABS_MODEL, help="ElevenLabs Model")
    parser.add_argument("--video-format", default=settings.DEFAULT_VIDEO_FORMAT, choices=["Standard 16:9", "Vertical 9:16 (TikTok/Reels)"], help="Output video format")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode, watching the input directory for new files continuously.")
    parser.add_argument("--create-shorts", action="store_true", help="Extract 15-second short clips from the final video.")
    parser.add_argument("--stream-rtmp", default=None, help="RTMP URL for live DJ radio streaming")
    parser.add_argument("--visualizer", action="store_true", help="Enable audio-reactive visualizer overlay")
    parser.add_argument("--visualizer-mode", default="cline", choices=["cline", "line", "p2p", "avectorscope"], help="Visualizer mode type")
    parser.add_argument("--kids-mode", action="store_true", help="Enable Kids Mode (auto-downloads nursery rhymes if input is empty, sets kid-friendly styling, and enables COPPA youtube upload)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    try:
        renderer = MidiRenderer(soundfont_path=args.soundfont)
        remaker = MusicRemaker()
        suno_remaker = SunoRemaker(session_token=args.suno_session)
        content_gen = ContentGenerator()
        video_producer = VideoProducer()
        mxl_parser = MusicXMLParser()
        omr_processor = OMRProcessor()
        stem_separator = StemSeparator()
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        sys.exit(1)

    import concurrent.futures

    def run_pipeline(midi_file_list):
        if not midi_file_list:
            return
        worker_count = min(4, len(midi_file_list))
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
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
                    suno_remaker,
                    args.remake_priority,
                    content_gen,
                    video_producer,
                    mxl_parser=mxl_parser,
                    omr_processor=omr_processor,
                    tts_generator=None,
                    stem_separator=stem_separator,
                    voice_id=args.voice_id,
                    model=args.model,
                    video_format=args.video_format,
                    create_shorts=args.create_shorts,
                    enable_visualizer=args.visualizer,
                    visualizer_mode=args.visualizer_mode,
                    kids_mode=args.kids_mode
                ): midi_path
                for midi_path in midi_file_list
            }
            for future in concurrent.futures.as_completed(futures):
                midi_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing {midi_path} through executor: {e}")

    # Batch MP3 conversion mode
    if args.convert_mp3:
        logger.info("Batch converting base WAV files to MP3...")
        converted, failed = suno_remaker.batch_wav_to_mp3(args.output_dir, bitrate=settings.DEFAULT_MP3_BITRATE)
        logger.info(f"MP3 conversion complete: {converted} converted, {failed} failed")
        sys.exit(0 if failed == 0 else 1)

    if args.kids_mode:
        existing_inputs = (
            glob.glob(os.path.join(args.input_dir, "*.mid")) +
            glob.glob(os.path.join(args.input_dir, "*.midi")) +
            glob.glob(os.path.join(args.input_dir, "*.mxl")) +
            glob.glob(os.path.join(args.input_dir, "*.xml"))
        )
        if not existing_inputs:
            logger.info("Kids Mode is enabled and input directory is empty. Downloading curated nursery rhymes...")
            finder = ChildrenSongFinder()
            downloaded = finder.download_all(args.input_dir)
            logger.info(f"Downloaded {len(downloaded)} children's songs.")

    initial_midi_files = (
        glob.glob(os.path.join(args.input_dir, "*.mid")) +
        glob.glob(os.path.join(args.input_dir, "*.midi")) +
        glob.glob(os.path.join(args.input_dir, "*.mxl")) +
        glob.glob(os.path.join(args.input_dir, "*.xml"))
    )
    if initial_midi_files:
        logger.info(f"Found {len(initial_midi_files)} initial files to process.")
        run_pipeline(initial_midi_files)
    else:
        logger.warning(f"No files found to process in {args.input_dir}")

    streamer = None
    if args.stream_rtmp:
        logger.info(f"Initializing Live DJ Radio Stream to {args.stream_rtmp}...")
        streamer = RadioStreamer(args.stream_rtmp, input_dir=args.output_dir)
        streamer.start()

    if args.daemon:
        logger.info(f"Starting Daemon Mode. Monitoring {args.input_dir} for new files...")

        class MidiHandler(FileSystemEventHandler):
            def on_created(self, event):
                valid_exts = (".mid", ".mxl", ".xml", ".png", ".jpg", ".pdf")
                if not event.is_directory and any(event.src_path.lower().endswith(ext) for ext in valid_exts):
                    logger.info(f"Detected new Input file: {event.src_path}")
                    time.sleep(1)
                    run_pipeline([event.src_path])

            def on_moved(self, event):
                valid_exts = (".mid", ".mxl", ".xml", ".png", ".jpg", ".pdf")
                if not event.is_directory and any(event.dest_path.lower().endswith(ext) for ext in valid_exts):
                    logger.info(f"Detected moved file: {event.dest_path}")
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
            if streamer:
                streamer.stop()
            observer.join()
    else:
        if not initial_midi_files:
            sys.exit(0)


def process_single_midi(
    midi_path,
    output_dir,
    style,
    skip_render,
    skip_remake,
    upload,
    renderer,
    remaker,
    suno_remaker=None,
    remake_priority="suno",
    content_gen=None,
    video_producer=None,
    mxl_parser=None,
    omr_processor=None,
    tts_generator=None,
    stem_separator=None,
    normalize_audio=True,
    fade_in_ms=0,
    fade_out_ms=0,
    generate_vocals=False,
    voice_id=settings.DEFAULT_ELEVENLABS_VOICE_ID,
    model=settings.DEFAULT_ELEVENLABS_MODEL,
    video_format=settings.DEFAULT_VIDEO_FORMAT,
    create_shorts=False,
    status_callback=None,
    sub_font_size=24,
    sub_primary_color="#FFFFFF",
    sub_outline_color="#000000",
    sub_back_color="#000000",
    sub_box=True,
    enable_visualizer=False,
    visualizer_mode="cline",
    interactive_callback=None,
    kids_mode=False):

    base_audio_path = remake_audio_path = metadata_path = vocal_track_path = None
    try:
        filename = os.path.basename(midi_path)
        name_no_ext = os.path.splitext(filename)[0]

        if kids_mode:
            # Enforce children's styling
            lower_name = filename.lower()
            if any(word in lower_name for word in ["lullaby", "sleep", "bedtime", "night", "soothing"]):
                style = "lullaby, bedtime music, soft harp, toy piano, calming, peaceful, sleep music, high quality"
            else:
                style = "nursery rhyme, playful, happy, glockenspiel, toy piano, acoustic guitar, kids music, upbeat, high quality"
            logger.info(f"Kids Mode active. Auto-selected style preset: {style}")

        def update_status(msg, progress):
            logger.info(msg)
            if status_callback:
                status_callback(msg, progress)

        update_status(f"Processing {filename}...", 10)
        pre_extracted_metadata = {}
        target_midi_path = midi_path

        # -1. Check if input is an image/PDF (OMR)
        if filename.lower().endswith((".png", ".jpg", ".pdf")):
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
        if filename.lower().endswith((".mxl", ".xml")):
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

          # 2. Generate Remake (Suno AI -> Replicate MusicGen -> Base Audio Fallback)
        remake_audio_path = os.path.join(output_dir, f"{name_no_ext}_remake.wav")
        if not skip_remake or not os.path.exists(remake_audio_path):
            remake_success = False

            # --- Priority 1: Suno AI (audio influence -> Deep House) ---
            if remake_priority == "suno" and suno_remaker and suno_remaker.is_available():
                update_status(f"Step 2/4: Remaking Audio via Suno AI ({filename})...", 40)
                try:
                    tempo_enforced_style = f"{style}, {target_bpm:.1f} BPM"
                    suno_result = suno_remaker.remake(base_audio_path, tempo_enforced_style)
                    if suno_result and os.path.exists(suno_result):
                        # Suno returns the WAV path directly
                        if suno_result != remake_audio_path:
                            import shutil
                            shutil.move(suno_result, remake_audio_path)
                        update_status(f"Suno AI remake complete for {filename}", 55)
                        process_audio(remake_audio_path, remake_audio_path, normalize=normalize_audio, fade_in_ms=fade_in_ms, fade_out_ms=fade_out_ms)
                        remake_success = True
                        logger.info(f"Suno AI remake succeeded for {filename}")
                except Exception as suno_err:
                    err_msg = str(suno_err)
                    logger.warning(f"Suno AI failed for {filename}: {err_msg}")
                    if "credits" in err_msg.lower() or "402" in err_msg:
                        update_status(f"Suno credits exhausted for {filename}, trying fallback...", 42)
                    elif "invalid" in err_msg.lower() or "expired" in err_msg.lower() or "401" in err_msg:
                        update_status(f"Suno session token invalid/expired, trying Replicate fallback...", 42)
                    else:
                        update_status(f"Suno AI error for {filename}, trying fallback...", 42)

            # --- Priority 2: Replicate MusicGen ---
            if not remake_success and remake_priority == "replicate":
                update_status(f"Step 2/4: Remaking Audio via Replicate MusicGen ({filename})...", 40)
            elif not remake_success:
                update_status(f"Step 2/4: Trying Replicate MusicGen fallback ({filename})...", 43)

            if not remake_success:
                try:
                    tempo_enforced_style = f"{style}. The track must be exactly {target_bpm:.1f} BPM. Keep this exact tempo."
                    remake_url = remaker.remake(base_audio_path, tempo_enforced_style)
                    update_status(f"Downloading remake from {remake_url}...", 50)
                    response = requests.get(remake_url)
                    response.raise_for_status()
                    with open(remake_audio_path, "wb") as f:
                        f.write(response.content)
                    update_status(f"Applying advanced audio processing to {filename}...", 60)
                    process_audio(remake_audio_path, remake_audio_path, normalize=normalize_audio, fade_in_ms=fade_in_ms, fade_out_ms=fade_out_ms)
                    remake_success = True
                    logger.info(f"Replicate MusicGen remake succeeded for {filename}")
                except Exception as remake_err:
                    err_msg = str(remake_err)
                    if "Insufficient credit" in err_msg or "402" in err_msg:
                        update_status(f"Replicate credits insufficient for {filename}", 45)
                        logger.warning(f"Replicate credit error for {filename}.")
                    else:
                        update_status(f"Remake generation failed for {filename}: {err_msg[:100]}", 45)
                        logger.warning(f"Remake failed for {filename}: {err_msg}")

            # --- Priority 3: Base Audio Fallback ---
            if not remake_success:
                update_status(f"Using base audio as fallback for {filename}", 55)
                logger.warning(f"All AI remakers failed for {filename}. Copying base audio as fallback.")
                import shutil
                shutil.copy2(base_audio_path, remake_audio_path)
                logger.info(f"Copied base audio to remake path: {remake_audio_path}")
                update_status(f"Applying audio processing to fallback for {filename}...", 60)
                process_audio(remake_audio_path, remake_audio_path, normalize=normalize_audio, fade_in_ms=fade_in_ms, fade_out_ms=fade_out_ms)
        else:
            update_status(f"Skipping remake for {filename}, {remake_audio_path} exists.", 60)

# 3. Generate Content (Metadata, Lyrics & Art)
        update_status(f"Step 3/4: Generating Lyrics, Art & Metadata ({filename})...", 70)
        metadata_path = os.path.join(output_dir, f"{name_no_ext}_metadata.json")

        if os.path.exists(metadata_path):
            update_status(f"Loading existing metadata and lyrics from {metadata_path}...", 72)
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            lyrics = metadata.get("lyrics", [])
            default_art_prompt = (
                f"Cute cartoon illustration for children, vibrant colors, child-friendly storybook style, no text, high-quality vector art, depicting: {metadata.get('title', name_no_ext)}"
                if kids_mode else
                f"Abstract album art for {metadata.get('title', name_no_ext)}, {style} style, high quality, 4k"
            )
            art_prompt = metadata.get("art_prompt", default_art_prompt)
            if interactive_callback:
                update_status(f"Pausing for interactive review...", 76)
                edited_data = interactive_callback({
                    "metadata": metadata,
                    "lyrics": lyrics,
                    "art_prompt": art_prompt
                })
                if edited_data:
                    metadata = edited_data.get("metadata", metadata)
                    lyrics = edited_data.get("lyrics", lyrics)
                    art_prompt = edited_data.get("art_prompt", art_prompt)
                    with open(metadata_path, "w") as f:
                        metadata["lyrics"] = lyrics
                        metadata["art_prompt"] = art_prompt
                        json.dump(metadata, f, indent=4)
                    update_status(f"Resuming pipeline...", 78)
        else:
            # First time generation
            if pre_extracted_metadata and pre_extracted_metadata.get("title"):
                metadata = content_gen.generate_metadata(pre_extracted_metadata["title"], style=style, kids_mode=kids_mode)
            else:
                metadata = content_gen.generate_metadata(name_no_ext, style=style, kids_mode=kids_mode)

            extracted_lyrics = pre_extracted_metadata.get("lyrics") if pre_extracted_metadata else None
            if extracted_lyrics and isinstance(extracted_lyrics, list) and len(extracted_lyrics) > 0 and "start" in extracted_lyrics[0]:
                update_status("Using exact note-timed lyrics extracted from MusicXML...", 75)
                lyrics = extracted_lyrics
            else:
                update_status("Generating AI lyrics and timings via OpenAI...", 75)
                title_context = metadata.get("title") or name_no_ext
                lyrics = content_gen.generate_lyrics(title_context, kids_mode=kids_mode)

            art_prompt = (
                f"Cute cartoon illustration for children, vibrant colors, child-friendly storybook style, no text, high-quality vector art, depicting: {metadata.get('title', name_no_ext)}"
                if kids_mode else
                f"Abstract album art for {metadata.get('title', name_no_ext)}, {style} style, high quality, 4k"
            )

            with open(metadata_path, "w") as f:
                metadata["lyrics"] = lyrics
                metadata["art_prompt"] = art_prompt
                json.dump(metadata, f, indent=4)

            if interactive_callback:
                update_status(f"Pausing for interactive review...", 76)
                edited_data = interactive_callback({
                    "metadata": metadata,
                    "lyrics": lyrics,
                    "art_prompt": art_prompt
                })
                if edited_data:
                    metadata = edited_data.get("metadata", metadata)
                    lyrics = edited_data.get("lyrics", lyrics)
                    art_prompt = edited_data.get("art_prompt", art_prompt)
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
                vocal_track_path = None

        if vocal_track_path:
            update_status(f"Mixing Vocals into Instrumental ({filename})...", 82)
            stems = None
            if stem_separator:
                update_status(f"Running AI Stem Separation for smart vocal ducking ({filename})...", 83)
                stem_out_dir = os.path.join(output_dir, f"{name_no_ext}_stems")
                try:
                    stems = stem_separator.separate(remake_audio_path, stem_out_dir)
                except Exception as e:
                    logger.warning(f"Stem separation failed, falling back to basic ducking: {e}")
            process_audio(
                remake_audio_path,
                remake_audio_path,
                normalize=normalize_audio,
                fade_in_ms=fade_in_ms,
                fade_out_ms=fade_out_ms,
                vocal_track_path=vocal_track_path,
                stems=stems
            )

        # 4. Create Video (with subtitles if lyrics exist)
        update_status(f"Step 4/4: Creating Video with Subtitles ({filename})...", 85)
        video_path = os.path.join(output_dir, f"{name_no_ext}.mp4")
        video_producer.create_video(
            remake_audio_path, art_url, video_path,
            lyrics=lyrics, video_format=video_format,
            sub_font_size=sub_font_size,
            sub_primary_color=sub_primary_color,
            sub_outline_color=sub_outline_color,
            sub_back_color=sub_back_color,
            sub_box=sub_box,
            enable_visualizer=enable_visualizer,
            visualizer_mode=visualizer_mode
        )

        if create_shorts:
            update_status(f"Extracting Short Clips ({filename})...", 90)
            try:
                video_producer.create_shorts(video_path, output_dir)
                update_status(f"Short clips generated in output/shorts/", 92)
            except Exception as e:
                logger.error(f"Failed to generate shorts: {e}")

        if upload:
            update_status(f"Uploading {filename} to YouTube...", 95)
            def upload_progress_cb(pct):
                scaled_pct = int(95 + (pct * 0.05))
                update_status(f"Uploading {filename} to YouTube... {pct}%", scaled_pct)
            video_id = video_producer.upload_to_youtube(video_path, metadata, progress_callback=upload_progress_cb, kids_mode=kids_mode)
            update_status(f"Video uploaded: https://youtu.be/{video_id}", 100)
        else:
            update_status(f"Finished processing {filename}", 100)

    except Exception as e:
        logger.error(f"Error processing {midi_path}: {e}")
        logger.info(f"Cleaning up temporary files due to failure...")
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
