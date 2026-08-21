"""Tests for provider discovery and safe configuration handling."""

from pathlib import Path

from config import settings as settings_module


def _clear_provider_environment(monkeypatch) -> None:
    names = [
        "LLM_PROVIDER",
        "LLM_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_BASE_URL",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "GEMINI_BASE_URL",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "GROQ_BASE_URL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_BASE_URL",
        "HUGGINGFACE_API_KEY",
        "HUGGINGFACE_MODEL",
        "HUGGINGFACE_BASE_URL",
    ]
    for name in names:
        monkeypatch.delenv(name, raising=False)


def test_selects_first_real_key_and_ignores_placeholders(monkeypatch) -> None:
    _clear_provider_environment(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "replace-with-your-api-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-test-model")

    loaded = settings_module.load_settings()

    assert loaded.provider == "gemini"
    assert loaded.api_key == "gemini-test-key"
    assert loaded.model == "gemini-test-model"
    assert loaded.base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert loaded.env_file == settings_module.ENV_FILE


def test_requested_provider_is_preferred_when_configured(monkeypatch) -> None:
    _clear_provider_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")

    loaded = settings_module.load_settings()

    assert loaded.provider == "groq"
    assert loaded.api_key == "groq-test-key"


def test_falls_back_to_another_provider_when_requested_one_is_missing(monkeypatch) -> None:
    _clear_provider_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-test-key")

    loaded = settings_module.load_settings()

    assert loaded.provider == "openrouter"
    assert loaded.is_configured is True


def test_rejects_http_or_credential_bearing_custom_endpoint(monkeypatch) -> None:
    _clear_provider_environment(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://user:password@example.com/v1")

    loaded = settings_module.load_settings()

    assert loaded.is_configured is False
    assert "password" not in loaded.configuration_message


def test_reports_plain_language_message_when_no_key_is_available(monkeypatch) -> None:
    _clear_provider_environment(monkeypatch)

    loaded = settings_module.load_settings()

    assert loaded.is_configured is False
    assert "No AI provider is configured" in loaded.configuration_message
    assert str(Path(".venv") / ".env") in loaded.configuration_message
