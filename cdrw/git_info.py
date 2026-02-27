"""Retrieve the current git branch name or short SHA for a directory."""

import subprocess
from pathlib import Path


def get_git_info(path: str) -> str | None:
    """Return the current branch name, or short SHA if in detached HEAD state."""
    p = Path(path)
    if not (p / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=2,
        )
        branch = result.stdout.strip()
        if branch:
            return branch
        # Detached HEAD — return short SHA
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=2,
        )
        sha = result.stdout.strip()
        return sha or None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
