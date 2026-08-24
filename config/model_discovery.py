"""Discover and select an economical Gemini model."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"


@dataclass(frozen=True)
class ModelSelection:
    """Selected model and the reason it was selected."""

    model: str
    source: str


@dataclass(frozen=True)
class ModelPricing:
    """Local pricing policy for one model."""

    model: str
    is_free: bool
    input_cost: float
    output_cost: float


def _model_name(raw_name: str) -> str:
    return raw_name.removeprefix("models/")


def list_gemini_text_models(api_key: str, timeout_seconds: float = 8.0) -> list[str]:
    """Return available Gemini models that support text generation.

    Provider responses and API keys are intentionally not included in exceptions.
    """
    query = urlencode({"key": api_key})
    request = Request(
        f"{GEMINI_MODELS_URL}?{query}",
        headers={"Accept": "application/json"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        raise RuntimeError("Gemini model discovery was unavailable.") from error

    models: list[str] = []
    for item in payload.get("models", []):
        methods = item.get("supportedGenerationMethods", [])
        name = item.get("name", "")
        if "generateContent" in methods and name:
            models.append(_model_name(name))
    return models


def _load_pricing(pricing_file: Path, provider: str) -> dict[str, ModelPricing]:
    payload = json.loads(pricing_file.read_text(encoding="utf-8"))
    provider_payload = payload.get(provider, {})
    return {
        model: ModelPricing(
            model=model,
            is_free=bool(details.get("is_free", False)),
            input_cost=float(details.get("input_usd_per_1m_tokens", 0.0)),
            output_cost=float(details.get("output_usd_per_1m_tokens", 0.0)),
        )
        for model, details in provider_payload.items()
    }


def select_gemini_model(
    api_key: str,
    requested_model: str,
    pricing_file: Path,
    fallback_model: str,
) -> ModelSelection:
    """Apply free-first, lowest-cost, then fallback selection policy."""
    if requested_model.strip().lower() != "auto":
        return ModelSelection(requested_model, "configured")

    try:
        available_models = set(list_gemini_text_models(api_key))
    except RuntimeError:
        return ModelSelection(fallback_model, "configured fallback after discovery failure")

    pricing = _load_pricing(pricing_file, "gemini")
    known_available = [pricing[name] for name in available_models if name in pricing]
    free_models = [item for item in known_available if item.is_free]
    if free_models:
        selected = min(free_models, key=lambda item: (item.input_cost + item.output_cost, item.model))
        return ModelSelection(selected.model, "free Gemini model")
    if known_available:
        selected = min(known_available, key=lambda item: (item.input_cost + item.output_cost, item.model))
        return ModelSelection(selected.model, "lowest-cost available Gemini model")

    return ModelSelection(fallback_model, "configured fallback")
