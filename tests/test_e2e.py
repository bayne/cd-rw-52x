"""End-to-end tests: run the CLI as a subprocess and verify behaviour."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(*args: str, env: dict | None = None, **kwargs) -> subprocess.CompletedProcess:
    """Run the cdrw CLI via `python -m cdrw` and return the result."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "cdrw", *args],
        capture_output=True,
        text=True,
        env=merged_env,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# --record
# ---------------------------------------------------------------------------

class TestRecord:
    def test_record_git_dir(self, tmp_path, monkeypatch):
        repo = tmp_path / "myrepo"
        repo.mkdir()
        (repo / ".git").mkdir()
        cache_dir = tmp_path / "cache" / "cd-rw-52x"

        result = run_cli(
            "--record", str(repo),
            env={"XDG_CACHE_HOME": str(tmp_path / "cache")},
        )
        assert result.returncode == 0

        history_file = cache_dir / "history.jsonl"
        assert history_file.exists()
        entry = json.loads(history_file.read_text().strip())
        assert entry["path"] == str(repo)

    def test_record_non_git_dir_is_ignored(self, tmp_path):
        plain = tmp_path / "plain"
        plain.mkdir()
        cache_dir = tmp_path / "cache" / "cd-rw-52x"

        result = run_cli(
            "--record", str(plain),
            env={"XDG_CACHE_HOME": str(tmp_path / "cache")},
        )
        assert result.returncode == 0
        history_file = cache_dir / "history.jsonl"
        assert not history_file.exists() or history_file.read_text().strip() == ""

    def test_record_missing_path_argument(self, tmp_path):
        # --record with no path argument: should exit cleanly (no crash).
        result = run_cli(
            "--record",
            env={"XDG_CACHE_HOME": str(tmp_path / "cache")},
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# --install
# ---------------------------------------------------------------------------

class TestInstall:
    def test_install_appends_to_bashrc(self, tmp_path):
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("# existing content\n")

        result = run_cli(
            "--install",
            env={"HOME": str(tmp_path)},
        )
        assert result.returncode == 0
        content = bashrc.read_text()
        assert "cd-rw-52x" in content
        assert "__cd_rw_52x_record" in content
        assert "cdrw_jump" in content

    def test_install_is_idempotent(self, tmp_path):
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("# existing\n")

        # First install.
        run_cli("--install", env={"HOME": str(tmp_path)})
        content_after_first = bashrc.read_text()

        # Second install — should not duplicate.
        run_cli("--install", env={"HOME": str(tmp_path)})
        content_after_second = bashrc.read_text()

        assert content_after_first == content_after_second

    def test_install_creates_bashrc_if_missing(self, tmp_path):
        bashrc = tmp_path / ".bashrc"
        assert not bashrc.exists()

        result = run_cli("--install", env={"HOME": str(tmp_path)})
        assert result.returncode == 0
        assert bashrc.exists()
        assert "cdrw_jump" in bashrc.read_text()
