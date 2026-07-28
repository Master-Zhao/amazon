import csv
from pathlib import Path

from openpyxl import load_workbook
from django.conf import settings

from integrations.storage.local import LocalFileStorage


class ReportFileError(ValueError):
    pass


def iter_rows(storage_path: str):
    storage = LocalFileStorage()
    suffix = Path(storage_path).suffix.lower()
    if suffix == ".csv":
        with storage.open_binary(storage_path) as raw:
            import io

            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text)
            if not reader.fieldnames:
                raise ReportFileError("EMPTY_OR_MISSING_HEADER")
            for index, row in enumerate(reader, start=2):
                yield index, {
                    settings.REPORT_FIELD_ALIASES.get(str(key).strip(), str(key).strip()): value
                    for key, value in row.items()
                }
        return
    if suffix == ".xlsx":
        with storage.open_binary(storage_path) as raw:
            workbook = load_workbook(raw, read_only=True, data_only=True)
            sheet = workbook.active
            rows = sheet.iter_rows(values_only=True)
            try:
                headers = [str(value).strip() if value is not None else "" for value in next(rows)]
            except StopIteration as exc:
                raise ReportFileError("EMPTY_OR_MISSING_HEADER") from exc
            for index, values in enumerate(rows, start=2):
                yield index, {
                    settings.REPORT_FIELD_ALIASES.get(header, header): (
                        "" if value is None else str(value)
                    )
                    for header, value in zip(headers, values, strict=False)
                }
        return
    raise ReportFileError("UNSUPPORTED_FILE_TYPE")
