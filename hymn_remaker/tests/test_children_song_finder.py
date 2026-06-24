import unittest
import os
import shutil
import sys
from unittest.mock import patch, MagicMock

# Adjust path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from hymn_remaker.src.children_song_finder import ChildrenSongFinder

class TestChildrenSongFinder(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(__file__)
        self.output_dir = os.path.join(self.test_dir, "temp_finder_input")
        os.makedirs(self.output_dir, exist_ok=True)
        self.finder = ChildrenSongFinder()

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    @patch('hymn_remaker.src.children_song_finder.requests.get')
    def test_download_all_success(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = b"fake midi content"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        downloaded = self.finder.download_all(self.output_dir)
        
        # Verify that all songs are downloaded
        self.assertEqual(len(downloaded), len(self.finder.SONGS))
        for path in downloaded:
            self.assertTrue(os.path.exists(path))
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"fake midi content")

    @patch('hymn_remaker.src.children_song_finder.requests.get')
    def test_download_all_skips_existing(self, mock_get):
        # Create one file beforehand
        existing_file = os.path.join(self.output_dir, "twinkle_twinkle_little_star.midi")
        with open(existing_file, "wb") as f:
            f.write(b"existing content")

        mock_response = MagicMock()
        mock_response.content = b"new content"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        downloaded = self.finder.download_all(self.output_dir)
        
        self.assertEqual(len(downloaded), len(self.finder.SONGS))
        # Check that the existing file was NOT overwritten
        with open(existing_file, "rb") as f:
            self.assertEqual(f.read(), b"existing content")
            
        # Check that the other file was downloaded with new content
        other_file = os.path.join(self.output_dir, "mary_had_a_little_lamb.mid")
        self.assertTrue(os.path.exists(other_file))
        with open(other_file, "rb") as f:
            self.assertEqual(f.read(), b"new content")

    @patch('hymn_remaker.src.children_song_finder.requests.get')
    def test_download_all_handles_error(self, mock_get):
        # Mock requests.get to raise an exception
        mock_get.side_effect = Exception("Connection refused")

        downloaded = self.finder.download_all(self.output_dir)
        
        # None should have downloaded successfully since it raises an exception
        self.assertEqual(len(downloaded), 0)

if __name__ == '__main__':
    unittest.main()
