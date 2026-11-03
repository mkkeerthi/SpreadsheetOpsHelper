from __future__ import annotations

import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from core.adapters import open_workbook
from core.copier import copy_ranges
from core.validator import SheetRange

HEADER = ["Name", "Amount"]


def _write_csv(path: Path, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def _read_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


class CsvCopyTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.folder = Path(self._temp.name)
        self.source_path = self.folder / "source.csv"
        self.destination_path = self.folder / "destination.csv"
        _write_csv(
            self.source_path,
            [HEADER, ["alpha", "1.50"], ["", ""], ["gamma", "35.50"]],
        )
        _write_csv(self.destination_path, [HEADER, ["existing", "9.99"]])

    def tearDown(self):
        self._temp.cleanup()

    def test_csv_append_and_original_untouched(self):
        original_hash = hashlib.sha256(self.destination_path.read_bytes()).hexdigest()

        source = open_workbook(self.source_path)
        destination = open_workbook(self.destination_path)
        try:
            self.assertEqual(source.sheet_names(), ["Sheet1"])
            self.assertEqual(destination.sheet_names(), ["Sheet1"])
            results = copy_ranges(
                source, destination, [SheetRange("Sheet1", 2, 4)]
            )
            output_path = destination.save_copy()
        finally:
            source.close()
            destination.close()

        self.assertEqual(results[0].copied_rows, 2)
        self.assertEqual(results[0].skipped_rows, 1)
        self.assertEqual(results[0].destination_start_row, 3)
        self.assertEqual(results[0].destination_end_row, 4)

        self.assertEqual(
            hashlib.sha256(self.destination_path.read_bytes()).hexdigest(),
            original_hash,
        )
        self.assertEqual(output_path.suffix, ".csv")
        self.assertEqual(
            _read_csv(output_path),
            [HEADER, ["existing", "9.99"], ["alpha", "1.50"], ["gamma", "35.50"]],
        )
        self.assertEqual(_read_csv(self.destination_path), [HEADER, ["existing", "9.99"]])


if __name__ == "__main__":
    unittest.main()
