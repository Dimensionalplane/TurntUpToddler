import asyncio
import logging
import time
import urllib.request
from bs4 import BeautifulSoup
from classical_scraper.freellm_client import extract_midi_links_from_html

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Fetching mutopia browse.html...")
    try:
        html = urllib.request.urlopen("https://www.mutopiaproject.org/browse.html").read().decode("utf-8", errors="replace")
    except Exception as e:
        print("Failed to fetch mutopia browse.html:", e)
        return

    print("HTML length:", len(html))
    print("Extracting midi links from first 8000 chars of HTML...")
    start_time = time.time()
    try:
        # We call extract_midi_links_from_html directly, which calls chat_completion
        result = await extract_midi_links_from_html(html, "mutopia")
        elapsed = time.time() - start_time
        print(f"Success in {elapsed:.2f}s!")
        print("Result:", result)
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Failed in {elapsed:.2f}s with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
