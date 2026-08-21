"""Tests for the first account metadata extraction agent."""

from config.settings import Settings
from src.agents.account_agent import extract_account_metadata


def test_account_agent_returns_structured_model(monkeypatch) -> None:
    def fake_call_llm(system_prompt: str, user_prompt: str, settings: Settings) -> str:
        assert "Return only valid JSON" in system_prompt
        assert "Document text:" in user_prompt
        return """```json
{
  \"account_holder_name\": \"Alex Doe\",
  \"account_number\": \"123456789\",
  \"bank_name\": \"Demo Bank\",
  \"statement_start_date\": \"2026-01-01\",
  \"statement_end_date\": \"2026-01-31\",
  \"opening_balance\": \"1000.00\",
  \"closing_balance\": \"1500.00\"
}
```"""

    monkeypatch.setattr("src.agents.account_agent.call_llm", fake_call_llm)

    settings = Settings(
        api_key="test",
        model="test-model",
        base_url=None,
        input_directory=None,
        output_directory=None,
        memory_directory=None,
    )

    result, prompt_version = extract_account_metadata(
        document_text="Statement text",
        memory_context="No prior corrections",
        settings=settings,
    )

    assert result.account_holder_name == "Alex Doe"
    assert result.account_number == "123456789"
    assert prompt_version == "1.0.0"
