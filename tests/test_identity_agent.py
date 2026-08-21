"""Tests for customer identity extraction agent."""

from config.settings import Settings
from src.agents.identity_agent import extract_customer_identity


def test_identity_agent_returns_structured_model(monkeypatch) -> None:
    def fake_call_llm(system_prompt: str, user_prompt: str, settings: Settings) -> str:
        assert "Return only valid JSON" in system_prompt
        assert "Document text:" in user_prompt
        return """```json
{
  \"customer_name\": \"Alex Doe\",
  \"customer_address\": \"42 Main Street\",
  \"customer_email\": \"alex@example.com\",
  \"customer_phone\": \"+1-555-0100\"
}
```"""

    monkeypatch.setattr("src.agents.identity_agent.call_llm", fake_call_llm)

    settings = Settings(
        api_key="test",
        model="test-model",
        base_url=None,
        input_directory=None,
        output_directory=None,
        memory_directory=None,
    )

    result, prompt_version = extract_customer_identity(
        document_text="Statement text",
        memory_context="No prior corrections",
        settings=settings,
    )

    assert result.customer_name == "Alex Doe"
    assert result.customer_email == "alex@example.com"
    assert prompt_version == "1.0.0"
