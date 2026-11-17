from io import BytesIO
from zipfile import ZipFile

from openpyxl import Workbook, load_workbook
import pytest

from app.excel_export import render_xlsx
from app.exports import generate_exports
from app.service import build
from app.models import Identity, ServiceError
from app.selection import choose_records
from app.sheet_profiles import CANDIDATES, receipt_sheet_name
from tests.test_workflow import confirmed


def area_workbook():
    book = Workbook()
    book.remove(book.active)
    sources = []
    for area in ("FIBRA", "MASIVOS", "COMERCIAL"):
        for kind in ("planilla", "honorarios"):
            name = f"{kind.upper()} {area}"
            sources.append(name)
            sheet = book.create_sheet(name)
            sheet["A1"] = "EMPRESA DE PRUEBA"
            sheet["A4"] = "DEL 1 AL 15 DE NOVIEMBRE DEL 2026"
            candidate = (
                ("payroll_commission_v2" if area == "MASIVOS" else "payroll_bonus_v2")
                if kind == "planilla"
                else ("fees_reimbursements_v2" if area == "MASIVOS" else "fees_v2")
            )
            profile = dict(CANDIDATES[kind])[candidate]
            for field, (column, labels) in profile.items():
                sheet[f"{column}6"] = labels.split("|")[0]
                sheet[f"{column}7"] = 0
            values = {
                "sequence": 1,
                "employee_id": "MISMO-001",
                "name": "Persona de prueba",
                "dui": "00000000-0",
                "area": area,
                "role": "Pruebas",
                "contracted_amount": 900,
                "worked_days": 15,
                "base_payment": 450,
                "accrued_amount": 450,
                "net_payment": 450,
            }
            if kind == "planilla":
                values |= {"pension_provider": "AFP prueba", "taxable_amount": 450}
            else:
                values |= {"vat": 0, "other_deductions": 10, "net_payment": 440}
                if area == "MASIVOS":
                    values |= {"reimbursements": 5, "net_payment": 445}
            for field, value in values.items():
                sheet[f"{profile[field][0]}7"] = value
            sheet[f"{'F' if kind == 'planilla' else 'E'}9"] = "Total Planilla"
            sheet.print_area = "A1:D9"
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue(), sources


def test_six_sources_generate_adjacent_receipts_and_preserve_source_parts():
    data, sources = area_workbook()
    options = confirmed(data)
    result, records, _ = build(data, options)
    assert result["can_generate"], result["issues"]
    assert len(records) == 6
    assert len({r.source_sheet for r in records}) == 6
    output = render_xlsx(data, records, result["company"], options)
    book = load_workbook(BytesIO(output))
    assert book.sheetnames == [
        item for source in sources for item in (source, receipt_sheet_name(source))
    ]
    assert all(len(name) <= 31 for name in book.sheetnames)
    for source in sources:
        assert "$A$1:$D$9" in str(book[source].print_area)
    book.close()
    with ZipFile(BytesIO(data)) as before, ZipFile(BytesIO(output)) as after:
        for index in range(1, 7):
            part = f"xl/worksheets/sheet{index}.xml"
            assert before.read(part) == after.read(part)
    # Re-export replaces existing receipt sheets instead of duplicating them.
    again = render_xlsx(output, records, result["company"], options)
    book = load_workbook(BytesIO(again))
    assert len(book.sheetnames) == 12
    book.close()
    options.output_format = "both"
    archive, media, _ = generate_exports(data, records, result["company"], options)
    assert media == "application/zip"
    with ZipFile(BytesIO(archive)) as zipped:
        assert len(zipped.namelist()) == 7


def test_same_code_and_row_are_selected_by_source_sheet():
    data, _ = area_workbook()
    options = confirmed(data)
    _, records, _ = build(data, options)
    options.selected_records = [Identity(type="planilla", source_row=7, employee_id="MISMO-001")]
    with pytest.raises(ServiceError):
        choose_records(data, records, options)
    options.selected_records[0].source_sheet = "PLANILLA MASIVOS"
    chosen = choose_records(data, records, options)
    assert len(chosen) == 1 and chosen[0].source_sheet == "PLANILLA MASIVOS"
