"""Native file picker that runs in its own process.

Tk must be initialised on the process main thread. Streamlit runs app code on a
worker thread, and on macOS creating a Tk root there aborts the interpreter with
"NSWindow drag regions should only be invalidated on the Main Thread!".
Running the picker as a short-lived child process puts Tk on a real main thread
on every platform. ``app.py`` calls ``choose_file``; this module's ``main`` is
the child entry point (``python -m core.dialog <initial path>``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DIALOG_TITLE = "Select a spreadsheet"


class DialogError(RuntimeError):
    pass


def _start_dir(initial: str) -> Path:
    candidate = Path(initial).parent if initial else Path.home()
    if not candidate.is_dir():
        candidate = Path.home()
    return candidate


def choose_file(initial: str = "") -> str | None:
    """Open the picker and return the chosen path, or None when cancelled."""
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "core.dialog", str(_start_dir(initial))],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(Path(__file__).resolve().parent.parent),
        )
    except OSError as exc:
        raise DialogError(str(exc)) from exc

    chosen = completed.stdout.strip()
    if completed.returncode != 0 and not chosen:
        lines = (completed.stderr or "").strip().splitlines()
        raise DialogError(
            lines[-1] if lines else f"the picker exited with code {completed.returncode}"
        )
    return chosen or None


def main(argv: list[str]) -> int:
    initial = _start_dir(argv[1] if len(argv) > 1 else "")

    import tkinter as tk
    from tkinter import filedialog

    from .adapters import BROWSE_FILETYPES

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    try:
        chosen = filedialog.askopenfilename(
            title=DIALOG_TITLE,
            initialdir=str(initial),
            filetypes=BROWSE_FILETYPES,
        )
    finally:
        root.destroy()

    if chosen:
        sys.stdout.write(chosen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
