"""Unit tests for cdrw.git_info."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cdrw.git_info import get_git_info


@pytest.fixture()
def git_dir(tmp_path):
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture()
def plain_dir(tmp_path):
    return tmp_path


def test_returns_none_for_non_git_dir(plain_dir):
    assert get_git_info(str(plain_dir)) is None


def test_returns_branch_name(git_dir):
    mock_result = MagicMock()
    mock_result.stdout = "main\n"

    with patch("cdrw.git_info.subprocess.run", return_value=mock_result) as mock_run:
        result = get_git_info(str(git_dir))

    assert result == "main"
    mock_run.assert_called_once()


def test_returns_sha_when_detached_head(git_dir):
    branch_result = MagicMock(stdout="\n")    # empty = detached
    sha_result = MagicMock(stdout="a1b2c3d\n")

    with patch("cdrw.git_info.subprocess.run", side_effect=[branch_result, sha_result]):
        result = get_git_info(str(git_dir))

    assert result == "a1b2c3d"


def test_returns_none_on_timeout(git_dir):
    import subprocess

    with patch("cdrw.git_info.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 2)):
        result = get_git_info(str(git_dir))

    assert result is None


def test_returns_none_when_git_not_found(git_dir):
    with patch("cdrw.git_info.subprocess.run", side_effect=FileNotFoundError):
        result = get_git_info(str(git_dir))

    assert result is None


def test_returns_none_when_sha_also_empty(git_dir):
    branch_result = MagicMock(stdout="\n")
    sha_result = MagicMock(stdout="\n")

    with patch("cdrw.git_info.subprocess.run", side_effect=[branch_result, sha_result]):
        result = get_git_info(str(git_dir))

    assert result is None
