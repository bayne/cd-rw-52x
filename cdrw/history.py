"""Directory visit history stored as JSONL in ~/.cache/cd-rw-52x/history.jsonl."""

import json
import os
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "cd-rw-52x"
HISTORY_FILE = CACHE_DIR / "history.jsonl"


def get_history_file() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return HISTORY_FILE


def record(path: str) -> None:
    """Append a directory visit if it contains a .git directory."""
    p = Path(path)
    if not (p / ".git").exists():
        return
    entry = {"path": str(p.resolve()), "timestamp": datetime.now().isoformat()}
    with open(get_history_file(), "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_entries() -> list[dict]:
    """Load history, deduplicating by path (most recent timestamp wins)."""
    history_file = get_history_file()
    if not history_file.exists():
        return []
    seen: dict[str, dict] = {}
    with open(history_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                path = entry.get("path", "")
                if path and Path(path).is_dir():
                    seen[path] = entry
            except json.JSONDecodeError:
                pass
    return list(seen.values())
