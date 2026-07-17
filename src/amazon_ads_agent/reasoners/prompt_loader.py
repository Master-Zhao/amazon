"""Fail-closed loader for repository-owned Reasoner prompt templates."""

from __future__ import annotations

from pathlib import Path

from .errors import PromptError

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROMPT_ROOT = REPOSITORY_ROOT / "prompts"
ALLOWED_PROMPTS = frozenset(
    {"reasoner-system.md", "keyword-bid-optimization.md", "revision-feedback.md"}
)


def load_prompt(name: str) -> str:
    """Load one allow-listed UTF-8 prompt without accepting caller paths."""

    candidate = Path(name)
    if candidate.is_absolute() or candidate.name != name or name not in ALLOWED_PROMPTS:
        raise PromptError(
            "ERR_PROMPT_PATH_INVALID",
            "prompt name is not an allowed repository template",
            retryable=False,
            provider="llm",
        )
    path = PROMPT_ROOT / name
    if not path.is_file():
        raise PromptError(
            "ERR_PROMPT_FILE_NOT_FOUND",
            f"required prompt template is missing: {name}",
            retryable=False,
            provider="llm",
        )
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PromptError(
            "ERR_PROMPT_FILE_NOT_FOUND",
            f"required prompt template cannot be read: {name}",
            retryable=False,
            provider="llm",
        ) from exc
    if not content.strip():
        raise PromptError(
            "ERR_PROMPT_FILE_EMPTY",
            f"required prompt template is empty: {name}",
            retryable=False,
            provider="llm",
        )
    return content.strip()
