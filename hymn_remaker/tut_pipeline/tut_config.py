"""tut_config.py — master configuration for TurntUpToddler pipeline.

Every step imports from here. Change genres/speeds/paths in one place.
"""
import os

# ── Paths ──
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDERED_DIR = os.path.join(BASE, "rendered_wav")
GENERATED_DIR = os.path.join(BASE, "suno_generated")
VIDEO_DIR = os.path.join(BASE, "videos")
PACKAGE_DIR = os.path.join(BASE, "tut_packages")

for d in [GENERATED_DIR, VIDEO_DIR, PACKAGE_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Genres (prompt, slug) ──
GENRES = [
    ("full-on psytrance, 145bpm, rolling bassline, euphoric melodic, festival energy", "psytrance"),
    ("forest goa trance, 138bpm, dark atmospheric, nature sounds", "goa"),
    ("hardstyle, 150bpm, hard kick, orchestral sweeps, euphoric climax", "hardstyle"),
    ("happy hardcore, 170bpm, uplifting piano, pitched vocals, energetic", "happy_hardcore"),
    ("brostep dubstep, 140bpm, massive drops, growling wobbles, aggressive", "brostep"),
    ("drum and bass, 174bpm, amen breaks, liquid atmospheres, deep sub-bass", "dnb"),
    ("japanese hardcore techno, 185bpm, anime melodies, fast kicks", "jcore"),
    ("berlin techno, 135bpm, minimal driving, hypnotic repetition, warehouse", "berlin"),
    ("detroit techno, 128bpm, deep analog synths, soulful chord stabs", "detroit"),
    ("detroit house, 125bpm, soulful grooves, deep basslines, jazzy", "house"),
]

# ── Speeds (tempo multipliers) ──
SPEEDS = [0.5, 1.0, 2.5, 5.0]

# ── Songs ──
SONGS = [
    "twinkle_twinkle",
    "mary_had_lamb",
    "row_row_boat",
    "itsy_bitsy_spider",
    "old_macdonald",
    "wheels_on_bus",
    "bingo",
    "abc_song",
    "happy_birthday",
    "amazing_grace",
]

# ── CDP Browser ──
CDP_URL = "http://127.0.0.1:9222"
SUNO_CREATE_URL = "https://suno.com/create"

# ── File helpers ──
def wav_path(song, speed):
    """rendered_wav/{song}_speed_{speed}.wav"""
    return os.path.join(RENDERED_DIR, f"{song}_speed_{str(speed).replace('.', '_')}.wav")

def mp3_path(song, genre_slug, speed):
    """suno_generated/{song}_{genre}_speed_{speed}.mp3"""
    return os.path.join(GENERATED_DIR, f"{song}_{genre_slug}_speed_{str(speed).replace('.', '_')}.mp3")

def video_path(song, genre_slug, speed):
    """videos/{song}_{genre}_speed_{speed}.mp4"""
    return os.path.join(VIDEO_DIR, f"{song}_{genre_slug}_speed_{str(speed).replace('.', '_')}.mp4")
