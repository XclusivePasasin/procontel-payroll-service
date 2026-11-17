"""Explicit source layouts; sheet suffixes identify the business area, not columns."""

from hashlib import sha256
import re

from openpyxl.worksheet.worksheet import Worksheet

from app.models import Kind
from app.profile import PROFILES, normalize

Profile = dict[str, tuple[str, str]]


def source_kind(name: str) -> Kind | None:
    normalized = normalize(name)
    if normalized == "PLANILLA" or normalized.startswith("PLANILLA "):
        return "planilla"
    if normalized == "HONORARIOS" or normalized.startswith("HONORARIOS "):
        return "honorarios"
    return None


def receipt_sheet_name(source: str) -> str:
    if normalize(source) in {"PLANILLA", "HONORARIOS"}:
        return f"BOLETA {source.upper()}"
    full = f"BOLETAS DE PAGO {source}"
    if len(full) <= 31:
        return full
    shorter = f"BOLETAS {source}"
    if len(shorter) <= 31:
        return shorter
    return f"{shorter[:26]}-{sha256(source.encode()).hexdigest()[:4]}"


def mapped(kind: Kind, columns: dict[str, str]) -> Profile:
    base = PROFILES[kind]
    extras = {
        "annual_bonus": "AGUINALDO",
        "termination_payment": "PRESTACION POR RENUNCIA|INDEMNIZACION|IMDENNIZACION",
        "reimbursements": "REINTEGROS",
    }
    profile = {
        field: (column, base[field][1] if field in base else extras[field])
        for field, column in columns.items()
    }
    aliases = {
        "travel_or_reimbursements": "VIATICOS O REINTEGRO|VIATICOS O REINTEGROS|VIATICOS O ESTADIAS",
        "vacation_days": "DIAS VACACION",
    }
    for field, alias in aliases.items():
        if field in profile:
            column, labels = profile[field]
            profile[field] = (column, labels + "|" + alias)
    return profile


PAYROLL_BONUS_COLUMNS = {
    field: column
    for field, (column, _) in PROFILES["planilla"].items()
    if column
    in {
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
    }
} | {
    "bonus": "Y",
    "accrued_amount": "Z",
    "employee_social_security": "AA",
    "employee_pension": "AB",
    "taxable_amount": "AC",
    "income_tax": "AD",
    "other_deductions": "AE",
    "travel_or_reimbursements": "AF",
    "annual_bonus": "AG",
    "termination_payment": "AH",
    "net_payment": "AI",
    "employer_training": "AL",
    "employer_social_security": "AM",
    "employer_pension": "AN",
    "employer_total": "AO",
}
PAYROLL_COMMISSION_COLUMNS = {
    field: column for field, (column, _) in PROFILES["planilla"].items()
} | {
    "annual_bonus": "AH",
    "termination_payment": "AI",
    "net_payment": "AJ",
    "employer_training": "AM",
    "employer_social_security": "AN",
    "employer_pension": "AO",
    "employer_total": "AP",
}
FEES_V2_COLUMNS = {field: column for field, (column, _) in PROFILES["honorarios"].items()} | {
    "accrued_amount": "Y",
    "vat": "Z",
    "income_tax": "AA",
    "other_deductions": "AB",
}
FEES_REIMBURSEMENT_COLUMNS = FEES_V2_COLUMNS | {
    "reimbursements": "AD",
    "net_payment": "AE",
    "employer_training": "AH",
    "employer_social_security": "AI",
    "employer_pension": "AJ",
    "employer_total": "AK",
}

CANDIDATES: dict[Kind, list[tuple[str, Profile]]] = {
    "planilla": [
        ("fixed_v1", PROFILES["planilla"]),
        ("payroll_bonus_v2", mapped("planilla", PAYROLL_BONUS_COLUMNS)),
        ("payroll_commission_v2", mapped("planilla", PAYROLL_COMMISSION_COLUMNS)),
    ],
    "honorarios": [
        ("fixed_v1", PROFILES["honorarios"]),
        ("fees_v2", mapped("honorarios", FEES_V2_COLUMNS)),
        ("fees_reimbursements_v2", mapped("honorarios", FEES_REIMBURSEMENT_COLUMNS)),
    ],
}


def select_profile(kind: Kind, sheet: Worksheet) -> tuple[str, Profile]:
    for identifier, profile in CANDIDATES[kind]:
        if all(
            normalize(sheet[f"{column}6"].value)
            in {normalize(alias) for alias in labels.split("|")}
            for column, labels in profile.values()
        ):
            return identifier, profile
    # Retain the previous profile for precise, coordinate-based header diagnostics.
    return "unknown", PROFILES[kind]


def safe_pdf_suffix(sheet: str) -> str:
    normalized = normalize(sheet).lower()
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")[:60] or "boletas"
