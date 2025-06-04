"""Miscellaneous helper functions."""

import re

_fence_start = re.compile(r"^```[\w]*\n?", re.S)
_fence_end = re.compile(r"```$", re.S)


def strip_md_fence(text: str) -> str:
    """Remove a single Markdown code fence from ``text``."""
    text = text.strip()
    if text.startswith("```"):
        text = _fence_start.sub("", text)
        text = _fence_end.sub("", text).strip()
    return text
