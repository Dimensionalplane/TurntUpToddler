#!/usr/bin/env python
"""
Batch Suno Pipeline: Process multiple MIDIs through the full pipeline
MIDI -> WAV -> Speed Variants -> MP3 -> Suno API -> Download

Usage:
    # Single song
    python scripts/batch_suno_pipeline.py test_input/Emmanuel.mid
    
    # Batch all MIDIs in a directory
    python scripts/batch_suno_pipeline.py test_input/ --batch
    
    # With custom prompt and lyrics
    python scripts/batch_suno_pipeline.py test_input/Emmanuel.mid -p "Deep house, 124 BPM" -l lyrics.txt
    
    # Render only (skip Suno)
    python scripts/batch_suno_pipeline.py test_input/Emmanuel.mid --render-only
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
import subprocess
from pathlib import Path

sys.path.insert(0, os.getcwd())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("BatchSuno")


# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def get_suno_tokens_from_edge():
    """Extract Suno auth tokens from Edge CDP."""
    try:
        r = requests.get("http://127.0.0.1:9222/json", timeout=3)
        targets = r.json()
        suno_tabs = [t for t in targets if t.get('type') == 'page' and 'suno.com' in t.get('url', '').lower()]
        if not suno_tabs:
            logger.error("No Suno tab found in Edge. Open suno.com/create and log in.")
            return None, None
        tab = suno_tabs[0]
        ws_url = tab['webSocketDebuggerUrl'].replace('localhost', '127.0.0.1')
        import websocket
        ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=15)
        ws.send(json.dumps({'id': 1, 'method': 'Network.enable'})); ws.recv()
        ws.send(json.dumps({'id': 2, 'method': 'Network.getAllCookies'}))
        for _ in range(30):
            resp = json.loads(ws.recv())
            if resp.get('id') == 2:
                cookies = resp.get('result', {}).get('cookies', [])
                ws.close()
                session = next((c['value'] for c in cookies if c['name'] == '__session'), None)
                client = next((c['value'] for c in cookies if c['name'] == '__client'), None)
                return session, client
        ws.close()
    except Exception as e:
        logger.warning(f"Could not extract tokens: {e}")
    return None, None


def render_midi_to_wav(midi_path, output_wav):
    """Render MIDI to WAV using Python fallback."""
    import numpy as np
    from scipy.io import wavfile

    try:
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(str(midi_path))
        duration = pm.get_end_time()
    except Exception:
        import mido
        mid = mido.MidiFile(str(midi_path))
        duration = mid.length
        pm = pretty_midi.PrettyMIDI(initial_tempo=120.0)
        for i, track in enumerate(mid.tracks):
            inst = pretty_midi.Instrument(program=0, name=f"Track {i}")
            tick_time = 0
            for msg in track:
                tick_time += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    note = pretty_midi.Note(
                        velocity=msg.velocity, pitch=msg.note,
                        start=mid.tick_to_time(tick_time),
                        end=mid.tick_to_time(tick_time + 120),
                    )
                    inst.notes.append(note)
            if inst.notes:
                pm.instruments.append(inst)

    if duration <= 0:
        duration = 4.0

    sr = 44100
    audio = np.zeros(int(sr * duration), dtype=np.float32)
    for inst in pm.instruments:
        for note in inst.notes:
            start = int(note.start * sr)
            end = int(note.end * sr)
            if start >= len(audio):
                continue
            freq = 440 * (2 ** ((note.pitch - 69) / 12))
            t = np.arange(min(end, len(audio)) - start) / sr
            env = np.exp(-5 * t)
            sine = np.sin(2 * np.pi * freq * t) * (note.velocity / 127.0) * 0.3 * env
            audio[start:start + len(sine)] += sine

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9

    os.makedirs(os.path.dirname(output_wav) or '.', exist_ok=True)
    wavfile.write(output_wav, sr, (audio * 32767).astype(np.int16))
    size_kb = os.path.getsize(output_wav) / 1024
    return output_wav, size_kb


def export_speed_variants(audio, sr, output_base):
    """Export 0.5x, 1x, 2x, 4x speed variants."""
    import numpy as np
    from scipy.io import wavfile
    paths = {}
    variants = {
        "05x": lambda a: a[np.clip(np.arange(0, len(a), 0.5), 0, len(a)-1).astype(np.int64)],
        "1x": lambda a: a,
        "2x": lambda a: a[::2],
        "4x": lambda a: a[::4],
    }
    for name, func in variants.items():
        p = f"{output_base}_{name}.wav"
        wavfile.write(p, sr, (func(audio) * 32767).astype(np.int16))
        paths[name] = p
    return paths


def convert_to_mp3(wav_path):
    """Convert WAV to MP3 via ffmpeg."""
    mp3_path = wav_path.rsplit(".wav", 1)[0] + ".mp3"
    if os.path.exists(mp3_path):
        return mp3_path
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "192k", mp3_path],
        capture_output=True, timeout=60
    )
    return mp3_path


def download_from_cdn(clip_id, output_path, max_retries=60, delay=10):
    """Download a Suno clip from CDN, retrying until available."""
    if os.path.exists(output_path):
        logger.info(f"  Already downloaded: {output_path}")
        return True
        
    url = f"https://cdn1.suno.ai/{clip_id}.mp3"
    logger.info(f"  Waiting for CDN: {clip_id[:8]}...")
    
    for attempt in range(max_retries):
        try:
            r = requests.head(url, timeout=10,
                             headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                r2 = requests.get(url, stream=True, timeout=30,
                                 headers={'User-Agent': 'Mozilla/5.0'})
                with open(output_path, 'wb') as f:
                    for chunk in r2.iter_content(8192):
                        f.write(chunk)
                size = os.path.getsize(output_path)
                logger.info(f"  Downloaded: {output_path} ({size/1024:.0f} KB)")
                return True
        except Exception:
            pass
        
        if attempt % 6 == 0:
            logger.info(f"  Waiting for CDN... ({attempt*delay}s)")
        time.sleep(delay)
    
    return False


def submit_suno_generation(session, client, mp3_path, prompt, hymn_name,
                          make_instrumental=True, lyrics=None, tags=None):
    """Full Suno flow: upload audio -> generate -> wait -> download CDN."""
    from hymn_remaker.src.suno_api import SunoAPIClient
    
    api = SunoAPIClient(session_token=session, client_token=client)
    
    # Step 1: Check session
    try:
        api.get_session_info()
    except Exception as e:
        logger.error(f"Session invalid: {e}")
        return None
    
    # Step 2: Upload audio
    audio_influence_id = None
    if mp3_path and os.path.exists(mp3_path):
        logger.info(f"  Uploading audio: {os.path.basename(mp3_path)}")
        try:
            upload_info = api.upload_audio(mp3_path)
            if upload_info:
                audio_influence_id = upload_info.get("id")
                logger.info(f"  Audio upload successful! ID: {audio_influence_id}")
            else:
                logger.warning("  Audio upload returned no ID")
        except Exception as e:
            logger.warning(f"  Audio upload failed: {e}")
    
    # Step 3: Generate songs
    full_prompt = prompt or (
        f"Create a deep house version inspired by this hymn melody. "
        f"Transform it into a club-ready track with "
        f"four-on-the-floor kick, deep bass, atmospheric pads, "
        f"and subtle references to the original hymn's melody."
    )
    
    logger.info(f"  Submitting generation...")
    logger.info(f"    Prompt: {full_prompt[:60]}...")
    logger.info(f"    Audio influence: {audio_influence_id or 'none'}")
    logger.info(f"    Instrumental: {make_instrumental}")
    
    try:
        clips = api.generate_songs(
            prompt=full_prompt,
            make_instrumental=make_instrumental,
            tags=tags or "deep house, electronic, club",
            title=f"{hymn_name} (Deep House Remix)",
            audio_influence_id=audio_influence_id,
        )
    except Exception as e:
        logger.error(f"  Generation submission failed: {e}")
        return None
    
    if not clips:
        logger.error("  No clips returned")
        return None
    
    # Get clip IDs
    clip_ids = []
    if isinstance(clips, list):
        clip_ids = [c.get("id") for c in clips if c.get("id")]
    elif isinstance(clips, dict):
        clip_ids = [clips.get("id")] if clips.get("id") else []
    
    if not clip_ids:
        logger.error("  No clip IDs in response")
        return None
    
    logger.info(f"  Generation submitted! Clip IDs: {clip_ids}")
    logger.info(f"  Waiting for CDN availability (up to 5 min)...")
    
    # Step 4: Wait and download from CDN (don't wait for processing to complete)
    output_dir = os.path.dirname(mp3_path)
    downloaded = []
    
    for cid in clip_ids:
        out_path = os.path.join(output_dir, f"{hymn_name}_remake_{cid[:8]}.mp3")
        success = download_from_cdn(cid, out_path, max_retries=60, delay=10)
        if success:
            downloaded.append(out_path)
    
    # Step 5: If CDN fails, check audio_url from the API response clips
    if not downloaded:
        for clip in (clips if isinstance(clips, list) else [clips]):
            audio_url = clip.get("audio_url") if isinstance(clip, dict) else None
            if audio_url:
                try:
                    out_path = os.path.join(output_dir, f"{hymn_name}_remake.mp3")
                    r = requests.get(audio_url, stream=True, timeout=30)
                    if r.status_code == 200:
                        with open(out_path, 'wb') as f:
                            for chunk in r.iter_content(8192):
                                f.write(chunk)
                        logger.info(f"  Downloaded from audio_url: {out_path}")
                        downloaded.append(out_path)
                except:
                    pass
    
    if downloaded:
        logger.info(f"  Downloaded {len(downloaded)} clip(s): {downloaded}")
        return downloaded[0]  # Return first clip for compatibility
    
    logger.warning(f"  Clips not found on CDN yet. Check Suno UI for '{hymn_name}'")
    return None


# =====================================================================
# MAIN PIPELINE
# =====================================================================

def process_single_midi(midi_path, output_dir, session=None, client=None,
                        prompt=None, lyrics=None, render_only=False,
                        variant="1x", make_instrumental=True):
    """Process a single MIDI through the full pipeline."""
    hymn_name = Path(midi_path).stem
    out_dir = Path(output_dir) / hymn_name
    os.makedirs(out_dir, exist_ok=True)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {hymn_name}")
    logger.info(f"{'='*60}")
    
    # Step 1: Render MIDI to WAV
    logger.info(f"[1/5] Rendering MIDI -> WAV...")
    base_wav = str(out_dir / f"{hymn_name}_base.wav")
    wav_path, size_kb = render_midi_to_wav(midi_path, base_wav)
    logger.info(f"  {base_wav} ({size_kb:.0f} KB)")
    
    # Step 2: Export speed variants
    logger.info(f"[2/5] Exporting speed variants...")
    import numpy as np
    from scipy.io import wavfile
    sr, audio = wavfile.read(base_wav)
    audio = audio.astype(np.float32) / 32767.0
    variant_paths = export_speed_variants(audio, sr, str(out_dir / hymn_name))
    for name, path in variant_paths.items():
        logger.info(f"  {name}: {path} ({os.path.getsize(path)/1024:.0f} KB)")
    
    # Step 3: Convert selected variant to MP3
    logger.info(f"[3/5] Converting to MP3...")
    mp3_path = convert_to_mp3(variant_paths[variant])
    logger.info(f"  {mp3_path} ({os.path.getsize(mp3_path)/1024:.0f} KB)")
    
    if render_only:
        logger.info(f"[SKIP] Render only mode. Skipping Suno.")
        return {"name": hymn_name, "status": "rendered", "dir": str(out_dir)}
    
    # Step 4: Submit to Suno
    logger.info(f"[4/5] Submitting to Suno...")
    if not session:
        logger.error("  No Suno session token. Use --render-only or launch Edge with CDP.")
        return {"name": hymn_name, "status": "error", "error": "No session token"}
    
    result = submit_suno_generation(
        session=session,
        client=client,
        mp3_path=mp3_path,
        prompt=prompt,
        hymn_name=hymn_name,
        make_instrumental=make_instrumental or (lyrics is None),
        lyrics=lyrics,
    )
    
    if result:
        logger.info(f"[5/5] DOWNLOADED: {result}")
        return {"name": hymn_name, "status": "success", "file": result, "dir": str(out_dir)}
    else:
        logger.warning(f"[5/5] Download pending - check Suno UI manually")
        return {"name": hymn_name, "status": "pending", "dir": str(out_dir)}


def main():
    parser = argparse.ArgumentParser(description="Batch Suno Pipeline")
    parser.add_argument("input", help="MIDI file or directory")
    parser.add_argument("--batch", "-b", action="store_true", help="Process all MIDIs in directory")
    parser.add_argument("--output-dir", "-o", default="output_batch_suno", help="Output directory")
    parser.add_argument("--prompt", "-p", help="Style prompt for Suno")
    parser.add_argument("--lyrics", "-l", help="Lyrics text file")
    parser.add_argument("--variant", default="1x", choices=["05x", "1x", "2x", "4x"])
    parser.add_argument("--render-only", action="store_true", help="Skip Suno, just render")
    parser.add_argument("--instrumental", action="store_true", default=None,
                        help="Force instrumental (default: auto based on lyrics)")
    parser.add_argument("--delay", type=int, default=30,
                        help="Delay between batch items (seconds)")
    parser.add_argument("--max", type=int, default=0,
                        help="Max MIDIs to process (0 = all)")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    # Collect MIDI files
    if args.batch or input_path.is_dir():
        search_dir = input_path if input_path.is_dir() else input_path.parent
        midi_files = sorted(search_dir.glob("*.mid*"))
        if not midi_files:
            logger.error(f"No MIDI files found in {search_dir}")
            sys.exit(1)
        if args.max > 0:
            midi_files = midi_files[:args.max]
        logger.info(f"Found {len(midi_files)} MIDI files in {search_dir}")
    else:
        if not input_path.exists():
            logger.error(f"MIDI file not found: {input_path}")
            sys.exit(1)
        midi_files = [input_path]
    
    # Load lyrics
    lyrics = None
    if args.lyrics:
        with open(args.lyrics, "r", encoding="utf-8") as f:
            lyrics = f.read().strip()
    
    # Get Suno tokens
    session = client = None
    if not args.render_only:
        logger.info("Connecting to Edge for Suno tokens...")
        session, client = get_suno_tokens_from_edge()
        if not session:
            logger.warning("Could not get Suno tokens. Use --render-only or launch Edge with CDP.")
    
    # Process each MIDI
    results = []
    for i, midi_path in enumerate(midi_files):
        if midi_path.suffix.lower() not in ('.mid', '.midi'):
            continue
        
        logger.info(f"\n--- [{i+1}/{len(midi_files)}] {midi_path.name} ---")
        
        result = process_single_midi(
            midi_path=midi_path,
            output_dir=args.output_dir,
            session=session,
            client=client,
            prompt=args.prompt,
            lyrics=lyrics,
            render_only=args.render_only,
            variant=args.variant,
            make_instrumental=args.instrumental if args.instrumental is not None else (lyrics is None),
        )
        results.append(result)
        
        # Delay between items (for batch mode)
        if i < len(midi_files) - 1 and args.delay > 0 and not args.render_only:
            logger.info(f"Waiting {args.delay}s before next item...")
            time.sleep(args.delay)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("BATCH PIPELINE COMPLETE")
    logger.info(f"{'='*60}")
    
    success = [r for r in results if r.get("status") == "success"]
    rendered = [r for r in results if r.get("status") == "rendered"]
    pending = [r for r in results if r.get("status") == "pending"]
    errors = [r for r in results if r.get("status") == "error"]
    
    if success:
        logger.info(f"Downloaded: {len(success)}")
        for r in success:
            logger.info(f"  {r['name']}: {r['file']}")
    if rendered:
        logger.info(f"Rendered (Suno skipped): {len(rendered)}")
    if pending:
        logger.info(f"Pending (check Suno UI): {len(pending)}")
        for r in pending:
            logger.info(f"  {r['name']}")
    if errors:
        logger.info(f"Errors: {len(errors)}")
        for r in errors:
            logger.info(f"  {r['name']}: {r.get('error', '?')}")


if __name__ == "__main__":
    main()
