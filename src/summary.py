import json
import os
from typing import Dict, Any, List, Tuple, Optional
from src.config import config
from src.utils import logger
from src.artifact_normalizer import normalize_repository_state, SummaryValidationError

class SummaryGenerator:
    def __init__(self, impact_report_path: str, drift_report_path: str, commit_sha: str, output_dir: str, doc_snapshot: Optional[Dict[str, Any]] = None):
        self.impact_report_path = impact_report_path
        self.drift_report_path = drift_report_path
        self.commit_sha = commit_sha
        self.output_dir = output_dir
        self.doc_snapshot = doc_snapshot or {}

    def load_json(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            logger.warning(f"File not found: {path}. Returning empty dict.")
            return {}
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from {path}: {e}")
            return {}

    def generate(self) -> Tuple[str, str]:
        if not os.path.exists(self.impact_report_path):
            raise FileNotFoundError(f"Critical artifact missing: {self.impact_report_path}")

        impact = self.load_json(self.impact_report_path)
        drift = self.load_json(self.drift_report_path) if self.drift_report_path else {}
        doc_snapshot = self.doc_snapshot or {}

        summary_payload = self._build_summary_payload(impact, drift, doc_snapshot)

        summary_md = self._render_template(summary_payload)
        summary_payload["summary"] = summary_md # Add rendered MD for the UI
        summary_json = summary_payload.copy()

        # Contract-mandated filenames for Epic-5 dashboard integration
        output_filename_md = "summary.md"
        output_filename_json = "summary.json"
        
        output_path_md = os.path.join(self.output_dir, output_filename_md)
        output_path_json = os.path.join(self.output_dir, output_filename_json)

        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save MD
        with open(output_path_md, 'w') as f:
            f.write(summary_md)
            
        # Save JSON
        with open(output_path_json, 'w') as f:
            json.dump(summary_json, f, indent=2, sort_keys=True)

        logger.info(f"Summary generated at {output_path_md} and {output_path_json}")
        return output_path_md, output_path_json

    def _build_summary_payload(self, impact: Dict[str, Any], drift: Dict[str, Any], doc_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        # Normalize incoming data into reliable schema via normalizer layer
        repo_state = normalize_repository_state(impact, drift, doc_snapshot, self.commit_sha)

        risk_level = "LOW"
        if repo_state.severity in ["MAJOR", "CRITICAL"] or repo_state.breaking_changes:
            risk_level = "HIGH"
        elif repo_state.severity == "MINOR" or repo_state.drift_detected:
            risk_level = "MEDIUM"

        return {
            "commit": {
                "hash": repo_state.commit_hash,
                "author": repo_state.author,
                "timestamp": repo_state.timestamp
            },
            "files_changed_count": repo_state.changed_files_count,
            "changed_files": repo_state.changed_files, # Standardized name
            "api_endpoints": repo_state.api_endpoints,
            "affected_components": repo_state.affected_components, # Standardized name
            "breaking_changes": ["Major API or architecture changes detected"] if repo_state.breaking_changes else [], # Standardized as list
            "drift_detected": repo_state.drift_detected,
            "drift_findings": repo_state.drift_findings,
            "risk_level": risk_level.lower() # lowercase as expected by CSS/frontend
        }


    def _normalize_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            items = [self._stringify_field(item) for item in value]
        else:
            items = [self._stringify_field(value)]
        items = [item for item in items if item]
        items.sort()
        return items

    def _normalize_issue_list(self, value: Any) -> List[Dict[str, Any]]:
        if not value:
            return []
        if isinstance(value, list):
            items = value
        else:
            items = [value]
        normalized = []
        for item in items:
            if isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append({"description": self._stringify_field(item)})
        normalized.sort(key=lambda x: (
            str(x.get("severity", "")),
            str(x.get("description", "")),
            json.dumps(x, sort_keys=True)
        ))
        return normalized

    def _stringify_field(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return json.dumps(value, sort_keys=True)

    def _render_template(self, payload: Dict[str, Any]) -> str:
        commit = payload.get("commit", {})
        commit_author = commit.get("author", "Unknown")
        commit_timestamp = commit.get("timestamp", "Unknown")
        commit_hash = commit.get("hash", "Unknown")

        changed_files = payload.get("changed_files", [])
        files_count = payload.get("files_changed_count", 0)
        affected_components = payload.get("affected_components", [])
        api_endpoints = payload.get("api_endpoints", 0)
        drift_findings = payload.get("drift_findings", [])
        drift_detected = payload.get("drift_detected", False)
        risk_level = payload.get("risk_level", "LOW")
        breaking_changes = payload.get("breaking_changes", False)

        template = f"""# Change Summary

**Commit SHA:** `{commit_hash}`
**Commit Author:** {commit_author}
**Commit Time:** {commit_timestamp}
**Risk Level:** {risk_level}

## Impact Analysis
### Changed Modules/Files ({files_count})
"""
        if changed_files:
            for file in changed_files:
                template += f"- `{file}`\n"
        else:
            template += "- No changed files detected.\n"

        template += "\n### API Impact Summary\n"
        if api_endpoints > 0:
            template += f"Detected {api_endpoints} API endpoints\n"
        else:
            template += "No API impact summary provided.\n"

        template += "\n### Affected Components\n"
        if affected_components:
            for component in affected_components:
                template += f"- {component}\n"
        else:
            template += "- No affected components listed.\n"

        template += "\n### Risk Assessment\n"
        if breaking_changes:
            template += f"⚠️ BREAKING CHANGES DETECTED. Risk Level: {risk_level}. {files_count} files changed.\n"
        else:
            template += f"Risk Level: {risk_level}. {files_count} files changed.\n"

        template += f"\n## Drift Report ({'Detected' if drift_detected else 'None'})\n"
        if drift_findings:
            for issue in drift_findings:
                issue_type = issue.get("type", "unknown")
                count = issue.get("count", 0)
                template += f"- {issue_type}: {count}\n"
        else:
            template += "- No drift issues detected.\n"

        template += "\n---\n*Generated by Epic-4 Automation*\n"

        return template

def generate_summary_artifacts(impact_path, drift_path, commit_sha, output_dir, doc_snapshot=None):
    generator = SummaryGenerator(impact_path, drift_path, commit_sha, output_dir, doc_snapshot)
    return generator.generate()


def generate_summary(impact_path, drift_path, commit_sha, output_dir, doc_snapshot=None):
    # Backward-compatible return type: markdown path only.
    output_path_md, _ = generate_summary_artifacts(
        impact_path,
        drift_path,
        commit_sha,
        output_dir,
        doc_snapshot,
    )
    return output_path_md
