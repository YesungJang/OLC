"""Prompt file management utilities."""

from pathlib import Path
import os
import threading
from watchfiles import watch

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_PATH = PROMPT_DIR / "system_mysql.txt"
SYSTEM_PATH = Path(os.getenv("RAG_SYSTEM_PROMPT", DEFAULT_PATH))


def load_system_prompt() -> str:
    """Return the current system prompt text."""
    if not SYSTEM_PATH.exists():
        raise FileNotFoundError(f"Prompt file not found: {SYSTEM_PATH}")
    return SYSTEM_PATH.read_text(encoding="utf-8").strip()


class PromptManager:
    """Load and watch the system prompt file."""

    def __init__(self, path: Path = SYSTEM_PATH):
        self.path = path
        self.text = load_system_prompt()

    def start_watcher(self) -> None:
        """Start watching the prompt file for changes."""

        def _watch() -> None:
            for _ in watch(str(self.path)):
                self.text = load_system_prompt()
                print(f"[Prompt] reloaded -> {self.path}")

        threading.Thread(target=_watch, daemon=True).start()
