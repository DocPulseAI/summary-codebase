import os
from typing import Optional

# Load environment variables from .env if present.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

class Config:
    EXECUTION_MODE: str = os.getenv("MODE", os.getenv("EPIC4_MODE", "FULL_MODE"))
    REPO_OWNER: str = os.getenv("REPO_OWNER", "")
    REPO_NAME: str = os.getenv("REPO_NAME", "")
    TARGET_BRANCH: str = os.getenv("TARGET_BRANCH", "main")
    COMMIT_SHA: str = os.getenv("COMMIT_SHA", "")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    CI_RUN_ID: str = os.getenv("CI_RUN_ID", "")

    # Artifact paths defaults
    ARTIFACTS_DIR: str = os.getenv("ARTIFACTS_DIR", "artifacts")
    IMPACT_REPORT_PATH: str = os.path.join(ARTIFACTS_DIR, "impact_report.json")
    DRIFT_REPORT_PATH: str = os.path.join(ARTIFACTS_DIR, "drift_report.json")
    DOC_SNAPSHOT_PATH: str = os.path.join(ARTIFACTS_DIR, "doc_snapshot.json")
    DOCS_DIR: str = os.path.join(ARTIFACTS_DIR, "docs")
    DOCS_BUCKET_PATH: str = os.getenv("DOCS_BUCKET_PATH", "")  # Cloud storage path for Epic-2 docs
    SUMMARIES_DIR: str = os.path.join(ARTIFACTS_DIR, "summaries")
    LOGS_DIR: str = os.path.join(ARTIFACTS_DIR, "logs")

    # Cloudflare R2 configuration (S3-compatible)
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "ci-living-docs")  # Default bucket name

    # Azure Blob Storage configuration
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_STORAGE_ACCOUNT_URL: str = os.getenv("AZURE_STORAGE_ACCOUNT_URL", "")
    AZURE_STORAGE_ACCOUNT_KEY: str = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "")
    AZURE_CONTAINER_NAME: str = os.getenv("AZURE_CONTAINER_NAME", "ci-living-docs")


    @classmethod
    def validate(cls, require_git: bool = True):
        missing = []
        if require_git:
            if not cls.REPO_OWNER:
                missing.append("REPO_OWNER")
            if not cls.REPO_NAME:
                missing.append("REPO_NAME")
            if not cls.GITHUB_TOKEN:
                missing.append("GITHUB_TOKEN")

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

config = Config()
