import os
import requests
import logging

logger = logging.getLogger(__name__)

class ChildrenSongFinder:
    # Curated, open-license public domain children's songs MIDI file links (fallback)
    SONGS = {
        "twinkle_twinkle_little_star": "https://susam.net/files/music/twinkle-twinkle-little-star/twinkle-twinkle-little-star.midi",
        "mary_had_a_little_lamb": "https://raw.githubusercontent.com/vishnubob/python-midi/master/mary.mid",
        "itsy_bitsy_spider": "https://bitmidi.com/uploads/21307.mid",
        "row_row_row_your_boat": "https://bitmidi.com/uploads/86438.mid",
        "wheels_on_the_bus": "https://bitmidi.com/uploads/112674.mid"
    }

    def __init__(self, use_dynamic_search=True, dynamic_queries=["nursery", "children", "lullaby"]):
        self.use_dynamic_search = use_dynamic_search
        self.dynamic_queries = dynamic_queries
        self.api_base = "https://bitmidi.com"

    def _search_bitmidi(self, query, limit=5):
        """Searches BitMidi API for MIDI files matching the query."""
        url = f"{self.api_base}/api/midi/search?q={query}"
        results = []
        try:
            logger.info(f"Searching BitMidi for '{query}'...")
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            items = data.get("result", {}).get("results", [])
            for item in items[:limit]:
                name = item.get("name", "").replace(".mid", "").replace(".midi", "").replace(" ", "_")
                if not name:
                    name = item.get("slug", "unknown")
                download_url = item.get("downloadUrl")
                if download_url:
                    full_url = f"{self.api_base}{download_url}"
                    results.append((name, full_url))
        except Exception as e:
            logger.error(f"Error searching BitMidi for '{query}': {e}")

        return results

    def download_all(self, output_dir, limit_per_query=2):
        """
        Download curated children's songs to the target input directory,
        optionally scraping dynamically from BitMidi.
        """
        os.makedirs(output_dir, exist_ok=True)
        downloaded = []

        # Combine hardcoded and dynamic lists
        songs_to_download = dict(self.SONGS)

        if self.use_dynamic_search:
            for query in self.dynamic_queries:
                search_results = self._search_bitmidi(query, limit=limit_per_query)
                for name, url in search_results:
                    if name not in songs_to_download:
                        songs_to_download[name] = url

        for name, url in songs_to_download.items():
            # Clean up filename
            clean_name = "".join([c for c in name if c.isalnum() or c in ['_', '-']])
            ext = ".mid" if ".mid" in url.lower() else ".midi"
            dest_path = os.path.join(output_dir, f"{clean_name}{ext}")

            # Skip if already exists
            if os.path.exists(dest_path):
                logger.info(f"Song {clean_name} already exists at {dest_path}, skipping download.")
                downloaded.append(dest_path)
                continue

            logger.info(f"Downloading children's song '{clean_name}' from {url}...")
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Successfully downloaded {clean_name} to {dest_path}")
                downloaded.append(dest_path)
            except Exception as e:
                logger.error(f"Failed to download children's song '{clean_name}' from {url}: {e}")

        return downloaded
