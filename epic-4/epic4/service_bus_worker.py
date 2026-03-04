import argparse
import json
import time
from typing import Any, Dict, Optional

from epic4.config import config
from epic4.run import run_summary_pipeline
from epic4.utils import logger


class ServiceBusWorker:
    def __init__(
        self,
        connection_string: Optional[str] = None,
        queue_name: Optional[str] = None,
        response_queue_name: Optional[str] = None,
        max_wait_time: int = 20,
        idle_sleep_seconds: int = 2,
    ):
        self.connection_string = (connection_string or config.SERVICE_BUS_CONNECTION_STRING).strip()
        self.queue_name = (queue_name or config.EPIC4_QUEUE_NAME).strip()
        self.response_queue_name = (response_queue_name or config.EPIC4_RESPONSE_QUEUE_NAME).strip()
        self.max_wait_time = max_wait_time
        self.idle_sleep_seconds = idle_sleep_seconds

    def validate(self) -> None:
        missing = []
        if not self.connection_string:
            missing.append("SERVICE_BUS_CONNECTION_STRING")
        if not self.queue_name:
            missing.append("EPIC4_QUEUE_NAME")
        if missing:
            raise ValueError(f"Missing required Service Bus configuration: {', '.join(missing)}")

    def _decode_body(self, message: Any) -> str:
        body = getattr(message, "body", message)

        if isinstance(body, str):
            return body
        if isinstance(body, (bytes, bytearray)):
            return body.decode("utf-8")
        if isinstance(body, list):
            parts = []
            for part in body:
                if isinstance(part, (bytes, bytearray)):
                    parts.append(bytes(part))
                else:
                    parts.append(str(part).encode("utf-8"))
            return b"".join(parts).decode("utf-8")

        if hasattr(body, "__iter__"):
            chunks = []
            for chunk in body:
                if isinstance(chunk, (bytes, bytearray)):
                    chunks.append(bytes(chunk))
                else:
                    chunks.append(str(chunk).encode("utf-8"))
            if chunks:
                return b"".join(chunks).decode("utf-8")

        return str(body)

    def _parse_payload(self, message: Any) -> Dict[str, Any]:
        raw = self._decode_body(message).strip()
        if not raw:
            return {}

        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Service Bus message body must be a JSON object")
        return payload

    def process_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        impact_path = payload.get("impact_report_path", config.IMPACT_REPORT_PATH)
        drift_path = payload.get("drift_report_path", config.DRIFT_REPORT_PATH)
        snapshot_path = payload.get("doc_snapshot_path", config.DOC_SNAPSHOT_PATH)
        output_dir = payload.get("output_dir", config.SUMMARIES_DIR)
        summary_bucket_path = payload.get("summary_bucket_path", "")
        commit_sha = payload.get("commit_sha", config.COMMIT_SHA)

        logger.info(
            f"Processing Service Bus message for commit={commit_sha or 'from_snapshot'} "
            f"impact={impact_path} drift={drift_path}"
        )

        return run_summary_pipeline(
            impact_path=impact_path,
            drift_path=drift_path,
            commit_sha=commit_sha,
            output_dir=output_dir,
            snapshot_path=snapshot_path,
            summary_bucket_path_override=summary_bucket_path,
        )

    def run(self, max_messages: int = 0) -> None:
        self.validate()

        try:
            from azure.servicebus import ServiceBusClient, ServiceBusMessage
        except ImportError as e:
            raise RuntimeError(
                "azure-servicebus is not installed. Install with: pip install azure-servicebus"
            ) from e

        processed = 0

        with ServiceBusClient.from_connection_string(self.connection_string) as client:
            with client.get_queue_receiver(queue_name=self.queue_name) as receiver:
                sender = None
                sender_context = None
                if self.response_queue_name:
                    sender_context = client.get_queue_sender(queue_name=self.response_queue_name)
                    sender = sender_context.__enter__()

                try:
                    while True:
                        if max_messages > 0 and processed >= max_messages:
                            logger.info(f"Reached max_messages={max_messages}. Exiting worker loop.")
                            return

                        messages = receiver.receive_messages(
                            max_message_count=1,
                            max_wait_time=self.max_wait_time,
                        )

                        if not messages:
                            time.sleep(self.idle_sleep_seconds)
                            continue

                        for message in messages:
                            try:
                                payload = self._parse_payload(message)
                                result = self.process_payload(payload)

                                if sender:
                                    sender.send_messages(ServiceBusMessage(json.dumps(result)))

                                receiver.complete_message(message)
                                processed += 1
                                logger.info(f"Processed queue message successfully. count={processed}")
                            except Exception as e:
                                logger.error(f"Failed to process queue message: {e}")
                                receiver.abandon_message(message)
                finally:
                    if sender_context:
                        sender_context.__exit__(None, None, None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Epic-4 Azure Service Bus worker")
    parser.add_argument("--queue", default=config.EPIC4_QUEUE_NAME, help="Service Bus queue name")
    parser.add_argument(
        "--response-queue",
        default=config.EPIC4_RESPONSE_QUEUE_NAME,
        help="Optional queue to publish job results",
    )
    parser.add_argument("--max-messages", type=int, default=0, help="Stop after N messages (0 = infinite)")
    parser.add_argument("--max-wait-time", type=int, default=20, help="Receiver max wait time in seconds")

    args = parser.parse_args()

    worker = ServiceBusWorker(
        queue_name=args.queue,
        response_queue_name=args.response_queue,
        max_wait_time=args.max_wait_time,
    )
    worker.run(max_messages=args.max_messages)


if __name__ == "__main__":
    main()
