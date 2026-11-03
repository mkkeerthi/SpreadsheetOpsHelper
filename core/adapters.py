from __future__ import annotations

from pathlib import Path

from .workbook import CsvWorkbook, XLSX_SUFFIXES, XlsxWorkbook

SUPPORTED_SUFFIXES = XLSX_SUFFIXES | {".csv", ".numbers"}

BROWSE_FILETYPES = [
    ("Spreadsheets", "*.xlsx *.xlsm *.csv *.numbers"),
    ("Excel workbooks", "*.xlsx *.xlsm"),
    ("CSV files", "*.csv"),
    ("Apple Numbers", "*.numbers"),
    ("All files", "*.*"),
]


def open_workbook(path: str | Path):
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {target}")
    if not target.is_file():
        raise ValueError(f"Not a file: {target}")

    suffix = target.suffix.lower()
    if suffix in XLSX_SUFFIXES:
        return XlsxWorkbook(target)
    if suffix == ".csv":
        return CsvWorkbook(target)
    if suffix == ".numbers":
        from .numbers_macos import NumbersWorkbook

        return NumbersWorkbook(target)
    if suffix == ".xls":
        raise ValueError(
            "Legacy .xls files are not supported. Save the file as .xlsx and try again."
        )
    raise ValueError(
        f"Unsupported file type '{suffix or target.name}'. "
        "Use .xlsx, .xlsm, .csv, or .numbers."
    )
