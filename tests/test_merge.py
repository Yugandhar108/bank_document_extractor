"""Tests for Milestone 3 merge logic."""

from src.models.schemas import (
    AccountMetadata,
    CustomerIdentity,
    TransactionRow,
    TransactionTable,
)
from src.orchestration.merge import merge_parallel_results
from src.orchestration.parallel_runner import AgentTiming, ParallelExtractionResult


def _parallel_result(
    account_name: str,
    identity_name: str,
) -> ParallelExtractionResult:
    return ParallelExtractionResult(
        account_metadata=AccountMetadata(
            account_holder_name=account_name,
            account_number="12345",
            bank_name="Demo Bank",
            statement_start_date="2026-01-01",
            statement_end_date="2026-01-31",
            opening_balance="1000.00",
            closing_balance="1200.00",
        ),
        customer_identity=CustomerIdentity(
            customer_name=identity_name,
            customer_address="42 Main Street",
            customer_email="alex@example.com",
            customer_phone="+1-555-0100",
        ),
        transaction_table=TransactionTable(
            transactions=[
                TransactionRow(
                    transaction_date="2026-01-02",
                    description="Salary",
                    debit="",
                    credit="2000.00",
                    running_balance="3000.00",
                )
            ]
        ),
        prompt_versions={
            "account_metadata": "1.0.0",
            "customer_identity": "1.0.0",
            "transaction_table": "1.0.0",
        },
        timings=[
            AgentTiming("account_metadata", "2026-08-20T00:00:00+00:00", "2026-08-20T00:00:01+00:00", 1.0),
            AgentTiming("customer_identity", "2026-08-20T00:00:00+00:00", "2026-08-20T00:00:01+00:00", 1.0),
            AgentTiming("transaction_table", "2026-08-20T00:00:00+00:00", "2026-08-20T00:00:01+00:00", 1.0),
        ],
    )


def test_merge_combines_outputs_and_keeps_transactions_from_transaction_agent() -> None:
    parallel_result = _parallel_result(account_name="Alex Doe", identity_name="Alex Doe")

    merged = merge_parallel_results(parallel_result)

    assert merged.customer_name == "Alex Doe"
    assert merged.account_number == "12345"
    assert len(merged.transactions) == 1
    assert merged.transactions[0].description == "Salary"
    assert merged.merge_conflicts == []


def test_merge_records_conflict_when_customer_name_disagrees() -> None:
    parallel_result = _parallel_result(account_name="Alex Doe", identity_name="A. Doe")

    merged = merge_parallel_results(parallel_result)

    assert len(merged.merge_conflicts) == 1
    conflict = merged.merge_conflicts[0]
    assert conflict.field_name == "customer_name"
    assert conflict.values_by_agent["account_metadata"] == "Alex Doe"
    assert conflict.values_by_agent["customer_identity"] == "A. Doe"
    assert conflict.chosen_source == "customer_identity"
    assert merged.customer_name == "A. Doe"


def test_merge_falls_back_to_account_name_when_identity_name_missing() -> None:
    parallel_result = _parallel_result(account_name="Alex Doe", identity_name="")

    merged = merge_parallel_results(parallel_result)

    assert merged.customer_name == "Alex Doe"
    assert merged.merge_conflicts == []
