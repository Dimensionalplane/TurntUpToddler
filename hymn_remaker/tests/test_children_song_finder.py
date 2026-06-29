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
        # Use simple queries for testing so it's fast and predictable
        self.finder = ChildrenSongFinder(use_dynamic_search=True, dynamic_queries=["test"])

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    @patch('hymn_remaker.src.children_song_finder.requests.get')
    def test_search_bitmidi_success(self, mock_get):
        # Setup mock response for the API search
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "results": [
                    {
                        "name": "Test Song.mid",
                        "downloadUrl": "/uploads/123.mid"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        results = self.finder._search_bitmidi("test", limit=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "Test_Song")
        self.assertEqual(results[0][1], "https://bitmidi.com/uploads/123.mid")

    @patch('hymn_remaker.src.children_song_finder.requests.get')
    def test_search_bitmidi_failure(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        results = self.finder._search_bitmidi("test")
        self.assertEqual(len(results), 0)

    @patch('hymn_remaker.src.children_song_finder.ChildrenSongFinder._search_bitmidi')
    @patch('hymn_remaker.src.children_song_finder.requests.get')
    def test_download_all_success(self, mock_get, mock_search):
        # Setup mock response for downloading files
        mock_response = MagicMock()
        mock_response.content = b"fake midi content"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Setup mock response for search
        mock_search.return_value = [("dynamic_song", "https://bitmidi.com/uploads/123.mid")]

        downloaded = self.finder.download_all(self.output_dir)

        # Verify that all static songs + 1 dynamic song are downloaded
        self.assertEqual(len(downloaded), len(self.finder.SONGS) + 1)
        for path in downloaded:
            self.assertTrue(os.path.exists(path))
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"fake midi content")

    @patch('hymn_remaker.src.children_song_finder.ChildrenSongFinder._search_bitmidi')
    @patch('hymn_remaker.src.children_song_finder.requests.get')
    def test_download_all_skips_existing(self, mock_get, mock_search):
        # Mock search to return nothing so we just test static songs
        mock_search.return_value = []

        # Create one file beforehand
        existing_file = os.path.join(self.output_dir, "twinkle_twinkle_little_star.midi")
        with open(existing_file, "wb") as f:
            f.write(b"existing content")

        mock_response = MagicMock()
        mock_response.content = b"new content"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        downloaded = self.finder.download_all(self.output_dir)

        self.assertEqual(len(downloaded), 5)
        # Check that the existing file was NOT overwritten
        with open(existing_file, "rb") as f:
            self.assertEqual(f.read(), b"existing content")

        # Check that the other file was downloaded with new content
        other_file = os.path.join(self.output_dir, "mary_had_a_little_lamb.mid")
        self.assertTrue(os.path.exists(other_file))
        with open(other_file, "rb") as f:
            self.assertEqual(f.read(), b"new content")

    @patch('hymn_remaker.src.children_song_finder.ChildrenSongFinder._search_bitmidi')
    @patch('hymn_remaker.src.children_song_finder.requests.get')
    def test_download_all_handles_error(self, mock_get, mock_search):
        mock_search.return_value = []
        # Mock requests.get to raise an exception
        mock_get.side_effect = Exception("Connection refused")

        downloaded = self.finder.download_all(self.output_dir)

        # None should have downloaded successfully since it raises an exception
        self.assertEqual(len(downloaded), 0)

if __name__ == '__main__':
    unittest.main()
