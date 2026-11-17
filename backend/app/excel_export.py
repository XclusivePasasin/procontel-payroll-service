"""Build receipt sheets and insert them into a copy of the complete original workbook."""

from decimal import Decimal
from io import BytesIO
from math import ceil

from openpyxl import Workbook
from openpyxl.cell.cell import Cell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.pagebreak import Break
from openpyxl.worksheet.worksheet import Worksheet

from app.models import Options, Record, ServiceError
from app.receipt_content import ReceiptLine, receipt_lines
from app.workbook_package import patch_receipt_sheets
from app.sheet_profiles import receipt_sheet_name

MONEY_FORMAT = '"$"#,##0.00;-"$"#,##0.00'
BLUE = "1F4E78"
GREEN = "92D050"
THIN = Side(style="thin", color="777777")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def write_cell(
    sheet: Worksheet,
    row: int,
    column: int,
    value: str | Decimal | int,
    *,
    bold: bool = False,
    fill: str | None = None,
    monetary: bool = False,
) -> Cell:
    cell = sheet.cell(row, column, value)
    # Force workbook text cells to strings even when untrusted names start with '='.
    if isinstance(value, str):
        cell.data_type = "s"
    cell.font = Font(
        name="Calibri", size=10, bold=bold, color="FFFFFF" if fill == BLUE else "000000"
    )
    cell.alignment = Alignment(
        vertical="center", wrap_text=True, horizontal="right" if monetary else "left"
    )
    cell.border = BORDER
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    if monetary:
        cell.number_format = MONEY_FORMAT
    return cell


def write_receipt(
    sheet: Worksheet,
    top: int,
    column: int,
    record: Record,
    lines: list[ReceiptLine],
    block_rows: int,
) -> None:
    write_cell(sheet, top, column, record.sequence, bold=True, fill=BLUE)
    write_cell(sheet, top, column + 1, "BOLETA DE PAGO", bold=True, fill=BLUE)
    write_cell(sheet, top + 1, column, record.type.upper(), bold=True)
    write_cell(
        sheet, top + 1, column + 1, f"Código {record.employee_id}" if record.employee_id else ""
    )
    row = top + 2
    for line in lines:
        fill = (
            BLUE
            if line.kind == "section"
            else GREEN
            if line.kind == "net"
            else "EEEEEE"
            if line.kind == "subtotal"
            else None
        )
        write_cell(
            sheet,
            row,
            column,
            line.label,
            bold=line.kind in {"metadata", "section", "subtotal", "net"},
            fill=fill,
        )
        number = line.number
        if line.label == "Salario contratado":
            number = Decimal(line.value.replace("$", "").replace(",", ""))
        monetary = number is not None
        if (
            line.kind == "metadata"
            and line.label
            in {
                "Días trabajados",
                "Horas extras diurnas",
                "Horas extras nocturnas",
                "Horas de nocturnidad",
                "Días de asueto",
                "Días de vacaciones",
                "Días de incapacidad",
                "Días de permiso",
            }
            and line.value != "—"
        ):
            number = Decimal(line.value)
        value: str | Decimal = number if number is not None else line.value
        cell = write_cell(sheet, row, column + 1, value, fill=fill, monetary=monetary)
        if number is not None and not monetary:
            cell.number_format = "General"
        if line.kind == "section":
            sheet.merge_cells(
                start_row=row, start_column=column, end_row=row, end_column=column + 1
            )
        row += 1
    signature_end = top + block_rows - 2
    for blank in range(row, signature_end):
        write_cell(sheet, blank, column, "")
        write_cell(sheet, blank, column + 1, "")
    if row < signature_end:
        sheet.merge_cells(
            start_row=row, start_column=column, end_row=signature_end - 1, end_column=column + 1
        )
    write_cell(
        sheet,
        signature_end,
        column,
        "Firma del colaborador" if record.type == "planilla" else "Firma del prestador",
    )
    write_cell(sheet, signature_end, column + 1, "Firma y sello de la empresa")


def receipt_workbook(records: list[Record], company: str, options: Options) -> bytes:
    if not records:
        raise ServiceError(422, "EMPTY_SELECTION", "Selecciona al menos una boleta.")
    book = Workbook()
    book.remove(book.worksheets[0])
    try:
        sources = list(dict.fromkeys(r.source_sheet or r.type.upper() for r in records))
        for source in sources:
            group = [r for r in records if (r.source_sheet or r.type.upper()) == source]
            if not group:
                continue
            sheet = book.create_sheet(receipt_sheet_name(source))
            sheet.sheet_view.showGridLines = False
            sheet.column_dimensions["A"].width = 26
            sheet.column_dimensions["B"].width = 40
            sheet.column_dimensions["C"].width = 4
            sheet.column_dimensions["D"].width = 26
            sheet.column_dimensions["E"].width = 40
            contents = [receipt_lines(record, company, options) for record in group]
            block_rows = max(len(lines) for lines in contents) + 8
            page_count = ceil(len(group) / 2)
            for row in range(1, page_count * block_rows + 1):
                sheet.row_dimensions[row].height = 16
            for index, (record, lines) in enumerate(zip(group, contents, strict=True)):
                top = (index // 2) * block_rows + 1
                column = 1 if index % 2 == 0 else 4
                write_receipt(sheet, top, column, record, lines, block_rows)
                for offset, line in enumerate(lines, 2):
                    if line.kind == "metadata":
                        width = 40
                        text_lines = max(1, ceil(len(line.value) / width))
                        sheet.row_dimensions[top + offset].height = max(
                            sheet.row_dimensions[top + offset].height or 12, text_lines * 12
                        )
            sheet.sheet_properties.pageSetUpPr.fitToPage = True
            sheet.page_setup.orientation = "landscape"
            sheet.page_setup.paperSize = sheet.PAPERSIZE_LETTER
            sheet.page_setup.fitToWidth = 1
            sheet.page_setup.fitToHeight = page_count
            sheet.page_margins.left = sheet.page_margins.right = 0.25
            sheet.page_margins.top = sheet.page_margins.bottom = 0.25
            sheet.page_margins.header = sheet.page_margins.footer = 0
            sheet.print_area = f"A1:E{page_count * block_rows - 1}"
            sheet.print_options.horizontalCentered = True
            sheet.print_options.verticalCentered = True
            for page in range(1, page_count):
                sheet.row_breaks.append(Break(id=page * block_rows))
        with BytesIO() as buffer:
            book.save(buffer)
            return buffer.getvalue()
    finally:
        book.close()


def render_xlsx(source_data: bytes, records: list[Record], company: str, options: Options) -> bytes:
    sources = {
        receipt_sheet_name(r.source_sheet or r.type.upper()): r.source_sheet or r.type.upper()
        for r in records
    }
    return patch_receipt_sheets(source_data, receipt_workbook(records, company, options), sources)
