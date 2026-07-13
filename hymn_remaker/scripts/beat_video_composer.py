"""BEAT-SYNCED VIDEO COMPOSER
Analyzes audio beat structure, assembles video clips synced to the beat.
Features:
- librosa beat detection for phrase-accurate clip switching
- Random clip selection with variety guarantees (no back-to-back repeats)
- Mix of magnific + music visualizer sources
- ffmpeg-based clip trimming/stretching to fit beat intervals
- Optional crossfade transitions
- Overlay experiments (visualizer on top of magnific)
"""
import os, sys, json, time, subprocess, random, hashlib, glob
import numpy as np
import librosa

ROOT = os.path.dirname(os.path.abspath(__file__))
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

MAGNIFIC_DIR = os.path.join(ROOT, "pipeline_output", "magnific_videos")
VIDEOS_DIR = os.path.join(ROOT, "pipeline_output", "videos")
OUTPUT_DIR = os.path.join(ROOT, "pipeline_output", "beat_videos")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_clip_duration(video_path):
    """Get duration of a video in seconds."""
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        return 10.0


def get_all_video_clips():
    """Get all usable video clips from magnific + videos folders."""
    clips = []
    for folder in [MAGNIFIC_DIR, VIDEOS_DIR]:
        if not os.path.exists(folder):
            continue
        for f in os.listdir(folder):
            if not f.endswith(".mp4"):
                continue
            fp = os.path.join(folder, f)
            sz = os.path.getsize(fp)
            if sz < 50000:  # Skip tiny files
                continue
            dur = get_clip_duration(fp)
            if dur < 0.5:  # Skip ultra-short
                continue
            source = "magnific" if "magnific" in folder else "rendered"
            clips.append({
                "path": os.path.abspath(fp),
                "name": f,
                "duration": dur,
                "source": source,
                "size": sz,
            })
    return clips


def detect_beats(audio_path, min_interval=2.0, max_interval=8.0):
    """Detect beat/onset times in audio. Returns list of beat times in seconds.
    min_interval: minimum time between cuts (avoids hyper-fast switching)
    max_interval: maximum time between cuts (ensures variety)"""
    print(f"  Analyzing audio: {os.path.basename(audio_path)}...")
    y, sr = librosa.load(audio_path, sr=22050)
    duration = len(y) / sr
    print(f"  Duration: {duration:.1f}s, SR: {sr}")

    # Get tempo and beats
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    tempo = float(tempo.item()) if hasattr(tempo, 'item') else float(tempo)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"  Tempo: {tempo:.1f} BPM, {len(beat_times)} beats detected")

    # Group beats into phrases (every 4 or 8 beats for musical cuts)
    phrase_beats = []
    beats_per_phrase = 4 if tempo > 120 else 8  # Faster tempos = shorter phrases
    for i in range(0, len(beat_times), beats_per_phrase):
        phrase_beats.append(beat_times[i])
    if beat_times[-1] > phrase_beats[-1] + 1:
        phrase_beats.append(beat_times[-1])

    # Enforce min/max intervals and add endpoints
    cut_times = [0.0]
    last = 0.0
    for bt in phrase_beats:
        gap = bt - last
        if gap >= min_interval and gap <= max_interval:
            cut_times.append(bt)
            last = bt
        elif gap > max_interval:
            # Insert intermediate cuts
            num = int(gap / max_interval) + 1
            for j in range(1, num):
                cut_times.append(last + j * gap / num)
            last = bt
            cut_times.append(bt)
    if duration - cut_times[-1] > 1:
        cut_times.append(duration)

    print(f"  {len(cut_times)} cut points (avg {duration/len(cut_times):.1f}s per clip)")
    return cut_times, tempo


def select_clips_for_intervals(cut_times, all_clips, hymn_name, genre_name):
    """Select clips for each interval, ensuring no back-to-back repeats."""
    intervals = [(cut_times[i], cut_times[i+1] - cut_times[i])
                 for i in range(len(cut_times) - 1)]

    # Categorize clips by source
    magnific_clips = [c for c in all_clips if c["source"] == "magnific"]
    rendered_clips = [c for c in all_clips if c["source"] == "rendered"]

    if not magnific_clips:
        magnific_clips = all_clips
    if not rendered_clips:
        rendered_clips = all_clips

    # Create a weighted pool: 60% magnific, 40% rendered
    pool = magnific_clips * 6 + rendered_clips * 4
    random.Random(hymn_name + genre_name).shuffle(pool)

    selected = []
    last_clip = None
    clip_idx = 0

    for start, dur in intervals:
        # Pick a clip, avoiding back-to-back repeats
        for _ in range(50):
            candidate = pool[clip_idx % len(pool)]
            clip_idx += 1
            if candidate["name"] != last_clip:
                break

        # Handle clip longer than interval: trim from random position
        candidate_dur = candidate["duration"]
        if candidate_dur >= dur:
            max_start = candidate_dur - dur
            trim_start = random.uniform(0, max_start) if max_start > 0 else 0
        else:
            # Clip shorter than interval: loop or stretch
            trim_start = 0

        selected.append({
            "path": candidate["path"],
            "source": candidate["source"],
            "start_time": start,
            "duration": dur,
            "clip_trim_start": trim_start,
            "clip_duration": candidate_dur,
            "actual_duration": candidate_dur,
            "needs_loop": candidate_dur < dur,
            "name": candidate["name"],
        })
        last_clip = candidate["name"]

    return selected


def build_ffmpeg_filter(segments, audio_path, output_path, tempo):
    """Build ffmpeg filter complex for assembling video."""
    n = len(segments)
    filter_parts = []
    inputs = []

    for i, seg in enumerate(segments):
        fp = seg["path"]
        dur = seg["duration"]
        trim_start = seg["clip_trim_start"]
        actual_dur = seg.get("actual_duration", dur)
        trim_end = min(trim_start + dur, actual_dur)
        if trim_end <= trim_start:
            trim_start = 0
            trim_end = min(dur, actual_dur)
        
        inputs.append(fp)
        filter_parts.append(
            f"[{i}:v]trim={trim_start}:{trim_end},setpts=PTS-STARTPTS,"
            f"scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            f"fps=30,setdar=16/9[v{i}]"
        )

    # Build crossfade chain
    if n <= 1:
        filter_parts.append(f"[v0]null[vout]")
    elif n <= 30:
        # Crossfade transitions: separate filters joined by semicolons
        prev_label = "v0"
        xfades = []
        for i in range(1, n):
            next_label = f"x{i}" if i < n - 1 else "vout"
            fade_dur = min(0.4, min(segments[i]["duration"], segments[i-1]["duration"]) / 3)
            offset = segments[i-1]["duration"] - fade_dur
            xfades.append(
                f"[{prev_label}][v{i}]xfade=transition=fade:"
                f"duration={fade_dur}:offset={offset}[{next_label}]"
            )
            prev_label = next_label
        filter_parts.append(";".join(xfades))
    else:
        # Too many clips for xfade, use concat
        all_v = "".join(f"[v{i}]" for i in range(n))
        filter_parts.append(f"{all_v}concat=n={n}:v=1:a=0[vout]")

    # Build full command
    input_args = []
    for fp in inputs:
        input_args.extend(["-i", fp])
    input_args.extend(["-i", audio_path])

    filter_str = ";".join(filter_parts)
    map_args = ["-map", "[vout]", "-map", f"{n}:a:0", "-shortest"]

    cmd = [FFMPEG, "-y"] + input_args + [
        "-filter_complex", filter_str
    ] + map_args + [
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]

    print(f"  Composing {n} clips ({len(inputs)} inputs)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        err = result.stderr[-500:] if result.stderr else "unknown"
        print(f"  FFMPEG ERROR: {err}")
        return None
    return output_path


def compose_beat_video(audio_path, hymn_name, genre_name):
    """Main function: compose a beat-synced video for an audio track."""
    print(f"\n{'='*60}")
    print(f"Composing: {hymn_name} - {genre_name}")
    print(f"{'='*60}")

    output_path = os.path.join(
        OUTPUT_DIR,
        f"{hymn_name.replace(' ','_')}_{genre_name.replace(' ','_')}_beatsynced.mp4"
    )

    # Step 1: Detect beats
    cut_times, tempo = detect_beats(audio_path)

    # Step 2: Get available clips
    all_clips = get_all_video_clips()
    print(f"  Available clips: {len(all_clips)}")

    if not all_clips:
        print("  No video clips found!")
        return None

    # Step 3: Select clips for each interval
    segments = select_clips_for_intervals(cut_times, all_clips, hymn_name, genre_name)
    print(f"  Selected {len(segments)} clip segments")

    # Step 4: Compose with ffmpeg
    result = build_ffmpeg_filter(segments, audio_path, output_path, tempo)
    if result:
        sz = os.path.getsize(output_path) // 1024 // 1024
        print(f"  Output: {sz}MB -> {output_path}")
    return result


if __name__ == "__main__":
    # Demo: compose a beat-synced video for an existing cover
    import sys

    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        hymn = sys.argv[2] if len(sys.argv) > 2 else "Test"
        genre = sys.argv[3] if len(sys.argv) > 3 else "Demo"
    else:
        # Find a cover to test with
        suno_dir = os.path.join(ROOT, "pipeline_output", "suno_downloads")
        generated_dir = os.path.join(ROOT, "generated")

        covers = []
        for d in [suno_dir, generated_dir]:
            if os.path.exists(d):
                covers.extend(glob.glob(os.path.join(d, "*Cover*.mp3")))
                covers.extend(glob.glob(os.path.join(d, "*_cover*.mp3")))

        if not covers:
            # Fallback to any MP3
            covers = glob.glob(os.path.join(ROOT, "**/*.mp3"), recursive=True)[:1]

        if not covers:
            print("No audio files found!")
            sys.exit(1)

        audio_path = covers[0]
        hymn = os.path.splitext(os.path.basename(audio_path))[0].split("_")[0]
        genre = "Demo"

    print(f"Audio: {audio_path}")
    compose_beat_video(audio_path, hymn, genre)
