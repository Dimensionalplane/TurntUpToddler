import os
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

    def create_video(self, audio_path, image_url, output_path, lyrics=None, use_visualizer=False):
        """
        Create an MP4 video from an audio file, image URL, and optional lyrics using ffmpeg.

        Args:
            audio_path (str): Path to the input audio file.
            image_url (str): URL of the album art image.
            output_path (str): Path to the output video file.
            lyrics (list): Optional list of synced lyrics dicts.
            use_visualizer (bool): If True, use a dynamic ffmpeg waveform instead of the static image.
        """
        logger.info(f"Creating video from {audio_path}...")

        import uuid
        unique_id = uuid.uuid4().hex
        temp_image_path = f"temp_art_{unique_id}.png"
        temp_srt_path = f"{output_path}.srt"

        try:
            if not use_visualizer:
                # 1. Download the image to a temporary file if we are using static art
                response = requests.get(image_url)
                response.raise_for_status()
                with open(temp_image_path, 'wb') as f:
                    f.write(response.content)

            # 2. Prepare SRT if lyrics are provided
            has_subtitles = False
            if lyrics:
                has_subtitles = self._create_srt_file(lyrics, temp_srt_path)

            # 3. Setup core ffmpeg command depending on visualizer toggle
            if use_visualizer:
                # Complex filter for showwaves visualizer. Needs a background to draw on
                # We create a black background first, then input the audio
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "lavfi",
                    "-i", "color=c=black:s=1920x1080",
                    "-i", audio_path,
                ]
            else:
                # Static image loop
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-loop", "1",
                    "-i", temp_image_path,
                    "-i", audio_path,
                ]

            # Helper to execute ffmpeg
            def run_ffmpeg(subtitles_enabled):
                ffmpeg_cmd = cmd.copy()

                # Build the video filter
                vf_filters = []
                if use_visualizer:
                    # [VISUALIZER GENERATION LOGIC]
                    # We use ffmpeg's 'showwaves' filter to create a dynamic, moving waveform of the audio.
                    # We output it, scale it, and overlay it on the black background.
                    vf_filters.append("[1:a]showwaves=s=1920x1080:mode=cline:colors=cyan[v];[0:v][v]overlay=format=auto")

                if subtitles_enabled:
                    safe_srt_path = temp_srt_path.replace('\\', '/').replace(':', '\\:')
                    if use_visualizer:
                        # Append the subtitles to the overlay output
                        vf_filters.append(f"subtitles='{safe_srt_path}'")
                    else:
                        vf_filters.append(f"subtitles='{safe_srt_path}'")

                if vf_filters:
                    # Combine filters with commas if multiple exist
                    if use_visualizer:
                        # For complex graphs with multiple inputs/outputs, commas won't work perfectly if chaining
                        # We chain the overlay into the subtitles if both exist
                        filter_str = "[1:a]showwaves=s=1920x1080:mode=cline:colors=cyan[wave];[0:v][wave]overlay=format=auto[out1]"
                        if subtitles_enabled:
                            safe_srt_path = temp_srt_path.replace('\\', '/').replace(':', '\\:')
                            filter_str += f";[out1]subtitles='{safe_srt_path}'[out2]"
                            ffmpeg_cmd.extend(["-filter_complex", filter_str, "-map", "[out2]", "-map", "1:a"])
                        else:
                            ffmpeg_cmd.extend(["-filter_complex", filter_str, "-map", "[out1]", "-map", "1:a"])
                    else:
                        ffmpeg_cmd.extend(["-vf", ",".join(vf_filters)])

                # Encoding parameters
                ffmpeg_cmd.extend([
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-shortest",
                    output_path
                ])

                # If using static art, we want to tune for stillimage to save space
                if not use_visualizer:
                    ffmpeg_cmd.insert(ffmpeg_cmd.index("-c:v") + 2, "-tune")
                    ffmpeg_cmd.insert(ffmpeg_cmd.index("-tune") + 1, "stillimage")

                logger.info(f"Running ffmpeg: {' '.join(ffmpeg_cmd)}")
                subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            try:
                # Try with subtitles first if they exist
                run_ffmpeg(has_subtitles)
                logger.info(f"Video created at {output_path}")
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode()
                logger.error(f"FFmpeg failed: {error_msg}")
                if has_subtitles:
                    logger.warning("FFmpeg failed with subtitles. Retrying WITHOUT subtitles...")
                    run_ffmpeg(False)
                    logger.info(f"Video created at {output_path} (without subtitles fallback)")
                else:
                    raise

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

    def upload_to_youtube(self, video_path, metadata):
        """
        Upload the video to YouTube.

        Args:
            video_path (str): Path to the video file.
            metadata (dict): Metadata dictionary (title, description, tags).

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
                logger.info(f"Uploaded {int(status.progress() * 100)}%")

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
