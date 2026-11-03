from __future__ import annotations

import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

XLSX_SUFFIXES = {".xlsx", ".xlsm"}
CSV_SHEET_NAME = "Sheet1"


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def timestamped_output_path(destination: str | Path, suffix: str | None = None) -> Path:
    dest = Path(destination)
    suffix = suffix or dest.suffix
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{dest.stem}_{stamp}"
    candidate = dest.with_name(base + suffix)
    counter = 1
    while candidate.exists():
        candidate = dest.with_name(f"{base}_{counter}{suffix}")
        counter += 1
    return candidate


def _temp_path(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(
        prefix=f".{target.stem}_", suffix=target.suffix, dir=str(target.parent)
    )
    os.close(handle)
    return Path(name)


class XlsxWorkbook:
    """openpyxl-backed workbook with a small read/write surface for the copier."""

    def __init__(self, path: str | Path, data_only: bool = False):
        self.path = Path(path)
        self._keep_vba = self.path.suffix.lower() == ".xlsm"
        self._wb = openpyxl.load_workbook(
            self.path, data_only=data_only, keep_vba=self._keep_vba
        )
        self._value_wb = self._wb if data_only else None

    def sheet_names(self) -> list[str]:
        return list(self._wb.sheetnames)

    def _sheet(self, name: str) -> Worksheet:
        if name not in self._wb.sheetnames:
            raise KeyError(f"Sheet '{name}' was not found in {self.path.name}.")
        return self._wb[name]

    def max_column(self, name: str) -> int:
        return self._sheet(name).max_column

    def last_data_row(self, name: str) -> int:
        sheet = self._sheet(name)
        for index in range(sheet.max_row, 0, -1):
            values = next(
                sheet.iter_rows(min_row=index, max_row=index, values_only=True), ()
            )
            if any(not is_blank(value) for value in values):
                return index
        return 0

    def get_value(self, name: str, row: int, column: int) -> Any:
        cell = self._sheet(name).cell(row=row, column=column)
        if cell.data_type == "f":
            return self._cached_value(name, row, column)
        return cell.value

    def _cached_value(self, name: str, row: int, column: int) -> Any:
        if self._value_wb is None:
            self._value_wb = openpyxl.load_workbook(
                self.path, data_only=True, keep_vba=self._keep_vba
            )
        return self._value_wb[name].cell(row=row, column=column).value

    def get_number_format(self, name: str, row: int, column: int) -> str:
        return self._sheet(name).cell(row=row, column=column).number_format

    def set_value(
        self, name: str, row: int, column: int, value: Any, number_format: str | None
    ) -> None:
        cell = self._sheet(name).cell(row=row, column=column)
        cell.value = value
        if number_format:
            cell.number_format = number_format

    def save_as(self, target: str | Path) -> Path:
        target = Path(target)
        temp = _temp_path(target)
        try:
            self._wb.save(temp)
            check = openpyxl.load_workbook(temp, read_only=True)
            check.close()
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
        return target

    def save_copy(self) -> Path:
        return self.save_as(timestamped_output_path(self.path))

    def close(self) -> None:
        self._wb.close()
        if self._value_wb is not None and self._value_wb is not self._wb:
            self._value_wb.close()


class CsvWorkbook:
    """A CSV file exposed as a single sheet."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        with self.path.open("r", newline="", encoding="utf-8-sig") as handle:
            self._rows: list[list[Any]] = [list(row) for row in csv.reader(handle)]
        self._width = max((len(row) for row in self._rows), default=0)
        self._name = CSV_SHEET_NAME

    def sheet_names(self) -> list[str]:
        return [self._name]

    def _check(self, name: str) -> None:
        if name != self._name:
            raise KeyError(f"Sheet '{name}' was not found in {self.path.name}.")

    def max_column(self, name: str) -> int:
        self._check(name)
        return self._width

    def last_data_row(self, name: str) -> int:
        self._check(name)
        for index in range(len(self._rows), 0, -1):
            if any(not is_blank(value) for value in self._rows[index - 1]):
                return index
        return 0

    def get_value(self, name: str, row: int, column: int) -> Any:
        self._check(name)
        if row - 1 >= len(self._rows):
            return None
        values = self._rows[row - 1]
        return values[column - 1] if column - 1 < len(values) else None

    def get_number_format(self, name: str, row: int, column: int) -> str:
        self._check(name)
        return "General"

    def set_value(
        self, name: str, row: int, column: int, value: Any, number_format: str | None
    ) -> None:
        self._check(name)
        while len(self._rows) < row:
            self._rows.append([])
        values = self._rows[row - 1]
        while len(values) < column:
            values.append("")
        values[column - 1] = value
        self._width = max(self._width, column, len(values))

    def save_as(self, target: str | Path) -> Path:
        target = Path(target)
        temp = _temp_path(target)
        try:
            with temp.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerows(self._rows)
            with temp.open("r", newline="", encoding="utf-8") as verify:
                list(csv.reader(verify))
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
        return target

    def save_copy(self) -> Path:
        return self.save_as(timestamped_output_path(self.path))

    def close(self) -> None:
        return None
