"""
Tests for ChildrenSongFinder.
"""

import unittest
import os
import tempfile
from src.children_song_finder import ChildrenSongFinder


class TestChildrenSongFinder(unittest.TestCase):
    """Test the ChildrenSongFinder class."""

    def setUp(self):
        # Create temp input dir with some fake .mid files
        self.test_dir = tempfile.mkdtemp()
        for name in ["twinkle_twinkle_little_star", "mary_had_a_little_lamb"]:
            path = os.path.join(self.test_dir, f"{name}.mid")
            with open(path, "wb") as f:
                f.write(b"fake midi content")

    def test_finder_scans_directory(self):
        """Finder should find all .mid files in the input directory."""
        finder = ChildrenSongFinder(input_dir=self.test_dir)
        songs = finder.SONGS
        self.assertEqual(len(songs), 2)
        self.assertIn("twinkle_twinkle_little_star", songs)
        self.assertIn("mary_had_a_little_lamb", songs)

    def test_finder_returns_paths(self):
        """download_all should return full file paths."""
        finder = ChildrenSongFinder(input_dir=self.test_dir)
        paths = finder.download_all()
        self.assertEqual(len(paths), 2)
        for p in paths:
            self.assertTrue(os.path.exists(p))

    def test_finder_no_directory(self):
        """Finder should handle missing directory gracefully."""
        finder = ChildrenSongFinder(input_dir="/nonexistent/path")
        self.assertEqual(len(finder.SONGS), 0)

    def test_finder_real_input(self):
        """Finder should work with the real input directory."""
        # Try the actual project input dir
        finder = ChildrenSongFinder()
        songs = finder.SONGS
        # Should find all the downloaded songs
        self.assertGreaterEqual(
            len(songs), 100, f"Expected 100+ songs in input dir, found {len(songs)}"
        )


if __name__ == "__main__":
    unittest.main()
