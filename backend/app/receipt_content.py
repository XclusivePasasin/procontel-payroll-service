"""Receipt content independent of paper size and imposition layout."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.models import Options, Record
from app.reconciliation import amount, presentation, rounded


@dataclass(frozen=True)
class ReceiptLine:
    label: str
    value: str
    kind: Literal["detail", "section", "subtotal", "net", "metadata"] = "detail"
    number: Decimal | None = None


def currency(value: Decimal) -> str:
    return f"{'-' if value < 0 else ''}${abs(value):,.2f}"


def receipt_lines(record: Record, company: str, options: Options) -> list[ReceiptLine]:
    period = options.periods[record.type]
    rows = [
        ReceiptLine("Nombre del colaborador", str(record.fields.get("name", "")), "metadata"),
        ReceiptLine("Cargo", str(record.fields.get("role", "")), "metadata"),
        ReceiptLine("Área", str(record.fields.get("area", "")), "metadata"),
        ReceiptLine("Empresa", company, "metadata"),
        ReceiptLine(
            "Período de pago", f"DEL {period.start:%d/%m/%Y} AL {period.end:%d/%m/%Y}", "metadata"
        ),
        ReceiptLine(
            "Salario contratado", currency(rounded(amount(record, "contracted_amount"))), "metadata"
        ),
        ReceiptLine("Días trabajados", str(record.fields.get("worked_days", "")), "metadata"),
        ReceiptLine(
            "Horas extras diurnas", str(amount(record, "daytime_overtime_hours")), "metadata"
        ),
        ReceiptLine("Días de asueto", str(amount(record, "holiday_days")), "metadata"),
        ReceiptLine(
            "Días de vacaciones",
            str(amount(record, "vacation_days")) if record.type == "planilla" else "—",
            "metadata",
        ),
    ]
    for field, label in (
        ("nighttime_overtime_hours", "Horas extras nocturnas"),
        ("night_hours", "Horas de nocturnidad"),
        ("sick_days", "Días de incapacidad"),
        ("personal_leave_days", "Días de permiso"),
    ):
        if amount(record, field):
            rows.append(ReceiptLine(label, str(amount(record, field)), "metadata"))
    lines, _, final_net = presentation(record)
    values = dict(lines)
    rows.append(ReceiptLine("INGRESOS", "", "section"))
    income_total = Decimal(0)

    def money_row(
        label: str, value: Decimal, kind: Literal["detail", "subtotal", "net"] = "detail"
    ) -> None:
        rows.append(ReceiptLine(label, currency(value), kind, value))

    for field, label, always in (
        ("base_payment", "Sueldo quincenal", True),
        ("daytime_overtime_amount", "Horas extras diurnas", True),
        ("nighttime_overtime_amount", "Horas extras nocturnas", False),
        ("night_amount", "Nocturnidad", False),
        ("holiday_amount", "Asuetos", False),
        ("commission", "Comisión", False),
        ("bonus", "Bonificación", True),
    ):
        value = values[field]
        income_total += value
        if value or always:
            money_row(label, value)
    for field, label in (("annual_bonus", "Aguinaldo"), ("reimbursements", "Reintegros")):
        if field in record.fields:
            money_row(label, values[field])
            income_total += values[field]
        else:
            rows.append(ReceiptLine(label, "—"))
    if amount(record, "termination_payment"):
        money_row("Prestación / indemnización", values["termination_payment"])
        income_total += values["termination_payment"]
    travel = values["travel_or_reimbursements"]
    money_row(
        "Viáticos o reintegros" if record.type == "planilla" else "Viáticos o estadías", travel
    )
    income_total += travel + values["vacation_amount"]
    money_row("Vacaciones", values["vacation_amount"])
    rows.append(ReceiptLine("Otros ingresos", "—"))
    if record.type == "honorarios":
        money_row("IVA (adición)", values["vat"])
        income_total += values["vat"]
    money_row("Subtotal ingresos", income_total, "subtotal")
    rows.append(ReceiptLine("DESCUENTOS", "", "section"))
    deductions = Decimal(0)
    for field, label, always in (
        ("sick_amount", "Incapacidad", False),
        ("personal_leave_amount", "Permisos personales", False),
        ("employee_social_security", "ISSS", record.type == "planilla"),
        ("employee_pension", "AFP", record.type == "planilla"),
        ("income_tax", "Renta", True),
        ("other_deductions", "Otros descuentos", True),
    ):
        if field not in values:
            continue
        value = -values[field]
        deductions += value
        if value or always:
            money_row(label, value)
    money_row("Total descuentos", deductions, "subtotal")
    money_row("LÍQUIDO A RECIBIR", final_net, "net")
    return rows
