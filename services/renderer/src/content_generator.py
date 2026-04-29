import os
import openai
import logging
import json
import hashlib
import requests
from .utils import retry_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self, api_key=None):
        """
        Initialize the ContentGenerator with an OpenAI API key.

        Args:
            api_key (str): OpenAI API key. Defaults to OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. ContentGenerator will not function.")

        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)

    @retry_request(max_retries=3, delay=2, backoff=2)
    def generate_metadata(self, hymn_name, style="Deep House"):
        """
        Generate title, description, and tags using GPT-4.

        Args:
            hymn_name (str): Name of the original hymn.
            style (str): The musical style of the remake.

        Returns:
            dict: {
                "title": str,
                "description": str,
                "tags": list
            }
        """
        prompt = (
            f"Generate metadata for a YouTube video featuring a {style} remake of the hymn '{hymn_name}'.\n"
            f"Provide the following fields in JSON format:\n"
            f"1. title: A catchy, modern title for the video.\n"
            f"2. description: A compelling description (max 1000 chars) explaining the remake.\n"
            f"3. tags: A list of 10 relevant tags."
        )

        logger.info(f"Generating metadata for '{hymn_name}'...")
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",  # Using a model that supports JSON mode
            messages=[
                {"role": "system", "content": "You are a creative content strategist for a music channel. You must respond in valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        content = response.choices[0].message.content
        metadata = json.loads(content)
        logger.info("Metadata generated successfully.")
        return metadata

    @retry_request(max_retries=3, delay=2, backoff=2)
    def generate_lyrics(self, hymn_name):
        """
        Generate or retrieve the original lyrics for a hymn and estimate timestamps for subtitles.

        Args:
            hymn_name (str): Name of the original hymn.

        Returns:
            list: A list of dicts with 'start', 'end' (in seconds, approximate) and 'text'.
        """
        prompt = (
            f"Provide the original public domain lyrics for the hymn '{hymn_name}'.\n"
            f"Please output them in a JSON array where each element is an object with:\n"
            f"- 'text': The line of lyrics.\n"
            f"- 'start': An estimated start time in seconds (float) for this line, assuming a standard tempo.\n"
            f"- 'end': An estimated end time in seconds (float) for this line.\n"
            f"Make the first line start around 5 seconds in. Just estimate the pacing for a standard 3-4 minute song."
        )

        logger.info(f"Generating synced lyrics for '{hymn_name}'...")
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a lyric synchronization expert. You must respond in valid JSON containing a list of objects under the key 'lyrics'."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        content = response.choices[0].message.content
        try:
            lyrics_data = json.loads(content)
            lyrics = lyrics_data.get("lyrics", [])
            logger.info(f"Generated {len(lyrics)} lines of synced lyrics.")
            return lyrics
        except Exception as e:
            logger.error(f"Failed to parse lyrics JSON: {e}")
            return []

    @retry_request(max_retries=3, delay=2, backoff=2)
    def generate_art(self, prompt):
        """
        Generate album art using DALL-E 3, with local caching to avoid redundant API calls.

        Args:
            prompt (str): Description for the image.

        Returns:
            str: URL of the generated image or path to the local cached image.
        """
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache", "art")
        os.makedirs(cache_dir, exist_ok=True)

        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        cached_image_path = os.path.join(cache_dir, f"{prompt_hash}.png")

        if os.path.exists(cached_image_path):
            logger.info(f"Found cached album art for prompt hash {prompt_hash}")
            return cached_image_path

        logger.info(f"Generating album art for prompt: '{prompt}'...")
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        logger.info(f"Album art generated: {image_url}")

        # Download and cache the image
        try:
            logger.info(f"Caching album art to {cached_image_path}...")
            img_response = requests.get(image_url)
            img_response.raise_for_status()
            with open(cached_image_path, "wb") as f:
                f.write(img_response.content)
            return cached_image_path
        except Exception as e:
            logger.error(f"Failed to cache album art: {e}")
            return image_url # Fallback to URL if caching fails

if __name__ == "__main__":
    if os.environ.get("OPENAI_API_KEY"):
        generator = ContentGenerator()
        # Test metadata
        import sys
        if len(sys.argv) > 1:
            hymn = sys.argv[1]
            print(generator.generate_metadata(hymn))
        else:
            print("Usage: python content_generator.py <hymn_name>")
    else:
        print("OPENAI_API_KEY not set. Skipping real test.")
