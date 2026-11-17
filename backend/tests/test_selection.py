from io import BytesIO
from pydantic import ValidationError
from pypdf import PdfReader
import pytest

from app.models import Identity, Options, ServiceError
from app.service import build
from tests.fixtures import workbook
from tests.test_workflow import confirmed, post


def selected(data: bytes, code: str = "S-001") -> Options:
    options = confirmed(data)
    options.selected_records = [Identity(type="planilla", source_row=7, employee_id=code)]
    options.periods.pop("honorarios")
    return options


def test_default_selects_all_and_single_record_is_pdf():
    data = workbook()
    result, records, _ = build(data, confirmed(data))
    assert result["selected_count"] == 2 and len(records) == 2
    response = post("generate", data, selected(data))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    pdf = PdfReader(BytesIO(response.content))
    assert len(pdf.pages) == 1
    text = pdf.pages[0].extract_text()
    assert "PLANILLA" in text and "$851.67" in text and "HONORARIOS" not in text


def test_blank_employee_ids_remain_blank_and_select_independently():
    from openpyxl import load_workbook
    from app.excel_export import render_xlsx
    from app.pdf import render_pdf

    def without_codes(book):
        sheet = book["PLANILLA"]
        sheet["B7"] = None
        for column in range(1, 41):
            sheet.cell(13, column).value = sheet.cell(7, column).value
        sheet["A13"] = 2
        sheet["C13"] = "Segunda persona sin ID"
        book["HONORARIOS"]["B7"] = None

    data = workbook(without_codes)
    options = confirmed(data)
    result, records, _ = build(data, options)
    assert result["can_generate"], result["issues"]
    assert len(records) == 3 and all(r.employee_id == "" for r in records)
    options.selected_records = [
        Identity(type="planilla", source_sheet="PLANILLA", source_row=13, employee_id="")
    ]
    result, chosen, _ = build(data, options)
    assert result["can_generate"] and len(chosen) == 1
    assert chosen[0].source_row == 13
    output = render_xlsx(data, chosen, result["company"], options)
    book = load_workbook(BytesIO(output))
    assert book["BOLETA PLANILLA"]["B2"].value in (None, "")
    assert book["PLANILLA"]["B7"].value is None
    book.close()
    pdf = PdfReader(BytesIO(render_pdf(chosen, result["company"], options)))
    text = pdf.pages[0].extract_text()
    assert "Segunda persona sin ID" in text and "Código" not in text


def test_selection_retains_source_order_and_filters_people():
    def add_person(book):
        sheet = book["PLANILLA"]
        for col in range(1, 41):
            sheet.cell(13, col).value = sheet.cell(7, col).value
        sheet["A13"] = 2
        sheet["B13"] = "S-002"
        sheet["C13"] = "Segunda persona"
        sheet["F13"] = "Otra área"

    data = workbook(add_person)
    options = selected(data)
    options.selected_records = [Identity(type="planilla", source_row=13, employee_id="S-002")]
    result, records, _ = build(data, options)
    assert result["selected_count"] == 1 and len(result["records"]) == 3
    assert records[0].source_row == 13
    response = post("generate", data, options)
    assert response.status_code == 200
    text = PdfReader(BytesIO(response.content)).pages[0].extract_text()
    assert "Segunda persona" in text and "Persona Sintética" not in text


@pytest.mark.parametrize("variant", ["empty", "duplicate", "foreign", "hash"])
def test_invalid_selections_are_rejected(variant):
    data = workbook()
    options = selected(data)
    if variant == "empty":
        options.selected_records = []
    elif variant == "duplicate":
        options.selected_records *= 2
    elif variant == "foreign":
        options.selected_records[0].employee_id = "unknown"
    else:
        options.file_sha256 = "wrong"
    with pytest.raises(ServiceError):
        build(data, options)


def test_unselected_record_errors_do_not_block_chosen_person():
    data = workbook(lambda book: setattr(book["HONORARIOS"]["AA7"], "value", "=0"))
    result, _, _ = build(data, selected(data))
    assert result["can_generate"]
    assert any(i["code"] == "FORMULA_CACHE_MISSING" for i in result["source_issues"])
    assert not any(i["code"] == "FORMULA_CACHE_MISSING" for i in result["issues"])


def test_preview_cannot_include_unselected_person():
    data = workbook()
    options = selected(data)
    options.preview_record = Identity(type="honorarios", source_row=7, employee_id="H-001")
    assert post("preview", data, options).status_code == 422


@pytest.mark.parametrize("field,value", [("overrides", []), ("company_override", "Otra empresa")])
def test_data_editing_contract_is_removed(field, value):
    with pytest.raises(ValidationError):
        Options.model_validate({field: value})
