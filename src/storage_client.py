import os
import shutil
from typing import Optional
from urllib.parse import urlparse
from src.utils import logger, get_retry_decorator

retry_with_backoff = get_retry_decorator()


class StorageClient:
    """
    Cloud storage client for downloading documentation artifacts.
    Supports gs:// (Google Cloud Storage), s3:// (AWS S3), r2:// (Cloudflare R2),
    and az:// (Azure Blob Storage) URIs.
    """

    def __init__(self):
        from src.config import config

        self.gcs_available = False
        self.s3_available = False
        self.r2_available = False

        try:
            from google.cloud import storage
            self.gcs_client = storage.Client()
            self.gcs_available = True
            logger.info("Google Cloud Storage client initialized")
        except ImportError:
            logger.warning("google-cloud-storage not installed - GCS support disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize GCS client: {e}")

        try:
            import boto3
            self.s3_client = boto3.client('s3')
            self.s3_available = True
            logger.info("AWS S3 client initialized")
        except ImportError:
            logger.warning("boto3 not installed - S3 support disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize S3 client: {e}")

        # Initialize Cloudflare R2 client (S3-compatible)
        if config.R2_ACCOUNT_ID and config.R2_ACCESS_KEY_ID and config.R2_SECRET_ACCESS_KEY:
            try:
                import boto3
                endpoint_url = f"https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
                self.r2_client = boto3.client(
                    's3',
                    endpoint_url=endpoint_url,
                    aws_access_key_id=config.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
                    region_name='auto'  # R2 uses 'auto' region
                )
                self.r2_available = True
                logger.info("Cloudflare R2 client initialized")
            except ImportError:
                logger.warning("boto3 not installed - R2 support disabled")
            except Exception as e:
                logger.warning(f"Failed to initialize R2 client: {e}")
        else:
            logger.info("R2 credentials not provided - R2 support disabled")

    @retry_with_backoff
    def download_from_gcs(self, bucket_name: str, prefix: str, local_dir: str) -> int:
        """Download all files from GCS bucket path to local directory."""
        if not self.gcs_available:
            raise RuntimeError("GCS client not available")

        from google.cloud import storage
        bucket = self.gcs_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)

        count = 0
        for blob in blobs:
            # Skip directories
            if blob.name.endswith('/'):
                continue

            # Construct local path
            rel_path = blob.name[len(prefix):].lstrip('/')
            local_path = os.path.join(local_dir, rel_path)

            # Create parent directories
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded {blob.name} to {local_path}")
            count += 1

        return count

    @retry_with_backoff
    def download_from_s3(self, bucket_name: str, prefix: str, local_dir: str) -> int:
        """Download all files from S3 bucket path to local directory."""
        if not self.s3_available:
            raise RuntimeError("S3 client not available")

        paginator = self.s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        count = 0
        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']

                # Skip directories
                if key.endswith('/'):
                    continue

                # Construct local path
                rel_path = key[len(prefix):].lstrip('/')
                local_path = os.path.join(local_dir, rel_path)

                # Create parent directories
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Download
                self.s3_client.download_file(bucket_name, key, local_path)
                logger.info(f"Downloaded {key} to {local_path}")
                count += 1

        return count

    @retry_with_backoff
    def download_from_r2(self, bucket_name: str, prefix: str, local_dir: str) -> int:
        """Download all files from Cloudflare R2 bucket to local directory."""
        if not self.r2_available:
            raise RuntimeError("R2 client not available - check R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")

        paginator = self.r2_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        count = 0
        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']

                # Skip directories
                if key.endswith('/'):
                    continue

                # Construct local path
                rel_path = key[len(prefix):].lstrip('/')
                local_path = os.path.join(local_dir, rel_path)

                # Create parent directories
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Download
                self.r2_client.download_file(bucket_name, key, local_path)
                logger.info(f"Downloaded {key} to {local_path}")
                count += 1

        return count

    def download_artifacts(self, bucket_path: str, local_dir: str) -> bool:
        """
        Download artifacts from cloud storage to local directory.

        Args:
            bucket_path: Cloud storage URI:
                - gs://bucket/path (Google Cloud Storage)
                - s3://bucket/path (AWS S3)
                - r2://bucket/path (Cloudflare R2)
            local_dir: Local directory to download to

        Returns:
            True if successful, False otherwise
        """
        if not bucket_path:
            logger.info("No bucket path provided, skipping cloud download")
            return False

        try:
            parsed = urlparse(bucket_path)
            scheme = parsed.scheme
            bucket_name = parsed.netloc
            prefix = parsed.path.lstrip('/')

            os.makedirs(local_dir, exist_ok=True)

            if scheme == 'gs':
                count = self.download_from_gcs(bucket_name, prefix, local_dir)
                logger.info(f"Downloaded {count} files from GCS")
                return True
            elif scheme == 's3':
                count = self.download_from_s3(bucket_name, prefix, local_dir)
                logger.info(f"Downloaded {count} files from S3")
                return True
            elif scheme == 'r2':
                count = self.download_from_r2(bucket_name, prefix, local_dir)
                logger.info(f"Downloaded {count} files from Cloudflare R2")
                return True
            else:
                logger.error(f"Unsupported storage scheme: {scheme}. Supported: gs://, s3://, r2://")
                return False

        except Exception as e:
            logger.error(f"Failed to download from cloud storage: {e}")
            return False

    @retry_with_backoff
    def upload_to_r2(self, local_path: str, bucket_name: str, key: str) -> bool:
        """Upload a file to Cloudflare R2 bucket."""
        if not self.r2_available:
            raise RuntimeError("R2 client not available")

        try:
            self.r2_client.upload_file(local_path, bucket_name, key)
            logger.info(f"Uploaded {local_path} to r2://{bucket_name}/{key}")
            return True
        except Exception as e:
            try:
                from botocore.exceptions import NoCredentialsError, PartialCredentialsError
                if isinstance(e, (NoCredentialsError, PartialCredentialsError)):
                    logger.error("R2 credentials missing; skipping upload")
                    return False
            except Exception:
                pass
            raise

    @retry_with_backoff
    def upload_to_s3(self, local_path: str, bucket_name: str, key: str) -> bool:
        """Upload a file to AWS S3 bucket."""
        if not self.s3_available:
            raise RuntimeError("S3 client not available")

        try:
            self.s3_client.upload_file(local_path, bucket_name, key)
            logger.info(f"Uploaded {local_path} to s3://{bucket_name}/{key}")
            return True
        except Exception as e:
            try:
                from botocore.exceptions import NoCredentialsError, PartialCredentialsError
                if isinstance(e, (NoCredentialsError, PartialCredentialsError)):
                    logger.error("AWS credentials missing; skipping upload")
                    return False
            except Exception:
                pass
            raise

    @retry_with_backoff
    def upload_to_gcs(self, local_path: str, bucket_name: str, key: str) -> bool:
        """Upload a file to Google Cloud Storage bucket."""
        if not self.gcs_available:
            raise RuntimeError("GCS client not available")

        from google.cloud import storage
        bucket = self.gcs_client.bucket(bucket_name)
        blob = bucket.blob(key)
        blob.upload_from_filename(local_path)
        logger.info(f"Uploaded {local_path} to gs://{bucket_name}/{key}")
        return True

    def upload_file(self, local_path: str, bucket_path_prefix: str) -> bool:
        """
        Upload a file to cloud storage.

        Args:
            local_path: Path to the local file to upload.
            bucket_path_prefix: Cloud storage URI prefix where the file should be uploaded.
                                Depending on strategy, this could be the full path or just a directory prefix.
                                Here we treat it as a directory prefix if it ends with /, otherwise as full path?
                                Usually for CI artifacts we want to upload with specific names.
                                Let's assume bucket_path_prefix is the DIRECTORY where we put the file.
                                e.g. s3://my-bucket/ci-runs/123/
        """
        if not bucket_path_prefix:
            logger.error("No bucket path provided for upload")
            return False

        if not os.path.exists(local_path):
            logger.error(f"File to upload not found: {local_path}")
            return False

        try:
            parsed = urlparse(bucket_path_prefix)
            scheme = parsed.scheme
            bucket_name = parsed.netloc
            prefix = parsed.path.lstrip('/') # This is the directory path in the bucket

            filename = os.path.basename(local_path)
            # If prefix is empty, key is just filename. If prefix present, join.
            # Avoid double slashes.
            if prefix and not prefix.endswith('/'):
                 prefix += '/'
            
            key = f"{prefix}{filename}"

            if scheme == 'gs':
                return self.upload_to_gcs(local_path, bucket_name, key)
            elif scheme == 's3':
                return self.upload_to_s3(local_path, bucket_name, key)
            elif scheme == 'r2':
                return self.upload_to_r2(local_path, bucket_name, key)
            else:
                logger.error(f"Unsupported storage scheme: {scheme}")
                return False

        except Exception as e:
            logger.error(f"Failed to upload to cloud storage: {e}")
            return False
