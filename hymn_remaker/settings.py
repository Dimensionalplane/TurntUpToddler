import os

# --- Paths ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INPUT_DIR = os.path.join(BASE_DIR, "hymn_remaker", "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "hymn_remaker", "output")
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
ART_CACHE_DIR = os.path.join(CACHE_DIR, "art")

# --- Default Fallback Paths ---
# Local soundfonts directory (bundled with the project)
_SOUNDFONTS_DIR = os.path.join(os.path.dirname(__file__), "soundfonts")

DEFAULT_SOUNDFONT_PATHS = [
    # Local project soundfonts (Windows/macOS/Linux portable)
    os.path.join(_SOUNDFONTS_DIR, "MV30_SC-55.sf2"),
    os.path.join(_SOUNDFONTS_DIR, "FluidR3_GM.sf2"),
    os.path.join(_SOUNDFONTS_DIR, "GeneralUser_GS.sf2"),
    # Linux system paths
    '/usr/share/sounds/sf2/FluidR3_GM.sf2',
    '/usr/share/sounds/sf2/default-GM.sf2',
    '/usr/share/soundfonts/default.sf2',
    '/usr/local/share/fluidsynth/sounds/FluidR3_GM.sf2',
    # macOS Homebrew paths
    '/opt/homebrew/share/soundfonts/FluidR3_GM.sf2',
    '/usr/local/share/soundfonts/FluidR3_GM.sf2',
]

# --- Pipeline Settings ---
DEFAULT_STYLE = "Deep House, high quality, electronic"

STYLE_PRESETS = {
    "Deep House": "Deep House, high quality, electronic, club-ready, 4/4 beat",
    "Lofi Hip Hop": "Lofi hip hop, chill, relaxed, nostalgic, vinyl crackle, jazz samples",
    "Ambient / Cinematic": "Ambient, orchestral, cinematic, soaring pads, ethereal, high quality",
    "Synthwave": "Synthwave, 80s retro, neon, analog synthesizers, driving bassline",
    "Techno": "Melodic techno, dark, driving, hypnotic, warehouse vibes",
    "Pop / Acoustic": "Modern pop, acoustic guitar, clean production, radio-friendly"
}

DEFAULT_VIDEO_FORMAT = "Standard 16:9"
DEFAULT_ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
DEFAULT_ELEVENLABS_MODEL = "eleven_multilingual_v2"

# --- Audio Engine Settings ---
SAMPLE_RATE = 44100
REVERB_TAIL_SECONDS = 2.0

# --- FluidSynth Binary ---
# Local bundled binary (Windows) or system PATH
_BIN_DIR = os.path.join(os.path.dirname(__file__), "bin")
FLUIDSYNTH_BIN = os.path.join(_BIN_DIR, "fluidsynth.exe") if os.name == "nt" else "fluidsynth"
# --- FFmpeg Binary ---
# Local bundled binary (Windows) or system PATH
FFMPEG_BIN = os.path.join(_BIN_DIR, "ffmpeg.exe") if os.name == "nt" else "ffmpeg"
FFPROBE_BIN = os.path.join(_BIN_DIR, "ffprobe.exe") if os.name == "nt" else "ffprobe"


# --- Suno AI Music API ---
SUNO_SESSION_TOKEN = os.environ.get("SUNO_SESSION_TOKEN", "")
SUNO_MODEL_VERSION = os.environ.get("SUNO_MODEL_VERSION", "chirp-v4")
SUNO_BASE_URL = os.environ.get("SUNO_BASE_URL", "https://studio-api.suno.ai")
SUNO_POLL_INTERVAL = int(os.environ.get("SUNO_POLL_INTERVAL", "5"))
SUNO_POLL_TIMEOUT = int(os.environ.get("SUNO_POLL_TIMEOUT", "300"))

# --- MP3 Conversion ---
DEFAULT_MP3_BITRATE = "192k"

# --- Remake Priority ---
# Which AI service to use first for Step 2 (remake)
# Options: "suno", "replicate"
REMAKE_PRIORITY = os.environ.get("REMAKE_PRIORITY", "suno")