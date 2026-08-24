"""Tests for secure application logging."""

import logging

from src.logging_utils import get_app_logger, log_event, new_run_id


def test_log_file_is_created_and_secrets_are_redacted(tmp_path) -> None:
    logger = get_app_logger(tmp_path)
    run_id = new_run_id()

    log_event(
        logger,
        logging.INFO,
        "Test event",
        run_id=run_id,
        provider="gemini",
        api_key="secret-value",
        note="authorization=Bearer hidden-value",
    )

    log_text = (tmp_path / "application.log").read_text(encoding="utf-8")
    assert run_id in log_text
    assert "Test event" in log_text
    assert "secret-value" not in log_text
    assert "hidden-value" not in log_text
    assert "[REDACTED]" in log_text


def test_run_ids_are_short_and_unique() -> None:
    first = new_run_id()
    second = new_run_id()

    assert len(first) == 12
    assert first != second
