"""Command-line entry point for cdrw."""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    args = sys.argv[1:]

    if "--install" in args:
        from cdrw.install import install
        install()
        return

    if "--record" in args:
        idx = args.index("--record")
        if idx + 1 < len(args):
            from cdrw.history import record
            record(args[idx + 1])
        return

    # Default (no args) or --select: open TUI.
    from cdrw.tui import run_tui

    target = run_tui()
    if not target:
        return

    if os.environ.get("TMUX"):
        # In a tmux session: type the cd command into the current pane's prompt.
        safe_path = target.replace("'", "'\\''")
        subprocess.run(["tmux", "send-keys", f"cd '{safe_path}'"])
    else:
        # Shell function captures this and does `cd "$target"`.
        print(target)
