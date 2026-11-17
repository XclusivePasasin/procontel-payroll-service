from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
from typing import Any

from app.config import SCHEMA
from app.models import Issue, Options, Record, ServiceError
from app.selection import choose_records, confirm_issues
from app.parser import extract
from app.reconciliation import amount, presentation, rounded, totals


def serialize_record(record: Record) -> dict[str, Any]:
    return {
        "type": record.type,
        "source_row": record.source_row,
        "source_sheet": record.source_sheet,
        "sequence": record.sequence,
        "employee_id": record.employee_id,
        "fields": {k: str(v) for k, v in record.fields.items()},
        "derived": {k: str(v) for k, v in totals(record).items()},
        "final_net": str(rounded(amount(record, "net_payment"))),
    }


def build(data: bytes, options: Options) -> tuple[dict[str, Any], list[Record], list[Issue]]:
    if options.schema_version != SCHEMA:
        raise ServiceError(422, "UNKNOWN_PROFILE", "Versión de perfil no admitida.")
    digest = sha256(data).hexdigest()
    company, originals, source_issues, metadata = extract(data, options)
    records = choose_records(data, originals, options)
    issues = confirm_issues(source_issues, originals, records, options)
    for record in records:
        if not any(
            i.severity == "error" and i.sheet == record.source_sheet and i.row == record.source_row
            for i in issues
        ):
            try:
                presentation(record)
            except ValueError:
                issues.append(
                    Issue(
                        "UNEXPLAINED_ROUNDING",
                        "error",
                        "El líquido presenta una diferencia que no se explica por redondeo. Corrige el Excel y vuelve a cargarlo.",
                        record.type,
                        record.source_sheet,
                        row=record.source_row,
                        field="net_payment",
                    )
                )
    summary = {}
    for kind in options.kinds():
        group = [r for r in records if r.type == kind]
        original_group = [r for r in originals if r.type == kind]
        net = sum((rounded(amount(r, "net_payment")) for r in group), Decimal(0))
        summary[kind] = {
            "count": len(original_group),
            "selected_count": len(group),
            "net_total": str(net),
            **metadata.get(kind, {}),
        }
    response = {
        "can_generate": not any(i.severity in {"error", "confirmation"} for i in issues),
        "schema_version": SCHEMA,
        "file_sha256": digest,
        "company": company,
        "types": summary,
        "records": [serialize_record(r) for r in originals],
        "selected_count": len(records),
        "issues": [asdict(i) for i in issues],
        "source_issues": [asdict(i) for i in source_issues],
        "source_sheets": [
            dict(item, type=kind)
            for kind, details in metadata.items()
            for item in details.get("sources", [])
        ],
    }
    return response, records, issues


def require_ready(issues: list[Issue]) -> None:
    blocked = [i for i in issues if i.severity in {"error", "confirmation"}]
    if blocked:
        raise ServiceError(
            422,
            "REVIEW_REQUIRED",
            "Resuelve los errores y confirmaciones antes de emitir boletas.",
            issues,
        )
