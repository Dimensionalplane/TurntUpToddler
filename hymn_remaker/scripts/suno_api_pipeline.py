#!/usr/bin/env python
"""
Suno API Pipeline: MIDI -> WAV -> Speed Variants -> MP3 -> Suno API -> Download

Uses the Suno API directly instead of browser automation.
Much more reliable than CDP-based browser manipulation.

Usage:
    python scripts/suno_api_pipeline.py <midi_path> [--lyrics <lyrics.txt>] [--prompt "style"]
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path

sys.path.insert(0, os.getcwd())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("SunoAPI")


def extract_suno_tokens_from_edge():
    """Extract Suno auth tokens from Edge browser cookies via CDP."""
    import requests as req

    try:
        r = req.get("http://127.0.0.1:9222/json", timeout=3)
        targets = r.json()
        suno_tabs = [t for t in targets if t.get('type') == 'page' and 'suno.com' in t.get('url', '').lower()]
        if not suno_tabs:
            raise RuntimeError("No Suno tab found in Edge")

        tab = suno_tabs[0]
        ws_url = tab.get('webSocketDebuggerUrl', '').replace('localhost', '127.0.0.1')

        import websocket
        ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=15)
        ws.send(json.dumps({'id': 1, 'method': 'Network.enable'}))
        ws.recv()
        ws.send(json.dumps({'id': 2, 'method': 'Network.getAllCookies'}))
        cookies = None
        for _ in range(30):
            resp = json.loads(ws.recv())
            if resp.get('id') == 2:
                cookies = resp.get('result', {}).get('cookies', [])
                break
        ws.close()

        session_token = None
        client_token = None
        for c in cookies:
            if c.get('name') == '__session':
                session_token = c.get('value')
            elif c.get('name') == '__client':
                client_token = c.get('value')

        if session_token:
            logger.info("Extracted Suno session token from Edge")
        if client_token:
            logger.info("Extracted Suno client token from Edge")

        return session_token, client_token

    except Exception as e:
        logger.warning(f"Could not extract tokens from Edge: {e}")
        return None, None


def render_midi_to_wav(midi_path, output_wav):
    """Render MIDI to WAV using Python fallback."""
    import numpy as np
    from scipy.io import wavfile

    logger.info(f"Rendering MIDI -> WAV: {midi_path}")

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
    logger.info(f"  Rendered: {output_wav} ({os.path.getsize(output_wav)/1024:.0f} KB)")
    return audio, sr


def export_speed_variants(audio, sr, output_base):
    """Export 0.5x, 1x, 2x, 4x speed variants."""
    import numpy as np
    from scipy.io import wavfile

    paths = {}
    variants = {
        "1x": lambda a: a,
        "05x": lambda a: a[np.clip(np.arange(0, len(a), 0.5), 0, len(a)-1).astype(np.int64)],
        "2x": lambda a: a[::2],
        "4x": lambda a: a[::4],
    }

    for name, func in variants.items():
        p = f"{output_base}_{name}.wav"
        wavfile.write(p, sr, (func(audio) * 32767).astype(np.int16))
        paths[name] = p
        logger.info(f"  {name}: {p} ({os.path.getsize(p)/1024:.0f} KB)")

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
    logger.info(f"  MP3: {mp3_path} ({os.path.getsize(mp3_path)/1024:.0f} KB)")
    return mp3_path


def main():
    parser = argparse.ArgumentParser(description="Suno API Pipeline")
    parser.add_argument("midi", help="Path to input MIDI file")
    parser.add_argument("--lyrics", "-l", help="Path to lyrics text file")
    parser.add_argument("--prompt", "-p", help="Style prompt for Suno")
    parser.add_argument("--output-dir", "-o", default="output_suno_api", help="Output directory")
    parser.add_argument("--variant", choices=["05x", "1x", "2x", "4x"], default="1x",
                        help="Speed variant to upload")
    parser.add_argument("--render-only", action="store_true", help="Render only, skip Suno")
    args = parser.parse_args()

    midi_path = Path(args.midi)
    if not midi_path.exists():
        logger.error(f"MIDI not found: {midi_path}")
        sys.exit(1)

    hymn_name = midi_path.stem
    output_dir = Path(args.output_dir) / hymn_name
    os.makedirs(output_dir, exist_ok=True)

    # Load lyrics
    lyrics = None
    if args.lyrics:
        with open(args.lyrics, "r", encoding="utf-8") as f:
            lyrics = f.read().strip()
        logger.info(f"Loaded lyrics: {len(lyrics)} chars")

    # Step 1-2: Render + speed variants
    base_wav = str(output_dir / f"{hymn_name}_base.wav")
    audio, sr = render_midi_to_wav(midi_path, base_wav)
    variant_paths = export_speed_variants(audio, sr, str(output_dir / hymn_name))

    # Step 3: Convert selected variant to MP3
    wav_to_upload = variant_paths[args.variant]
    mp3_path = convert_to_mp3(wav_to_upload)

    logger.info(f"\n{'='*60}")
    logger.info(f"Files in: {output_dir}")
    for name, path in variant_paths.items():
        logger.info(f"  {name}: {path} ({os.path.getsize(path)/1024:.0f} KB)")
    logger.info(f"  MP3: {mp3_path} ({os.path.getsize(mp3_path)/1024:.0f} KB)")
    logger.info(f"{'='*60}\n")

    if args.render_only:
        logger.info("Render only. Skipping Suno.")
        return

    # Step 4: Get Suno tokens from Edge
    logger.info("Extracting Suno tokens from Edge...")
    session_token, client_token = extract_suno_tokens_from_edge()
    if not session_token:
        logger.error(
            "Could not get Suno token. Make sure Edge is running with --remote-debugging-port=9222\n"
            "and you're logged into suno.com/create."
        )
        sys.exit(1)

    # Step 5: Use Suno API to upload and generate
    logger.info(f"\n=== Connecting to Suno API ===")
    from hymn_remaker.src.suno_api import SunoAPIClient

    api = SunoAPIClient(session_token=session_token, client_token=client_token)

    # Check session
    try:
        session_info = api.get_session_info()
        logger.info(f"Session: {json.dumps(session_info, indent=2)[:200]}")
    except Exception as e:
        logger.error(f"Session check failed: {e}")
        logger.info("Tokens may be expired. Refresh suno.com and try again.")
        sys.exit(1)

    # Upload audio
    logger.info(f"\nUploading audio: {mp3_path}")
    try:
        upload_result = api.upload_audio(mp3_path)
        audio_influence_id = upload_result.get("id")
        logger.info(f"Audio uploaded! ID: {audio_influence_id}")
    except Exception as e:
        logger.warning(f"Upload failed: {e}")
        logger.info("Upload via API may not be supported. Trying fallback...")
        audio_influence_id = None

    # Build prompt
    full_prompt = args.prompt or (
        f"Create a deep house version inspired by this hymn melody. "
        f"Transform it into a club-ready track with "
        f"four-on-the-floor kick, deep bass, atmospheric pads, "
        f"and subtle references to the original hymn's melody."
    )

    # Generate
    logger.info(f"\nGenerating songs...")
    logger.info(f"  Prompt: {full_prompt[:80]}...")
    logger.info(f"  Instrumental: {lyrics is None}")
    logger.info(f"  Audio influence: {audio_influence_id or 'none'}")

    try:
        clips = api.generate_songs(
            prompt=full_prompt,
            make_instrumental=(lyrics is None),
            tags="deep house, electronic, club",
            title=f"{hymn_name} (Deep House Remix)",
            audio_influence_id=audio_influence_id,
        )
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        sys.exit(1)

    if not clips or len(clips) == 0:
        logger.error("No clips returned from generation")
        sys.exit(1)

    clip_ids = [c.get("id") for c in clips if c.get("id")]
    logger.info(f"Generation submitted! Clip IDs: {clip_ids}")

    # Poll for completion
    logger.info(f"\nPolling for completion (timeout=5min)...")
    completed = api.poll_songs(clip_ids)

    if not completed:
        logger.error("No completed clips")
        sys.exit(1)

    # Filter valid clips
    valid = [c for c in completed if c.get("status") not in ("error", "failed") and c.get("audio_url")]
    if not valid:
        logger.error("All clips failed")
        sys.exit(1)

    # Select best and download
    best = SunoAPIClient.select_best_clip(valid)
    logger.info(f"Best clip: {json.dumps(best, indent=2)[:200]}")

    output_wav = str(output_dir / f"{hymn_name}_remake.wav")
    api.download_audio(best, output_wav)

    if os.path.exists(output_wav):
        logger.info(f"\n{'='*60}")
        logger.info(f"DOWNLOADED: {output_wav}")
        logger.info(f"Size: {os.path.getsize(output_wav)/1024:.0f} KB")
        logger.info(f"{'='*60}")
    else:
        logger.error("Download failed")

    logger.info("\n=== Pipeline Complete ===")


if __name__ == "__main__":
    main()
