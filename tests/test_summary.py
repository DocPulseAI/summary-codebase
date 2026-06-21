import unittest
import os
import json
import tempfile
import shutil
from src.summary import generate_summary
from src.artifact_normalizer import SummaryValidationError

class TestSummaryGeneration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.impact_path = os.path.join(self.test_dir, "impact.json")
        self.drift_path = os.path.join(self.test_dir, "drift.json")
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def write_json(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f)

    def test_deterministic_generation(self):
        impact_data = {
            "analysis_summary": {
                "highest_severity": "HIGH",
                "total_files": 2
            },
            "affected_symbols": ["func_b", "func_a"],
            "api_contract": { "endpoints": [] }
        }
        drift_data = {
            "drift_detected": True,
            "statistics": { "obsolete_documentation_count": 2 }
        }
        doc_snapshot = {
            "changed_files": ["b_module.py", "a_module.py"]
        }

        self.write_json(self.impact_path, impact_data)
        self.write_json(self.drift_path, drift_data)

        summary_path = generate_summary(self.impact_path, self.drift_path, "sha123", self.output_dir, doc_snapshot)

        self.assertEqual(os.path.basename(summary_path), "summary.md")

        with open(summary_path, 'r') as f:
            content = f.read()

        self.assertIn("a_module.py", content)
        self.assertIn("b_module.py", content)
        self.assertLess(content.index("a_module.py"), content.index("b_module.py"))
        self.assertLess(content.index("func_a"), content.index("func_b"))

    def test_empty_generation(self):
        impact_data = {
            "analysis_summary": {
                "highest_severity": "LOW",
                "total_files": 0
            },
            "api_contract": { "endpoints": [] }
        }
        doc_snapshot = {
            "changed_files": []
        }
        self.write_json(self.impact_path, impact_data)
        self.write_json(self.drift_path, {"drift_detected": False})

        summary_path = generate_summary(self.impact_path, self.drift_path, "sha123", self.output_dir, doc_snapshot)
        with open(summary_path, 'r') as f:
            content = f.read()

        self.assertIn("No changed files detected", content)

    def test_summary_files_extraction(self):
        impact_data = {
            "analysis_summary": { "total_files": 1 },
            "api_contract": { "endpoints": [] }
        }
        doc_snapshot = {
            "changed_files": [{"path": "file1.py"}]
        }
        self.write_json(self.impact_path, impact_data)
        self.write_json(self.drift_path, {"drift_detected": False})
        
        generate_summary(self.impact_path, self.drift_path, "sha123", self.output_dir, doc_snapshot)
        with open(os.path.join(self.output_dir, "summary.json")) as f:
            out = json.load(f)
            self.assertEqual(out["changed_files"], ["file1.py"])
            self.assertEqual(out["files_changed_count"], 1)

    def test_summary_drift_parsing(self):
        impact_data = { "analysis_summary": { "total_files": 0 }, "api_contract": { "endpoints": [] } }
        doc_snapshot = { "changed_files": [] }
        drift_data = {
            "drift_detected": True,
            "statistics": { "obsolete_documentation_count": 5 }
        }
        self.write_json(self.impact_path, impact_data)
        self.write_json(self.drift_path, drift_data)
        generate_summary(self.impact_path, self.drift_path, "sha123", self.output_dir, doc_snapshot)
        with open(os.path.join(self.output_dir, "summary.json")) as f:
            out = json.load(f)
            self.assertTrue(out["drift_detected"])
            self.assertEqual(out["drift_findings"][0]["count"], 5)

    def test_summary_commit_metadata(self):
        impact_data = { "analysis_summary": { "total_files": 0 }, "api_contract": { "endpoints": [] } }
        doc_snapshot = { 
            "changed_files": [],
            "author": "Alice",
            "commit_hash": "abc1234",
            "timestamp": "2026-01-01T12:00:00Z"
        }
        self.write_json(self.impact_path, impact_data)
        self.write_json(self.drift_path, {"drift_detected": False})
        generate_summary(self.impact_path, self.drift_path, "sha123", self.output_dir, doc_snapshot)
        with open(os.path.join(self.output_dir, "summary.json")) as f:
            out = json.load(f)
            self.assertEqual(out["commit"]["author"], "Alice")
            self.assertEqual(out["commit"]["hash"], "abc1234")

    def test_summary_consistency_guard(self):
        # 1. Provide an invalid doc_snapshot to trigger SummaryValidationError
        
        impact_data = { "analysis_summary": { "total_files": 1 }, "api_contract": { "endpoints": [] } }
        # Consistency error: changed_files array is empty but expected count is > 0 based on doc_snapshot length normally...
        # Wait, the logic says if changed_files_count > 0 and len(raw_changed_files) == 0: raise SummaryValidationError
        
        # Another consistency guard is: "files_changed_count != len(changed_files)"
        # Or no changed_files key at all:
        doc_snapshot = {} # missing changed_files
        
        self.write_json(self.impact_path, impact_data)
        self.write_json(self.drift_path, {"drift_detected": False})
        
        with self.assertRaises(SummaryValidationError):
            generate_summary(self.impact_path, self.drift_path, "sha123", self.output_dir, doc_snapshot)
