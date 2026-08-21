"""Pydantic schemas used by extraction agents and merge stage."""

from typing import Dict, List

from pydantic import BaseModel, Field


class AccountMetadata(BaseModel):
    """Structured output expected from the first extraction agent."""

    account_holder_name: str = Field(default="", description="Full name on the statement")
    account_number: str = Field(default="", description="Account number as shown")
    bank_name: str = Field(default="", description="Bank name on statement")
    statement_start_date: str = Field(
        default="", description="Start date in YYYY-MM-DD format"
    )
    statement_end_date: str = Field(
        default="", description="End date in YYYY-MM-DD format"
    )
    opening_balance: str = Field(
        default="", description="Opening balance value as shown on document"
    )
    closing_balance: str = Field(
        default="", description="Closing balance value as shown on document"
    )


class CustomerIdentity(BaseModel):
    """Structured output expected from the customer identity agent."""

    customer_name: str = Field(default="", description="Customer full name")
    customer_address: str = Field(default="", description="Customer postal address")
    customer_email: str = Field(default="", description="Customer email if present")
    customer_phone: str = Field(default="", description="Customer phone if present")


class TransactionRow(BaseModel):
    """Single transaction row extracted from the statement."""

    transaction_date: str = Field(default="", description="Date in YYYY-MM-DD format")
    description: str = Field(default="", description="Transaction description")
    debit: str = Field(default="", description="Outgoing amount value")
    credit: str = Field(default="", description="Incoming amount value")
    running_balance: str = Field(default="", description="Balance after transaction")


class TransactionTable(BaseModel):
    """Structured output expected from the transaction extraction agent."""

    transactions: List[TransactionRow] = Field(default_factory=list)


class MergeConflict(BaseModel):
    """Describes a disagreement detected while merging agent outputs."""

    field_name: str
    values_by_agent: Dict[str, str]
    chosen_source: str
    chosen_value: str
    reason: str


class MergedStatement(BaseModel):
    """Unified output shape after merging parallel extraction results."""

    customer_name: str = Field(default="")
    customer_address: str = Field(default="")
    customer_email: str = Field(default="")
    customer_phone: str = Field(default="")
    account_number: str = Field(default="")
    bank_name: str = Field(default="")
    statement_start_date: str = Field(default="")
    statement_end_date: str = Field(default="")
    opening_balance: str = Field(default="")
    closing_balance: str = Field(default="")
    transactions: List[TransactionRow] = Field(default_factory=list)
    merge_conflicts: List[MergeConflict] = Field(default_factory=list)
    prompt_versions: Dict[str, str] = Field(default_factory=dict)


class ValidationErrorDetail(BaseModel):
    """Machine-checkable validation failure detail."""

    code: str
    field_path: str
    message: str
    expected: str = Field(default="")
    actual: str = Field(default="")


class ValidationResult(BaseModel):
    """Result of deterministic statement validation checks."""

    is_valid: bool
    errors: List[ValidationErrorDetail] = Field(default_factory=list)


class ReflectionResult(BaseModel):
    """Self-critique output used to improve future runs."""

    mistake_description: str
    correction_rule: str
    confidence: float = Field(ge=0.0, le=1.0)
