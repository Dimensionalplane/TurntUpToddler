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

# Add the project root to sys.path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.midi_renderer import MidiRenderer
from src.remaker import MusicRemaker
from src.content_generator import ContentGenerator
from src.video_uploader import VideoProducer
from src.tts_generator import TTSGenerator
<<<<<<< HEAD
from src.utils import process_audio
=======
from src.s3_uploader import S3Uploader
from src.webhook_notifier import WebhookNotifier
from src.midi_analyzer import MidiAnalyzer
from src.utils import process_audio
from src.db import add_history
>>>>>>> origin/feature/web-ui-and-parallelization-5540056130352860192

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
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        sys.exit(1)

    import concurrent.futures

    def run_pipeline(midi_file_list):
        if not midi_file_list:
            return

<<<<<<< HEAD
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
    initial_midi_files = glob.glob(os.path.join(args.input_dir, "*.mid"))
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
                if not event.is_directory and event.src_path.lower().endswith(".mid"):
                    logger.info(f"Detected new MIDI file: {event.src_path}")
                    # Give the file a moment to finish copying/downloading
                    time.sleep(1)
                    run_pipeline([event.src_path])

            def on_moved(self, event):
                if not event.is_directory and event.dest_path.lower().endswith(".mid"):
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
    renderer, remaker, content_gen, video_producer, tts_generator=None,
    normalize_audio=True, fade_in_ms=0, fade_out_ms=0, generate_vocals=False,
    voice_id="21m00Tcm4TlvDq8ikWAM", model="eleven_multilingual_v2", video_format="Standard 16:9", create_shorts=False, status_callback=None
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

        # 1. Render MIDI to Audio (WAV)
        update_status(f"Step 1/4: Rendering MIDI ({filename})...", 20)
        base_audio_path = os.path.join(output_dir, f"{name_no_ext}_base.wav")
        if not skip_render or not os.path.exists(base_audio_path):
            renderer.render(midi_path, base_audio_path)
        else:
            update_status(f"Skipping render for {filename}, {base_audio_path} exists.", 30)

        # 2. Generate Remake (MusicGen)
        update_status(f"Step 2/4: Remaking Audio via Replicate ({filename})...", 40)
        remake_audio_path = os.path.join(output_dir, f"{name_no_ext}_remake.wav")

        if not skip_remake or not os.path.exists(remake_audio_path):
            # Call Replicate
            remake_url = remaker.remake(base_audio_path, style)

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
        # We can do this in parallel, but sequential is safer for now
        metadata = content_gen.generate_metadata(name_no_ext, style=style)
        lyrics = content_gen.generate_lyrics(name_no_ext)

        art_prompt = f"Abstract album art for {metadata.get('title', name_no_ext)}, {style} style, high quality, 4k"
        art_url = content_gen.generate_art(art_prompt)

        # Save metadata to file for reference
        metadata_path = os.path.join(output_dir, f"{name_no_ext}_metadata.json")
        with open(metadata_path, "w") as f:
            metadata["lyrics"] = lyrics # Add lyrics to saved metadata
            json.dump(metadata, f, indent=4)

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
        video_producer.create_video(remake_audio_path, art_url, video_path, lyrics=lyrics, video_format=video_format)

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
=======
    import concurrent.futures

    # [CONCURRENCY LIMITS EXPLAINED]
    # We use ThreadPoolExecutor to process multiple MIDI files simultaneously.
    # We cap `max_workers` to 4 globally across the project to prevent Replicate, OpenAI, and ElevenLabs
    # API endpoints from hitting Too Many Requests (429) rate limit errors, and to prevent ffmpeg/fluidsynth
    # from entirely starving local CPU cores, especially if deployed in constrained Docker environments.
    max_workers = min(4, len(midi_files))

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
                video_producer
            ): midi_path for midi_path in midi_files
        }

        for future in concurrent.futures.as_completed(futures):
            midi_path = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error processing {midi_path} through executor: {e}")

def process_single_midi(
    midi_path, output_dir, style, skip_render, skip_remake, upload,
    renderer, remaker, content_gen, video_producer, tts_generator=None,
    normalize_audio=True, fade_in_ms=0, fade_out_ms=0, generate_vocals=False, use_visualizer=False,
    use_dynamic_prompt=False, s3_bucket=None, webhook_url=None, status_callback=None
):
    try:
        filename = os.path.basename(midi_path)
        name_no_ext = os.path.splitext(filename)[0]

        def update_status(msg, progress):
            logger.info(msg)
            if status_callback:
                status_callback(msg, progress)

        update_status(f"Processing {filename}...", 10)

        # 0. Pre-Process: Analyze MIDI and Generate Dynamic Prompt
        final_prompt = style
        if use_dynamic_prompt:
            update_status(f"Analyzing MIDI structure & generating dynamic AI prompt ({filename})...", 15)
            midi_metrics = MidiAnalyzer.analyze_file(midi_path)

            try:
                final_prompt = content_gen.generate_dynamic_prompt(
                    name_no_ext,
                    style,
                    bpm=midi_metrics.get("bpm"),
                    time_signature=midi_metrics.get("time_signature")
                )
                logger.info(f"Replaced generic style '{style}' with dynamic prompt: '{final_prompt}'")
            except Exception as e:
                logger.error(f"Failed to generate dynamic prompt, falling back to generic style: {e}")

        # 1. Render MIDI to Audio (WAV)
        update_status(f"Step 1/4: Rendering MIDI ({filename})...", 20)
        base_audio_path = os.path.join(output_dir, f"{name_no_ext}_base.wav")
        if not skip_render or not os.path.exists(base_audio_path):
            renderer.render(midi_path, base_audio_path)
        else:
            update_status(f"Skipping render for {filename}, {base_audio_path} exists.", 30)

        # 2. Generate Remake (MusicGen)
        update_status(f"Step 2/4: Remaking Audio via Replicate ({filename})...", 40)
        remake_audio_path = os.path.join(output_dir, f"{name_no_ext}_remake.wav")

        if not skip_remake or not os.path.exists(remake_audio_path):
            # Call Replicate
            remake_url = remaker.remake(base_audio_path, final_prompt)

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
        # We can do this in parallel, but sequential is safer for now
        metadata = content_gen.generate_metadata(name_no_ext, style=style) # Metadata prompt stays original style so titles aren't crazy long
        lyrics = content_gen.generate_lyrics(name_no_ext)

        art_prompt = f"Abstract album art for {metadata.get('title', name_no_ext)}, {style} style, high quality, 4k"
        art_url = content_gen.generate_art(art_prompt)

        # Save metadata to file for reference
        metadata_path = os.path.join(output_dir, f"{name_no_ext}_metadata.json")
        with open(metadata_path, "w") as f:
            metadata["lyrics"] = lyrics # Add lyrics to saved metadata
            metadata["ai_generation_prompt"] = final_prompt # Log what was actually fed to Replicate
            json.dump(metadata, f, indent=4)

        # Optional: Generate Vocals via ElevenLabs
        vocal_track_path = None
        if generate_vocals and tts_generator and lyrics:
            update_status(f"Step 3.5/4: Generating Vocals via ElevenLabs ({filename})...", 70)
            vocal_track_path = os.path.join(output_dir, f"{name_no_ext}_vocals.wav")
            try:
                # Pass the update_status callback deep into the generator so the UI ticks up per lyric line
                tts_generator.generate_vocals(lyrics, vocal_track_path, status_callback=update_status)
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
        video_producer.create_video(remake_audio_path, art_url, video_path, lyrics=lyrics, use_visualizer=use_visualizer)

        # 5. Upload to YouTube (Optional)
        youtube_url = None
        if upload:
            update_status(f"Uploading {filename} to YouTube...", 90)
            video_id = video_producer.upload_to_youtube(video_path, metadata)
            youtube_url = f"https://youtu.be/{video_id}"
            update_status(f"Video uploaded: {youtube_url}", 92)

        # 6. Upload to AWS S3 (Optional)
        s3_video_url = None
        s3_audio_url = None
        if s3_bucket:
            update_status(f"Uploading {filename} to AWS S3 ({s3_bucket})...", 94)
            s3_uploader = S3Uploader()
            # Upload Video
            s3_video_url = s3_uploader.upload_file(video_path, s3_bucket)
            # Upload Audio
            s3_audio_url = s3_uploader.upload_file(remake_audio_path, s3_bucket)
            # Upload Metadata
            s3_uploader.upload_file(metadata_path, s3_bucket)
            update_status(f"S3 Upload Complete.", 96)

        # 7. Send Webhook Notification (Optional)
        if webhook_url:
            update_status(f"Sending Webhook Notification for {filename}...", 98)
            notifier = WebhookNotifier(webhook_url=webhook_url)
            title = f"🎵 New Hymn Generated: {metadata.get('title', name_no_ext)}"
            desc = metadata.get('description', f"A new {style} remake of {name_no_ext} has finished processing.")
            notifier.send_notification(title, desc, s3_video_url=s3_video_url, youtube_url=youtube_url, s3_audio_url=s3_audio_url, style=style)
            update_status(f"Webhook Sent.", 99)

        update_status(f"Finished processing {filename}", 100)

        # 8. Add to SQLite History DB
        try:
            add_history(
                hymn_name=name_no_ext,
                style=style,
                video_path=video_path,
                audio_path=remake_audio_path,
                metadata_path=metadata_path,
                remote_video_url=s3_video_url,
                remote_audio_url=s3_audio_url
            )
        except Exception as db_err:
            logger.error(f"Failed to record history to SQLite: {db_err}")

    except Exception as e:
        logger.error(f"Error processing {midi_path}: {e}")
>>>>>>> origin/feature/web-ui-and-parallelization-5540056130352860192
        raise e

if __name__ == "__main__":
    main()
