from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.excel_export import render_xlsx
from app.models import Options, Record
from app.pdf import render_pdf
from app.sheet_profiles import safe_pdf_suffix

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def generate_exports(
    source_data: bytes, records: list[Record], company: str, options: Options
) -> tuple[bytes, str, str]:
    files: list[tuple[str, bytes, str]] = []
    if options.output_format in {"xlsx", "both"}:
        files.append(
            (
                "boletas_procontel.xlsx",
                render_xlsx(source_data, records, company, options),
                XLSX_MIME,
            )
        )
    if options.output_format in {"pdf", "both"}:
        sources = list(dict.fromkeys(r.source_sheet or r.type.upper() for r in records))
        for source in sources:
            group = [r for r in records if (r.source_sheet or r.type.upper()) == source]
            kind = group[0].type
            if not group:
                continue
            period = options.periods[kind]
            filename = (
                f"boletas_{safe_pdf_suffix(source)}_{period.start:%Y%m%d}_{period.end:%Y%m%d}.pdf"
            )
            files.append((filename, render_pdf(group, company, options), "application/pdf"))
    if len(files) == 1:
        filename, payload, media = files[0]
        return payload, media, filename
    with BytesIO() as buffer:
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            for filename, payload, _ in files:
                archive.writestr(filename, payload)
        return buffer.getvalue(), "application/zip", "boletas_procontel.zip"
