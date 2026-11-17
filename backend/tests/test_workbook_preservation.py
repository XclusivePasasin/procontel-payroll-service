from hashlib import sha256
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill

from app.excel_export import render_xlsx
from app.models import Identity
from app.service import build
from app.workbook_package import MAIN, REL, PACKAGE_REL, CONTENT, read_xml
from tests.fixtures import workbook
from tests.test_workflow import confirmed


def source_workbook():
    def enhance(book):
        sheet = book["PLANILLA"]
        sheet["C7"].font = Font(name="Arial", bold=True, color="AB1234")
        sheet["C7"].fill = PatternFill("solid", fgColor="ABCDEF")
        sheet["H7"].number_format = '"USD" #,##0.000'
        sheet.freeze_panes = "H7"
        sheet.column_dimensions["C"].width = 47
        for name in ["BOLETA PLANILLA", "BOLETA HONORARIOS"]:
            receipt = book.create_sheet(name)
            receipt["A1"] = "PLANTILLA ANTERIOR"
            receipt["B2"] = "=PLANILLA!C7"
        extra = book.create_sheet("INFORMACION ADICIONAL")
        extra["A1"] = "Dato de empleado que debe conservarse"
        extra["B2"] = "=PLANILLA!H7"
        extra.sheet_state = "hidden"
        book.active = 0

    data = workbook(enhance)
    with BytesIO() as buffer:
        with ZipFile(BytesIO(data)) as source, ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            archive.comment = b"Original package comment"
            for entry in source.infolist():
                payload = source.read(entry.filename)
                if entry.filename == "xl/worksheets/sheet1.xml":
                    payload = payload.replace(
                        b'<c r="J7" t="n"><v>450</v></c>',
                        b'<c r="J7"><f>H7/30*I7</f><v>450</v></c>',
                    )
                archive.writestr(entry, payload)
        return buffer.getvalue()


def test_original_data_formula_caches_formats_and_extra_sheets_remain():
    data = source_workbook()
    digest = sha256(data).hexdigest()
    options = confirmed(data)
    result, records, _ = build(data, options)
    output = render_xlsx(data, records, result["company"], options)
    with ZipFile(BytesIO(data)) as source, ZipFile(BytesIO(output)) as exported:
        # Only the receipt XML, appended style definitions and print-area metadata change.
        changed = {
            "xl/styles.xml",
            "xl/workbook.xml",
            "xl/worksheets/sheet3.xml",
            "xl/worksheets/sheet4.xml",
        }
        assert set(source.namelist()) == set(exported.namelist())
        assert source.comment == exported.comment
        for path in source.namelist():
            if path not in changed:
                assert source.read(path) == exported.read(path), path
        before, _ = read_xml(source.read("xl/styles.xml"))
        after, _ = read_xml(exported.read("xl/styles.xml"))
        for section in ["fonts", "fills", "borders", "cellStyleXfs", "cellXfs"]:
            old = before.find(f"{{{MAIN}}}{section}")
            new = after.find(f"{{{MAIN}}}{section}")
            for index, old_item in enumerate(old):
                assert ET.tostring(old_item) == ET.tostring(new[index])
    values = load_workbook(BytesIO(output), data_only=True)
    formulas = load_workbook(BytesIO(output), data_only=False)
    try:
        assert values["PLANILLA"]["J7"].value == 450
        assert formulas["PLANILLA"]["J7"].value == "=H7/30*I7"
        assert formulas["INFORMACION ADICIONAL"].sheet_state == "hidden"
        assert formulas["INFORMACION ADICIONAL"]["B2"].value == "=PLANILLA!H7"
        assert formulas["PLANILLA"]["C7"].font.color.rgb == "00AB1234"
        assert formulas["PLANILLA"]["C7"].fill.fgColor.rgb == "00ABCDEF"
        assert formulas["PLANILLA"]["H7"].number_format == '"USD" #,##0.000'
        assert formulas["PLANILLA"].freeze_panes == "H7"
        assert formulas["BOLETA PLANILLA"]["B1"].value == "BOLETA DE PAGO"
        assert formulas["BOLETA HONORARIOS"]["B1"].value == "BOLETA DE PAGO"
    finally:
        values.close()
        formulas.close()
    assert sha256(data).hexdigest() == digest


def test_unselected_receipt_sheet_and_all_employee_data_are_preserved():
    data = source_workbook()
    options = confirmed(data)
    options.selected_records = [Identity(type="planilla", source_row=7, employee_id="S-001")]
    result, records, _ = build(data, options)
    output = render_xlsx(data, records, result["company"], options)
    with ZipFile(BytesIO(data)) as source, ZipFile(BytesIO(output)) as exported:
        for path in [
            "xl/worksheets/sheet1.xml",
            "xl/worksheets/sheet2.xml",
            "xl/worksheets/sheet4.xml",
            "xl/worksheets/sheet5.xml",
        ]:
            assert source.read(path) == exported.read(path)


def with_calculation_chain(data):
    with BytesIO() as buffer:
        with ZipFile(BytesIO(data)) as source, ZipFile(buffer, "w", ZIP_DEFLATED) as output:
            for entry in source.infolist():
                payload = source.read(entry.filename)
                if entry.filename == "xl/_rels/workbook.xml.rels":
                    root = ET.fromstring(payload)
                    ET.SubElement(
                        root,
                        f"{{{PACKAGE_REL}}}Relationship",
                        {"Id": "rIdChain", "Type": f"{REL}/calcChain", "Target": "calcChain.xml"},
                    )
                    payload = ET.tostring(root)
                if entry.filename == "[Content_Types].xml":
                    root = ET.fromstring(payload)
                    ET.SubElement(
                        root,
                        f"{{{CONTENT}}}Override",
                        {
                            "PartName": "/xl/calcChain.xml",
                            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml",
                        },
                    )
                    payload = ET.tostring(root)
                output.writestr(entry, payload)
            output.writestr(
                "xl/calcChain.xml",
                f'<calcChain xmlns="{MAIN}"><c r="J7" i="1"/><c r="B2" i="3"/><c r="B2" i="4"/><c r="B2" i="5"/></calcChain>',
            )
        return buffer.getvalue()


def test_calculation_chain_only_removes_replaced_receipt_formulas():
    data = with_calculation_chain(source_workbook())
    options = confirmed(data)
    result, records, _ = build(data, options)
    output = render_xlsx(data, records, result["company"], options)
    with ZipFile(BytesIO(output)) as archive:
        chain = ET.fromstring(archive.read("xl/calcChain.xml"))
        assert [(node.attrib["i"], node.attrib["r"]) for node in chain] == [
            ("1", "J7"),
            ("5", "B2"),
        ]
