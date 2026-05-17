from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIR = Path(__file__).resolve().parent
ENV_PATHS = (PROJECT_ROOT / ".env", UI_DIR / ".env")


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str


def load_local_env() -> None:
    for env_path in ENV_PATHS:
        if env_path.exists():
            load_env_file(env_path)


def load_env_file(env_path: Path) -> None:
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_llm_config() -> LLMConfig:
    load_local_env()
    base_url = os.getenv("LITELLM_BASE_URL", "").strip()
    api_key = os.getenv("LITELLM_API_KEY", "").strip()
    model = os.getenv("LITELLM_MODEL", "gpt-5-nano").strip()

    if is_missing_config_value(base_url) or is_missing_config_value(api_key):
        raise RuntimeError(
            "Missing LLM config. Add LITELLM_BASE_URL and LITELLM_API_KEY to .env or UI/.env."
        )

    return LLMConfig(base_url=base_url, api_key=api_key, model=model)


def is_missing_config_value(value: str) -> bool:
    return value in {"", "********", "replace-with-your-api-key"}
