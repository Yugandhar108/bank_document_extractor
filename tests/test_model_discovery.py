"""Tests for economical Gemini model discovery."""

import json
from pathlib import Path

from config.model_discovery import (
    ModelSelection,
    list_gemini_text_models,
    select_gemini_model,
)


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(
            {
                "models": [
                    {
                        "name": "models/gemini-3.6-flash",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemini-3.5-flash-lite",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemini-embedding",
                        "supportedGenerationMethods": ["embedContent"],
                    },
                ]
            }
        ).encode("utf-8")


def test_lists_only_text_generation_models(monkeypatch) -> None:
    monkeypatch.setattr("config.model_discovery.urlopen", lambda request, timeout: FakeResponse())

    models = list_gemini_text_models("test-key")

    assert models == ["gemini-3.6-flash", "gemini-3.5-flash-lite"]


def test_prefers_free_available_model(tmp_path: Path, monkeypatch) -> None:
    pricing_file = tmp_path / "pricing.json"
    pricing_file.write_text(
        json.dumps(
            {
                "gemini": {
                    "gemini-3.6-flash": {
                        "is_free": False,
                        "input_usd_per_1m_tokens": 1.0,
                        "output_usd_per_1m_tokens": 5.0,
                    },
                    "gemini-3.5-flash-lite": {
                        "is_free": True,
                        "input_usd_per_1m_tokens": 0.0,
                        "output_usd_per_1m_tokens": 0.0,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "config.model_discovery.list_gemini_text_models",
        lambda api_key: ["gemini-3.6-flash", "gemini-3.5-flash-lite"],
    )

    selection = select_gemini_model("test-key", "auto", pricing_file, "gemini-fallback")

    assert selection == ModelSelection("gemini-3.5-flash-lite", "free Gemini model")


def test_uses_lowest_cost_when_no_free_model_is_available(tmp_path: Path, monkeypatch) -> None:
    pricing_file = tmp_path / "pricing.json"
    pricing_file.write_text(
        json.dumps(
            {
                "gemini": {
                    "expensive": {
                        "is_free": False,
                        "input_usd_per_1m_tokens": 2.0,
                        "output_usd_per_1m_tokens": 4.0,
                    },
                    "cheap": {
                        "is_free": False,
                        "input_usd_per_1m_tokens": 0.1,
                        "output_usd_per_1m_tokens": 0.2,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "config.model_discovery.list_gemini_text_models",
        lambda api_key: ["expensive", "cheap"],
    )

    selection = select_gemini_model("test-key", "auto", pricing_file, "fallback")

    assert selection == ModelSelection("cheap", "lowest-cost available Gemini model")


def test_uses_fallback_when_discovery_fails(tmp_path: Path, monkeypatch) -> None:
    pricing_file = tmp_path / "pricing.json"
    pricing_file.write_text(json.dumps({"gemini": {}}), encoding="utf-8")
    monkeypatch.setattr(
        "config.model_discovery.list_gemini_text_models",
        lambda api_key: (_ for _ in ()).throw(RuntimeError("discovery unavailable")),
    )

    selection = select_gemini_model("test-key", "auto", pricing_file, "gemini-fallback")

    assert selection == ModelSelection("gemini-fallback", "configured fallback after discovery failure")
