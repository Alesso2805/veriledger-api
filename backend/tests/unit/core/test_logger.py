import json
import logging
from collections.abc import Generator

import pytest
import structlog

from backend.app.core.logger import setup_logging


@pytest.fixture(autouse=True)
def default_structlog() -> Generator[None, None, None]:
    yield
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()


def test_production_logs_are_one_json_object_per_line_with_the_request_id(caplog: pytest.LogCaptureFixture) -> None:
    # pytest's own handlers make basicConfig a no-op, so the level is set here
    caplog.set_level(logging.INFO)
    setup_logging(json_logs=True)
    structlog.contextvars.bind_contextvars(request_id="trace-9")

    structlog.get_logger("test").info("Request handled", status=200)

    line = json.loads(caplog.records[-1].getMessage())
    assert (line["event"], line["request_id"], line["status"], line["level"]) == (
        "Request handled",
        "trace-9",
        200,
        "info",
    )
    assert "timestamp" in line
