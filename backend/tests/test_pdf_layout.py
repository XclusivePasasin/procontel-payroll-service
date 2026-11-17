from dataclasses import replace
from io import BytesIO

import pytest
import pymupdf
from pypdf import PdfReader

from app.pdf import CELL_HEIGHT, CELL_WIDTH, COLUMNS, GUTTER, MARGIN, PAGE_SIZE, render_pdf
from app.service import build
from tests.fixtures import workbook
from tests.test_workflow import confirmed


def sample_records(count: int):
    data = workbook()
    options = confirmed(data)
    result, records, _ = build(data, options)
    people = [
        replace(
            records[0],
            sequence=i + 1,
            employee_id=f"TEST-{i + 1:03}",
            fields=records[0].fields | {"name": f"Persona de prueba {i + 1:03}"},
        )
        for i in range(count)
    ]
    return people, result["company"], options


@pytest.mark.parametrize("count,pages", [(1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (11, 6)])
def test_two_receipts_per_letter_landscape_page(count, pages):
    people, company, options = sample_records(count)
    document = PdfReader(BytesIO(render_pdf(people, company, options)))
    assert len(document.pages) == pages
    for index, page in enumerate(document.pages):
        assert float(page.mediabox.width) == 792 and float(page.mediabox.height) == 612
        text = page.extract_text()
        assert text.count("BOLETA DE PAGO") == min(2, count - index * 2)
        assert text.count("LÍQUIDO A RECIBIR") == min(2, count - index * 2)
    text = "\n".join(page.extract_text() for page in document.pages)
    for person in people:
        assert text.count(str(person.fields["name"])) == 1


def test_receipt_text_stays_inside_cutting_cells():
    people, company, options = sample_records(2)
    document = pymupdf.open(stream=render_pdf(people, company, options), filetype="pdf")
    try:
        for block in document[0].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if span["text"].startswith("Carta horizontal"):
                        continue
                    x0, y0, x1, y1 = span["bbox"]
                    column = min(int((x0 - MARGIN) / (CELL_WIDTH + GUTTER)), COLUMNS - 1)
                    row = min(int((y0 - MARGIN) / (CELL_HEIGHT + GUTTER)), 1)
                    left = MARGIN + column * (CELL_WIDTH + GUTTER)
                    top = MARGIN + row * (CELL_HEIGHT + GUTTER)
                    assert x0 >= left - 0.5 and x1 <= left + CELL_WIDTH + 0.5
                    assert y0 >= top - 0.5 and y1 <= top + CELL_HEIGHT + 0.5
        assert tuple(document[0].rect[2:]) == PAGE_SIZE
    finally:
        document.close()


def test_long_fields_wrap_without_disappearing():
    people, company, options = sample_records(1)
    people[0].fields["name"] = "Nombre de persona " * 12
    people[0].fields["role"] = "Coordinación de operaciones " * 10
    text = PdfReader(BytesIO(render_pdf(people, company, options))).pages[0].extract_text()
    normalized = " ".join(text.split())
    assert " ".join(str(people[0].fields["name"]).split()) in normalized
    assert " ".join(str(people[0].fields["role"]).split()) in normalized
    assert "Firma del colaborador" in normalized
    assert "$851.67" in text
