import unittest
from unittest.mock import patch
from hymn_remaker.src.webhook_notifier import WebhookNotifier

class TestWebhookNotifier(unittest.TestCase):
    @patch('hymn_remaker.src.webhook_notifier.requests.post')
    def test_send_notification(self, mock_post):
        notifier = WebhookNotifier(webhook_url="http://fake-webhook")

        result = notifier.send_notification("Test Title", "Test Desc", style="Deep House", s3_video_url="http://s3/video.mp4")

        self.assertTrue(result)
        mock_post.assert_called_once()

        # Verify payload structure
        call_args = mock_post.call_args
        import json
        payload = json.loads(call_args.kwargs['data'])
        self.assertEqual(payload['embeds'][0]['title'], "Test Title")
        self.assertEqual(len(payload['embeds'][0]['fields']), 2) # Style and Video fields

if __name__ == '__main__':
    unittest.main()
