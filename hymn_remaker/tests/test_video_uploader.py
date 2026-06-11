import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from hymn_remaker.src.video_uploader import VideoProducer

class TestVideoProducer(unittest.TestCase):
    def setUp(self):
        self.test_audio = "test_audio.wav"
        with open(self.test_audio, "w") as f:
            f.write("dummy audio")

    def tearDown(self):
        if os.path.exists(self.test_audio):
            os.remove(self.test_audio)
        if os.path.exists("test_video.mp4"):
            os.remove("test_video.mp4")

    @patch('hymn_remaker.src.video_uploader.requests.get')
    @patch('hymn_remaker.src.video_uploader.subprocess.run')
    def test_create_video(self, mock_subprocess, mock_get):
        # Mock requests.get
        mock_response = MagicMock()
        mock_response.content = b"fake image content"
        mock_get.return_value = mock_response

        producer = VideoProducer()
        output_path = "test_video.mp4"

        producer.create_video(self.test_audio, "http://image.url", output_path)

        mock_get.assert_called_with("http://image.url")
        mock_subprocess.assert_called_once()

        cmd = mock_subprocess.call_args[0][0]
        self.assertTrue(cmd[0].endswith("ffmpeg.exe") or cmd[0] == "ffmpeg")
        self.assertIn("-loop", cmd)
        self.assertIn("-shortest", cmd)

if __name__ == '__main__':
    unittest.main()
