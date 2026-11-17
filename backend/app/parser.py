from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from app.config import LIMITS
from app.models import Issue, Options, Provenance, Record, ServiceError
from app.numeric_values import empty_or_zero, numeric_value
from app.profile import TEXT, normalize, quantity
from app.sheet_profiles import source_kind, select_profile, receipt_sheet_name
from app.periods import suggest_period
from app.reconciliation import amount, totals
from app.security import inspect_package


def extract(data: bytes, options: Options) -> tuple[str, list[Record], list[Issue], dict[str, Any]]:
    inspect_package(data)
    books = []
    streams: list[BytesIO] = []
    issues: list[Issue] = []
    records: list[Record] = []
    metadata: dict[str, Any] = {}
    try:
        for data_only in (False, True):
            stream = BytesIO(data)
            streams.append(stream)
            books.append(load_workbook(stream, data_only=data_only, keep_links=False))
        source, cached = books
        sources = [
            (name, source_kind(name)) for name in source.sheetnames if source_kind(name) is not None
        ]
        if not sources:
            raise ServiceError(
                422,
                "UNKNOWN_STRUCTURE",
                "No se encontraron hojas PLANILLA u HONORARIOS con el perfil admitido.",
            )
        payroll_sources = [name for name, kind in sources if kind == "planilla"]
        company_source = payroll_sources[0] if payroll_sources else sources[0][0]
        company = str(cached[company_source]["A1"].value or "").strip()
        if not company or normalize(company) in {"NOMBRE EMPRESA", "EMPRESA"}:
            issues.append(
                Issue(
                    "COMPANY_REQUIRED",
                    "error",
                    "Completa la empresa en la hoja fuente y vuelve a cargar el Excel.",
                )
            )
        for selected_kind in options.kinds():
            if not any(kind == selected_kind for _, kind in sources):
                issues.append(
                    Issue(
                        "EMPTY_SELECTION",
                        "error",
                        "No hay hojas del tipo solicitado.",
                        selected_kind,
                    )
                )
        for sheet, discovered_kind in sources:
            if discovered_kind is None or discovered_kind not in options.kinds():
                continue
            kind = discovered_kind
            ws, values = source[sheet], cached[sheet]
            profile_id, profile = select_profile(kind, ws)
            for field, (column, aliases) in profile.items():
                actual = normalize(ws[f"{column}6"].value)
                if actual not in {normalize(a) for a in aliases.split("|")}:
                    issues.append(
                        Issue(
                            "HEADER_MISMATCH",
                            "error",
                            f"Encabezado no reconocido para {field}. Se requiere el perfil fijo.",
                            kind,
                            sheet,
                            f"{column}6",
                            6,
                            field,
                        )
                    )
            total_cols = (
                ["F"] if kind == "planilla" else (["E"] if profile_id == "fixed_v1" else ["D", "E"])
            )
            markers = [
                r
                for r in range(7, min(ws.max_row, LIMITS.rows) + 1)
                if any(normalize(ws[f"{col}{r}"].value) == "TOTAL PLANILLA" for col in total_cols)
            ]
            if len(markers) != 1:
                issues.append(
                    Issue(
                        "TOTAL_MARKER_INVALID",
                        "error",
                        "Se requiere un único marcador Total Planilla.",
                        kind,
                        sheet,
                    )
                )
                continue
            periods = [
                {"sheet": sheet, "cell": c, "value": str(values[c].value or "")[:500]}
                for c in ("A2", "A4")
            ]
            if kind == "planilla":
                periods.append(
                    {"sheet": sheet, "cell": "AB2", "value": str(values["AB2"].value or "")[:500]}
                )
            template = receipt_sheet_name(sheet)
            if template not in source.sheetnames:
                issues.append(
                    Issue(
                        "TEMPLATE_MISSING",
                        "warning",
                        "La plantilla de referencia no está incluida; se usa el diseño del servicio.",
                        kind,
                        sheet,
                    )
                )
            elif kind == "honorarios":
                periods.append(
                    {
                        "sheet": template,
                        "cell": "B6",
                        "value": str(cached[template]["B6"].value or "")[:500],
                    }
                )
            if template in source.sheetnames:
                issues.append(
                    Issue(
                        "TEMPLATE_MAPPING_MISMATCH",
                        "warning",
                        "La plantilla Excel es solo referencia: el servicio distingue comisión/bonificación, incluye extras nocturnas y trata el IVA como adición. Revisa las denominaciones antes de emitir.",
                        kind,
                        template,
                    )
                )
            current_meta = metadata.setdefault(
                kind, {"periods": [], "suggested_period": None, "sources": []}
            )
            current_meta["periods"].extend(periods)
            current_meta["suggested_period"] = current_meta["suggested_period"] or suggest_period(
                values["A4"].value
            )
            current_meta["sources"].append(
                {"sheet": sheet, "profile": profile_id, "receipt_sheet": receipt_sheet_name(sheet)}
            )
            issues.append(
                Issue(
                    "PERIOD_CONFLICT",
                    "confirmation",
                    "Confirma fechas de inicio y fin; los textos del libro no constituyen aprobación del período.",
                    kind,
                    sheet,
                )
            )
            seen_sequence: set[int] = set()
            seen_code: set[str] = set()
            count = 0
            for row in range(7, markers[0]):
                identity = [values[f"{c}{row}"].value for c in "ABCD"]
                numeric = [
                    values[f"{c}{row}"].value
                    for f, (c, _) in profile.items()
                    if f not in TEXT and f != "sequence"
                ]
                if all(v in (None, "") for v in identity) and all(
                    empty_or_zero(v) for v in numeric
                ):
                    continue
                try:
                    seq = Decimal(str(identity[0]))
                    if (
                        not seq.is_finite()
                        or seq <= 0
                        or seq != seq.to_integral_value()
                        or not identity[2]
                    ):
                        raise ValueError
                except (InvalidOperation, ValueError):
                    issues.append(
                        Issue(
                            "ROW_INCOMPLETE",
                            "error",
                            "La fila requiere correlativo positivo y nombre.",
                            kind,
                            sheet,
                            f"A{row}",
                            row,
                        )
                    )
                    continue
                count += 1
                if count > LIMITS.people:
                    raise ServiceError(
                        413, "PERSON_LIMIT", "Se excedió el límite de personas por tipo."
                    )
                code = str(identity[1]).strip() if identity[1] is not None else ""
                if int(seq) in seen_sequence or (code and code in seen_code):
                    issues.append(
                        Issue(
                            "DUPLICATE_IDENTITY",
                            "error",
                            "Código o correlativo repetido dentro del tipo.",
                            kind,
                            sheet,
                            f"B{row}",
                            row,
                        )
                    )
                seen_sequence.add(int(seq))
                if code:
                    seen_code.add(code)
                record = Record(
                    kind,
                    row,
                    int(seq),
                    code,
                    {},
                    source_sheet=sheet,
                    profile_id=profile_id,
                    fees_deductions_in_accrued=profile_id
                    not in {"fees_v2", "fees_reimbursements_v2"},
                )
                for field, col in (("sequence", "A"), ("employee_id", "B")):
                    origin = ws[f"{col}{row}"]
                    record.provenance[field] = Provenance(
                        sheet,
                        f"{col}{row}",
                        str(origin.value) if origin.data_type == "f" else None,
                        values[f"{col}{row}"].value,
                    )
                for field, (col, _) in profile.items():
                    if field in {"sequence", "employee_id"}:
                        continue
                    cell = f"{col}{row}"
                    original, saved = ws[cell], values[cell]
                    value = saved.value
                    record.provenance[field] = Provenance(
                        sheet,
                        cell,
                        str(original.value) if original.data_type == "f" else None,
                        value,
                    )
                    if original.data_type == "f" and value is None:
                        issues.append(
                            Issue(
                                "FORMULA_CACHE_MISSING",
                                "error",
                                "Abre el libro en Excel, recalcula, guarda y vuelve a cargarlo.",
                                kind,
                                sheet,
                                cell,
                                row,
                                field,
                            )
                        )
                        continue
                    if field in TEXT:
                        if saved.data_type == "e":
                            issues.append(
                                Issue(
                                    "INVALID_TEXT",
                                    "error",
                                    "La celda de texto contiene un error Excel.",
                                    kind,
                                    sheet,
                                    cell,
                                    row,
                                    field,
                                )
                            )
                            continue
                        record.fields[field] = str(value or "").strip()
                        if field in {"dui", "area", "role"} and not value:
                            issues.append(
                                Issue(
                                    "OPTIONAL_IDENTITY_MISSING",
                                    "warning",
                                    f"Falta {field}; se omitirá cuando corresponda.",
                                    kind,
                                    sheet,
                                    cell,
                                    row,
                                    field,
                                )
                            )
                        if field == "dui" and value is not None and not isinstance(value, str):
                            issues.append(
                                Issue(
                                    "DOCUMENT_MUST_BE_TEXT",
                                    "error",
                                    "Conserva el documento como texto en Excel.",
                                    kind,
                                    sheet,
                                    cell,
                                    row,
                                    field,
                                )
                            )
                        continue
                    required = {"base_payment", "accrued_amount", "net_payment", "income_tax"}
                    if kind == "planilla":
                        required |= {
                            "employee_social_security",
                            "employee_pension",
                            "taxable_amount",
                        }
                    if value in (None, ""):
                        if field in required:
                            issues.append(
                                Issue(
                                    "REQUIRED_AMOUNT_MISSING",
                                    "error",
                                    "Falta un importe central; corrige el Excel y vuelve a cargarlo.",
                                    kind,
                                    sheet,
                                    cell,
                                    row,
                                    field,
                                )
                            )
                            continue
                        if field == "vat":
                            issues.append(
                                Issue(
                                    "IVA_CONFIRMATION_REQUIRED",
                                    "warning",
                                    "IVA vacío: se utiliza cero.",
                                    kind,
                                    sheet,
                                    cell,
                                    row,
                                    field,
                                )
                            )
                        value = 0
                    try:
                        number = numeric_value(value, accounting=not quantity(field))
                        if (
                            saved.data_type == "e"
                            or isinstance(value, bool)
                            or not number.is_finite()
                            or number < 0
                            or number > Decimal("10000000")
                        ):
                            raise InvalidOperation
                        record.fields[field] = number
                        if quantity(field) and number > (744 if field.endswith("hours") else 31):
                            issues.append(
                                Issue(
                                    "QUANTITY_LIMIT",
                                    "error",
                                    "Cantidad fuera del límite; corrígela expresamente.",
                                    kind,
                                    sheet,
                                    cell,
                                    row,
                                    field,
                                )
                            )
                    except InvalidOperation:
                        issues.append(
                            Issue(
                                "INVALID_AMOUNT",
                                "error",
                                "Importe o cantidad no válido; revisa la celda.",
                                kind,
                                sheet,
                                cell,
                                row,
                                field,
                            )
                        )
                for field, expected in totals(record).items():
                    if (
                        field not in {"accrued_amount", "taxable_amount", "net_payment"}
                        or field not in record.fields
                    ):
                        continue
                    if kind == "honorarios" and field == "taxable_amount":
                        continue
                    if abs(amount(record, field) - expected) > Decimal("0.01"):
                        issues.append(
                            Issue(
                                "SOURCE_RECONCILIATION_FAILED",
                                "warning",
                                f"El {field} no concilia: esperado {expected}, encontrado {amount(record, field)}.",
                                kind,
                                sheet,
                                record.provenance[field].cell,
                                row,
                                field,
                            )
                        )
                records.append(record)
            type_records = [r for r in records if r.source_sheet == sheet]
            for source_metadata in metadata[kind]["sources"]:
                if source_metadata["sheet"] == sheet:
                    source_metadata["count"] = len(type_records)
            if not type_records:
                issues.append(
                    Issue(
                        "EMPTY_SELECTION",
                        "error",
                        "No hay personas válidas en el tipo solicitado.",
                        kind,
                        sheet,
                    )
                )
            for field, (col, _) in profile.items():
                if field in TEXT or field == "sequence":
                    continue
                total_cell = values[f"{col}{markers[0]}"].value
                try:
                    actual_total = Decimal(str(total_cell))
                except InvalidOperation:
                    continue
                expected_total = sum((amount(r, field) for r in type_records), Decimal(0))
                if actual_total.is_finite() and abs(actual_total - expected_total) > Decimal(
                    "0.01"
                ):
                    issues.append(
                        Issue(
                            "TOTAL_RANGE_INCOMPLETE",
                            "warning",
                            "El total del consolidado difiere del detalle; se usa la suma de personas.",
                            kind,
                            sheet,
                            f"{col}{markers[0]}",
                            markers[0],
                            field,
                        )
                    )
        for selected_kind in options.kinds():
            if sum(record.type == selected_kind for record in records) > LIMITS.people:
                raise ServiceError(
                    413, "PERSON_LIMIT", "Se excedió el límite total de personas por tipo."
                )
        for a in records:
            if any(
                a.type != b.type
                and (
                    (bool(a.employee_id) and a.employee_id == b.employee_id)
                    or normalize(a.fields.get("name")) == normalize(b.fields.get("name"))
                )
                for b in records
            ):
                issues.append(
                    Issue(
                        "CROSS_TYPE_MATCH",
                        "warning",
                        "Posible coincidencia entre tipos; ambos registros se conservan.",
                        a.type,
                        a.source_sheet,
                        row=a.source_row,
                    )
                )
        issues.append(
            Issue(
                "CACHE_FRESHNESS",
                "warning",
                "Las cachés no prueban actualidad: usa un libro recalculado y guardado por RRHH.",
            )
        )
        return company, records, issues, metadata
    except ServiceError:
        raise
    except Exception as exc:
        raise ServiceError(400, "UNREADABLE_FILE", "No se pudo inspeccionar el libro.") from exc
    finally:
        for book in books:
            book.close()
        for stream in streams:
            stream.close()
