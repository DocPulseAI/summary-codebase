from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from epic4.summary import generate_summary, SummaryGenerator
from epic4.storage_client import StorageClient
from epic4.config import config
from epic4.utils import logger
import os

# Comprehensive API metadata for Swagger documentation
app = FastAPI(
    title="Epic-4 Summary Generation Service",
    description="""
## 🚀 CI Living Documentation - Summary Generation API

Production-grade service for generating deterministic change summaries from impact and drift analysis reports.

### Features
- **Deterministic Summaries**: Consistent Markdown and JSON summaries
- **Cloud Storage Integration**: Automatic upload to R2/S3/GCS after generation
- **Fault Tolerant**: Handles missing drift reports gracefully
- **Security Hardened**: No credential logging

### Workflow
1. **Generate Summary**: Process impact and drift reports
2. **Upload Artifacts**: Automatically store summaries in cloud storage

### Links
- [GitHub Repository](https://github.com/kireeti-ai/ci-living-documentation)
- [Documentation](https://github.com/kireeti-ai/ci-living-documentation/tree/main/epic-4)
    """,
    version="1.0.0",
    contact={
        "name": "Epic-4 Team",
        "url": "https://github.com/kireeti-ai/ci-living-documentation",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and service status endpoints"
        },
        {
            "name": "summary",
            "description": "Summary generation and artifact upload operations"
        }
    ]
)

# ==================== Pydantic Models with Examples ====================

class HealthCheck(BaseModel):
    """Health check response model"""
    status: str = Field(
        ..., 
        description="Service health status",
        example="ok"
    )
    storage_configured: Optional[bool] = Field(
        None,
        description="Whether cloud storage is configured",
        example=True
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "storage_configured": True
            }
        }

class ImpactReport(BaseModel):
    """Impact report structure"""
    report: Dict[str, Any] = Field(
        ...,
        description="Nested impact analysis report",
        example={
            "report": {
                "analysis_summary": {
                    "severity": "MAJOR",
                    "breaking_changes": True,
                    "files_changed": 114
                }
            }
        }
    )

class DriftReport(BaseModel):
    """Drift report structure"""
    findings: List[Dict[str, Any]] = Field(
        default=[],
        description="List of drift findings",
        example=[]
    )
    statistics: Optional[Dict[str, Any]] = Field(
        None,
        description="Drift statistics",
        example={"total_issues": 0}
    )

class GenerateSummaryRequest(BaseModel):
    """Request model for summary generation"""
    impact_report: Dict[str, Any] = Field(
        ...,
        description="Impact analysis report containing severity, changed files, and affected symbols",
        example={
            "report": {
                "analysis_summary": {
                    "severity": "MAJOR",
                    "breaking_changes": True,
                    "files_changed": 114,
                    "affected_symbols": ["./config", "./middleware"],
                    "api_endpoints": 46
                }
            }
        }
    )
    drift_report: Dict[str, Any] = Field(
        ...,
        description="Documentation drift analysis report",
        example={
            "findings": [],
            "statistics": {"total_issues": 0}
        }
    )
    doc_snapshot: Dict[str, Any] = Field(
        default={},
        description="Documentation snapshot metadata (optional but recommended for commit details)",
        example={
            "project_id": "quiz-app-java",
            "generated_at": "2026-02-11T10:59:22Z",
            "commit": "63d36c2b"
        }
    )
    commit_sha: str = Field(
        ...,
        description="Git commit SHA (8+ characters)",
        example="63d36c2b",
        min_length=8
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "impact_report": {
                    "report": {
                        "analysis_summary": {
                            "severity": "MAJOR",
                            "breaking_changes": True,
                            "files_changed": 114
                        }
                    }
                },
                "drift_report": {
                    "findings": [],
                    "statistics": {"total_issues": 0}
                },
                "doc_snapshot": {
                    "project_id": "quiz-app-java",
                    "generated_at": "2026-02-11T10:59:22Z"
                },
                "commit_sha": "63d36c2b"
            }
        }

class UploadResult(BaseModel):
    """Upload result details"""
    uploaded: bool = Field(
        ...,
        description="Whether the upload to cloud storage was successful",
        example=True
    )
    bucket_path: Optional[str] = Field(
        None,
        description="Cloud storage path where artifacts were uploaded",
        example="quiz-app-java/63d36c2b/docs/summary/"
    )
    files: List[str] = Field(
        default=[],
        description="List of uploaded file names",
        example=["summary.md", "summary.json"]
    )
    error: Optional[str] = Field(
        None,
        description="Error message if upload failed",
        example=None
    )

class SummaryResponse(BaseModel):
    """Response model for summary generation and upload"""
    summary_markdown: str = Field(
        ...,
        description="Generated summary in Markdown format",
        example="# Change Summary\n\n**Commit SHA:** `63d36c2b`\n**Severity:** MAJOR\n\n## Impact Analysis\n..."
    )
    upload: Optional[UploadResult] = Field(
        None,
        description="Cloud storage upload result (null if storage not configured)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary_markdown": "# Change Summary\n\n**Commit SHA:** `63d36c2b`\n**Severity:** MAJOR\n\n## Impact Analysis\n### Changed Modules/Files (114)\n...",
                "upload": {
                    "uploaded": True,
                    "bucket_path": "quiz-app-java/63d36c2b/docs/summary/",
                    "files": ["summary.md", "summary.json"],
                    "error": None
                }
            }
        }

# ==================== API Endpoints ====================

@app.get(
    "/health",
    response_model=HealthCheck,
    tags=["health"],
    summary="Health Check",
    description="""
    Check the health status of the Epic-4 Summary Generation Service.
    
    Returns:
    - Service status (ok/degraded)
    - Storage configuration status
    
    This endpoint is used by monitoring systems and load balancers.
    """,
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "storage_configured": True
                    }
                }
            }
        }
    }
)
def health():
    """Health check endpoint for monitoring and load balancers"""
    storage_configured = bool(
        config.AZURE_CONTAINER_NAME and (
            config.AZURE_STORAGE_CONNECTION_STRING or
            (config.AZURE_STORAGE_ACCOUNT_URL and config.AZURE_STORAGE_ACCOUNT_KEY)
        )
    )
    return {
        "status": "ok",
        "storage_configured": storage_configured
    }

@app.post(
    "/generate-summary",
    response_model=SummaryResponse,
    tags=["summary"],
    summary="Generate Change Summary",
    description="""
    Generate a deterministic change summary from impact and drift analysis reports,
    and automatically upload artifacts to cloud storage.
    
    ### Process Flow:
    1. Accepts impact_report, drift_report, and optional doc_snapshot as JSON
    2. Generates comprehensive Markdown and JSON summaries
    3. Uploads artifacts to cloud storage (if configured via doc_snapshot)
    4. Returns formatted summary content with upload status
    
    ### Input Requirements:
    - **impact_report**: Must contain nested structure with analysis_summary
    - **drift_report**: Optional drift findings and statistics
    - **doc_snapshot**: Optional metadata (project_id, timestamp) for richer summary
    - **commit_sha**: 8+ character Git commit hash
    
    ### Output:
    - Human-readable Markdown summary with:
      - Commit metadata (Author, Time, Message)
      - Impact analysis (severity, changed files, affected symbols)
      - API impact summary
      - Risk assessment
      - Recommended actions
      - Drift findings (if available)
    - Upload result (if cloud storage is configured)
    
    ### Error Handling:
    - Returns 500 if summary generation fails
    - Validates input schema before processing
    """,
    responses={
        200: {
            "description": "Summary generated and uploaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "summary_markdown": "# Change Summary\n\n**Commit SHA:** `63d36c2b`\n**Severity:** MAJOR\n\n## Impact Analysis\n### Changed Modules/Files (114)\n...",
                        "upload": {
                            "uploaded": True,
                            "bucket_path": "quiz-app-java/63d36c2b/docs/summary/",
                            "files": ["summary.md", "summary.json"],
                            "error": None
                        }
                    }
                }
            }
        },
        422: {
            "description": "Validation error - invalid input format"
        },
        500: {
            "description": "Internal server error - summary generation failed"
        }
    }
)
def api_generate_summary(req: GenerateSummaryRequest):
    """
    Generate a comprehensive change summary from impact and drift reports,
    then upload artifacts to cloud storage.
    
    This endpoint processes the provided reports, generates a deterministic
    Markdown summary, and uploads summary.md + summary.json to cloud storage.
    """
    try:
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            impact_path = os.path.join(tmpdir, "impact.json")
            drift_path = os.path.join(tmpdir, "drift.json")

            with open(impact_path, 'w') as f:
                json.dump(req.impact_report, f)
            with open(drift_path, 'w') as f:
                json.dump(req.drift_report, f)

            generator = SummaryGenerator(
                impact_report_path=impact_path, 
                drift_report_path=drift_path, 
                commit_sha=req.commit_sha, 
                output_dir=tmpdir,
                doc_snapshot=req.doc_snapshot
            )
            output_path_md, output_path_json = generator.generate()
            
            with open(output_path_md, 'r') as f:
                content = f.read()

            # --- Upload to cloud storage ---
            upload_result = _upload_summary_artifacts(
                output_path_md, output_path_json, req.doc_snapshot, req.commit_sha
            )

            return {
                "summary_markdown": content,
                "upload": upload_result
            }

    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Summary generation failed: {str(e)}"
        )

def _upload_summary_artifacts(
    summary_md_path: str,
    summary_json_path: str,
    doc_snapshot: Dict[str, Any],
    commit_sha: str
) -> Dict[str, Any]:
    """
    Upload summary artifacts to cloud storage.
    Derives the upload path from doc_snapshot's docs_bucket_path.
    
    Returns:
        dict with keys: uploaded, bucket_path, files, error
    """
    # Derive upload path from doc_snapshot
    docs_bucket_path = None
    if doc_snapshot:
        docs_bucket_path = doc_snapshot.get("docs_bucket_path")
    
    # Fallback to config if not provided in doc_snapshot
    if not docs_bucket_path:
        docs_bucket_path = config.DOCS_BUCKET_PATH
    
    if not docs_bucket_path:
        logger.info("No docs_bucket_path available — skipping cloud upload")
        return {
            "uploaded": False,
            "bucket_path": None,
            "files": [],
            "error": "No docs_bucket_path configured (provide in doc_snapshot or DOCS_BUCKET_PATH env)"
        }
    
    # Build the summary bucket path: <docs_bucket_path>summary/
    summary_path_relative = docs_bucket_path
    if not summary_path_relative.endswith('/'):
        summary_path_relative += '/'
    summary_path_relative += "summary/"
    
    # Construct full Azure URI
    summary_bucket_uri = f"az://{config.AZURE_CONTAINER_NAME}/{summary_path_relative}"
    logger.info(f"Uploading summary artifacts to {summary_bucket_uri}")
    
    try:
        storage_client = StorageClient()
        upload_md = storage_client.upload_file(summary_md_path, summary_bucket_uri)
        upload_json = storage_client.upload_file(summary_json_path, summary_bucket_uri)
        
        if upload_md and upload_json:
            logger.info("Summary artifacts uploaded successfully")
            return {
                "uploaded": True,
                "bucket_path": summary_path_relative,
                "files": ["summary.md", "summary.json"],
                "error": None
            }
        else:
            error_msg = "One or more artifact uploads failed"
            logger.error(error_msg)
            return {
                "uploaded": False,
                "bucket_path": summary_path_relative,
                "files": [],
                "error": error_msg
            }
    except Exception as e:
        error_msg = f"Upload failed: {str(e)}"
        logger.error(error_msg)
        return {
            "uploaded": False,
            "bucket_path": summary_path_relative,
            "files": [],
            "error": error_msg
        }
