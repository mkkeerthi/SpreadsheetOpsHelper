from __future__ import annotations

import unittest

from core.validator import (
    ValidationError,
    compare_workbooks,
    parse_row_range,
)


class FakeWorkbook:
    def __init__(self, sheets):
        self._sheets = sheets

    def sheet_names(self):
        return list(self._sheets)

    def max_column(self, name):
        return self._sheets[name]


class ParseRowRangeTests(unittest.TestCase):
    def test_both_blank_skips_sheet(self):
        self.assertIsNone(parse_row_range("Sheet1", "", "   ", 14))

    def test_one_blank_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_row_range("Sheet1", "7", "", 14)
        with self.assertRaises(ValidationError):
            parse_row_range("Sheet1", "", "14", 14)

    def test_non_numeric_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_row_range("Sheet1", "seven", "14", 14)

    def test_start_after_end_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_row_range("Sheet1", "14", "7", 14)

    def test_end_beyond_source_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_row_range("Sheet1", "7", "15", 14)

    def test_start_beyond_source_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_row_range("Sheet1", "15", "15", 14)

    def test_sheet_without_data_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_row_range("Sheet1", "1", "2", 0)

    def test_valid_range(self):
        parsed = parse_row_range("Sheet1", "7", "14", 14)
        self.assertEqual(parsed.sheet, "Sheet1")
        self.assertEqual(parsed.start_row, 7)
        self.assertEqual(parsed.end_row, 14)


class CompareWorkbooksTests(unittest.TestCase):
    def test_identical_sheets_pass(self):
        source = FakeWorkbook({"Subscriptions": 27, "Refunds": 27})
        destination = FakeWorkbook({"Subscriptions": 27, "Refunds": 27})
        report = compare_workbooks(source, destination)
        self.assertTrue(report.ok)
        self.assertEqual(report.warnings, [])

    def test_sheet_count_mismatch_fails(self):
        source = FakeWorkbook({"Subscriptions": 27, "Refunds": 27})
        destination = FakeWorkbook({"Subscriptions": 27})
        report = compare_workbooks(source, destination)
        self.assertFalse(report.ok)

    def test_missing_sheet_is_named(self):
        source = FakeWorkbook({"Subscriptions": 27})
        destination = FakeWorkbook({"Refunds": 27})
        report = compare_workbooks(source, destination)
        self.assertFalse(report.ok)
        joined = " ".join(report.errors)
        self.assertIn("Subscriptions", joined)
        self.assertIn("Refunds", joined)

    def test_column_count_mismatch_fails(self):
        source = FakeWorkbook({"Subscriptions": 27})
        destination = FakeWorkbook({"Subscriptions": 26})
        report = compare_workbooks(source, destination)
        self.assertFalse(report.ok)
        self.assertIn("27", report.errors[0])
        self.assertIn("26", report.errors[0])

    def test_sheet_order_difference_warns(self):
        source = FakeWorkbook({"Subscriptions": 27, "Refunds": 27})
        destination = FakeWorkbook({"Refunds": 27, "Subscriptions": 27})
        report = compare_workbooks(source, destination)
        self.assertTrue(report.ok)
        self.assertTrue(report.warnings)


if __name__ == "__main__":
    unittest.main()
