"""Tests for transaction table extraction agent."""

from config.settings import Settings
from src.agents.transaction_agent import extract_transaction_table


def test_transaction_agent_returns_rows(monkeypatch) -> None:
    def fake_call_llm(system_prompt: str, user_prompt: str, settings: Settings) -> str:
        assert "Return only valid JSON" in system_prompt
        assert "Document text:" in user_prompt
        return """{
  \"transactions\": [
    {
      \"transaction_date\": \"2026-01-02\",
      \"description\": \"Salary\",
      \"debit\": \"\",
      \"credit\": \"2000.00\",
      \"running_balance\": \"3000.00\"
    }
  ]
}"""

    monkeypatch.setattr("src.agents.transaction_agent.call_llm", fake_call_llm)

    settings = Settings(
        api_key="test",
        model="test-model",
        base_url=None,
        input_directory=None,
        output_directory=None,
        memory_directory=None,
    )

    result, prompt_version = extract_transaction_table(
        document_text="Statement text",
        memory_context="No prior corrections",
        settings=settings,
    )

    assert len(result.transactions) == 1
    assert result.transactions[0].description == "Salary"
    assert prompt_version == "1.0.0"
