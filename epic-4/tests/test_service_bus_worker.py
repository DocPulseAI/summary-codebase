import unittest
from unittest.mock import patch

from epic4.service_bus_worker import ServiceBusWorker


class DummyMessage:
    def __init__(self, body):
        self.body = body


class TestServiceBusWorker(unittest.TestCase):
    def test_parse_payload_from_bytes(self):
        worker = ServiceBusWorker(connection_string="Endpoint=sb://example/", queue_name="jobs")
        msg = DummyMessage(b'{"commit_sha":"abc12345"}')

        payload = worker._parse_payload(msg)

        self.assertEqual(payload["commit_sha"], "abc12345")

    def test_parse_payload_from_list_body(self):
        worker = ServiceBusWorker(connection_string="Endpoint=sb://example/", queue_name="jobs")
        msg = DummyMessage([b'{"impact_report_path":"artifacts/impact_report.json"}'])

        payload = worker._parse_payload(msg)

        self.assertEqual(payload["impact_report_path"], "artifacts/impact_report.json")

    @patch("epic4.service_bus_worker.run_summary_pipeline")
    def test_process_payload_forwards_values(self, mock_run_summary):
        worker = ServiceBusWorker(connection_string="Endpoint=sb://example/", queue_name="jobs")
        mock_run_summary.return_value = {"status": "success"}

        payload = {
            "impact_report_path": "custom/impact.json",
            "drift_report_path": "custom/drift.json",
            "doc_snapshot_path": "custom/doc_snapshot.json",
            "commit_sha": "cafebabe",
            "output_dir": "custom/out",
            "summary_bucket_path": "custom/path/summary/",
        }

        result = worker.process_payload(payload)

        self.assertEqual(result["status"], "success")
        mock_run_summary.assert_called_once_with(
            impact_path="custom/impact.json",
            drift_path="custom/drift.json",
            commit_sha="cafebabe",
            output_dir="custom/out",
            snapshot_path="custom/doc_snapshot.json",
            summary_bucket_path_override="custom/path/summary/",
        )


if __name__ == "__main__":
    unittest.main()
