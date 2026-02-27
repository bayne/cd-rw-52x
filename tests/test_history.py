"""Unit tests for cdrw.history."""

import json
import os
from pathlib import Path

import pytest

import cdrw.history as history_mod


@pytest.fixture()
def tmp_history(tmp_path, monkeypatch):
    """Redirect history storage to a temp directory."""
    cache_dir = tmp_path / "cache" / "cd-rw-52x"
    cache_dir.mkdir(parents=True)
    history_file = cache_dir / "history.jsonl"

    monkeypatch.setattr(history_mod, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(history_mod, "HISTORY_FILE", history_file)

    return history_file


@pytest.fixture()
def git_dir(tmp_path):
    """Create a fake git repository directory."""
    repo = tmp_path / "myproject"
    repo.mkdir()
    (repo / ".git").mkdir()
    return repo


def test_record_creates_entry(tmp_history, git_dir):
    history_mod.record(str(git_dir))
    lines = tmp_history.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["path"] == str(git_dir)
    assert "timestamp" in entry


def test_record_ignores_non_git_dir(tmp_history, tmp_path):
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    history_mod.record(str(plain_dir))
    assert not tmp_history.exists() or tmp_history.read_text().strip() == ""


def test_record_multiple_paths(tmp_history, tmp_path):
    repos = []
    for name in ("alpha", "beta", "gamma"):
        r = tmp_path / name
        r.mkdir()
        (r / ".git").mkdir()
        repos.append(r)
        history_mod.record(str(r))

    lines = tmp_history.read_text().strip().splitlines()
    assert len(lines) == 3
    paths = [json.loads(l)["path"] for l in lines]
    assert all(str(r) in paths for r in repos)


def test_load_entries_empty_when_no_file(tmp_history):
    entries = history_mod.load_entries()
    assert entries == []


def test_load_entries_returns_recorded(tmp_history, git_dir):
    history_mod.record(str(git_dir))
    entries = history_mod.load_entries()
    assert len(entries) == 1
    assert entries[0]["path"] == str(git_dir)


def test_load_entries_deduplicates_keeps_latest(tmp_history, git_dir):
    # Write two entries for the same path manually (simulating two visits).
    with open(tmp_history, "a") as f:
        f.write(json.dumps({"path": str(git_dir), "timestamp": "2024-01-01T10:00:00"}) + "\n")
        f.write(json.dumps({"path": str(git_dir), "timestamp": "2024-06-01T12:00:00"}) + "\n")

    entries = history_mod.load_entries()
    assert len(entries) == 1
    assert entries[0]["timestamp"] == "2024-06-01T12:00:00"


def test_load_entries_skips_malformed_lines(tmp_history, git_dir):
    with open(tmp_history, "a") as f:
        f.write(json.dumps({"path": str(git_dir), "timestamp": "2024-01-01T00:00:00"}) + "\n")
        f.write("not valid json\n")
        f.write("{}\n")  # valid JSON but no 'path' key — ignored

    entries = history_mod.load_entries()
    assert len(entries) == 1


def test_load_entries_skips_blank_lines(tmp_history, git_dir):
    with open(tmp_history, "a") as f:
        f.write("\n")
        f.write(json.dumps({"path": str(git_dir), "timestamp": "2024-01-01T00:00:00"}) + "\n")
        f.write("  \n")

    entries = history_mod.load_entries()
    assert len(entries) == 1
