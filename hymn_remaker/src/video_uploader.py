import os
import shutil
import subprocess
import logging
import json
import time
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scopes required for YouTube Data API
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class VideoProducer:
    def __init__(self, client_secrets_file=None):
        """
        Initialize the VideoProducer.

        Args:
            client_secrets_file (str): Path to client_secrets.json.
                                       Defaults to GOOGLE_CLIENT_SECRETS_FILE env var or 'client_secrets.json'.
        """
        self.client_secrets_file = (
            client_secrets_file or
            os.environ.get("GOOGLE_CLIENT_SECRETS_FILE") or
            "client_secrets.json"
        )
        self.youtube = None

    def _create_srt_file(self, lyrics, srt_path):
        """Convert list of lyric dicts into a standard SRT file."""
        if not lyrics:
            return False

        try:
            with open(srt_path, 'w') as f:
                for i, line in enumerate(lyrics):
                    start = float(line.get('start', i * 5))
                    end = float(line.get('end', start + 4))
                    text = line.get('text', '')

                    # Convert seconds to SRT timestamp: HH:MM:SS,mmm
                    def format_time(seconds):
                        hours = int(seconds // 3600)
                        minutes = int((seconds % 3600) // 60)
                        secs = int(seconds % 60)
                        millis = int((seconds - int(seconds)) * 1000)
                        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

                    start_str = format_time(start)
                    end_str = format_time(end)

                    f.write(f"{i+1}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{text}\n\n")

            logger.info(f"SRT file created at {srt_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create SRT: {e}")
            return False

    def create_video(self, audio_path, image_url, output_path, lyrics=None, video_format="Standard 16:9", sub_font_size=24, sub_primary_color="#FFFFFF", sub_outline_color="#000000", sub_back_color="#000000", sub_box=True, enable_visualizer=False, visualizer_mode="cline"):
        """
        Create an MP4 video from an audio file, image URL, and optional lyrics using ffmpeg.

        Args:
            audio_path (str): Path to the input audio file.
            image_url (str): URL of the album art image.
            output_path (str): Path to the output video file.
            lyrics (list): Optional list of synced lyrics dicts.
            video_format (str): The aspect ratio of the output video.
        """
        logger.info(f"Creating video from {audio_path} and {image_url}...")

        # 1. Download the image to a temporary file, or copy if local
        import uuid
        unique_id = uuid.uuid4().hex
        temp_image_path = f"temp_art_{unique_id}.png"
        temp_srt_path = f"{output_path}.srt"
        try:
            if image_url.startswith('http://') or image_url.startswith('https://'):
                response = requests.get(image_url)
                response.raise_for_status()
                with open(temp_image_path, 'wb') as f:
                    f.write(response.content)
            else:
                # Assume it's a local file path
                if not os.path.exists(image_url):
                    raise FileNotFoundError(f"Local image file not found: {image_url}")
                shutil.copy2(image_url, temp_image_path)

            # 2. Prepare SRT if lyrics are provided
            has_subtitles = False
            if lyrics:
                has_subtitles = self._create_srt_file(lyrics, temp_srt_path)

            # 3. Use ffmpeg to combine image and audio (and burn subtitles if available)
            cmd = [
                "ffmpeg",
                "-y", # Overwrite output
                "-loop", "1",
                "-i", temp_image_path,
                "-i", audio_path,
            ]

            # Helper to execute ffmpeg
            def run_ffmpeg(subtitles_enabled):
                ffmpeg_cmd = cmd.copy()

                # Determine base filters depending on format
                base_vf = ""
                if video_format == "Vertical 9:16 (TikTok/Reels)":
                    # Scale the image to fit horizontally, pad vertically
                    base_vf = "[0:v]scale=1080:-1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black[v_base]"
                else:
                    # Standard 16:9, just scale/pad to 1920x1080
                    base_vf = "[0:v]scale=-1:1080,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black[v_base]"

                filters = [base_vf]

                # Add Audio-Reactive Visualizer
                if enable_visualizer:
                    w, h = ("1080", "150") if video_format == "Vertical 9:16 (TikTok/Reels)" else ("1920", "200")
                    y_pos = "(H-h)/2" # Center vertically

                    if visualizer_mode == "avectorscope":
                        vis_filter = f"[1:a]avectorscope=s={h}x{h}:draw=line:color=white[wave];[v_base][wave]overlay=x=(W-w)/2:y={y_pos}[v]"
                    else:
                        vis_filter = f"[1:a]showwaves=s={w}x{h}:mode={visualizer_mode}:colors=white@0.5[wave];[v_base][wave]overlay=x=0:y={y_pos}[v]"

                    filters.append(vis_filter)
                else:
                    # Just pass the base video through
                    filters.append("[v_base]copy[v]")

                if subtitles_enabled:
                    safe_srt_path = temp_srt_path.replace('\\', '/').replace(':', '\\:')
                    # Add subtitle filter on top of the mapped [v] stream

                    # Convert hex colors (#RRGGBB) to ASS format (&HBBGGRR&)
                    def to_ass_color(hex_str):
                        h = hex_str.lstrip('#')
                        if len(h) == 6:
                            return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}&"
                        return "&H00FFFFFF&"

                    p_color = to_ass_color(sub_primary_color)
                    o_color = to_ass_color(sub_outline_color)
                    b_color = to_ass_color(sub_back_color)
                    border_style = "3" if sub_box else "1" # 3 = Opaque box, 1 = Outline

                    force_style = f"FontSize={sub_font_size},PrimaryColour={p_color},OutlineColour={o_color},BackColour={b_color},BorderStyle={border_style}"
                    filters.append(f"[v]subtitles='{safe_srt_path}':force_style='{force_style}'[v_sub]")

                    ffmpeg_cmd.extend(["-filter_complex", ";".join(filters), "-map", "[v_sub]", "-map", "1:a"])
                else:
                    ffmpeg_cmd.extend(["-filter_complex", ";".join(filters), "-map", "[v]", "-map", "1:a"])

                ffmpeg_cmd.extend([
                    "-c:v", "libx264",
                    "-tune", "stillimage",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-shortest",
                    output_path
                ])
                logger.info(f"Running ffmpeg: {' '.join(ffmpeg_cmd)}")
                subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            max_retries = 3
            success = False
            for attempt in range(max_retries):
                try:
                    # Try with subtitles first if they exist
                    run_ffmpeg(has_subtitles)
                    logger.info(f"Video created at {output_path}")
                    success = True
                    break
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.decode()
                    logger.error(f"FFmpeg failed on attempt {attempt + 1}: {error_msg}")
                    if has_subtitles and attempt < max_retries - 1:
                        logger.warning("Sanitizing lyrics and retrying...")
                        # Basic sanitization: strip non-ascii
                        sanitized_lyrics = []
                        for line in lyrics:
                            new_line = line.copy()
                            new_line['text'] = "".join([c for c in line.get('text', '') if ord(c) < 128])
                            sanitized_lyrics.append(new_line)
                        self._create_srt_file(sanitized_lyrics, temp_srt_path)
                    else:
                        break

            if not success:
                if has_subtitles:
                    logger.warning("All subtitle retries failed. Retrying WITHOUT subtitles...")
                    run_ffmpeg(False)
                    logger.info(f"Video created at {output_path} (without subtitles fallback)")
                else:
                    raise RuntimeError("FFmpeg failed to create video after all retries.")

        except Exception as e:
            logger.error(f"Failed to create video: {e}")
            raise
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            if os.path.exists(temp_srt_path):
                os.remove(temp_srt_path)

    def _get_authenticated_service(self):
        """Authenticate and return the YouTube API service."""
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        token_path = "token.json"
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.client_secrets_file):
                     raise FileNotFoundError(f"Client secrets file not found at {self.client_secrets_file}. Cannot authenticate.")

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    def create_shorts(self, video_path, output_dir):
        """
        Extract 15-second short clips from the main video using FFmpeg.

        Args:
            video_path (str): Path to the main output video.
            output_dir (str): Base output directory.
        """
        shorts_dir = os.path.join(output_dir, "shorts")
        os.makedirs(shorts_dir, exist_ok=True)

        logger.info(f"Extracting 15-second shorts from {video_path} into {shorts_dir}...")

        filename = os.path.basename(video_path)
        name_no_ext = os.path.splitext(filename)[0]

        output_pattern = os.path.join(shorts_dir, f"{name_no_ext}_short_%03d.mp4")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-f", "segment",
            "-segment_time", "15",
            "-c", "copy",
            output_pattern
        ]

        try:
            logger.info(f"Running ffmpeg: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Shorts generated successfully in {shorts_dir}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode()
            logger.error(f"FFmpeg shorts extraction failed: {error_msg}")
            raise e

    def upload_to_youtube(self, video_path, metadata, progress_callback=None):
        """
        Upload the video to YouTube.

        Args:
            video_path (str): Path to the video file.
            metadata (dict): Metadata dictionary (title, description, tags).
            progress_callback (callable): Optional callback function for upload progress (takes integer 0-100).

        Returns:
            str: ID of the uploaded video.
        """
        logger.info(f"Uploading {video_path} to YouTube...")

        if not self.youtube:
            self.youtube = self._get_authenticated_service()

        body = {
            "snippet": {
                "title": metadata.get("title", "My New Song"),
                "description": metadata.get("description", "Generated by AI"),
                "tags": metadata.get("tags", []),
                "categoryId": "10" # Music
            },
            "status": {
                "privacyStatus": "private" # Default to private for safety
            }
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                logger.info(f"Uploaded {pct}%")
                if progress_callback:
                    progress_callback(pct)

        logger.info(f"Upload complete! Video ID: {response['id']}")
        return response['id']

if __name__ == "__main__":
    # Test video creation (requires dummy audio)
    producer = VideoProducer()

    # We need a dummy audio file for testing video creation
    test_audio = "hymn_remaker/output/test_hymn.wav" # created in step 2

    # Check if we have internet access or need to use a local file for testing
    test_image_url = "https://via.placeholder.com/1024.png"

    # For testing in an environment without internet/dummy purposes, we can write a local file
    # and bypass the download step if the URL is "file://..." or just handle it in the test block
    # But to keep the class clean, let's just mock the download if it's a local file path

    test_output = "hymn_remaker/output/test_video.mp4"

    if os.path.exists(test_audio):
        try:
            producer.create_video(test_audio, test_image_url, test_output)
        except Exception as e:
            logger.warning(f"Standard test failed (likely network): {e}")
            logger.info("Attempting local test...")
            # Create a dummy image
            from PIL import Image
            local_img = "hymn_remaker/output/test_art.png"
            Image.new('RGB', (1024, 1024), color='red').save(local_img)

            # Monkey patch requests.get to return file content
            class MockResponse:
                def __init__(self, content):
                    self.content = content
                def raise_for_status(self):
                    pass

            original_get = requests.get
            def mock_get(url):
                if url == "local_test_url":
                    with open(local_img, "rb") as f:
                        return MockResponse(f.read())
                return original_get(url)

            requests.get = mock_get
            producer.create_video(test_audio, "local_test_url", test_output)
            requests.get = original_get

    else:
        print(f"Test audio {test_audio} not found. Run step 2 first.")
