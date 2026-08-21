"""Milestone 4: deterministic rule-based validation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from src.models.schemas import MergedStatement, ValidationErrorDetail, ValidationResult


def _to_decimal(value: str, field_path: str, allow_empty: bool = False) -> Decimal | None:
    raw = value.strip()
    if not raw:
        if allow_empty:
            return Decimal("0")
        return None

    normalized = raw.replace(",", "").replace("$", "")
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"

    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _to_date(value: str) -> date | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _amount_to_string(amount: Decimal) -> str:
    return f"{amount:.2f}"


def _validate_required_fields(statement: MergedStatement) -> list[ValidationErrorDetail]:
    errors: list[ValidationErrorDetail] = []

    required_fields = {
        "customer_name": statement.customer_name,
        "customer_address": statement.customer_address,
        "account_number": statement.account_number,
        "bank_name": statement.bank_name,
        "statement_start_date": statement.statement_start_date,
        "statement_end_date": statement.statement_end_date,
        "opening_balance": statement.opening_balance,
        "closing_balance": statement.closing_balance,
    }

    for field_name, value in required_fields.items():
        if not value.strip():
            errors.append(
                ValidationErrorDetail(
                    code="REQUIRED_FIELD_MISSING",
                    field_path=field_name,
                    message="Required field is empty.",
                    expected="non-empty value",
                    actual="",
                )
            )

    return errors


def _validate_dates(statement: MergedStatement) -> tuple[list[ValidationErrorDetail], date | None, date | None]:
    errors: list[ValidationErrorDetail] = []

    start_date = _to_date(statement.statement_start_date)
    end_date = _to_date(statement.statement_end_date)

    if not start_date:
        errors.append(
            ValidationErrorDetail(
                code="DATE_FORMAT_INVALID",
                field_path="statement_start_date",
                message="Statement start date must be YYYY-MM-DD.",
                expected="YYYY-MM-DD",
                actual=statement.statement_start_date,
            )
        )
    if not end_date:
        errors.append(
            ValidationErrorDetail(
                code="DATE_FORMAT_INVALID",
                field_path="statement_end_date",
                message="Statement end date must be YYYY-MM-DD.",
                expected="YYYY-MM-DD",
                actual=statement.statement_end_date,
            )
        )

    if start_date and end_date and start_date > end_date:
        errors.append(
            ValidationErrorDetail(
                code="DATE_RANGE_INVALID",
                field_path="statement_period",
                message="Statement start date is after statement end date.",
                expected=f"{start_date.isoformat()} <= {end_date.isoformat()}",
                actual=f"{start_date.isoformat()} > {end_date.isoformat()}",
            )
        )

    return errors, start_date, end_date


def _validate_transaction_dates(
    statement: MergedStatement,
    start_date: date | None,
    end_date: date | None,
) -> list[ValidationErrorDetail]:
    errors: list[ValidationErrorDetail] = []

    for index, row in enumerate(statement.transactions):
        tx_path = f"transactions[{index}].transaction_date"
        tx_date = _to_date(row.transaction_date)
        if not tx_date:
            errors.append(
                ValidationErrorDetail(
                    code="DATE_FORMAT_INVALID",
                    field_path=tx_path,
                    message="Transaction date must be YYYY-MM-DD.",
                    expected="YYYY-MM-DD",
                    actual=row.transaction_date,
                )
            )
            continue

        if start_date and end_date and not (start_date <= tx_date <= end_date):
            errors.append(
                ValidationErrorDetail(
                    code="TRANSACTION_DATE_OUT_OF_RANGE",
                    field_path=tx_path,
                    message="Transaction date falls outside statement period.",
                    expected=f"between {start_date.isoformat()} and {end_date.isoformat()}",
                    actual=tx_date.isoformat(),
                )
            )

    return errors


def _validate_balances(statement: MergedStatement) -> list[ValidationErrorDetail]:
    errors: list[ValidationErrorDetail] = []

    opening_balance = _to_decimal(statement.opening_balance, "opening_balance")
    if opening_balance is None:
        errors.append(
            ValidationErrorDetail(
                code="AMOUNT_FORMAT_INVALID",
                field_path="opening_balance",
                message="Opening balance must be a numeric amount.",
                expected="numeric value",
                actual=statement.opening_balance,
            )
        )
        return errors

    closing_balance = _to_decimal(statement.closing_balance, "closing_balance")
    if closing_balance is None:
        errors.append(
            ValidationErrorDetail(
                code="AMOUNT_FORMAT_INVALID",
                field_path="closing_balance",
                message="Closing balance must be a numeric amount.",
                expected="numeric value",
                actual=statement.closing_balance,
            )
        )
        return errors

    running_expected = opening_balance

    for index, row in enumerate(statement.transactions):
        debit = _to_decimal(row.debit, f"transactions[{index}].debit", allow_empty=True)
        credit = _to_decimal(row.credit, f"transactions[{index}].credit", allow_empty=True)
        running_balance = _to_decimal(
            row.running_balance,
            f"transactions[{index}].running_balance",
        )

        if debit is None:
            errors.append(
                ValidationErrorDetail(
                    code="AMOUNT_FORMAT_INVALID",
                    field_path=f"transactions[{index}].debit",
                    message="Debit value must be numeric when present.",
                    expected="numeric value or empty",
                    actual=row.debit,
                )
            )
            continue
        if credit is None:
            errors.append(
                ValidationErrorDetail(
                    code="AMOUNT_FORMAT_INVALID",
                    field_path=f"transactions[{index}].credit",
                    message="Credit value must be numeric when present.",
                    expected="numeric value or empty",
                    actual=row.credit,
                )
            )
            continue
        if running_balance is None:
            errors.append(
                ValidationErrorDetail(
                    code="AMOUNT_FORMAT_INVALID",
                    field_path=f"transactions[{index}].running_balance",
                    message="Running balance must be numeric.",
                    expected="numeric value",
                    actual=row.running_balance,
                )
            )
            continue

        expected_running_balance = running_expected - debit + credit
        if running_balance != expected_running_balance:
            errors.append(
                ValidationErrorDetail(
                    code="RUNNING_BALANCE_MISMATCH",
                    field_path=f"transactions[{index}].running_balance",
                    message="Running balance does not match opening + credits - debits progression.",
                    expected=_amount_to_string(expected_running_balance),
                    actual=_amount_to_string(running_balance),
                )
            )

        running_expected = running_balance

    if running_expected != closing_balance:
        errors.append(
            ValidationErrorDetail(
                code="CLOSING_BALANCE_MISMATCH",
                field_path="closing_balance",
                message="Final computed balance does not equal closing balance.",
                expected=_amount_to_string(running_expected),
                actual=_amount_to_string(closing_balance),
            )
        )

    return errors


def validate_merged_statement(statement: MergedStatement) -> ValidationResult:
    """Run deterministic checks and return is_valid with actionable errors."""
    errors: list[ValidationErrorDetail] = []

    errors.extend(_validate_required_fields(statement))

    date_errors, start_date, end_date = _validate_dates(statement)
    errors.extend(date_errors)

    errors.extend(_validate_transaction_dates(statement, start_date, end_date))
    errors.extend(_validate_balances(statement))

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)
