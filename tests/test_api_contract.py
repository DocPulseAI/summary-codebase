from fastapi.testclient import TestClient
from unittest.mock import patch

from src.api import app


client = TestClient(app)


def test_generate_summary_returns_pipeline_metadata_envelope():
    payload = {
        "impact_report": {"report": {"analysis_summary": {"severity": "MINOR"}}},
        "drift_report": {"findings": [], "statistics": {"total_issues": 0}},
        "doc_snapshot": {
            "project_id": "proj-1",
            "commit": "abc12345",
            "docs_bucket_path": "proj-1/abc12345/docs/",
        },
        "commit_sha": "abc12345",
        "project_id": "proj-1",
        "run_id": "run-55",
        "ref_name": "main",
        "ref_type": "default_branch",
        "is_preview": True,
        "baseline_ref": "default",
    }

    with patch("src.api.SummaryGenerator.generate", return_value=("/tmp/summary.md", "/tmp/summary.json")), \
         patch("builtins.open") as open_mock, \
         patch("src.api._upload_summary_artifacts", return_value={"uploaded": True, "bucket_path": "x", "files": ["summary.md", "summary.json"], "error": None}):
        open_mock.return_value.__enter__.return_value.read.return_value = "# Summary"
        response = client.post("/generate-summary", json=payload)

    assert response.status_code == 200
    body = response.json()
    metadata = body["pipeline_metadata"]
    assert metadata["run_id"] == "run-55"
    assert metadata["ref_name"] == "main"
    assert metadata["ref_type"] == "default_branch"
    assert metadata["is_preview"] is True
    assert metadata["baseline_ref"] == "default"
    assert metadata["project_id"] == "proj-1"
    assert metadata["commit_sha"] == "abc12345"
    assert metadata["view_type"] == "preview"
    assert metadata["published_status"] == "preview"

