import unittest
from unittest.mock import patch, MagicMock
from hymn_remaker.src.s3_uploader import S3Uploader
import os

class TestS3Uploader(unittest.TestCase):
    @patch('hymn_remaker.src.s3_uploader.boto3.client')
    def test_upload_success(self, mock_boto):
        # Setup mock S3 client
        mock_client = MagicMock()
        mock_boto.return_value = mock_client

        uploader = S3Uploader(access_key="fake", secret_key="fake", region_name="us-west-2")

        # Test file upload (mocking os.path.exists so it doesn't fail)
        with patch('os.path.exists', return_value=True):
            url = uploader.upload_file("dummy.mp4", "test-bucket")

        mock_client.upload_file.assert_called_once_with(
            "dummy.mp4",
            "test-bucket",
            "dummy.mp4",
            ExtraArgs={'ACL': 'public-read', 'ContentType': 'video/mp4'}
        )
        self.assertEqual(url, "https://s3-us-west-2.amazonaws.com/test-bucket/dummy.mp4")

if __name__ == '__main__':
    unittest.main()
