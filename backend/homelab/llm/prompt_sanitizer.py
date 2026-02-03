"""Prompt sanitization helpers for cloud LLM providers."""

from __future__ import annotations

import re


_RECENT_LOGS_HEADING = "**Recent Logs:**"


def _redact_markdown_section(prompt: str, heading: str) -> str:
    pattern = re.compile(rf"({re.escape(heading)}\n)(.*?)(\n\*\*|\Z)", re.DOTALL)

    def repl(match: re.Match[str]) -> str:
        tail = match.group(3)
        return f"{match.group(1)}[REDACTED FOR CLOUD]\n{tail}"

    return pattern.sub(repl, prompt, count=1)


def sanitize_prompt_for_cloud(prompt: str) -> str:
    """Remove raw log lines from prompts before sending to cloud LLMs."""
    sanitized = _redact_markdown_section(prompt, _RECENT_LOGS_HEADING)
    return sanitized
