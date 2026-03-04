import json
import os
from typing import Dict, Any, List, Tuple, Optional
from epic4.config import config
from epic4.utils import logger

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

        summary_payload = self._build_summary_payload(impact, drift)

        summary_md = self._render_template(summary_payload)
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

    def _build_summary_payload(self, impact: Dict[str, Any], drift: Dict[str, Any]) -> Dict[str, Any]:
        # Handle nested structure: impact_report.json has report.report.* structure
        if "report" in impact and isinstance(impact["report"], dict):
            if "report" in impact["report"]:
                impact_data = impact["report"]["report"]
            else:
                impact_data = impact["report"]
        else:
            impact_data = impact
        
        # Extract analysis summary
        analysis_summary = impact_data.get("analysis_summary", {})
        severity = (
            analysis_summary.get("highest_severity")
            or analysis_summary.get("severity")
            or impact_data.get("severity")
            or "UNKNOWN"
        )
        changed_files = impact_data.get("changed_files", [])
        total_files = analysis_summary.get("total_files", len(changed_files))
        breaking_changes = bool(
            analysis_summary.get("breaking_changes_detected", impact_data.get("breaking_changes", False))
        )
        
        # Extract commit metadata from doc_snapshot if available
        commit_metadata = {}
        if self.doc_snapshot:
            # Use generated_at as commit timestamp
            generated_at = self.doc_snapshot.get("generated_at", "")
            project_id = self.doc_snapshot.get("project_id", "")
            
            commit_metadata = {
                "timestamp": generated_at,
                "project_id": project_id,
                "author": "Unknown",  # Not available in current data
                "message": "Unknown"  # Not available in current data
            }
        
        if not isinstance(commit_metadata, dict):
            commit_metadata = {"raw": commit_metadata}
        
        # Extract changed files and affected packages
        affected_symbols = impact_data.get("affected_packages") or impact_data.get("affected_symbols", [])
        
        # Extract API impact
        api_contract = impact_data.get("api_contract", {})
        endpoints = api_contract.get("endpoints", [])
        api_impact_summary = f"Detected {len(endpoints)} API endpoints" if endpoints else ""
        
        # Extract drift information
        drift_issues = drift.get("issues") or drift.get("findings") or drift.get("drift_findings") or []
        
        # Build risk assessment
        risk_assessment = ""
        if breaking_changes:
            risk_assessment = f"⚠️ BREAKING CHANGES DETECTED. Severity: {severity}. {total_files} files changed."
        else:
            risk_assessment = f"Severity: {severity}. {total_files} files changed."
        
        # Build affected components from packages
        affected_components = affected_symbols[:10] if affected_symbols else []  # Limit to top 10
        
        # Build recommended actions
        recommended_actions = []
        if breaking_changes:
            recommended_actions.append("Review breaking changes carefully before deployment")
            recommended_actions.append("Update API documentation")
            recommended_actions.append("Notify dependent teams")
        if len(endpoints) > 0:
            recommended_actions.append(f"Review {len(endpoints)} API endpoint changes")
        if drift_issues:
            recommended_actions.append(f"Address {len(drift_issues)} documentation drift issues")

        # Deterministic sorting/normalization
        changed_files = self._normalize_list(changed_files)
        affected_symbols = self._normalize_list(affected_symbols)
        affected_components = self._normalize_list(affected_components)
        recommended_actions = self._normalize_list(recommended_actions)
        drift_issues = self._normalize_issue_list(drift_issues)

        changed_files_count = total_files

        api_impact_text = self._stringify_field(api_impact_summary)
        risk_text = self._stringify_field(risk_assessment)

        payload = {
            "summary_version": "1",
            "commit_sha": self.commit_sha,
            "commit_metadata": commit_metadata,
            "severity": severity,
            "changed_files_count": changed_files_count,
            "changed_files": changed_files,
            "affected_symbols": affected_symbols,
            "api_impact_summary": api_impact_text,
            "drift_findings": drift_issues,
            "risk_assessment": risk_text,
            "affected_components": affected_components,
            "recommended_actions": recommended_actions,
            "drift_report_present": bool(drift)
        }

        return payload


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
        commit_meta = payload.get("commit_metadata") or {}
        commit_author = commit_meta.get("author") or commit_meta.get("author_name") or "Unknown"
        commit_timestamp = commit_meta.get("timestamp") or commit_meta.get("date") or "Unknown"
        commit_message = commit_meta.get("message") or commit_meta.get("title") or "Unknown"

        changed_files = payload.get("changed_files", [])
        affected_symbols = payload.get("affected_symbols", [])
        drift_issues = payload.get("drift_findings", [])
        affected_components = payload.get("affected_components", [])
        recommended_actions = payload.get("recommended_actions", [])
        api_impact_summary = payload.get("api_impact_summary", "")
        risk_assessment = payload.get("risk_assessment", "")

        template = f"""# Change Summary

**Commit SHA:** `{payload.get("commit_sha", "")}`
**Commit Author:** {commit_author}
**Commit Time:** {commit_timestamp}
**Commit Message:** {commit_message}
**Severity:** {payload.get("severity", "UNKNOWN")}

## Impact Analysis
### Changed Modules/Files ({payload.get("changed_files_count", len(changed_files))})
"""
        if changed_files:
            for file in changed_files:
                template += f"- `{file}`\n"
        else:
            template += "- No changed files detected.\n"

        template += f"\n### Affected Symbols/Functions ({len(affected_symbols)})\n"
        if affected_symbols:
            for symbol in affected_symbols:
                template += f"- `{symbol}`\n"
        else:
            template += "- No specific symbols identified as affected.\n"

        template += "\n### API Impact Summary\n"
        if api_impact_summary:
            template += f"{api_impact_summary}\n"
        else:
            template += "No API impact summary provided.\n"

        template += "\n### Affected Components\n"
        if affected_components:
            for component in affected_components:
                template += f"- {component}\n"
        else:
            template += "- No affected components listed.\n"

        template += "\n### Risk Assessment\n"
        if risk_assessment:
            template += f"{risk_assessment}\n"
        else:
            template += "No risk assessment provided.\n"

        template += "\n### Recommended Developer Actions\n"
        if recommended_actions:
            for action in recommended_actions:
                template += f"- {action}\n"
        else:
            template += "- No recommended actions provided.\n"

        template += f"\n## Drift Report ({len(drift_issues)} Issues)\n"
        if drift_issues:
            for issue in drift_issues:
                desc = issue.get("description", "")
                severity = issue.get("severity", "")
                label = f"[{severity}] " if severity else ""
                template += f"- {label}{desc}\n"
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
