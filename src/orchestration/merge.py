"""Milestone 3: deterministic merge of parallel agent outputs."""

from __future__ import annotations

from src.models.schemas import MergeConflict, MergedStatement
from src.orchestration.parallel_runner import ParallelExtractionResult


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _pick_non_empty(preferred_value: str, fallback_value: str) -> str:
    if preferred_value.strip():
        return preferred_value
    return fallback_value


def _merge_customer_name(parallel_result: ParallelExtractionResult) -> tuple[str, list[MergeConflict]]:
    account_name = parallel_result.account_metadata.account_holder_name
    identity_name = parallel_result.customer_identity.customer_name

    chosen = _pick_non_empty(identity_name, account_name)
    conflicts: list[MergeConflict] = []

    normalized_account = _normalize(account_name)
    normalized_identity = _normalize(identity_name)

    if normalized_account and normalized_identity and normalized_account != normalized_identity:
        conflicts.append(
            MergeConflict(
                field_name="customer_name",
                values_by_agent={
                    "account_metadata": account_name,
                    "customer_identity": identity_name,
                },
                chosen_source="customer_identity",
                chosen_value=chosen,
                reason="Policy prefers customer_identity for person-level fields.",
            )
        )

    return chosen, conflicts


def merge_parallel_results(parallel_result: ParallelExtractionResult) -> MergedStatement:
    """Merge the parallel extraction outputs into one statement object.

    Conflict policy:
    - customer_name can come from two sources. If they differ, keep
      customer_identity.customer_name and record a conflict.
    - transaction rows are copied directly from transaction_table output to avoid
      LLM re-transcription risk for large tables.
    """
    customer_name, conflicts = _merge_customer_name(parallel_result)

    # Keep transaction data directly from the transaction agent output.
    transactions = parallel_result.transaction_table.transactions

    merged = MergedStatement(
        customer_name=customer_name,
        customer_address=parallel_result.customer_identity.customer_address,
        customer_email=parallel_result.customer_identity.customer_email,
        customer_phone=parallel_result.customer_identity.customer_phone,
        account_number=parallel_result.account_metadata.account_number,
        bank_name=parallel_result.account_metadata.bank_name,
        statement_start_date=parallel_result.account_metadata.statement_start_date,
        statement_end_date=parallel_result.account_metadata.statement_end_date,
        opening_balance=parallel_result.account_metadata.opening_balance,
        closing_balance=parallel_result.account_metadata.closing_balance,
        transactions=transactions,
        merge_conflicts=conflicts,
        prompt_versions=parallel_result.prompt_versions,
    )
    return merged
