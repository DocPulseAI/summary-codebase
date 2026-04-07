import logging

from epic4.utils import JsonFormatter, get_retry_decorator


def test_json_formatter_includes_core_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="epic4",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="summary generated",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)

    assert '"level": "INFO"' in formatted
    assert '"message": "summary generated"' in formatted
    assert '"module":' in formatted
    assert '"function":' in formatted


def test_retry_decorator_retries_until_success():
    calls = {"count": 0}

    @get_retry_decorator()
    def flaky_function():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky_function() == "ok"
    assert calls["count"] == 3
