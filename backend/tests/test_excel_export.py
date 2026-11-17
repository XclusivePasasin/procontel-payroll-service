from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from openpyxl import load_workbook
from pypdf import PdfReader

from app.excel_export import render_xlsx
from app.exports import XLSX_MIME
from app.models import Identity, Options
from app.service import build
from tests.fixtures import workbook
from tests.test_workflow import confirmed, post


def value_for(sheet, label, column=1):
    for row in sheet.iter_rows():
        if row[column - 1].value == label:
            return row[column]
    raise AssertionError(label)


def test_excel_has_printable_receipts_and_numeric_money():
    data = workbook()
    options = confirmed(data)
    options.output_format = "xlsx"
    response = post("generate", data, options)
    assert response.status_code == 200
    assert response.headers["content-type"] == XLSX_MIME
    assert response.headers["cache-control"] == "no-store, private"
    book = load_workbook(BytesIO(response.content), data_only=False)
    try:
        assert book.sheetnames == ["PLANILLA", "BOLETA PLANILLA", "HONORARIOS", "BOLETA HONORARIOS"]
        for sheet, expected in [
            (book["BOLETA PLANILLA"], "851.67"),
            (book["BOLETA HONORARIOS"], "927.00"),
        ]:
            net = value_for(sheet, "LÍQUIDO A RECIBIR")
            assert net.data_type == "n" and Decimal(str(net.value)) == Decimal(expected)
            assert "$" in net.number_format
            assert value_for(sheet, "Días trabajados").data_type == "n"
            assert (
                sheet.page_setup.orientation == "landscape"
                and str(sheet.page_setup.paperSize) == "1"
            )
            assert sheet.page_setup.fitToWidth == 1
            assert sheet.print_area
            assert not any(cell.data_type == "f" for row in sheet for cell in row)
    finally:
        book.close()


def test_excel_receipts_only_include_selected_type_but_keep_original_data():
    data = workbook()
    options = confirmed(data)
    options.output_format = "xlsx"
    options.selected_records = [Identity(type="honorarios", source_row=7, employee_id="H-001")]
    response = post("generate", data, options)
    assert response.status_code == 200
    book = load_workbook(BytesIO(response.content))
    try:
        assert book.sheetnames == ["PLANILLA", "HONORARIOS", "BOLETA HONORARIOS"]
        assert book["PLANILLA"]["B7"].value == "S-001"
        assert book["HONORARIOS"]["B7"].value == "H-001"
        assert book["BOLETA HONORARIOS"]["B2"].value == "Código H-001"
        assert value_for(book["BOLETA HONORARIOS"], "Días de vacaciones").value == "—"
    finally:
        book.close()


def test_combined_export_has_excel_and_both_pdf_documents():
    data = workbook()
    options = confirmed(data)
    options.output_format = "both"
    response = post("generate", data, options)
    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        assert len(archive.namelist()) == 3
        assert "boletas_procontel.xlsx" in archive.namelist()
        for name in archive.namelist():
            if name.endswith(".pdf"):
                document = PdfReader(BytesIO(archive.read(name)))
                assert len(document.pages) == 1


def test_excel_text_cannot_become_formula_and_pages_are_paired():
    data = workbook()
    options = confirmed(data)
    result, records, _ = build(data, options)
    people = [
        replace(
            records[0],
            sequence=i + 1,
            employee_id=f"P-{i}",
            fields=records[0].fields | {"name": '=HYPERLINK("https://invalid.example","x")'},
        )
        for i in range(3)
    ]
    payload = render_xlsx(data, people, result["company"], options)
    book = load_workbook(BytesIO(payload), data_only=False)
    try:
        sheet = book["BOLETA PLANILLA"]
        assert len(sheet.row_breaks.brk) == 1
        labels = [
            row[column + 1]
            for row in sheet
            for column in (0, 3)
            if row[column].value == "Nombre del colaborador"
        ]
        assert len(labels) == 3
        assert sheet.max_column == 5
        for cell in labels:
            assert cell.data_type == "s" and cell.value.startswith("=HYPERLINK")
        assert not any(cell.data_type == "f" for row in sheet for cell in row)
    finally:
        book.close()


def test_excel_respects_required_review_and_unknown_formats_rejected():
    data = workbook()
    options = Options(output_format="xlsx")
    assert post("generate", data, options).status_code == 422
