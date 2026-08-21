"""Load provider and application settings from the private virtualenv file."""

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".venv" / ".env"
load_dotenv(ENV_FILE)

_PLACEHOLDER_VALUES = {
    "",
    "replace-with-your-api-key",
    "replace-with-your-gemini-key",
    "replace-with-your-groq-key",
    "replace-with-your-huggingface-key",
    "replace-with-your-openrouter-key",
}

_PROVIDER_CONFIG = {
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "gpt-4o-mini", None),
    "gemini": (
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "GEMINI_BASE_URL",
        "gemini-2.0-flash",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    ),
    "groq": ("GROQ_API_KEY", "GROQ_MODEL", "GROQ_BASE_URL", "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1"),
    "openrouter": (
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_BASE_URL",
        "openai/gpt-oss-20b:free",
        "https://openrouter.ai/api/v1",
    ),
    "huggingface": (
        "HUGGINGFACE_API_KEY",
        "HUGGINGFACE_MODEL",
        "HUGGINGFACE_BASE_URL",
        "Qwen/Qwen2.5-72B-Instruct",
        "https://router.huggingface.co/v1",
    ),
}


def _usable(value: str | None) -> bool:
    return bool(value and value.strip().lower() not in _PLACEHOLDER_VALUES)


def _safe_base_url(value: str | None) -> str | None:
    """Accept only HTTPS API endpoints without embedded credentials."""
    if not value:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    return value.strip()


def _select_provider() -> tuple[str, str, str, str | None]:
    """Select a configured provider without exposing its secret."""
    requested = os.getenv("LLM_PROVIDER", "").strip().lower()
    provider_names = [requested] if requested in _PROVIDER_CONFIG else []
    provider_names.extend(name for name in _PROVIDER_CONFIG if name not in provider_names)

    for provider in provider_names:
        key_name, model_name, base_url_name, default_model, default_base_url = _PROVIDER_CONFIG[provider]
        api_key = os.getenv(key_name, "").strip()
        if _usable(api_key):
            model = os.getenv(model_name, "").strip() or os.getenv("LLM_MODEL", "").strip() or default_model
            configured_base_url = os.getenv(base_url_name, "").strip() or default_base_url
            base_url = _safe_base_url(configured_base_url)
            if configured_base_url and base_url is None:
                continue
            return provider, api_key, model, base_url

    return "", "", "", None


def _project_path(value: str) -> Path:
    """Resolve a configured path relative to the project root."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    """Runtime settings used by the document extractor."""

    api_key: str
    model: str
    base_url: str | None
    input_directory: Path
    output_directory: Path
    memory_directory: Path
    provider: str = ""
    env_file: Path = ENV_FILE

    @property
    def pricing_file(self) -> Path:
        return PROJECT_ROOT / "config" / "pricing.json"

    @property
    def is_configured(self) -> bool:
        return bool(self.provider and self.api_key and self.model)

    @property
    def configuration_message(self) -> str:
        if self.is_configured:
            return f"Using {self.provider.title()} with model {self.model}."
        return (
            "No AI provider is configured. Add one real API key to "
            f"{self.env_file} and start the application again."
        )


def load_settings() -> Settings:
    """Create settings from environment variables and project defaults."""
    provider, api_key, model, base_url = _select_provider()
    return Settings(
        api_key=api_key,
        model=model,
        base_url=base_url,
        input_directory=_project_path(os.getenv("INPUT_DIRECTORY", "data/input")),
        output_directory=_project_path(os.getenv("OUTPUT_DIRECTORY", "data/output")),
        memory_directory=_project_path(os.getenv("MEMORY_DIRECTORY", "storage")),
        provider=provider,
    )


def ensure_runtime_directories(settings: Settings) -> None:
    """Create writable runtime directories when the application starts."""
    for directory in (
        settings.input_directory,
        settings.output_directory,
        settings.memory_directory,
    ):
        directory.mkdir(parents=True, exist_ok=True)
