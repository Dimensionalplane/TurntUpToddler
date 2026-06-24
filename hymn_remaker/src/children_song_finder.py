"""
ChildrenSongFinder — auto-detects and manages public domain children's songs.
Scans the input directory for downloaded MIDI files.
"""

import os
import logging

logger = logging.getLogger(__name__)


class ChildrenSongFinder:
    """Finds available children's songs by scanning the input directory."""

    def __init__(self, input_dir=None):
        self.input_dir = input_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input"
        )
        self.SONGS = self._scan_songs()

    def _scan_songs(self):
        """Dynamically scan input dir for .mid/.midi files and build URL map."""
        songs = {}
        if os.path.isdir(self.input_dir):
            for fname in os.listdir(self.input_dir):
                if fname.endswith((".mid", ".midi")):
                    name = os.path.splitext(fname)[0]
                    path = os.path.join(self.input_dir, fname)
                    songs[name] = path
        if not songs:
            logger.warning(f"No MIDI files found in {self.input_dir}")
        return songs

    def download_all(self, output_dir=None):
        """Return list of available MIDI file paths."""
        output_dir = output_dir or self.input_dir
        return list(self.SONGS.values())
