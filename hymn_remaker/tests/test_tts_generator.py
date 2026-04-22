import unittest
from unittest.mock import patch, MagicMock
from hymn_remaker.src.tts_generator import TTSGenerator
import os

class TestTTSGenerator(unittest.TestCase):
    def setUp(self):
        # Prevent it from actually making requests if API key somehow exists
        self.patcher = patch('hymn_remaker.src.tts_generator.ElevenLabs')
        self.mock_elevenlabs = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_init_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            generator = TTSGenerator(api_key=None)
            self.assertIsNone(generator.api_key)

    def test_init_with_api_key(self):
        generator = TTSGenerator(api_key="test_key")
        self.assertEqual(generator.api_key, "test_key")
        self.mock_elevenlabs.assert_called_once_with(api_key="test_key")

    @patch('hymn_remaker.src.tts_generator.AudioSegment')
    def test_generate_vocals(self, mock_audio_segment):
        generator = TTSGenerator(api_key="test_key")

        # Setup mock audio
        mock_silent = MagicMock()
        mock_audio_segment.silent.return_value = mock_silent
        mock_line_audio = MagicMock()
        mock_audio_segment.from_file.return_value = mock_line_audio
        mock_silent.overlay.return_value = mock_silent

        # Setup mock client
        mock_client_instance = self.mock_elevenlabs.return_value
        mock_client_instance.generate.return_value = iter([b"audio", b"data"])

        lyrics = [
            {"text": "Line 1", "start": 1.0, "end": 2.0},
            {"text": "Line 2", "start": 3.0, "end": 4.0}
        ]

        result = generator.generate_vocals(lyrics, "dummy_output.wav")

        self.assertEqual(result, "dummy_output.wav")
        self.assertEqual(mock_client_instance.generate.call_count, 2)

        # Verify the specific parameters were passed down
        mock_client_instance.generate.assert_any_call(
            text='Line 1',
            voice='21m00Tcm4TlvDq8ikWAM',
            model='eleven_multilingual_v2'
        )

        mock_silent.export.assert_called_once_with("dummy_output.wav", format="wav")

if __name__ == '__main__':
    unittest.main()
