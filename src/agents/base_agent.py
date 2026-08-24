"""Shared helper for calling the LLM provider."""

import logging
from time import perf_counter

from openai import OpenAI

from config.settings import Settings
from src.logging_utils import get_app_logger, log_event


class AgentCallError(RuntimeError):
    """Raised when an LLM call fails."""


def call_llm(system_prompt: str, user_prompt: str, settings: Settings) -> str:
    """Call the configured OpenAI-compatible model and return text content."""
    logger = get_app_logger(settings.log_directory)
    started = perf_counter()
    if not settings.is_configured:
        log_event(logger, logging.ERROR, "Provider configuration is incomplete")
        raise AgentCallError(settings.configuration_message)

    client_kwargs: dict[str, str] = {"api_key": settings.api_key}
    if settings.base_url:
        client_kwargs["base_url"] = settings.base_url

    client = OpenAI(**client_kwargs)

    try:
        response = client.chat.completions.create(
            model=settings.model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as error:  # pragma: no cover - network/provider dependent
        status_code = getattr(error, "status_code", None)
        error_type = type(error).__name__
        log_event(
            logger,
            logging.ERROR,
            "Provider request failed",
            provider=settings.provider,
            model=settings.model,
            error_type=error_type,
            status_code=status_code or "unknown",
            duration_seconds=round(perf_counter() - started, 3),
        )
        raise AgentCallError(
            _provider_error_message(settings, status_code)
        ) from error

    content = response.choices[0].message.content
    if not content:
        log_event(logger, logging.ERROR, "Provider returned an empty response", provider=settings.provider)
        raise AgentCallError("LLM returned an empty response.")
    log_event(
        logger,
        logging.INFO,
        "Provider request completed",
        provider=settings.provider,
        model=settings.model,
        duration_seconds=round(perf_counter() - started, 3),
    )
    return content


def _provider_error_message(settings: Settings, status_code: int | None) -> str:
    """Return useful guidance without exposing provider response details."""
    if status_code in {401, 403}:
        return f"{settings.provider.title()} rejected the API key. Replace the key in .venv/.env."
    if status_code == 404:
        return f"{settings.provider.title()} could not find model '{settings.model}'. Check the model name in .venv/.env."
    if status_code == 429:
        return f"{settings.provider.title()} has reached a usage limit. Check the provider quota or wait and try again."
    if status_code and status_code >= 500:
        return f"{settings.provider.title()} is temporarily unavailable. Try again later."
    return "The AI provider could not be reached. Check your internet connection and provider settings."
