import pytest
import os
from unittest.mock import patch, MagicMock
from hymn_remaker.src.video_generator import AdvancedVideoGenerator

@patch('subprocess.run')
def test_generate_video_stub(mock_run, tmp_path):
    generator = AdvancedVideoGenerator()
    output_path = str(tmp_path / "test_bg.mp4")

    # Touch the file to simulate ffmpeg outputting the file
    def side_effect(*args, **kwargs):
        with open(output_path, "w") as f:
            f.write("mock video data")
        return MagicMock()

    mock_run.side_effect = side_effect

    result = generator.generate_video("test prompt", output_path, duration_sec=1)

    assert result == output_path
    assert os.path.exists(output_path)
    mock_run.assert_called_once()
