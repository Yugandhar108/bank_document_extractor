"""Conditional reflection orchestration for milestone 5."""

from src.agents.reflection_agent import reflect_on_validation_failure
from src.models.schemas import MergedStatement, ReflectionResult, ValidationResult


def run_reflection_if_needed(
    validation_result: ValidationResult,
    merged_statement: MergedStatement,
    document_text: str,
):
    """Run reflection only when validation fails.

    Returns:
        Tuple[reflection_result_or_none, prompt_version_or_none]
    """
    if validation_result.is_valid:
        return None, None

    reflection, prompt_version = reflect_on_validation_failure(
        validation_result=validation_result,
        merged_statement=merged_statement,
        document_text=document_text,
    )
    return reflection, prompt_version
