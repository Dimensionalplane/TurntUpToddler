import unittest
import os
import tempfile
import time
from unittest.mock import patch, MagicMock
import threading

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from hymn_remaker.src.radio_streamer import RadioStreamer

class TestRadioStreamer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.streamer = RadioStreamer(rtmp_url="rtmp://dummy", input_dir=self.temp_dir.name)

        # Create a dummy video file
        with open(os.path.join(self.temp_dir.name, "test1.mp4"), "w") as f:
            f.write("dummy video content")

    def tearDown(self):
        self.streamer.stop()
        self.temp_dir.cleanup()

    @patch("subprocess.Popen")
    def test_start_stop(self, mock_popen):
        # Mock the Popen process
        mock_process = MagicMock()
        # Make poll() return None initially (process is running), then return 0 (finished)
        mock_process.poll.side_effect = [None, None, 0]
        mock_popen.return_value = mock_process

        self.streamer.start()
        self.assertTrue(self.streamer.is_streaming)

        time.sleep(0.1) # Let the thread run briefly

        self.streamer.stop()
        self.assertFalse(self.streamer.is_streaming)
        # Ensure terminate was called if stopped while running
        mock_process.terminate.assert_called()

    @patch("subprocess.Popen")
    def test_skip_track(self, mock_popen):
        mock_process = MagicMock()
        mock_process.poll.return_value = None # Always running until stopped/skipped
        mock_popen.return_value = mock_process

        self.streamer.start()

        time.sleep(0.1) # For thread start
        self.assertTrue(self.streamer.is_streaming)

        # Trigger skip
        self.streamer.skip_track()


        # Wait up to 2 seconds for the thread to process the event
        for _ in range(20):
            if not self.streamer.skip_event.is_set():
                break
            time.sleep(0.1)

        # Process should have been terminated due to skip
        mock_process.terminate.assert_called()
        self.assertFalse(self.streamer.skip_event.is_set()) # Should be cleared

        self.streamer.stop()

if __name__ == "__main__":
    unittest.main()
