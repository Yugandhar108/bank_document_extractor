"""Tests for Milestone 4 deterministic validation."""

from src.models.schemas import MergedStatement, TransactionRow
from src.validation.validator import validate_merged_statement


def _valid_statement() -> MergedStatement:
    return MergedStatement(
        customer_name="Alex Doe",
        customer_address="42 Main Street",
        customer_email="alex@example.com",
        customer_phone="+1-555-0100",
        account_number="12345",
        bank_name="Demo Bank",
        statement_start_date="2026-01-01",
        statement_end_date="2026-01-31",
        opening_balance="1000.00",
        closing_balance="1150.00",
        transactions=[
            TransactionRow(
                transaction_date="2026-01-10",
                description="Salary",
                debit="",
                credit="200.00",
                running_balance="1200.00",
            ),
            TransactionRow(
                transaction_date="2026-01-11",
                description="Groceries",
                debit="50.00",
                credit="",
                running_balance="1150.00",
            ),
        ],
    )


def test_validator_passes_when_statement_is_consistent() -> None:
    result = validate_merged_statement(_valid_statement())
    assert result.is_valid is True
    assert result.errors == []


def test_validator_catches_required_field_and_date_errors() -> None:
    statement = _valid_statement()
    statement.customer_name = ""
    statement.statement_start_date = "01-01-2026"

    result = validate_merged_statement(statement)

    assert result.is_valid is False
    codes = {error.code for error in result.errors}
    assert "REQUIRED_FIELD_MISSING" in codes
    assert "DATE_FORMAT_INVALID" in codes


def test_validator_catches_transaction_date_out_of_range() -> None:
    statement = _valid_statement()
    statement.transactions[0].transaction_date = "2026-02-01"

    result = validate_merged_statement(statement)

    assert result.is_valid is False
    assert any(error.code == "TRANSACTION_DATE_OUT_OF_RANGE" for error in result.errors)


def test_validator_catches_running_balance_mismatch() -> None:
    statement = _valid_statement()
    statement.transactions[1].running_balance = "1100.00"

    result = validate_merged_statement(statement)

    assert result.is_valid is False
    assert any(error.code == "RUNNING_BALANCE_MISMATCH" for error in result.errors)


def test_validator_catches_closing_balance_mismatch() -> None:
    statement = _valid_statement()
    statement.closing_balance = "900.00"

    result = validate_merged_statement(statement)

    assert result.is_valid is False
    assert any(error.code == "CLOSING_BALANCE_MISMATCH" for error in result.errors)


def test_validator_catches_invalid_amount_format() -> None:
    statement = _valid_statement()
    statement.transactions[0].credit = "two hundred"

    result = validate_merged_statement(statement)

    assert result.is_valid is False
    assert any(error.code == "AMOUNT_FORMAT_INVALID" for error in result.errors)
