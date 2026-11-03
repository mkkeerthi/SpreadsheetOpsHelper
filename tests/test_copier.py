from __future__ import annotations

import hashlib
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook

from core.adapters import open_workbook
from core.copier import copy_ranges
from core.validator import SheetRange


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_source(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet["A1"] = "Header"
    sheet["B1"] = "Date"
    sheet["A2"] = "alpha"
    sheet["B2"] = datetime(2026, 1, 2)
    sheet["B2"].number_format = "mm-dd-yy"
    sheet["A3"] = None
    sheet["B3"] = None
    sheet["A4"] = "gamma"
    sheet["B4"] = 35.5
    sheet["B4"].number_format = "0.00"
    sheet["C4"] = ""
    workbook.save(path)


def _build_destination(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet["A1"] = "Header"
    sheet["B1"] = "Date"
    sheet["A2"] = "existing"
    sheet["B2"] = 100
    sheet["A5"].number_format = "mm-dd-yy"
    workbook.save(path)


class CopyRangesTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.folder = Path(self._temp.name)
        self.source_path = self.folder / "source.xlsx"
        self.destination_path = self.folder / "destination.xlsx"
        _build_source(self.source_path)
        _build_destination(self.destination_path)

    def tearDown(self):
        self._temp.cleanup()

    def test_copy_appends_after_last_non_blank_row_and_preserves_formats(self):
        original_hash = _file_hash(self.destination_path)
        progress = []

        source = open_workbook(self.source_path)
        destination = open_workbook(self.destination_path)
        try:
            results = copy_ranges(
                source,
                destination,
                [SheetRange("Sheet1", 2, 4)],
                on_progress=lambda done, total: progress.append((done, total)),
            )
            output_path = destination.save_copy()
        finally:
            source.close()
            destination.close()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].copied_rows, 2)
        self.assertEqual(results[0].skipped_rows, 1)
        self.assertEqual(results[0].destination_start_row, 3)
        self.assertEqual(results[0].destination_end_row, 4)
        self.assertEqual(progress, [(1, 3), (2, 3), (3, 3)])

        self.assertEqual(_file_hash(self.destination_path), original_hash)
        self.assertTrue(output_path.exists())
        self.assertTrue(output_path.name.startswith("destination_"))
        self.assertEqual(output_path.suffix, ".xlsx")

        output = load_workbook(output_path)
        try:
            sheet = output["Sheet1"]
            self.assertEqual(sheet["A2"].value, "existing")
            self.assertEqual(sheet["A3"].value, "alpha")
            self.assertIsInstance(sheet["B3"].value, datetime)
            self.assertEqual(sheet["B3"].number_format, "mm-dd-yy")
            self.assertEqual(sheet["A4"].value, "gamma")
            self.assertEqual(sheet["B4"].value, 35.5)
            self.assertEqual(sheet["B4"].number_format, "0.00")
            self.assertIsNone(sheet["C4"].value)
            self.assertIsNone(sheet["A5"].value)
        finally:
            output.close()

        original = load_workbook(self.destination_path)
        try:
            self.assertIsNone(original["Sheet1"]["A3"].value)
        finally:
            original.close()

    def test_each_run_writes_a_distinct_file(self):
        source = open_workbook(self.source_path)
        destination = open_workbook(self.destination_path)
        try:
            copy_ranges(source, destination, [SheetRange("Sheet1", 2, 4)])
            first = destination.save_copy()
            copy_ranges(source, destination, [SheetRange("Sheet1", 2, 4)])
            second = destination.save_copy()
        finally:
            source.close()
            destination.close()

        self.assertNotEqual(first, second)
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())

    def test_blank_range_copies_nothing(self):
        source = open_workbook(self.source_path)
        destination = open_workbook(self.destination_path)
        try:
            results = copy_ranges(source, destination, [SheetRange("Sheet1", 3, 3)])
            output_path = destination.save_copy()
        finally:
            source.close()
            destination.close()

        self.assertEqual(results[0].copied_rows, 0)
        self.assertEqual(results[0].skipped_rows, 1)
        output = load_workbook(output_path)
        try:
            self.assertIsNone(output["Sheet1"]["A3"].value)
        finally:
            output.close()


if __name__ == "__main__":
    unittest.main()
