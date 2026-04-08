import os
import openai
import logging
import json
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
    def generate_dynamic_prompt(self, hymn_name, style, bpm=None, time_signature=None):
        """
        Generate an expert-level MusicGen prompt based on the user's style, hymn name, and extracted MIDI metrics.

        Args:
            hymn_name (str): Name of the original hymn.
            style (str): User's selected generic style (e.g. 'Deep House').
            bpm (int): Extracted BPM from MIDI file.
            time_signature (str): Extracted time signature (e.g., '4/4').

        Returns:
            str: An optimized, detailed music prompt for Replicate's MusicGen.
        """
        metrics = []
        if bpm:
            metrics.append(f"{bpm} BPM")
        if time_signature:
            metrics.append(f"{time_signature} time signature")

        metric_str = f", structured precisely at {', '.join(metrics)}, " if metrics else " "

        system_prompt = (
            "You are a master music producer and prompt engineer. Your job is to convert a user's generic "
            "style request and a hymn's name into a highly specific, professional, and detailed text-to-music prompt. "
            "Describe the instruments, the energy level, the groove, and the mixing quality required. "
            "Do NOT include conversational filler like 'Here is your prompt:'. Only output the raw prompt string itself, max 250 characters."
        )

        user_prompt = (
            f"Write a detailed music production prompt to remix the traditional hymn '{hymn_name}' "
            f"into a modern '{style}' track{metric_str}combining the original melody with high-end modern production techniques."
        )

        logger.info(f"Generating dynamic MusicGen prompt for '{hymn_name}'...")
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )

        dynamic_prompt = response.choices[0].message.content.strip().strip('"')
        logger.info(f"Dynamic Prompt: '{dynamic_prompt}'")
        return dynamic_prompt

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
        Generate album art using DALL-E 3.

        Args:
            prompt (str): Description for the image.

        Returns:
            str: URL of the generated image.
        """
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
        return image_url

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
