import os
import sys
import pytest
from pydub import AudioSegment
from pydub.generators import Sine
import numpy as np

# Ensure hymn_remaker path is valid for importing tts_generator
sys.path.insert(0, os.path.abspath('hymn_remaker'))
from src.tts_generator import TTSGenerator

def test_pitch_shift_length_and_samples():
    """
    Test that the pyrubberband pitch shift implementation correctly shifts pitch
    without altering the duration or number of samples of the original audio.
    """
    # Create a 1-second sine wave
    sound = Sine(440).to_audio_segment(duration=1000)

    tts = TTSGenerator()
    tts.api_key = "dummy"

    # Apply a pitch shift (+4 semitones)
    shifted = tts._pitch_shift(sound, 4)

    # Assert duration remains unchanged (1000ms)
    assert len(shifted) == len(sound), "Duration changed after pitch shift!"

    # Assert number of samples remains unchanged
    assert len(shifted.get_array_of_samples()) == len(sound.get_array_of_samples()), "Number of samples changed after pitch shift!"
