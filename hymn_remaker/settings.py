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
DEFAULT_VIDEO_FORMAT = "Standard 16:9"
DEFAULT_ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
DEFAULT_ELEVENLABS_MODEL = "eleven_multilingual_v2"

# --- Audio Engine Settings ---
SAMPLE_RATE = 44100
REVERB_TAIL_SECONDS = 2.0
