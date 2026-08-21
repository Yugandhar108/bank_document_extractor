"""Tests for parallel extraction runner and timing evidence."""

import asyncio
from datetime import datetime
import time

from src.models.schemas import AccountMetadata, CustomerIdentity, TransactionRow, TransactionTable
from src.orchestration.parallel_runner import run_parallel_extraction


def _has_overlap(intervals: list[tuple[datetime, datetime]]) -> bool:
    for left in range(len(intervals)):
        for right in range(left + 1, len(intervals)):
            start_a, end_a = intervals[left]
            start_b, end_b = intervals[right]
            if start_a < end_b and start_b < end_a:
                return True
    return False


def test_parallel_runner_executes_agents_concurrently(monkeypatch) -> None:
    def fake_account(*args, **kwargs):
        time.sleep(0.12)
        return AccountMetadata(account_holder_name="A"), "1.0.0"

    def fake_identity(*args, **kwargs):
        time.sleep(0.12)
        return CustomerIdentity(customer_name="B"), "1.0.0"

    def fake_transactions(*args, **kwargs):
        time.sleep(0.12)
        return TransactionTable(transactions=[TransactionRow(description="C")]), "1.0.0"

    monkeypatch.setattr("src.orchestration.parallel_runner.extract_account_metadata", fake_account)
    monkeypatch.setattr("src.orchestration.parallel_runner.extract_customer_identity", fake_identity)
    monkeypatch.setattr("src.orchestration.parallel_runner.extract_transaction_table", fake_transactions)

    result = asyncio.run(run_parallel_extraction(document_text="x"))

    intervals = [
        (datetime.fromisoformat(item.started_at), datetime.fromisoformat(item.ended_at))
        for item in result.timings
    ]

    assert _has_overlap(intervals)
    assert len(result.timings) == 3


def test_parallel_runner_waits_for_slowest_agent(monkeypatch) -> None:
    def fake_account(*args, **kwargs):
        time.sleep(0.05)
        return AccountMetadata(account_holder_name="A"), "1.0.0"

    def fake_identity(*args, **kwargs):
        time.sleep(0.10)
        return CustomerIdentity(customer_name="B"), "1.0.0"

    def fake_transactions(*args, **kwargs):
        time.sleep(0.20)
        return TransactionTable(transactions=[]), "1.0.0"

    monkeypatch.setattr("src.orchestration.parallel_runner.extract_account_metadata", fake_account)
    monkeypatch.setattr("src.orchestration.parallel_runner.extract_customer_identity", fake_identity)
    monkeypatch.setattr("src.orchestration.parallel_runner.extract_transaction_table", fake_transactions)

    started = time.perf_counter()
    asyncio.run(run_parallel_extraction(document_text="x"))
    elapsed = time.perf_counter() - started

    assert elapsed >= 0.19
