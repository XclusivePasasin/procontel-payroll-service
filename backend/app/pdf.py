"""Two side-by-side receipts on landscape US Letter."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from app.models import Options, Record, ServiceError
from app.receipt_content import ReceiptLine, receipt_lines

FONT_PATH = Path(__file__).parent / "assets" / "fonts"
PAGE_SIZE = landscape(letter)
COLUMNS = 2
ROWS = 1
PER_PAGE = COLUMNS * ROWS
MARGIN = 18.0
GUTTER = 12.0
CELL_WIDTH = (PAGE_SIZE[0] - 2 * MARGIN - (COLUMNS - 1) * GUTTER) / COLUMNS
CELL_HEIGHT = (PAGE_SIZE[1] - 2 * MARGIN - (ROWS - 1) * GUTTER) / ROWS
BLUE = colors.HexColor("#1f4e78")
GREEN = colors.HexColor("#92d050")
MIN_SIGNATURE_HEIGHT = 60.0


def register_fonts() -> None:
    if "Procontel" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Procontel", str(FONT_PATH / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("ProcontelBold", str(FONT_PATH / "DejaVuSans-Bold.ttf")))


def receipt_table(
    record: Record,
    lines: list[ReceiptLine],
    font_size: float,
    signature_height: float = MIN_SIGNATURE_HEIGHT,
) -> Table:
    normal = ParagraphStyle(
        "receipt",
        fontName="Procontel",
        fontSize=font_size,
        leading=font_size * 1.17,
        textColor=colors.black,
    )
    bold = ParagraphStyle("receipt-bold", parent=normal, fontName="ProcontelBold")
    right = ParagraphStyle("receipt-money", parent=normal, alignment=TA_RIGHT)
    header = ParagraphStyle(
        "receipt-header",
        parent=bold,
        alignment=TA_CENTER,
        textColor=colors.white,
        fontSize=font_size + 0.6,
        leading=font_size + 1.4,
    )
    foot = ParagraphStyle(
        "receipt-foot",
        parent=normal,
        fontSize=font_size * 0.8,
        leading=font_size,
        alignment=TA_LEFT,
    )

    def paragraph(value: object, style: ParagraphStyle = normal) -> Paragraph:
        return Paragraph(escape(str(value)), style)

    data: list[list[Paragraph | str]] = [
        [paragraph(record.sequence, header), paragraph("BOLETA DE PAGO", header)],
        [
            paragraph(record.type.upper(), bold),
            paragraph(f"Código {record.employee_id}" if record.employee_id else ""),
        ],
    ]
    commands: list[tuple] = [
        ("GRID", (0, 0), (-1, -1), 0.22, colors.HexColor("#505050")),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.7),
        ("TOPPADDING", (0, 0), (-1, -1), 0.3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.3),
    ]
    for line in lines:
        index = len(data)
        if line.kind == "section":
            data.append([paragraph(line.label, header), ""])
            commands += [
                ("SPAN", (0, index), (-1, index)),
                ("BACKGROUND", (0, index), (-1, index), BLUE),
            ]
        else:
            strong = line.kind in {"metadata", "subtotal", "net"}
            label_style = bold if strong else normal
            value_style = (
                normal if line.kind == "metadata" and not line.value.startswith("$") else right
            )
            data.append([paragraph(line.label, label_style), paragraph(line.value, value_style)])
            if line.kind == "subtotal":
                commands.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor("#eeeeee")))
            elif line.kind == "net":
                commands += [
                    ("BACKGROUND", (0, index), (-1, index), GREEN),
                    ("TOPPADDING", (0, index), (-1, index), 2),
                    ("BOTTOMPADDING", (0, index), (-1, index), 2),
                ]
    signature_space = len(data)
    data.append(["", ""])
    commands += [
        ("SPAN", (0, signature_space), (-1, signature_space)),
    ]
    data.append(
        [
            paragraph(
                "Firma del colaborador" if record.type == "planilla" else "Firma del prestador",
                foot,
            ),
            paragraph("Firma y sello de la empresa", foot),
        ]
    )
    heights: list[float | None] = [None] * len(data)
    heights[signature_space] = signature_height
    table = Table(data, colWidths=[CELL_WIDTH * 0.44, CELL_WIDTH * 0.56], rowHeights=heights)
    table.setStyle(TableStyle(commands))
    return table


def draw_receipt(
    canvas: Canvas, record: Record, company: str, options: Options, x: float, y: float
) -> None:
    lines = receipt_lines(record, company, options)
    # Retain all content and wrap long fields; never clip or silently truncate.
    for font_size in (10.5, 10.0, 9.5, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0):
        table = receipt_table(record, lines, font_size)
        _, height = table.wrap(CELL_WIDTH, CELL_HEIGHT)
        if height <= CELL_HEIGHT:
            table.drawOn(canvas, x, y + (CELL_HEIGHT - height) / 2)
            return
    raise ServiceError(
        422,
        "RECEIPT_LAYOUT_OVERFLOW",
        "Un registro contiene textos demasiado extensos para el formato de dos boletas por hoja. Revisa el nombre, cargo o área en Excel.",
    )


def cutting_guides(canvas: Canvas) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#bbbbbb"))
    canvas.setLineWidth(0.25)
    canvas.setDash(1, 2)
    for column in range(1, COLUMNS):
        x = MARGIN + column * CELL_WIDTH + (column - 0.5) * GUTTER
        canvas.line(x, MARGIN / 2, x, PAGE_SIZE[1] - MARGIN / 2)
    for row in range(1, ROWS):
        y = PAGE_SIZE[1] - MARGIN - row * CELL_HEIGHT - (row - 0.5) * GUTTER
        canvas.line(MARGIN / 2, y, PAGE_SIZE[0] - MARGIN / 2, y)
    canvas.restoreState()


def render_pdf(records: list[Record], company: str, options: Options) -> bytes:
    if not records:
        raise ServiceError(422, "EMPTY_SELECTION", "Selecciona al menos una boleta.")
    register_fonts()
    with BytesIO() as buffer:
        canvas = Canvas(buffer, pagesize=PAGE_SIZE, pageCompression=1)
        canvas.setTitle("Boletas de pago")
        canvas.setAuthor("Procontel")
        for start in range(0, len(records), PER_PAGE):
            cutting_guides(canvas)
            for index, record in enumerate(records[start : start + PER_PAGE]):
                row, column = divmod(index, COLUMNS)
                x = MARGIN + column * (CELL_WIDTH + GUTTER)
                y = PAGE_SIZE[1] - MARGIN - (row + 1) * CELL_HEIGHT - row * GUTTER
                draw_receipt(canvas, record, company, options, x, y)
            canvas.setFont("Procontel", 4)
            canvas.setFillColor(colors.HexColor("#666666"))
            canvas.drawRightString(
                PAGE_SIZE[0] - MARGIN,
                3,
                f"Carta horizontal · 2 boletas por hoja · Página {start // PER_PAGE + 1}",
            )
            canvas.showPage()
        canvas.save()
        return buffer.getvalue()
