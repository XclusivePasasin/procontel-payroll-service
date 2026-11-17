from copy import deepcopy
from hashlib import sha256

from app.models import Identity, Issue, Kind, Options, Record, ServiceError


def record_key(record: Record) -> tuple[str, str, int, str]:
    return (
        record.type,
        record.source_sheet or record.type.upper(),
        record.source_row,
        record.employee_id,
    )


def matches_identity(record: Record, identity: Identity) -> bool:
    return (record.type, record.source_row, record.employee_id) == (
        identity.type,
        identity.source_row,
        identity.employee_id,
    ) and (identity.source_sheet is None or identity.source_sheet == record.source_sheet)


def choose_records(data: bytes, records: list[Record], options: Options) -> list[Record]:
    if options.selected_records is None:
        return records
    if options.file_sha256 != sha256(data).hexdigest():
        raise ServiceError(409, "FILE_CHANGED", "El archivo cambió; vuelve a analizarlo.")
    if not options.selected_records:
        raise ServiceError(422, "EMPTY_SELECTION", "Selecciona al menos una boleta.")
    chosen: set[tuple[str, str, int, str]] = set()
    for identity in options.selected_records:
        matches = [r for r in records if matches_identity(r, identity)]
        if len(matches) != 1 or record_key(matches[0]) in chosen:
            raise ServiceError(
                422,
                "INVALID_SELECTION",
                "La selección contiene registros repetidos, ambiguos o ajenos al archivo. Identifica también la hoja de origen.",
            )
        chosen.add(record_key(matches[0]))
    return [r for r in records if record_key(r) in chosen]


def confirm_issues(
    source: list[Issue], records: list[Record], selected: list[Record], options: Options
) -> list[Issue]:
    kinds: set[Kind] = (
        set(options.kinds()) if options.selected_records is None else {r.type for r in selected}
    )
    available_rows = {(r.source_sheet, r.source_row) for r in records}
    chosen_rows = {(r.source_sheet, r.source_row) for r in selected}
    selected_sheets = {r.source_sheet for r in selected}
    source_sheets = {r.source_sheet for r in records}
    issues = deepcopy(
        [
            i
            for i in source
            if (i.type is None or i.type in kinds)
            and (
                options.selected_records is None
                or i.sheet not in source_sheets
                or i.sheet in selected_sheets
            )
            and ((i.sheet, i.row) not in available_rows or (i.sheet, i.row) in chosen_rows)
        ]
    )
    vat_keys: set[tuple[str, int]] = set()
    for confirmation in options.zero_vat_confirmations:
        key = (confirmation.sheet, confirmation.row)
        if key in vat_keys or not any(
            i.code == "IVA_CONFIRMATION_REQUIRED" and (i.sheet, i.row) == key for i in source
        ):
            raise ServiceError(
                422,
                "INVALID_CONFIRMATION",
                "La confirmación de IVA no corresponde a una celda manual vacía.",
            )
        vat_keys.add(key)
    for issue in issues:
        if issue.code == "IVA_CONFIRMATION_REQUIRED" and (issue.sheet, issue.row) in vat_keys:
            issue.severity = "warning"
            issue.message = "IVA vacío confirmado expresamente como cero para esta fila."
        period = next(
            (period for kind, period in options.periods.items() if kind == issue.type), None
        )
        if issue.code == "PERIOD_CONFLICT" and period and period.confirmed:
            issue.severity = "warning"
            issue.message = "Se usará el período confirmado expresamente por RRHH."
    return issues
