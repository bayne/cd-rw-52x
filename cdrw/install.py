"""Install shell hooks into ~/.bashrc for directory history tracking."""

from pathlib import Path

MARKER_START = "# >>> cd-rw-52x >>>"
MARKER_END = "# <<< cd-rw-52x <<<"

BASH_SNIPPET = """\
# >>> cd-rw-52x >>>
# Directory jump tool — auto-generated, do not edit manually.
__cd_rw_52x_record() {
    command cdrw --record "$PWD" 2>/dev/null
}
if [[ ":${PROMPT_COMMAND}:" != *":__cd_rw_52x_record:"* ]]; then
    PROMPT_COMMAND="${PROMPT_COMMAND:+${PROMPT_COMMAND}:}__cd_rw_52x_record"
fi
cdrw_jump() {
    local target
    target=$(command cdrw --select)
    if [ -n "$target" ]; then
        cd "$target" || return 1
    fi
}
# <<< cd-rw-52x <<<
"""


def install(bashrc_path: Path | None = None) -> None:
    """Append hooks to ~/.bashrc (or provided path). Idempotent."""
    if bashrc_path is None:
        bashrc_path = Path.home() / ".bashrc"

    content = bashrc_path.read_text() if bashrc_path.exists() else ""
    if MARKER_START in content:
        print(f"cd-rw-52x hooks already present in {bashrc_path}")
        return

    with open(bashrc_path, "a") as f:
        f.write("\n" + BASH_SNIPPET)

    print(f"Installed cd-rw-52x hooks into {bashrc_path}")
    print("Restart your shell or run:")
    print(f"  source {bashrc_path}")
    print()
    print("Then use 'cdrw_jump' to open the project picker.")
    print("(Tip: bind it to a key, e.g.  bind '\"\\C-g\":\"cdrw_jump\\n\"')")
