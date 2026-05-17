from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str


def load_local_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

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

    if not base_url or not api_key:
        raise RuntimeError(
            "Missing LLM config. Add LITELLM_BASE_URL and LITELLM_API_KEY to .env."
        )

    return LLMConfig(base_url=base_url, api_key=api_key, model=model)
