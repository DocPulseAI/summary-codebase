import pytest

from epic4.artifact_normalizer import SummaryValidationError, normalize_repository_state


def _minimal_valid_impact():
    return {
        "analysis_summary": {
            "highest_severity": "MINOR",
            "breaking_changes_detected": False,
        },
        "api_contract": {
            "endpoints": [{"path": "/users"}],
        },
        "affected_symbols": ["b.mod", "a.mod"],
    }


def _minimal_valid_doc_snapshot():
    return {
        "author": "alice",
        "commit": "abc12345",
        "generated_at": "2026-01-01T00:00:00Z",
        "changed_files": ["b.py", "a.py"],
    }


def test_normalize_repository_state_sorts_and_normalizes_lists():
    state = normalize_repository_state(
        impact_report=_minimal_valid_impact(),
        drift_report={"drift_detected": False},
        doc_snapshot=_minimal_valid_doc_snapshot(),
        commit_override="override-ignored",
    )

    assert state.commit_hash == "abc12345"
    assert state.changed_files == ["a.py", "b.py"]
    assert state.changed_files_count == 2
    assert state.api_endpoints == 1
    assert state.affected_components == ["a.mod", "b.mod"]
    assert state.severity == "MINOR"
    assert state.breaking_changes is False


def test_normalize_repository_state_raises_when_analysis_summary_missing():
    with pytest.raises(SummaryValidationError, match="Missing required field: impact_report.analysis_summary"):
        normalize_repository_state(
            impact_report={"api_contract": {"endpoints": []}},
            drift_report={"drift_detected": False},
            doc_snapshot=_minimal_valid_doc_snapshot(),
        )


def test_normalize_repository_state_raises_when_api_contract_missing():
    with pytest.raises(SummaryValidationError, match="Missing required field: impact_report.api_contract"):
        normalize_repository_state(
            impact_report={"analysis_summary": {"highest_severity": "PATCH"}},
            drift_report={"drift_detected": False},
            doc_snapshot=_minimal_valid_doc_snapshot(),
        )


def test_normalize_repository_state_raises_on_file_count_mismatch_when_array_present():
    snapshot = _minimal_valid_doc_snapshot()
    snapshot["analysis"] = {"files_changed": 3}

    with pytest.raises(SummaryValidationError, match=r"changed_files_count \(3\) != len\(changed_files\) \(2\)"):
        normalize_repository_state(
            impact_report=_minimal_valid_impact(),
            drift_report={"drift_detected": False},
            doc_snapshot=snapshot,
        )


def test_normalize_repository_state_raises_when_drift_detected_but_no_findings():
    with pytest.raises(SummaryValidationError, match="Drift detected but drift_findings is empty"):
        normalize_repository_state(
            impact_report=_minimal_valid_impact(),
            drift_report={"drift_detected": True, "statistics": {"obsolete_documentation_count": 0}},
            doc_snapshot=_minimal_valid_doc_snapshot(),
        )


def test_normalize_repository_state_populates_drift_findings_with_fallback_count_keys():
    state = normalize_repository_state(
        impact_report=_minimal_valid_impact(),
        drift_report={"drift_detected": True, "statistics": {"obsolete_endpoints": 2}},
        doc_snapshot=_minimal_valid_doc_snapshot(),
    )

    assert state.drift_detected is True
    assert state.drift_findings == [{"type": "obsolete_documentation", "count": 2}]
