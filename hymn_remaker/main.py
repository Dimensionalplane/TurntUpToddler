import os
import sys
import glob
import logging
import argparse
import json
import requests
from dotenv import load_dotenv

# Add the project root to sys.path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.midi_renderer import MidiRenderer
from src.remaker import MusicRemaker
from src.content_generator import ContentGenerator
from src.video_uploader import VideoProducer
from src.tts_generator import TTSGenerator
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

    # Find MIDI files
    midi_files = glob.glob(os.path.join(args.input_dir, "*.mid"))
    if not midi_files:
        logger.warning(f"No MIDI files found in {args.input_dir}")
        sys.exit(0)

    logger.info(f"Found {len(midi_files)} MIDI files to process.")

    import concurrent.futures

    # We use ThreadPoolExecutor to run process_single_midi concurrently for each file
    max_workers = min(4, len(midi_files)) # Adjust this value as needed, but let's stick to max 4 to not overload rate limits

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
                model=args.model
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
    normalize_audio=True, fade_in_ms=0, fade_out_ms=0, generate_vocals=False,
    voice_id="21m00Tcm4TlvDq8ikWAM", model="eleven_multilingual_v2", status_callback=None
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
        video_producer.create_video(remake_audio_path, art_url, video_path, lyrics=lyrics)

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
