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

    safe_path = target.replace("'", "'\\''")
    cd_cmd = f"cd '{safe_path}'"

    if os.environ.get("TMUX"):
        try:
            # In a tmux session: type the cd command into the current pane's prompt.
            subprocess.run(["tmux", "send-keys", cd_cmd])
            return
        except FileNotFoundError:
            pass

    # Print the cd command for the shell wrapper to eval.
    print(cd_cmd)
