from __future__ import annotations

from dataclasses import dataclass, field


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SheetRange:
    sheet: str
    start_row: int
    end_row: int


@dataclass(frozen=True)
class ComparisonReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_row_range(
    sheet: str, start_text: str | None, end_text: str | None, last_source_row: int
) -> SheetRange | None:
    start_text = (start_text or "").strip()
    end_text = (end_text or "").strip()

    if not start_text and not end_text:
        return None
    if not start_text or not end_text:
        raise ValidationError(
            f"{sheet}: enter both a starting and an ending row, "
            "or leave both blank to skip this sheet."
        )

    try:
        start_row = int(start_text)
        end_row = int(end_text)
    except ValueError as exc:
        raise ValidationError(f"{sheet}: row numbers must be whole numbers.") from exc

    if start_row < 1 or end_row < 1:
        raise ValidationError(f"{sheet}: row numbers must be 1 or greater.")
    if start_row > end_row:
        raise ValidationError(
            f"{sheet}: starting row {start_row} is greater than ending row {end_row}."
        )
    if last_source_row < 1:
        raise ValidationError(f"{sheet}: this sheet has no data rows in the source file.")
    if start_row > last_source_row:
        raise ValidationError(
            f"{sheet}: starting row {start_row} is beyond the last source row "
            f"{last_source_row}."
        )
    if end_row > last_source_row:
        raise ValidationError(
            f"{sheet}: ending row {end_row} is beyond the last source row "
            f"{last_source_row}."
        )
    return SheetRange(sheet=sheet, start_row=start_row, end_row=end_row)


def compare_workbooks(source, destination) -> ComparisonReport:
    errors: list[str] = []
    warnings: list[str] = []

    source_sheets = source.sheet_names()
    destination_sheets = destination.sheet_names()

    if not source_sheets:
        errors.append("The source file has no sheets.")
    if len(source_sheets) != len(destination_sheets):
        errors.append(
            f"Sheet count differs: source has {len(source_sheets)}, "
            f"destination has {len(destination_sheets)}."
        )

    missing = [name for name in source_sheets if name not in destination_sheets]
    extra = [name for name in destination_sheets if name not in source_sheets]
    if missing:
        errors.append(
            "Sheets missing from destination: " + ", ".join(f"'{n}'" for n in missing)
        )
    if extra:
        errors.append(
            "Sheets only in destination: " + ", ".join(f"'{n}'" for n in extra)
        )

    for name in source_sheets:
        if name not in destination_sheets:
            continue
        source_columns = source.max_column(name)
        destination_columns = destination.max_column(name)
        if source_columns != destination_columns:
            errors.append(
                f"Sheet '{name}': source has {source_columns} columns, "
                f"destination has {destination_columns}."
            )

    if not errors and source_sheets != destination_sheets:
        warnings.append(
            "Sheet order differs between files; copying still matches sheets by name."
        )

    return ComparisonReport(errors=errors, warnings=warnings)


def parse_ranges(entries, source) -> list[SheetRange]:
    ranges: list[SheetRange] = []
    for name, start_text, end_text in entries:
        parsed = parse_row_range(
            name, start_text, end_text, source.last_data_row(name)
        )
        if parsed is not None:
            ranges.append(parsed)
    return ranges
