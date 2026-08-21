"""Tests for conditional reflection orchestration."""

from src.models.schemas import MergedStatement, ReflectionResult, ValidationResult
from src.orchestration.reflection import run_reflection_if_needed


def _sample_merged_statement() -> MergedStatement:
    return MergedStatement(
        customer_name="Alex Doe",
        customer_address="42 Main Street",
        account_number="12345",
        bank_name="Demo Bank",
        statement_start_date="2026-01-01",
        statement_end_date="2026-01-31",
        opening_balance="1000.00",
        closing_balance="1000.00",
        transactions=[],
    )


def test_reflection_not_triggered_when_validation_passes(monkeypatch) -> None:
    called = {"value": False}

    def fake_reflection(*args, **kwargs):
        called["value"] = True
        return ReflectionResult(
            mistake_description="x",
            correction_rule="y",
            confidence=0.5,
        ), "1.0.0"

    monkeypatch.setattr("src.orchestration.reflection.reflect_on_validation_failure", fake_reflection)

    reflection, version = run_reflection_if_needed(
        validation_result=ValidationResult(is_valid=True, errors=[]),
        merged_statement=_sample_merged_statement(),
        document_text="text",
    )

    assert reflection is None
    assert version is None
    assert called["value"] is False


def test_reflection_triggered_when_validation_fails(monkeypatch) -> None:
    def fake_reflection(*args, **kwargs):
        return ReflectionResult(
            mistake_description="m",
            correction_rule="r",
            confidence=0.8,
        ), "1.0.0"

    monkeypatch.setattr("src.orchestration.reflection.reflect_on_validation_failure", fake_reflection)

    reflection, version = run_reflection_if_needed(
        validation_result=ValidationResult(
            is_valid=False,
            errors=[],
        ),
        merged_statement=_sample_merged_statement(),
        document_text="text",
    )

    assert reflection is not None
    assert reflection.correction_rule == "r"
    assert version == "1.0.0"
