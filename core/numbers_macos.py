from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from .workbook import XlsxWorkbook, timestamped_output_path

EXPORT_TO_XLSX = """
on run argv
    set inPath to POSIX file (item 1 of argv)
    set outPath to POSIX file (item 2 of argv)
    tell application "Numbers"
        set doc to open inPath
        export doc to outPath as Microsoft Excel
        close doc saving no
    end tell
end run
"""

SAVE_AS_NUMBERS = """
on run argv
    set inPath to POSIX file (item 1 of argv)
    set outPath to POSIX file (item 2 of argv)
    tell application "Numbers"
        set doc to open inPath
        save doc in outPath
        close doc saving no
    end tell
end run
"""


class UnsupportedPlatformError(RuntimeError):
    pass


def require_macos() -> None:
    if sys.platform != "darwin":
        raise UnsupportedPlatformError(
            "Apple Numbers (.numbers) files require macOS and the Numbers app. "
            "On this machine, export the file to .xlsx or .csv first."
        )


def _run_osascript(script: str, source: Path, target: Path) -> None:
    require_macos()
    result = subprocess.run(
        ["osascript", "-e", script, str(source), str(target)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Numbers automation failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    if not target.exists():
        raise RuntimeError(f"Numbers did not create the expected file: {target}")


def export_to_xlsx(source: str | Path, target: str | Path) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _run_osascript(EXPORT_TO_XLSX, Path(source), target)
    return target


def save_as_numbers(source_xlsx: str | Path, target: str | Path) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _run_osascript(SAVE_AS_NUMBERS, Path(source_xlsx), target)
    return target


class NumbersWorkbook:
    """Exports a .numbers document to a temp .xlsx and saves results beside the original."""

    def __init__(self, path: str | Path):
        require_macos()
        self.path = Path(path)
        self._temp_dir = tempfile.TemporaryDirectory(prefix="numbers_helper_")
        self._xlsx_path = export_to_xlsx(
            self.path, Path(self._temp_dir.name) / f"{self.path.stem}.xlsx"
        )
        self._inner = XlsxWorkbook(self._xlsx_path)

    def __getattr__(self, name: str):
        return getattr(self._inner, name)

    def save_as(self, target: str | Path) -> Path:
        target = Path(target)
        temp_xlsx = Path(self._temp_dir.name) / "output.xlsx"
        self._inner.save_as(temp_xlsx)
        return save_as_numbers(temp_xlsx, target)

    def save_copy(self) -> Path:
        return self.save_as(timestamped_output_path(self.path, ".numbers"))

    def close(self) -> None:
        self._inner.close()
        self._temp_dir.cleanup()
