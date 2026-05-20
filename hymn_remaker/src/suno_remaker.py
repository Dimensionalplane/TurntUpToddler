"""
Suno AI Music Remaker — High-level orchestration facade.

Re-exports the decomposed sub-modules:
    - suno_api:    HTTP client, auth, polling, download
    - suno_browser: Playwright browser automation & Turnstile harvesting

This module provides the ``SunoRemaker`` class that the pipeline imports,
preserving full backward compatibility with ``main.py`` and ``app.py``.

Usage:
    from hymn_remaker.src.suno_remaker import SunoRemaker
    remaker = SunoRemaker(session_token="...")
    wav_path = remaker.remake("input_base.wav", "Deep House, 120 BPM")
"""

import os
import glob
import time
import subprocess
import logging
from pathlib import Path

from hymn_remaker import settings
from hymn_remaker.src.suno_api import SunoAPIClient
from hymn_remaker.src import suno_browser

logger = logging.getLogger(__name__)


class SunoRemaker:
    """Generate Deep House remixes of hymn audio using Suno AI.

    Supports two modes:
        - API mode:   Direct HTTP requests with Turnstile token
        - Browser mode: Playwright automation of the Suno web UI

    Delegates HTTP work to :class:`SunoAPIClient` and browser work
    to :mod:`suno_browser`.
    """

    def __init__(self, session_token=None, client_token=None, model_version=None):
        self.api = SunoAPIClient(
            session_token=session_token,
            client_token=client_token,
            model_version=model_version,
        )
        # Backward-compatible property access
        self.session_token = self.api.session_token
        self.client_token = self.api.client_token
        self.model_version = self.api.model_version

    def is_available(self):
        """Check if Suno API is configured and session is valid."""
        return self.api.is_available()

    def check_captcha(self):
        """Check if CAPTCHA is required for generation."""
        return self.api.check_captcha()

    def get_session_info(self):
        """Get current session info from Suno API."""
        return self.api.get_session_info()

    def get_feed(self, page=1):
        """Get user's song feed."""
        return self.api.get_feed(page)

    def get_turnstile_token(self, timeout=30):
        """Obtain a Cloudflare Turnstile token using Playwright."""
        return suno_browser.get_turnstile_token(
            session_token=self.session_token,
            client_token=self.client_token,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Main Entry Points
    # ------------------------------------------------------------------

    def remake(self, wav_path, prompt, duration=30, make_instrumental=True,
               tags="deep house, electronic, club", keep_mp3=False,
               mode="auto", turnstile_token=None):
        """Generate a Deep House remake of a hymn using Suno AI.

        This is the main entry point for the pipeline. It supports two modes:
            - "api":     Direct HTTP API calls (requires Turnstile token)
            - "browser": Playwright browser automation (handles Turnstile automatically)
            - "auto":    Try API first, fall back to browser

        Args:
            wav_path (str): Path to the input WAV file (hymn base audio).
            prompt (str): Text prompt for the Deep House style.
            duration (int): Target duration in seconds.
            make_instrumental (bool): Generate without vocals (default True).
            tags (str): Genre tags for the generation.
            keep_mp3 (bool): Keep the intermediate MP3 file (default False).
            mode (str): Generation mode - "api", "browser", or "auto".
            turnstile_token (str): Pre-obtained Turnstile token (for API mode).

        Returns:
            str: Path to the generated remake WAV file.

        Raises:
            RuntimeError: If Suno API fails.
            FileNotFoundError: If input WAV doesn't exist.
        """
        if not self.session_token:
            raise RuntimeError("SunoRemaker not configured. Set SUNO_SESSION_TOKEN.")
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"Input WAV not found: {wav_path}")

        hymn_name = Path(wav_path).stem.replace("_base", "")
        logger.info(f"=== Suno Remake: {hymn_name} ===")

        full_prompt = (
            f"Create a {prompt} version inspired by this hymn melody. "
            f"Transform it into a club-ready deep house track with "
            f"four-on-the-floor kick, deep bass, atmospheric pads, "
            f"and subtle references to the original hymn's melody."
        )

        clips = None

        # Try API mode first (if auto or api)
        if mode in ("auto", "api"):
            try:
                if not turnstile_token:
                    captcha = self.check_captcha()
                    if captcha.get("required"):
                        logger.info("CAPTCHA required, obtaining Turnstile token...")
                        turnstile_token = self.get_turnstile_token()

                clips = self.api.generate_songs(
                    prompt=full_prompt,
                    turnstile_token=turnstile_token,
                    make_instrumental=make_instrumental,
                    tags=tags,
                    title=f"{hymn_name} (Deep House Remix)",
                )
            except RuntimeError as e:
                logger.warning(f"API mode failed: {e}")
                if mode == "auto":
                    logger.info("Falling back to browser mode...")
                else:
                    raise

        # Prepare audio influence path (prefer MP3, fall back to WAV)
        audio_influence = None
        mp3_path = wav_path.rsplit('_base.wav', 1)[0] + '_base.mp3'
        if os.path.exists(mp3_path):
            audio_influence = mp3_path
            logger.info(f"Using MP3 as audio influence: {mp3_path}")
        elif os.path.exists(wav_path):
            audio_influence = wav_path
            logger.info(f"Using WAV as audio influence: {wav_path}")

        # Fall back to browser mode
        if clips is None and mode in ("auto", "browser"):
            clips = suno_browser.generate_songs_browser(
                prompt=full_prompt,
                session_token=self.session_token,
                client_token=self.client_token,
                make_instrumental=make_instrumental,
                audio_influence_path=audio_influence,
            )

        if not clips:
            raise RuntimeError("No clips generated")

        # Poll for completion
        clip_ids = [clip.get("id") for clip in clips if clip.get("id")]
        if not clip_ids:
            raise RuntimeError("Suno returned no clip IDs")

        completed_clips = self.api.poll_songs(clip_ids)

        # Filter out errored clips
        valid_clips = [
            c for c in completed_clips
            if c.get("status") != "error" and c.get("audio_url")
        ]
        if not valid_clips:
            raise RuntimeError("All Suno clips failed or have no audio_url")

        # Select best clip and download
        best_clip = SunoAPIClient.select_best_clip(valid_clips)
        remake_wav = wav_path.rsplit("_base.wav", 1)[0] + "_remake.wav"
        self.api.download_audio(best_clip, remake_wav)

        logger.info(f"=== Suno Remake Complete: {remake_wav} ===")
        return remake_wav

    def remake_simple(self, prompt, make_instrumental=True,
                      tags="deep house, electronic",
                      mode="auto", turnstile_token=None):
        """Generate a song from a text prompt only (no audio influence).

        Simpler version of remake() that doesn't require an input WAV.
        Useful for testing or generating standalone tracks.

        Args:
            prompt (str): Text description for the song.
            make_instrumental (bool): Generate without vocals.
            tags (str): Genre tags.
            mode (str): "api", "browser", or "auto".
            turnstile_token (str): Pre-obtained Turnstile token.

        Returns:
            list: List of completed clip dictionaries.
        """
        clips = None

        if mode in ("auto", "api"):
            try:
                if not turnstile_token:
                    captcha = self.check_captcha()
                    if captcha.get("required"):
                        turnstile_token = self.get_turnstile_token()

                clips = self.api.generate_songs(
                    prompt=prompt,
                    turnstile_token=turnstile_token,
                    make_instrumental=make_instrumental,
                    tags=tags,
                )
            except RuntimeError as e:
                logger.warning(f"API mode failed: {e}")
                if mode != "auto":
                    raise

        if clips is None and mode in ("auto", "browser"):
            clips = suno_browser.generate_songs_browser(
                prompt=prompt,
                session_token=self.session_token,
                client_token=self.client_token,
                make_instrumental=make_instrumental,
            )

        if not clips:
            raise RuntimeError("No clips generated")

        clip_ids = [clip.get("id") for clip in clips if clip.get("id")]
        if clip_ids:
            return self.api.poll_songs(clip_ids)
        return clips

    # ------------------------------------------------------------------
    # Batch & Conversion Utilities
    # ------------------------------------------------------------------

    def batch_wav_to_mp3(self, output_dir, bitrate="192k"):
        """Convert all base WAV files in the output directory to MP3.

        Args:
            output_dir (str): Directory containing WAV files.
            bitrate (str): MP3 bitrate (default 192k).

        Returns:
            tuple: (converted_count, failed_count)
        """
        wav_files = glob.glob(os.path.join(output_dir, "*_base.wav"))
        logger.info(f"Found {len(wav_files)} base WAV files to convert to MP3")

        converted = 0
        failed = 0

        for wav_path in sorted(wav_files):
            mp3_path = wav_path.rsplit("_base.wav", 1)[0] + "_base.mp3"
            if os.path.exists(mp3_path):
                logger.info(f"  Already exists: {os.path.basename(mp3_path)}")
                converted += 1
                continue
            try:
                self._wav_to_mp3(wav_path, mp3_path, bitrate=bitrate)
                converted += 1
            except Exception as e:
                logger.error(f"  FAILED: {os.path.basename(wav_path)}: {e}")
                failed += 1

        logger.info(f"Batch WAV->MP3 complete: {converted} converted, {failed} failed")
        return converted, failed

    def _wav_to_mp3(self, wav_path, mp3_path=None, bitrate="192k"):
        """Convert a WAV file to MP3 using ffmpeg.

        Args:
            wav_path (str): Path to input WAV file.
            mp3_path (str): Path for output MP3. Defaults to same name + .mp3.
            bitrate (str): MP3 bitrate (default 192k).

        Returns:
            str: Path to the generated MP3 file.
        """
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"WAV file not found: {wav_path}")
        if mp3_path is None:
            mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"

        cmd = [
            settings.FFMPEG_BIN,
            "-y", "-i", wav_path,
            "-codec:a", "libmp3lame",
            "-b:a", bitrate,
            "-joint_stereo", "1",
            mp3_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")
        return mp3_path

    def batch_remake(self, output_dir, style="Deep House", skip_existing=True):
        """Batch generate Deep House remakes for all hymn WAVs using Suno.

        Args:
            output_dir (str): Directory containing base WAV files.
            style (str): Style prompt for generation.
            skip_existing (bool): Skip if _remake.wav already exists.

        Returns:
            tuple: (success_count, failed_count)
        """
        wav_files = glob.glob(os.path.join(output_dir, "*_base.wav"))
        logger.info(f"Found {len(wav_files)} hymns to remake via Suno")

        success = 0
        failed = 0

        for wav_path in sorted(wav_files):
            name = Path(wav_path).stem.replace("_base", "")
            remake_path = wav_path.replace("_base.wav", "_remake.wav")

            if skip_existing and os.path.exists(remake_path):
                remake_size = os.path.getsize(remake_path)
                base_size = os.path.getsize(wav_path)
                if remake_size != base_size:
                    logger.info(f"  Skipping {name} (remake exists and differs from base)")
                    success += 1
                    continue

            try:
                logger.info(f"\n--- Remaking: {name} ---")
                self.remake(wav_path, style)
                success += 1
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error(f"  FAILED: {name}: {e}")
                failed += 1
                if "credits" in str(e).lower() or "402" in str(e):
                    logger.error("Suno credits exhausted. Stopping batch.")
                    break

        logger.info(f"\n=== Batch Suno Remake Complete ===")
        logger.info(f"Success: {success}")
        logger.info(f"Failed: {failed}")
        return success, failed
