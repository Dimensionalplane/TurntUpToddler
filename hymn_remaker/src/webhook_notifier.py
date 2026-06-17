import requests
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookNotifier:
    def __init__(self, webhook_url=None):
        """
        Initialize the Webhook Notifier.

        Args:
            webhook_url (str or dict): The Discord/Slack compatible webhook URL,
                                       or a dict mapping channel names to URLs.
        """
        self.webhooks = {"default": webhook_url} if isinstance(webhook_url, str) else (webhook_url or {})

    def send_notification(self, title, description, s3_video_url=None, youtube_url=None, s3_audio_url=None, style=None, color=5814783, channel="default"):
        """
        Send a rich embed notification to a Discord webhook.

        Args:
            title (str): Title of the embed.
            description (str): Description or body text.
            s3_video_url (str): Public URL of the generated video.
            youtube_url (str): YouTube URL if uploaded.
            s3_audio_url (str): Public URL of the generated audio.
            style (str): The musical style prompt used.
            color (int): Decimal color code for the embed.

        Returns:
            bool: True if successful, False otherwise.
        """
        target_url = self.webhooks.get(channel)
        if not target_url:
            logger.warning(f"No webhook URL configured for channel '{channel}'. Skipping notification.")
            return False

        logger.info(f"Sending webhook notification to {target_url.split('/api/webhooks/')[0]} (channel: {channel})...")

        # Construct Discord-style Rich Embed
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Hymn Remaker AI Pipeline"
            },
            "fields": []
        }

        if style:
            embed["fields"].append({"name": "Style", "value": style, "inline": True})

        if youtube_url:
            embed["fields"].append({"name": "YouTube Link", "value": f"[Watch on YouTube]({youtube_url})", "inline": False})

        if s3_video_url:
            embed["fields"].append({"name": "Raw MP4", "value": f"[Download MP4]({s3_video_url})", "inline": True})

        if s3_audio_url:
            embed["fields"].append({"name": "Raw WAV", "value": f"[Download WAV]({s3_audio_url})", "inline": True})

        payload = {
            "username": "Hymn Remaker Bot",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/2995/2995101.png",
            "embeds": [embed]
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(target_url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            logger.info("Webhook notification sent successfully.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        notifier = WebhookNotifier(webhook_url=sys.argv[1])
        notifier.send_notification("Test Hymn Generated", "This is a test notification from the CLI.", style="Deep House", s3_video_url="https://example.com/video.mp4")
    else:
        print("Usage: python webhook_notifier.py <webhook_url>")
