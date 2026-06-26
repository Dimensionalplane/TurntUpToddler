import os
import requests
import logging

logger = logging.getLogger(__name__)

import urllib.parse

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

    def search_and_download_bitmidi(self, query, output_dir, limit=5):
        """
        Dynamically search BitMidi for a query and download the results.
        """
        os.makedirs(output_dir, exist_ok=True)
        downloaded = []

        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://bitmidi.com/api/midi/search?q={encoded_query}&limit={limit}"

        try:
            logger.info(f"Searching BitMidi API for '{query}'...")
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            response.raise_for_status()
            data = response.json()

            results = data.get("result", {}).get("results", [])
            for item in results:
                name = item.get("slug", "unknown").replace("-", "_")
                download_path = item.get("downloadUrl")
                if not download_path:
                    continue

                full_url = f"https://bitmidi.com{download_path}"
                dest_path = os.path.join(output_dir, f"{name}.mid")

                if os.path.exists(dest_path):
                    logger.info(f"Song {name} already exists at {dest_path}, skipping download.")
                    downloaded.append(dest_path)
                    continue

                logger.info(f"Downloading dynamically found song '{name}' from {full_url}...")
                dl_response = requests.get(full_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                dl_response.raise_for_status()
                with open(dest_path, "wb") as f:
                    f.write(dl_response.content)
                logger.info(f"Successfully downloaded {name} to {dest_path}")
                downloaded.append(dest_path)

        except Exception as e:
            logger.error(f"Failed to dynamically search/download from BitMidi for '{query}': {e}")

        return downloaded
