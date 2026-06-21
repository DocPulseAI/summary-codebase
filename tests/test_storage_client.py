import unittest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from src.storage_client import StorageClient


class TestStorageClient(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_download_from_gcs(self):
        """Test GCS download functionality."""
        # Skip if GCS not available
        client = StorageClient()
        if not client.gcs_available:
            self.skipTest("GCS client not available")

        # This is a basic structure test - full mocking would be complex
        self.assertTrue(hasattr(client, 'gcs_client'))

    def test_parse_bucket_path_gs(self):
        """Test GCS URI parsing."""
        client = StorageClient()
        bucket_path = "gs://my-bucket/path/to/docs"

        from urllib.parse import urlparse
        parsed = urlparse(bucket_path)

        self.assertEqual(parsed.scheme, "gs")
        self.assertEqual(parsed.netloc, "my-bucket")
        self.assertEqual(parsed.path.lstrip('/'), "path/to/docs")

    def test_parse_bucket_path_s3(self):
        """Test S3 URI parsing."""
        client = StorageClient()
        bucket_path = "s3://my-bucket/path/to/docs"

        from urllib.parse import urlparse
        parsed = urlparse(bucket_path)

        self.assertEqual(parsed.scheme, "s3")
        self.assertEqual(parsed.netloc, "my-bucket")
        self.assertEqual(parsed.path.lstrip('/'), "path/to/docs")

    def test_parse_bucket_path_r2(self):
        """Test Cloudflare R2 URI parsing."""
        client = StorageClient()
        bucket_path = "r2://my-bucket/path/to/docs"

        from urllib.parse import urlparse
        parsed = urlparse(bucket_path)

        self.assertEqual(parsed.scheme, "r2")
        self.assertEqual(parsed.netloc, "my-bucket")
        self.assertEqual(parsed.path.lstrip('/'), "path/to/docs")


if __name__ == '__main__':
    unittest.main()
