# Epic-4: Summary Generation Service

**Version:** 1.0.0
**Mode:** SUMMARY-ONLY
**Status:** Production Ready ✅

Epic-4 is a production-grade summary generation service that creates deterministic change summaries from impact and drift analysis reports. It operates in SUMMARY-ONLY mode, generating comprehensive documentation artifacts and uploading them to cloud storage.

## Features

- **Deterministic Summaries**: Generates consistent Markdown and JSON summaries from `impact_report.json` and `drift_report.json`
- **Cloud Storage Integration**: Uploads summary artifacts to R2/S3/GCS cloud storage
- **Dynamic Path Derivation**: Automatically derives storage paths from `doc_snapshot.json`
- **Comprehensive Analysis**: Includes severity assessment, API impact, risk analysis, and recommended actions
- **Fault Tolerant**: Handles missing drift reports gracefully; creates degraded summaries on failures
- **Security Hardened**: No credential logging; secure environment variable handling
- **Validated**: Comprehensive test suite with automated validation

## Installation

### Basic Installation

```bash
pip install -r requirements.txt
```

### With Cloud Storage Support

```bash
# Install with all cloud providers
pip install boto3  # For S3 and R2
pip install google-cloud-storage  # For GCS (optional)
```

## Quick Start

1. **Configure environment variables** (create `.env` file):
   ```bash
   R2_ACCOUNT_ID=your-account-id
   R2_ACCESS_KEY_ID=your-access-key
   R2_SECRET_ACCESS_KEY=your-secret-key
   R2_BUCKET_NAME=ci-living-docs
   ```

2. **Prepare input artifacts**:
   - `artifacts/impact_report.json` (required)
   - `artifacts/doc_snapshot.json` (required)
   - `artifacts/drift_report.json` (optional)

3. **Run the service**:
   ```bash
   python -m epic4.run
   ```

4. **Validate**:
   ```bash
   python validate_epic4.py
   ```

## Usage

### CLI Execution

```bash
python -m epic4.run \
    --impact artifacts/impact_report.json \
    --drift artifacts/drift_report.json \
    --commit <commit_sha>
```

### HTTP API Usage

Start the API server:

```bash
uvicorn epic4.api:app --host 0.0.0.0 --port 8000
```

Generate a summary via HTTP POST:

```bash
curl -X POST http://localhost:8000/generate-summary \
  -H "Content-Type: application/json" \
  -d '{
    "impact_report": { "report": { "analysis_summary": {"severity": "MAJOR", "breaking_changes": true, "files_changed": 114}}},
    "drift_report": {"findings": [], "statistics": {"total_issues": 0}},
    "doc_snapshot": {"project_id": "quiz-app-java", "generated_at": "2026-02-11T10:59:22Z", "commit": "63d36c2b"},
    "commit_sha": "63d36c2b"
  }'
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--impact` | Path to impact report JSON | `artifacts/impact_report.json` |
| `--drift` | Path to drift report JSON | `artifacts/drift_report.json` |
| `--docs` | Path to docs directory | `artifacts/docs` |
| `--commit` | Commit SHA | From environment or doc_snapshot.json |
| `--mode` | Execution mode | `SUMMARY_ONLY_MODE` |

## Input Requirements

### Required Artifacts

1. **impact_report.json** - Change impact analysis
   - Contains: severity, affected packages, API endpoints, breaking changes
   - Nested structure: `report.report.analysis_summary`

2. **doc_snapshot.json** - Documentation metadata
   - Required fields:
     - `project_id` - Project identifier
     - `commit` - Commit hash
     - `docs_bucket_path` - Base storage path (e.g., `"quiz-app-java/63d36c2b/docs/"`)

3. **drift_report.json** (optional) - Documentation drift analysis
   - Contains: drift findings, severity, statistics

## Output Artifacts

### Generated Files

```
artifacts/summaries/
├── summary.md          # Human-readable markdown summary
└── summary.json        # Machine-readable JSON summary
```

### Cloud Storage

Files are uploaded to:
```
<project_id>/<commit_hash>/docs/summary/
├── summary.md
└── summary.json
```

Example: `quiz-app-java/63d36c2b/docs/summary/`

### Response Format

```json
{
  "status": "success",
  "project_id": "quiz-app-java",
  "commit": "63d36c2b",
  "summary_bucket_path": "quiz-app-java/63d36c2b/docs/summary/",
  "generated_files": [
    "summary.md",
    "summary.json"
  ]
}
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `R2_ACCOUNT_ID` | Cloudflare R2 Account ID | Yes (for R2) | - |
| `R2_ACCESS_KEY_ID` | R2 Access Key ID | Yes (for R2) | - |
| `R2_SECRET_ACCESS_KEY` | R2 Secret Access Key | Yes (for R2) | - |
| `R2_BUCKET_NAME` | R2 Bucket Name | No | `ci-living-docs` |

| `ARTIFACTS_DIR` | Local artifacts directory | No | `artifacts` |
| `COMMIT_SHA` | Commit SHA (override) | No | From doc_snapshot.json |

### Cloud Storage Configuration

#### Cloudflare R2 (Recommended)

```bash
export R2_ACCOUNT_ID="your-account-id"
export R2_ACCESS_KEY_ID="your-access-key-id"
export R2_SECRET_ACCESS_KEY="your-secret-access-key"
export R2_BUCKET_NAME="ci-living-docs"
```

#### Amazon S3

```bash
# Uses AWS credentials from ~/.aws/credentials or IAM role
export R2_BUCKET_NAME="your-s3-bucket"
```

#### Google Cloud Storage

```bash
# Uses Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS
export R2_BUCKET_NAME="your-gcs-bucket"
```

## Summary Content

### summary.md (Human-Readable)

- **Commit Metadata**: SHA, author, timestamp, message
- **Impact Analysis**:
  - Severity level (MAJOR, MINOR, PATCH)
  - Changed files count
  - Affected symbols/packages
  - API impact summary
  - Affected components
- **Risk Assessment**: Breaking changes warnings, severity analysis
- **Recommended Actions**: Developer guidance based on changes
- **Drift Report**: Documentation drift findings (if available)

### summary.json (Machine-Readable)

Deterministic JSON structure with:
- `summary_version`: Schema version
- `commit_sha`: Commit identifier
- `severity`: Change severity level
- `changed_files_count`: Number of files changed
- `affected_symbols`: List of affected packages/modules
- `api_impact_summary`: API changes description
- `risk_assessment`: Risk analysis text
- `recommended_actions`: Sorted list of actions
- `drift_findings`: Drift issues (if available)

## Validation

Run the comprehensive validation script:

```bash
python validate_epic4.py
```

This validates:
- Input artifact validation
- Summary generation
- Response schema
- Generated files
- Cloud storage uploads

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_summary.py

# Run with coverage
pytest --cov=epic4 tests/
```

### Project Structure

```
epic-4/
├── epic4/
│   ├── run.py              # Main entry point
│   ├── summary.py          # Summary generation logic
│   ├── storage_client.py   # Cloud storage integration
│   ├── config.py           # Configuration management
│   └── utils.py            # Logging and utilities
├── artifacts/
│   ├── impact_report.json  # Input (required)
│   ├── doc_snapshot.json   # Input (required)
│   ├── drift_report.json   # Input (optional)
│   └── summaries/          # Output directory
├── tests/                  # Test suite
├── validate_epic4.py       # Validation script
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## Integration

### EPIC-2 (Documentation Generation)
- Consumes `doc_snapshot.json` from EPIC-2
- Uses `docs_bucket_path` for storage hierarchy

### EPIC-3 (Drift Detection)
- Optionally consumes `drift_report.json` from EPIC-3
- Includes drift findings in summary

### EPIC-5 (Dashboard)
- Provides `summary.json` for dashboard display
- Standardized schema for easy parsing

## Troubleshooting

### Common Issues

**Error: doc_snapshot.json not found**
```
Solution: Ensure EPIC-2 documentation generation ran successfully
```

**Error: docs_bucket_path not found in doc_snapshot.json**
```
Solution: Verify doc_snapshot.json contains the docs_bucket_path field
```

**Error: Upload failed**
```
Solution: Check R2 credentials in .env file
```

**Summary shows "UNKNOWN" for fields**
```
Solution: Verify impact_report.json structure matches expected format
```

## Security

- No credentials logged
- Secure environment variable handling
- No sensitive data in output files
- Proper error handling without credential exposure

## Observability

EPIC-4 now emits structured JSON logs for HTTP and upload stages.

- Request lifecycle events:
  - `EPIC4_HTTP_REQUEST_START`
  - `EPIC4_HTTP_REQUEST_END`
  - `EPIC4_HTTP_REQUEST_EXCEPTION`
- Summary generation events:
  - `EPIC4_GENERATE_REQUEST`
  - `EPIC4_GENERATE_SUCCESS`
  - `EPIC4_GENERATE_FAILED`
- Upload events:
  - `EPIC4_UPLOAD_START`
  - `EPIC4_UPLOAD_SUCCESS`
  - `EPIC4_UPLOAD_FAILED`
  - `EPIC4_UPLOAD_EXCEPTION`
  - `EPIC4_UPLOAD_SKIPPED`

Each response includes `X-Request-Id` so you can correlate upstream backend logs with EPIC-4 processing.

### Logging Controls

| Variable | Description | Default |
|----------|-------------|---------|
| `EPIC4_LOG_BODY_MAX_CHARS` | Max error/body preview length logged for failures | `1200` |

## Performance

- **Execution Time**: ~3 seconds (including cloud upload)
- **Memory Usage**: <100 MB
- **Deterministic**: Same input always produces same output
- **Retry Logic**: Exponential backoff for cloud operations

## Limitations

- **FULL_MODE**: Not implemented (PR creation disabled)
- **Commit Metadata**: Limited to data available in impact_report.json
- **Cloud Providers**: Tested with R2, S3, and GCS

## License

See LICENSE file for details.

## Support

For issues or questions:
1. Run `validate_epic4.py` for diagnostics
2. Check logs in console output
3. Review error messages for specific guidance
