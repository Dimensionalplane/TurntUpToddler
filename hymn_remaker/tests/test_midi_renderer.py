import unittest
import os
import shutil
import sys
from unittest.mock import patch, MagicMock

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
    @patch('hymn_remaker.src.midi_renderer.subprocess.run')
    def test_render_calls_midi_to_audio(self, mock_subprocess):
        # Mock subprocess to return success (code 0)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Mock soundfont existence and constructor setup
        with patch('os.path.exists', return_value=True):
            renderer = MidiRenderer(soundfont_path="dummy.sf2")
            renderer.fluidsynth_bin = "fake_fluidsynth"
            
            output_path = os.path.join(self.output_dir, "test.wav")
            # Create a mock output file since the code asserts its existence after rendering
            with open(output_path, "w") as f:
                f.write("dummy audio content")

            renderer.render(self.midi_path, output_path)

        mock_subprocess.assert_called_once()
        cmd = mock_subprocess.call_args[0][0]
        self.assertEqual(cmd[0], "fake_fluidsynth")
        self.assertIn("-ni", cmd)

    def test_render_missing_midi(self):
        with patch('os.path.exists', return_value=True):
            renderer = MidiRenderer(soundfont_path="dummy.sf2")
        
        # We pass a non-existent path to render, which should fail on the input midi check
        with self.assertRaises(FileNotFoundError):
            renderer.render("non_existent_midi.mid", "output.wav")

if __name__ == '__main__':
    unittest.main()

