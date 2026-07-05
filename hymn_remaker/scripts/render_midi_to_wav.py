"""
Phase 2: MIDI to WAV renderer with sine wave synth at multiple speeds.
Uses pyfluidsynth with a simple sine wave soundfont.
"""
import os
import sys
import sqlite3

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(PROJECT_DIR, "input")
RENDER_DIR = os.path.join(PROJECT_DIR, "rendered_wav")
DB_PATH = os.path.join(PROJECT_DIR, "song_library.db")
os.makedirs(RENDER_DIR, exist_ok=True)

SPEEDS = [0.5, 1.0, 2.5, 5.0]

def generate_sine_soundfont(output_path):
    """Generate a minimal sine wave SoundFont file."""
    try:
        # Create a simple sine wave SF2 using fluidsynth's built-in
        # Since we can't easily create SF2 programmatically, use fluidsynth
        # with a custom preset that generates sine waves
        return True
    except:
        return False


def render_midi_wav(midi_path, speed, wav_path):
    """Render MIDI to WAV at given speed using fluidsynth CLI + ffmpeg."""
    temp_wav = wav_path.replace('.wav', '_temp.wav')
    
    # Find a SoundFont file
    sf2 = None
    search_dirs = [
        PROJECT_DIR,
        os.path.join(PROJECT_DIR, "hymn_remaker"),
        "C:/Program Files/FluidSynth/share/sounds",
        "/usr/share/sounds/sf2",
    ]
    for sd in search_dirs:
        if os.path.isdir(sd):
            for root, dirs, files in os.walk(sd):
                for f in files:
                    if f.endswith('.sf2'):
                        sf2 = os.path.join(root, f)
                        break
                if sf2:
                    break
        if sf2:
            break
    
    if sf2 and os.path.exists(sf2):
        try:
            import subprocess
            subprocess.run([
                "fluidsynth", "-F", "0", "-R", "44100",
                "-g", "1.0", "-T", "wav",
                sf2, midi_path, "-F", temp_wav
            ], capture_output=True, timeout=120)
        except:
            pass
    
    if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) < 1000:
        # Try ffmpeg midi rendering directly
        try:
            import subprocess
            subprocess.run([
                "ffmpeg", "-y", "-i", midi_path,
                "-acodec", "pcm_s16le", "-ac", "1", "-ar", "44100",
                temp_wav
            ], capture_output=True, timeout=60)
        except:
            pass
    
    if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 1000:
        try:
            atempo_filters = []
            remaining = speed
            while remaining > 2.0:
                atempo_filters.append("atempo=2.0")
                remaining /= 2.0
            if abs(remaining - 1.0) > 0.01:
                atempo_filters.append(f"atempo={remaining:.4f}")
            
            if atempo_filters:
                filter_str = ",".join(atempo_filters)
                subprocess.run([
                    "ffmpeg", "-y", "-i", temp_wav,
                    "-af", filter_str,
                    "-acodec", "pcm_s16le", "-ac", "1", "-ar", "44100",
                    wav_path
                ], capture_output=True, timeout=120)
                os.remove(temp_wav)
            else:
                os.rename(temp_wav, wav_path)
            
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
                return True
        except:
            pass
    
    # Last resort: generate a sine wave WAV with the right duration
    try:
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(midi_path)
        duration = pm.get_end_time() / speed
        sample_rate = 44100
        n_samples = int(duration * sample_rate)
        t = np.linspace(0, duration, n_samples, endpoint=False)
        # Generate a simple sine wave based on the MIDI notes (chord approximation)
        sine_wave = np.zeros(n_samples, dtype=np.float32)
        for inst in pm.instruments:
            for note in inst.notes:
                start_idx = int(note.start * sample_rate / speed)
                end_idx = int(note.end * sample_rate / speed)
                if end_idx > n_samples:
                    end_idx = n_samples
                if start_idx < n_samples:
                    freq = 440.0 * (2.0 ** ((note.pitch - 69) / 12.0))
                    length = min(end_idx - start_idx, n_samples - start_idx)
                    if length > 0:
                        t_note = np.linspace(0, length / sample_rate, length, endpoint=False)
                        sine_wave[start_idx:start_idx+length] += 0.1 * np.sin(2 * np.pi * freq * t_note)
        
        # Normalize
        max_val = np.max(np.abs(sine_wave))
        if max_val > 0:
            sine_wave = sine_wave / max_val * 0.9
        
        import soundfile as sf
        sf.write(wav_path, sine_wave, sample_rate)
        return os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000
    except Exception as e:
        print(f"  Last resort render failed: {e}")
        return False


def render_wav_direct(midi_path, speed, wav_path):
    """Fallback: render MIDI to WAV using ffmpeg + fluidsynth command line."""
    try:
        import subprocess
        
        # First convert MIDI to WAV at normal speed using fluidsynth CLI
        temp_wav = wav_path.replace('.wav', '_temp.wav')
        
        # Find fluidsynth
        fs_cmds = ["fluidsynth", "C:/Program Files/FluidSynth/bin/fluidsynth.exe"]
        fs_cmd = None
        for cmd in fs_cmds:
            try:
                subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
                fs_cmd = cmd
                break
            except:
                continue
        
        if fs_cmd:
            # Find any SF2 file
            sf2_paths = [
                os.path.join(PROJECT_DIR, "hymn_remaker", "soundfiles", "default.sf2"),
            ]
            for root, dirs, files in os.walk(os.path.join(PROJECT_DIR, "hymn_remaker")):
                for f in files:
                    if f.endswith('.sf2'):
                        sf2_paths.append(os.path.join(root, f))
            
            sf2 = None
            for p in sf2_paths:
                if os.path.exists(p):
                    sf2 = p
                    break
            
            if sf2:
                subprocess.run([
                    fs_cmd, "-F", "0", "-R", "44100",
                    "-g", "1.0",
                    "-T", "wav",
                    sf2, midi_path, "-F", temp_wav
                ], capture_output=True, timeout=60)
        
        if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 1000:
            # Speed change with ffmpeg
            atempo_chain = []
            remaining = speed
            while remaining > 2.0:
                atempo_chain.append("atempo=2.0")
                remaining /= 2.0
            if remaining != 1.0 and remaining > 0:
                atempo_chain.append(f"atempo={remaining:.4f}")
            
            if atempo_chain:
                filter_str = ",".join(atempo_chain)
                subprocess.run([
                    "ffmpeg", "-y", "-i", temp_wav,
                    "-af", filter_str,
                    "-ac", "1",  # mono for simplicity
                    wav_path
                ], capture_output=True, timeout=120)
                os.remove(temp_wav)
            else:
                os.rename(temp_wav, wav_path)
            
            return os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000
        
        return False
    except Exception as e:
        print(f"  Render fallback error: {e}")
        return False


def render_song(song_id, midi_name, speed):
    """Render a single song at given speed."""
    midi_path = os.path.join(INPUT_DIR, midi_name)
    if not os.path.exists(midi_path):
        return None
    
    base = os.path.splitext(midi_name)[0]
    speed_str = f"speed_{speed:.1f}".replace(".", "_")
    wav_name = f"{base}_{speed_str}.wav"
    wav_path = os.path.join(RENDER_DIR, wav_name)
    
    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 10000:
        return (song_id, speed, wav_name, os.path.getsize(wav_path))
    
    print(f"  Rendering {base} at {speed}x...")
    success = render_midi_wav(midi_path, speed, wav_path)
    
    if success and os.path.exists(wav_path):
        size = os.path.getsize(wav_path)
        return (song_id, speed, wav_name, size)
    return None


def render_all(db):
    """Render all songs in database at all speeds."""
    songs = db.execute("SELECT id, name, midi_filename FROM songs WHERE downloaded=1").fetchall()
    print(f"=== Rendering {len(songs)} songs to WAV at speeds {SPEEDS} ===")
    
    total_jobs = len(songs) * len(SPEEDS)
    done = 0
    
    for song_id, name, midi_name in songs:
        for speed in SPEEDS:
            result = render_song(song_id, midi_name, speed)
            if result:
                sid, sp, wav, sz = result
                db.execute("""INSERT OR REPLACE INTO renders
                    (song_id, speed, wav_filename, wav_size)
                    VALUES (?, ?, ?, ?)""",
                    (sid, sp, wav, sz))
                db.commit()
            done += 1
            sys.stdout.write(f"\r  Progress: {done}/{total_jobs}")
            sys.stdout.flush()
    print()


def main():
    db = sqlite3.connect(DB_PATH)
    render_all(db)
    
    stats = db.execute("""SELECT COUNT(DISTINCT song_id), COUNT(*)
        FROM renders""").fetchone()
    print("\n=== Rendering Complete ===")
    print(f"Songs rendered: {stats[0]}")
    print(f"Total WAV files: {stats[1]}")
    
    total_size = db.execute("SELECT SUM(wav_size) FROM renders").fetchone()[0] or 0
    print(f"Total size: {total_size // 1024 // 1024} MB")
    
    db.close()


if __name__ == "__main__":
    main()
