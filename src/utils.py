import logging
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config import config
import os


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


LOG_BODY_MAX_CHARS = max(200, _int_env("EPIC4_LOG_BODY_MAX_CHARS", 1200))


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if hasattr(record, "event_id"):
            log_record["event_id"] = record.event_id
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "service"):
            log_record["service"] = record.service
        if hasattr(record, "payload") and isinstance(record.payload, dict):
            log_record.update(record.payload)
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logging():
    logger = logging.getLogger("epic4")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    # File handler
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    log_file = os.path.join(config.LOGS_DIR, "epic4_execution.json")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# Secure logging filter to redact token
# (Simple string replacement implementation for this scope)
# Ideally, we'd filter at the record level, but we rely on developers not to explicitly log tokens.
# We will just ensure we don't log the config object directly.

def get_retry_decorator():
    return retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )


def truncate_text(value: Optional[str], max_chars: int = LOG_BODY_MAX_CHARS) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}...(truncated)"


def log_event(level: int, event_id: str, message: str, request_id: Optional[str] = None, **fields: Any) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "payload": fields,
        "service": "epic4",
    }
    extra = {
        "event_id": event_id,
        "request_id": request_id or "n/a",
        "service": "epic4",
        "payload": payload["payload"],
    }
    logger.log(level, message, extra=extra)
