from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .workbook import is_blank

ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class SheetCopyResult:
    sheet: str
    copied_rows: int
    skipped_rows: int
    destination_start_row: int
    destination_end_row: int


def copy_ranges(
    source,
    destination,
    ranges,
    on_progress: ProgressCallback | None = None,
    logger=None,
) -> list[SheetCopyResult]:
    total_rows = sum(item.end_row - item.start_row + 1 for item in ranges)
    done = 0
    results: list[SheetCopyResult] = []

    for item in ranges:
        sheet = item.sheet
        columns = source.max_column(sheet)
        destination_row = destination.last_data_row(sheet) + 1
        start_destination_row = destination_row
        copied = 0
        skipped = 0

        for source_row in range(item.start_row, item.end_row + 1):
            wrote_row = False
            for column in range(1, columns + 1):
                value = source.get_value(sheet, source_row, column)
                if is_blank(value):
                    continue
                number_format = source.get_number_format(sheet, source_row, column)
                destination.set_value(
                    sheet, destination_row, column, value, number_format
                )
                wrote_row = True

            if wrote_row:
                copied += 1
                destination_row += 1
            else:
                skipped += 1

            done += 1
            if on_progress is not None:
                on_progress(done, total_rows)

        result = SheetCopyResult(
            sheet=sheet,
            copied_rows=copied,
            skipped_rows=skipped,
            destination_start_row=start_destination_row,
            destination_end_row=destination_row - 1,
        )
        results.append(result)
        if logger is not None:
            logger.info(
                "Sheet '%s': copied %d rows into destination rows %d-%d, "
                "skipped %d blank rows.",
                sheet,
                copied,
                result.destination_start_row,
                result.destination_end_row,
                skipped,
            )

    return results
