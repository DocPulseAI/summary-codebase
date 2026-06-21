from typing import Dict, Any, List, Optional
from dataclasses import dataclass

class SummaryValidationError(Exception):
    pass

@dataclass
class RepositoryState:
    commit_hash: str
    author: str
    timestamp: str
    changed_files: List[str]
    changed_files_count: int
    api_endpoints: int
    affected_components: List[str]
    drift_findings: List[Dict[str, Any]]
    drift_detected: bool
    severity: str
    breaking_changes: bool

def _normalize_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) if not isinstance(v, (str, dict)) else (v.get("path", "") if isinstance(v, dict) else v) for v in value]
    return []

def normalize_repository_state(
    impact_report: Dict[str, Any],
    drift_report: Dict[str, Any],
    doc_snapshot: Dict[str, Any],
    commit_override: str = ""
) -> RepositoryState:
    
    # 1. Structural pre-flight checks (fail fast)
    if "report" in impact_report and isinstance(impact_report["report"], dict):
        if "report" in impact_report["report"]:
            impact_data = impact_report["report"]["report"]
        else:
            impact_data = impact_report["report"]
    else:
        impact_data = impact_report
        
    analysis_summary = impact_data.get("analysis_summary")
    if analysis_summary is None:
        raise SummaryValidationError("Missing required field: impact_report.analysis_summary")
    
    api_contract = impact_data.get("api_contract")
    if api_contract is None:
         raise SummaryValidationError("Missing required field: impact_report.api_contract")
        
    if not doc_snapshot:
        raise SummaryValidationError("Missing required artifact: doc_snapshot")
        
    if not drift_report:
        raise SummaryValidationError("Missing required artifact: drift_report")

    # 2. Extract commit metadata safely
    author = str(doc_snapshot.get("author", "Unknown"))
    
    commit_hash = str(doc_snapshot.get("commit_hash") or doc_snapshot.get("commit") or commit_override or "Unknown")
    
    timestamp = str(doc_snapshot.get("timestamp") or doc_snapshot.get("generated_at") or drift_report.get("generated_at") or "Unknown")

    # 3. Normalize Changed Files
    # Support doc_snapshot.changed_files AND doc_snapshot.analysis.files_changed
    raw_changed_files = doc_snapshot.get("changed_files") or []
    
    changed_files = _normalize_list(raw_changed_files)
    changed_files.sort()
    
    analysis_node = doc_snapshot.get("analysis", {})
    files_changed_explicit = analysis_node.get("files_changed")
    
    if files_changed_explicit is not None:
        changed_files_count = int(files_changed_explicit)
    else:
        changed_files_count = len(changed_files)
        
    # Internal Consistency Guard 1
    # Only enforce parity if the array was provided (not explicitly dropped upstream)
    if changed_files_count > 0 and len(changed_files) > 0:
        if changed_files_count != len(changed_files):
            raise SummaryValidationError(f"changed_files_count ({changed_files_count}) != len(changed_files) ({len(changed_files)})")
            
    # 4. Normalize Impact Details
    endpoints = api_contract.get("endpoints", [])
    api_endpoints = len(endpoints)
    
    affected_packages = impact_data.get("affected_packages") or impact_data.get("affected_symbols", [])
    affected_components = _normalize_list(affected_packages)
    affected_components.sort()
    
    severity = analysis_summary.get("highest_severity") or analysis_summary.get("severity") or impact_data.get("severity") or "UNKNOWN"
    breaking_changes = bool(analysis_summary.get("breaking_changes_detected", impact_data.get("breaking_changes", False)))
    
    # 5. Normalize Drift Statistics
    drift_detected = bool(drift_report.get("drift_detected", False))
    drift_findings = []
    
    if drift_detected:
        stats = drift_report.get("statistics", {})
        
        # Fallback cascade logic
        obsolete_count = stats.get("obsolete_documentation_count") 
        if obsolete_count is None:
            obsolete_count = stats.get("obsolete_endpoints")
        if obsolete_count is None:
            obsolete_count = stats.get("total_drift_issues")
        if obsolete_count is None:
            obsolete_count = 0
            
        if obsolete_count > 0:
            drift_findings.append({
                "type": "obsolete_documentation",
                "count": obsolete_count
            })

    # Internal Consistency Guard 2
    if drift_detected and len(drift_findings) == 0:
        raise SummaryValidationError("Drift detected but drift_findings is empty")
        
    return RepositoryState(
        commit_hash=commit_hash,
        author=author,
        timestamp=timestamp,
        changed_files=changed_files,
        changed_files_count=changed_files_count,
        api_endpoints=api_endpoints,
        affected_components=affected_components,
        drift_findings=drift_findings,
        drift_detected=drift_detected,
        severity=severity,
        breaking_changes=breaking_changes
    )
