import os
import requests
import logging

logger = logging.getLogger(__name__)

class ChildrenSongFinder:
    # Curated, open-license public domain children's songs MIDI file links
    SONGS = {
        "twinkle_twinkle_little_star": "https://susam.net/files/music/twinkle-twinkle-little-star/twinkle-twinkle-little-star.midi",
        "mary_had_a_little_lamb": "https://raw.githubusercontent.com/vishnubob/python-midi/master/mary.mid",
        "itsy_bitsy_spider": "https://bitmidi.com/uploads/21307.mid",
        "row_row_row_your_boat": "https://bitmidi.com/uploads/86438.mid",
        "wheels_on_the_bus": "https://bitmidi.com/uploads/112674.mid"
    }

    def download_all(self, output_dir):
        """
        Download all curated children's songs to the target input directory.
        """
        os.makedirs(output_dir, exist_ok=True)
        downloaded = []
        for name, url in self.SONGS.items():
            ext = ".mid" if url.endswith(".mid") else ".midi"
            dest_path = os.path.join(output_dir, f"{name}{ext}")

            # Skip if already exists
            if os.path.exists(dest_path):
                logger.info(f"Song {name} already exists at {dest_path}, skipping download.")
                downloaded.append(dest_path)
                continue

            logger.info(f"Downloading children's song '{name}' from {url}...")
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Successfully downloaded {name} to {dest_path}")
                downloaded.append(dest_path)
            except Exception as e:
                logger.error(f"Failed to download children's song '{name}' from {url}: {e}")

        return downloaded
