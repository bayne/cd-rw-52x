"""Unit tests for the TUI logic (with curses mocked out)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import cdrw.tui as tui_mod
from cdrw.tui import _disambiguate_paths, _draw_row, _safe_addstr, _tui_main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stdscr(height: int = 24, width: int = 80) -> MagicMock:
    stdscr = MagicMock()
    stdscr.getmaxyx.return_value = (height, width)
    stdscr.getch.return_value = ord("q")  # default: quit
    return stdscr


def _entry(path: str, minutes_ago: int = 5) -> dict:
    ts = (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()
    return {"path": path, "timestamp": ts}


# ---------------------------------------------------------------------------
# _safe_addstr
# ---------------------------------------------------------------------------

class TestSafeAddStr:
    def test_normal_write(self):
        stdscr = _make_stdscr()
        _safe_addstr(stdscr, 0, 0, "hello")
        stdscr.addstr.assert_called_once_with(0, 0, "hello", 0)

    def test_skips_out_of_bounds_row(self):
        stdscr = _make_stdscr(height=5)
        _safe_addstr(stdscr, 10, 0, "hello")
        stdscr.addstr.assert_not_called()

    def test_skips_out_of_bounds_col(self):
        stdscr = _make_stdscr(width=5)
        _safe_addstr(stdscr, 0, 10, "hello")
        stdscr.addstr.assert_not_called()

    def test_truncates_text_to_fit(self):
        stdscr = _make_stdscr(width=10)
        _safe_addstr(stdscr, 0, 7, "hello")
        # only 3 chars available (width-col-1 = 10-7-1=2... actually 3)
        call_args = stdscr.addstr.call_args
        written_text = call_args[0][2]
        assert len(written_text) <= 10 - 7

    def test_swallows_curses_error(self):
        import curses
        stdscr = _make_stdscr()
        stdscr.addstr.side_effect = curses.error("test error")
        # Should not raise.
        _safe_addstr(stdscr, 0, 0, "hi")


# ---------------------------------------------------------------------------
# _tui_main via mocked entries + input sequence
# ---------------------------------------------------------------------------

def _run_tui_with_keys(entries: list[dict], key_sequence: list[int]) -> str | None:
    """Drive _tui_main with a fixed list of entries and key inputs."""
    import curses as _curses

    key_iter = iter(key_sequence)

    stdscr = MagicMock()
    stdscr.getmaxyx.return_value = (24, 80)
    stdscr.getch.side_effect = list(key_sequence)

    with (
        patch.object(tui_mod, "load_entries", return_value=entries),
        patch.object(tui_mod, "get_git_info", return_value="main"),
        patch("curses.start_color"),
        patch("curses.use_default_colors"),
        patch("curses.init_pair"),
        patch("curses.curs_set"),
        patch("curses.color_pair", return_value=0),
        patch.object(_curses, "A_BOLD", 0),
        patch.object(_curses, "A_REVERSE", 0),
        patch.object(_curses, "A_DIM", 0),
        patch.object(_curses, "KEY_UP", 259),
        patch.object(_curses, "KEY_DOWN", 258),
        patch.object(_curses, "KEY_ENTER", 343),
        patch.object(_curses, "KEY_BACKSPACE", 263),
        patch.object(_curses, "KEY_PPAGE", 339),
        patch.object(_curses, "KEY_NPAGE", 338),
    ):
        return _tui_main(stdscr)


# ---------------------------------------------------------------------------
# _disambiguate_paths
# ---------------------------------------------------------------------------

class TestDisambiguatePaths:
    def test_unique_basenames_unchanged(self):
        paths = ["/home/user/alpha", "/home/user/beta"]
        result = _disambiguate_paths(paths)
        assert result["/home/user/alpha"] == "alpha"
        assert result["/home/user/beta"] == "beta"

    def test_duplicate_basenames_get_parent(self):
        paths = ["/home/user/work/api", "/home/user/personal/api"]
        result = _disambiguate_paths(paths)
        assert result["/home/user/work/api"] == "work/api"
        assert result["/home/user/personal/api"] == "personal/api"

    def test_triple_duplicate_needs_two_levels(self):
        paths = ["/a/x/api", "/b/x/api", "/c/y/api"]
        result = _disambiguate_paths(paths)
        # /a/x/api and /b/x/api both have parent "x", so need grandparent
        assert result["/a/x/api"] == "a/x/api"
        assert result["/b/x/api"] == "b/x/api"
        # /c/y/api is unique at depth 2 ("y/api")
        assert result["/c/y/api"] == "y/api"

    def test_empty_list(self):
        assert _disambiguate_paths([]) == {}

    def test_single_entry(self):
        result = _disambiguate_paths(["/foo/bar"])
        assert result["/foo/bar"] == "bar"


class TestTuiMain:
    def test_esc_returns_none(self, tmp_path):
        entries = [_entry(str(tmp_path / "proj"))]
        result = _run_tui_with_keys(entries, [27])
        assert result is None

    def test_ctrl_c_returns_none(self, tmp_path):
        entries = [_entry(str(tmp_path / "proj"))]
        result = _run_tui_with_keys(entries, [3])
        assert result is None

    def test_enter_selects_first_entry(self, tmp_path):
        p = tmp_path / "myproject"
        p.mkdir()
        entries = [_entry(str(p))]
        result = _run_tui_with_keys(entries, [ord("\n")])
        assert result == str(p)

    def test_enter_on_empty_list_returns_none(self):
        result = _run_tui_with_keys([], [ord("\n")])
        assert result is None

    def test_arrow_down_then_enter_selects_second(self, tmp_path):
        import curses
        p1 = tmp_path / "alpha"
        p2 = tmp_path / "beta"
        p1.mkdir()
        p2.mkdir()
        entries = [_entry(str(p1), minutes_ago=1), _entry(str(p2), minutes_ago=2)]
        result = _run_tui_with_keys(entries, [258, ord("\n")])  # 258 = KEY_DOWN
        assert result == str(p2)

    def test_fuzzy_filter_reduces_results(self, tmp_path):
        p1 = tmp_path / "alpha-project"
        p2 = tmp_path / "beta-project"
        p1.mkdir()
        p2.mkdir()
        entries = [_entry(str(p1)), _entry(str(p2))]
        # Type 'alp', then Enter — should select alpha-project.
        result = _run_tui_with_keys(
            entries, [ord("a"), ord("l"), ord("p"), ord("\n")]
        )
        assert result == str(p1)

    def test_backspace_clears_query(self, tmp_path):
        p1 = tmp_path / "alpha"
        p2 = tmp_path / "beta"
        p1.mkdir()
        p2.mkdir()
        entries = [_entry(str(p1), 1), _entry(str(p2), 2)]
        # Type 'z' (no match), backspace (clears), Enter (selects first).
        result = _run_tui_with_keys(entries, [ord("z"), 127, ord("\n")])
        assert result == str(p1)

    def test_ctrl_u_clears_query(self, tmp_path):
        p1 = tmp_path / "myproject"
        p1.mkdir()
        entries = [_entry(str(p1))]
        # Type 'z' (no match), Ctrl-U, Enter (now matches again).
        result = _run_tui_with_keys(entries, [ord("z"), 21, ord("\n")])
        assert result == str(p1)
