"""Shared helper for calling the LLM provider."""

from openai import OpenAI

from config.settings import Settings


class AgentCallError(RuntimeError):
    """Raised when an LLM call fails."""


def call_llm(system_prompt: str, user_prompt: str, settings: Settings) -> str:
    """Call the configured OpenAI-compatible model and return text content."""
    if not settings.is_configured:
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
        raise AgentCallError("LLM call failed.") from error

    content = response.choices[0].message.content
    if not content:
        raise AgentCallError("LLM returned an empty response.")
    return content
