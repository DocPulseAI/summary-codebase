"""
Epic4Worker — Summary Generation Worker (Python)

Standalone Python worker for the summary-codebase service.
- Consumes: analysis-jobs-epic4-queue (Epic3Completed events)
- Invokes the Epic4 summary generation pipeline
- Publishes: Epic4Completed (signals pipeline end) or AnalysisFailed

Usage:
    python -m worker.epic4_worker

Environment:
    RABBITMQ_URL           — amqp://user:pass@host:5672/
    EPIC4_SERVICE_URL      — internal URL of summary-service HTTP service
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

LOG = logging.getLogger("epic4.worker")


def _setup_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )


_processed_event_ids: set[str] = set()


def _is_duplicate(event_id: str) -> bool:
    if event_id in _processed_event_ids:
        return True
    if len(_processed_event_ids) >= 10_000:
        to_remove = list(_processed_event_ids)[:5_000]
        for eid in to_remove:
            _processed_event_ids.discard(eid)
    _processed_event_ids.add(event_id)
    return False


def _publish(channel: Any, queue: str, envelope: Any) -> None:
    try:
        import amqp  # type: ignore
        channel.basic_publish(
            amqp.Message(json.dumps(envelope.model_dump()), content_type="application/json", delivery_mode=2),
            exchange="", routing_key=queue,
        )
    except ImportError:
        LOG.warning("amqp not available — skipping publish to %s", queue)


def handle_message(body: bytes, channel: Any) -> None:
    from worker.events.schemas import (
        EventEnvelope, Epic3CompletedPayload,
        EPIC3_COMPLETED, EPIC4_COMPLETED, ANALYSIS_FAILED,
        QUEUE_EPIC4_DLQ,
        build_envelope, is_compatible_version, EVENT_VERSION,
    )

    try:
        raw = json.loads(body)
        envelope = EventEnvelope.model_validate(raw)
    except Exception as exc:
        LOG.error("Epic4Worker: invalid message: %s", exc)
        return

    if _is_duplicate(envelope.eventId):
        LOG.warning("Epic4Worker: duplicate eventId=%s — skipping", envelope.eventId)
        return

    if not is_compatible_version(envelope.eventVersion):
        LOG.error("Epic4Worker: incompatible version %d", envelope.eventVersion)
        return

    if envelope.eventType != EPIC3_COMPLETED:
        LOG.warning("Epic4Worker: unexpected eventType=%s — ignoring", envelope.eventType)
        return

    try:
        payload = Epic3CompletedPayload.model_validate(envelope.payload)
    except Exception as exc:
        LOG.error("Epic4Worker: invalid payload: %s", exc)
        return

    run_id = payload.runId
    ctx = dict(correlation_id=envelope.correlationId, trace_id=envelope.traceId)
    LOG.info("Epic4Worker: processing Epic3Completed run_id=%s drift_succeeded=%s", run_id, payload.driftSucceeded)

    summary_ok = False
    error_message = None

    try:
        import requests  # type: ignore
        epic4_url = os.environ.get("EPIC4_SERVICE_URL", "")
        if not epic4_url:
            raise RuntimeError("EPIC4_SERVICE_URL not configured")

        resp = requests.post(epic4_url, json={
            "impact_report": payload.impactReport,
            "doc_snapshot": payload.docSnapshot,
            "drift_report": payload.driftReport,
            "commit_sha": payload.commitSha,
            "project_id": payload.projectId,
            "trace_id": envelope.traceId,
            "run_id": run_id,
            "ref_name": payload.refName,
            "ref_type": payload.refType,
            "is_preview": payload.isPreview,
        }, timeout=300)
        resp.raise_for_status()
        summary_ok = True
        LOG.info("Epic4Worker: summary generation succeeded run_id=%s", run_id)
    except Exception as exc:
        error_message = str(exc)
        LOG.error("Epic4Worker: summary generation failed: %s", error_message)

    if summary_ok:
        result = build_envelope(EPIC4_COMPLETED, EVENT_VERSION, {
            "runId": run_id, "projectId": payload.projectId,
            "branch": payload.branch, "commitSha": payload.commitSha,
            "refName": payload.refName, "refType": payload.refType,
            "triggerType": payload.triggerType, "isPreview": payload.isPreview,
            "manifestValidated": True,
        }, **ctx)
        # Epic4Completed has no downstream consumer — publish to its own queue for observability
        _publish(channel, "analysis-jobs-epic4-queue", result)
        LOG.info("Epic4Worker: published Epic4Completed run_id=%s", run_id)
    else:
        fail = build_envelope(ANALYSIS_FAILED, EVENT_VERSION, {
            "runId": run_id, "projectId": payload.projectId,
            "failedStage": "epic4",
            "errorMessage": error_message or "Unknown error",
            "retryCount": 0,
        }, **ctx)
        _publish(channel, QUEUE_EPIC4_DLQ, fail)


def run_worker() -> None:
    _setup_logging()
    rabbitmq_url = os.environ.get("RABBITMQ_URL", "amqp://localhost")
    queue_name = os.environ.get("EPIC4_QUEUE", "analysis-jobs-epic4-queue")
    LOG.info("Epic4Worker: connecting to %s", rabbitmq_url)
    try:
        import amqp  # type: ignore
    except ImportError:
        LOG.error("Epic4Worker: 'amqp' package not installed.")
        sys.exit(1)
    while True:
        try:
            conn = amqp.Connection(rabbitmq_url)
            conn.connect()
            ch = conn.channel()
            ch.queue_declare(queue=queue_name, durable=True, auto_delete=False)
            ch.basic_qos(prefetch_count=1)
            LOG.info("Epic4Worker: consuming from %s", queue_name)

            def _cb(msg: Any) -> None:
                try:
                    handle_message(msg.body, ch)
                    ch.basic_ack(msg.delivery_tag)
                except Exception as exc:
                    LOG.error("Epic4Worker: handler error: %s", exc)
                    ch.basic_reject(msg.delivery_tag, requeue=False)

            ch.basic_consume(queue_name, callback=_cb, no_ack=False)
            while True:
                conn.drain_events(timeout=1)
        except KeyboardInterrupt:
            LOG.info("Epic4Worker: shutting down")
            break
        except Exception as exc:
            LOG.error("Epic4Worker: connection error — reconnecting in 5s: %s", exc)
            time.sleep(5)


if __name__ == "__main__":
    run_worker()
