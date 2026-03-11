"""Curses-based interactive TUI for browsing and selecting a project directory."""

from __future__ import annotations

import curses
import os
import sys
from datetime import datetime
from pathlib import Path

from collections import Counter

from cdrw.fuzzy import fuzzy_match
from cdrw.git_info import get_git_info
from cdrw.history import load_entries
from cdrw.relative_time import relative_time

# Color pair IDs
_CP_MATCH = 1   # fuzzy-matched characters (bold yellow)
_CP_GIT = 2     # git branch label (cyan)
_CP_TIME = 3    # relative time (green)
_CP_DIM = 4     # dimmed / hint text


def run_tui() -> str | None:
    """Open the TUI on /dev/tty, return the selected path or None."""
    tty_fd: int | None = None
    saved_fd0: int | None = None
    saved_fd1: int | None = None

    try:
        # Flush Python-level buffers before touching raw fds.
        sys.stdout.flush()
        sys.stderr.flush()

        tty_fd = os.open("/dev/tty", os.O_RDWR)

        # Save original stdin/stdout fds (stdout may be a pipe from $(cdrw)).
        saved_fd0 = os.dup(0)
        saved_fd1 = os.dup(1)

        # Point fd 0 and fd 1 at the terminal so curses can do its job.
        os.dup2(tty_fd, 0)
        os.dup2(tty_fd, 1)
        os.close(tty_fd)
        tty_fd = None

        result = curses.wrapper(_tui_main)

    finally:
        # Restore original fds unconditionally.
        if saved_fd0 is not None:
            try:
                os.dup2(saved_fd0, 0)
                os.close(saved_fd0)
            except OSError:
                pass
        if saved_fd1 is not None:
            try:
                os.dup2(saved_fd1, 1)
                os.close(saved_fd1)
            except OSError:
                pass
        if tty_fd is not None:
            try:
                os.close(tty_fd)
            except OSError:
                pass

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _disambiguate_paths(paths: list[str]) -> dict[str, str]:
    """Build display names by adding parent dirs until all names are unique."""
    depth: dict[str, int] = {p: 1 for p in paths}

    while True:
        names: dict[str, str] = {}
        for p in paths:
            parts = Path(p).parts
            d = depth[p]
            names[p] = str(Path(*parts[-d:])) if d <= len(parts) else p

        name_counts = Counter(names.values())

        changed = False
        for p in paths:
            if name_counts[names[p]] > 1 and depth[p] < len(Path(p).parts):
                depth[p] += 1
                changed = True

        if not changed:
            break

    return names


def _safe_addstr(stdscr: curses.window, row: int, col: int, text: str, attr: int = 0) -> None:
    """Draw text, silently ignoring writes outside the screen boundary."""
    try:
        height, width = stdscr.getmaxyx()
        if row < 0 or row >= height or col < 0 or col >= width:
            return
        available = width - col
        # Never write to the very last cell of the last row (curses raises error).
        if row == height - 1:
            available = max(0, width - col - 1)
        text = text[:available]
        if text:
            stdscr.addstr(row, col, text, attr)
    except curses.error:
        pass


def _draw_row(
    stdscr: curses.window,
    row: int,
    width: int,
    name: str,
    match_indices: list[int],
    git_info: str | None,
    time_str: str,
    is_selected: bool,
) -> None:
    """Render a single directory entry row."""
    # Build right-side info string.
    right = f"{git_info}  {time_str}" if git_info else time_str
    right_col = width - len(right) - 1

    # Fill the row with the selection background.
    if is_selected:
        _safe_addstr(stdscr, row, 0, " " * (width - 1), curses.A_REVERSE)

    # Selector indicator.
    prefix = "> " if is_selected else "  "
    prefix_attr = curses.A_REVERSE | curses.A_BOLD if is_selected else 0
    _safe_addstr(stdscr, row, 0, prefix, prefix_attr)

    # Name with fuzzy highlights.
    match_set = set(match_indices)
    col = len(prefix)
    name_limit = max(col, right_col - 2) if right_col > col + 4 else width - 2
    for ci, ch in enumerate(name):
        if col >= name_limit:
            _safe_addstr(stdscr, row, col, "…", curses.A_REVERSE if is_selected else 0)
            col += 1
            break
        if is_selected:
            attr = curses.A_REVERSE
        elif ci in match_set:
            attr = curses.color_pair(_CP_MATCH) | curses.A_BOLD
        else:
            attr = 0
        _safe_addstr(stdscr, row, col, ch, attr)
        col += 1

    # Right-side: git branch + time.
    if right_col > col + 1:
        if git_info:
            g_attr = curses.A_REVERSE if is_selected else curses.color_pair(_CP_GIT)
            _safe_addstr(stdscr, row, right_col, git_info, g_attr)
            right_col += len(git_info)
            _safe_addstr(stdscr, row, right_col, "  ", curses.A_REVERSE if is_selected else 0)
            right_col += 2
        t_attr = curses.A_REVERSE if is_selected else curses.color_pair(_CP_TIME)
        _safe_addstr(stdscr, row, right_col, time_str, t_attr)


# ---------------------------------------------------------------------------
# Main TUI loop
# ---------------------------------------------------------------------------

def _tui_main(stdscr: curses.window) -> str | None:  # type: ignore[override]
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(_CP_MATCH, curses.COLOR_YELLOW, -1)
    curses.init_pair(_CP_GIT, curses.COLOR_CYAN, -1)
    curses.init_pair(_CP_TIME, curses.COLOR_GREEN, -1)
    curses.init_pair(_CP_DIM, -1, -1)
    stdscr.keypad(True)

    entries = load_entries()
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    display_names = _disambiguate_paths([e["path"] for e in entries])

    # Pre-warm git cache for the first screenful.
    git_cache: dict[str, str | None] = {}
    for entry in entries[:30]:
        git_cache[entry["path"]] = get_git_info(entry["path"])

    query = ""
    selected = 0

    while True:
        height, width = stdscr.getmaxyx()
        stdscr.erase()

        # --- Filter ---
        if query:
            filtered: list[tuple[dict, list[int]]] = []
            for entry in entries:
                name = display_names[entry["path"]]
                ok, indices = fuzzy_match(query, name)
                if ok:
                    filtered.append((entry, indices))
        else:
            filtered = [(entry, []) for entry in entries]

        total = len(filtered)
        if total == 0:
            selected = 0
        else:
            selected = max(0, min(selected, total - 1))

        # --- Layout ---
        # Rows 0 .. height-2: list  |  Row height-1: search bar
        list_height = height - 1
        scroll = 0
        if total > 0:
            # Keep selected item centred in view.
            scroll = max(0, selected - list_height // 2)
            scroll = min(scroll, max(0, total - list_height))

        # --- Draw list rows ---
        for i in range(list_height):
            idx = i + scroll
            if idx >= total:
                break
            entry, indices = filtered[idx]
            path = entry["path"]
            name = display_names[path]

            if path not in git_cache:
                git_cache[path] = get_git_info(path)
            ginfo = git_cache[path]

            try:
                dt = datetime.fromisoformat(entry["timestamp"])
                tstr = relative_time(dt)
            except (ValueError, KeyError):
                tstr = "?"

            _draw_row(stdscr, i, width, name, indices, ginfo, tstr, idx == selected)

        # Empty-state hint.
        if total == 0:
            if entries:
                hint = "No matches"
            else:
                hint = "No history yet — run with --install to start tracking"
            _safe_addstr(stdscr, 0, 2, hint[: width - 3], curses.A_DIM)

        # --- Search bar ---
        search_line = f"> {query}"
        count_str = f" {total}/{len(entries)}"
        _safe_addstr(stdscr, height - 1, 0, search_line, curses.A_BOLD)
        if len(search_line) + len(count_str) + 1 < width:
            _safe_addstr(
                stdscr,
                height - 1,
                width - len(count_str) - 1,
                count_str,
                curses.A_DIM,
            )

        # Position cursor after query text.
        try:
            curses.curs_set(1)
            stdscr.move(height - 1, min(len(search_line), width - 1))
        except curses.error:
            pass

        stdscr.refresh()

        # --- Input ---
        key = stdscr.getch()

        if key in (27, 3):  # ESC, Ctrl-C
            return None
        elif key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(total - 1, selected + 1) if total > 0 else 0
        elif key == curses.KEY_PPAGE:  # Page Up
            selected = max(0, selected - list_height)
        elif key == curses.KEY_NPAGE:  # Page Down
            selected = min(total - 1, selected + list_height) if total > 0 else 0
        elif key in (ord("\n"), ord("\r"), curses.KEY_ENTER):
            if filtered:
                return filtered[selected][0]["path"]
            return None
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            query = query[:-1]
            selected = 0
        elif key == 21:  # Ctrl-U — clear query
            query = ""
            selected = 0
        elif 32 <= key <= 126:  # printable ASCII
            query += chr(key)
            selected = 0
