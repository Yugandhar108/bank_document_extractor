"""Tests for milestone 5 reflection agent."""

import pytest

from config.settings import Settings
from src.agents.reflection_agent import reflect_on_validation_failure
from src.models.schemas import (
    MergedStatement,
    ValidationErrorDetail,
    ValidationResult,
)


def _invalid_validation_result() -> ValidationResult:
    return ValidationResult(
        is_valid=False,
        errors=[
            ValidationErrorDetail(
                code="DATE_FORMAT_INVALID",
                field_path="statement_start_date",
                message="Statement start date must be YYYY-MM-DD.",
                expected="YYYY-MM-DD",
                actual="01/01/2026",
            )
        ],
    )


def _sample_merged_statement() -> MergedStatement:
    return MergedStatement(
        customer_name="Alex Doe",
        customer_address="42 Main Street",
        account_number="12345",
        bank_name="Demo Bank",
        statement_start_date="01/01/2026",
        statement_end_date="2026-01-31",
        opening_balance="1000.00",
        closing_balance="1000.00",
        transactions=[],
    )


def test_reflection_agent_returns_structured_result(monkeypatch) -> None:
    def fake_call_llm(system_prompt: str, user_prompt: str, settings: Settings) -> str:
        assert "generalizable" in system_prompt
        assert "Validation errors (JSON):" in user_prompt
        return """```json
{
  \"mistake_description\": \"Date format from statement header was interpreted as MM/DD instead of DD/MM.\",
  \"correction_rule\": \"For this bank source, parse statement header dates using DD/MM/YYYY and convert to YYYY-MM-DD.\",
  \"confidence\": 0.86
}
```"""

    monkeypatch.setattr("src.agents.reflection_agent.call_llm", fake_call_llm)

    settings = Settings(
        api_key="test",
        model="test-model",
        base_url=None,
        input_directory=None,
        output_directory=None,
        memory_directory=None,
    )

    result, prompt_version = reflect_on_validation_failure(
        validation_result=_invalid_validation_result(),
        merged_statement=_sample_merged_statement(),
        document_text="Statement sample text",
        settings=settings,
    )

    assert result.confidence == 0.86
    assert "DD/MM/YYYY" in result.correction_rule
    assert prompt_version == "1.0.0"


def test_reflection_agent_rejects_valid_validation_result() -> None:
    valid_result = ValidationResult(is_valid=True, errors=[])

    with pytest.raises(ValueError, match="only run when validation fails"):
        reflect_on_validation_failure(
            validation_result=valid_result,
            merged_statement=_sample_merged_statement(),
            document_text="Statement sample text",
        )
