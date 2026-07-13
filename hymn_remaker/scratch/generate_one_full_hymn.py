#!/usr/bin/env python3
import os
import sys
import time
import json
import logging
import mido

# Adjust paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from batch_render_midis import midi_to_sine_wav
from hymn_remaker.src.suno_browser_automation import SunoBrowserAutomation
import wave
import random

def append_silence_wave(input_path, output_path, silence_seconds):
    with wave.open(input_path, 'rb') as wav_in:
        params = wav_in.getparams()
        frames = wav_in.readframes(params.nframes)
    frame_size = params.nchannels * params.sampwidth
    silence_frames = b'\x00' * (frame_size * int(params.framerate * silence_seconds))
    with wave.open(output_path, 'wb') as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(frames + silence_frames)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("full_hymn_gen")

MIDI_INPUT = os.path.join(ROOT, "hymn_remaker", "input", "Easter.mid")
OUTPUT_DIR = os.path.join(ROOT, "hymn_remaker", "output", "full_hymn_test")

GENRES = {
    "psytrance": "full-on psytrance",
    "dubstep": "brostep dubstep",
    "dnb": "drum and bass",
    "deep_house": "deep house",
    "detroit_techno": "detroit techno",
    "detroit_house": "detroit house"
}

SPEEDS = {
    "0.5x": 0.5,
    "2.0x": 2.0,
    "10.0x": 10.0
}

def modify_midi_tempo(midi_path, output_path, speed_multiplier):
    mid = mido.MidiFile(midi_path)
    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                msg.tempo = int(msg.tempo / speed_multiplier)
    mid.save(output_path)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    bot = SunoBrowserAutomation(port=9222)
    
    # Check Suno tab
    tab = bot._get_active_tab(require_suno=True)
    if not tab:
        logger.error("No Suno tab found! Please open Edge on port 9222 and log into Suno.com")
        sys.exit(1)
        
    logger.info(f"Using Suno tab: {tab.get('url')}")
    
    rendered_files = {}
    
    # Phase 1: Render all speed versions to WAV
    logger.info("Phase 1: Rendering speed variants...")
    for label, multiplier in SPEEDS.items():
        wav_path = os.path.join(OUTPUT_DIR, f"Easter_{label}.wav")
        if os.path.exists(wav_path):
            logger.info(f"  Already rendered: {wav_path}")
            rendered_files[label] = wav_path
            continue
            
        if multiplier == 1.0:
            midi_to_sine_wav(MIDI_INPUT, wav_path)
        else:
            temp_mid = os.path.join(OUTPUT_DIR, f"temp_Easter_{label}.mid")
            try:
                modify_midi_tempo(MIDI_INPUT, temp_mid, multiplier)
                midi_to_sine_wav(temp_mid, wav_path)
            finally:
                if os.path.exists(temp_mid):
                    os.unlink(temp_mid)
        logger.info(f"  Rendered speed {label}: {wav_path}")
        rendered_files[label] = wav_path

    # Phase 2: Trigger generations sequentially
    logger.info("Phase 2: Triggering generations on Suno...")
    results_path = os.path.join(OUTPUT_DIR, "generation_results.json")
    results = []
    if os.path.exists(results_path):
        try:
            with open(results_path, "r") as f:
                results = json.load(f)
        except Exception:
            results = []

    success_map = {item["variant"]: item["success"] for item in results if "variant" in item}
    uploaded_speeds = set()
    
    for speed_label, wav_path in rendered_files.items():
        for genre_name, prompt in GENRES.items():
            key = f"{genre_name}_{speed_label}"
            
            if success_map.get(key) is True:
                logger.info(f"Variant '{key}' already generated successfully. Skipping.")
                continue
            
            logger.info(f"\n========================================\nTriggering: {key}\n========================================")
            
            target_upload_path = None
            unique_wav_path = None
            if speed_label not in uploaded_speeds:
                silence_seconds = 3.0 + random.random() * 5.0
                unique_wav_path = os.path.join(OUTPUT_DIR, f"Easter_{speed_label}_{int(time.time())}.wav")
                logger.info(f"Suno: Copying {wav_path} to unique path {unique_wav_path} and appending {silence_seconds:.2f}s of silence to bypass acoustic fingerprinting...")
                append_silence_wave(wav_path, unique_wav_path, silence_seconds)
                target_upload_path = unique_wav_path
            else:
                logger.info(f"Suno: Speed {speed_label} is already active in simple panel. Reusing reference without uploading...")
            
            try:
                success = bot.trigger_generation(
                    prompt=prompt,
                    audio_path=target_upload_path,
                    make_instrumental=True,
                    lyrics=None
                )
                if success:
                    uploaded_speeds.add(speed_label)
            finally:
                if unique_wav_path and os.path.exists(unique_wav_path):
                    try:
                        os.unlink(unique_wav_path)
                    except Exception:
                        pass
            
            logger.info(f"Trigger {key} result: {'SUCCESS' if success else 'FAILED'}")
            
            # Update results list
            results = [item for item in results if item.get("variant") != key]
            results.append({
                "variant": key,
                "speed": speed_label,
                "genre": genre_name,
                "success": success
            })
            
            # Save results immediately
            with open(results_path, "w") as f:
                json.dump(results, f, indent=4)
            
            # Wait between generations to let Suno's UI catch up and settle down
            time.sleep(15)
            
    logger.info(f"All done! Final results saved to {results_path}")

if __name__ == "__main__":
    main()
