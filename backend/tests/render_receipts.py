"""Visual QA with synthetic data; outputs only to ignored tmp/visual."""

from pathlib import Path
from dataclasses import replace

import pymupdf

from app.pdf import render_pdf
from app.excel_export import render_xlsx
from app.service import build
from tests.fixtures import workbook
from tests.test_workflow import confirmed


def main() -> None:
    output = Path(__file__).resolve().parents[2] / "tmp" / "visual"
    output.mkdir(parents=True, exist_ok=True)
    data = workbook()
    options = confirmed(data)
    result, records, _ = build(data, options)
    excel_records = []
    for record in records:
        people = [
            replace(
                record,
                sequence=i + 1,
                employee_id=f"TEST-{i + 1:03}",
                fields=record.fields | {"name": f"Persona sintética {i + 1:03}"},
            )
            for i in range(3)
        ]
        excel_records.extend(people)
        payload = render_pdf(people, result["company"], options)
        (output / f"{record.type}.pdf").write_bytes(payload)
        with pymupdf.open(stream=payload, filetype="pdf") as document:
            for index, page in enumerate(document):
                page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(
                    output / f"{record.type}-{index + 1}.png"
                )
    (output / "boletas-test.xlsx").write_bytes(
        render_xlsx(data, excel_records, result["company"], options)
    )


if __name__ == "__main__":
    main()
