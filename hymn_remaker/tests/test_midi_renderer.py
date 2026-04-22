import unittest
import os
import shutil
import sys
from unittest.mock import patch

# Adjust path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from hymn_remaker.src.midi_renderer import MidiRenderer

class TestMidiRenderer(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(__file__)
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)
        # Create a dummy midi file for testing
        self.midi_path = os.path.join(self.output_dir, "test.mid")
        with open(self.midi_path, "wb") as f:
            f.write(b'MThd\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60')

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    @patch('hymn_remaker.src.midi_renderer.NATIVE_ENGINE_AVAILABLE', False)
    @patch('hymn_remaker.src.midi_renderer.FluidSynth', create=True)
    def test_render_calls_midi_to_audio(self, MockFluidSynth):
        # Setup mock
        mock_fs_instance = MockFluidSynth.return_value

        renderer = MidiRenderer()
        output_path = os.path.join(self.output_dir, "test.wav")

        renderer.render(self.midi_path, output_path)

        mock_fs_instance.midi_to_audio.assert_called_once_with(self.midi_path, output_path)

    def test_render_missing_midi(self):
        # We don't need to patch here as it should fail before calling FluidSynth
        # But MidiRenderer constructor calls FluidSynth so we still need to patch it or let it run (if fluidsynth installed)
        # To be safe/fast, patch it.
        with patch('hymn_remaker.src.midi_renderer.NATIVE_ENGINE_AVAILABLE', False), patch('hymn_remaker.src.midi_renderer.FluidSynth', create=True):
            renderer = MidiRenderer()
            with self.assertRaises(FileNotFoundError):
                renderer.render("non_existent.mid", "output.wav")

if __name__ == '__main__':
    unittest.main()
