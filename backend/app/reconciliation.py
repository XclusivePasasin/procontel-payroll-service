from decimal import ROUND_HALF_UP, Decimal

from app.models import Record
from app.profile import INCOMES, REDUCTIONS

CENT = Decimal("0.01")


def rounded(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def amount(record: Record, field: str) -> Decimal:
    value = record.fields.get(field, Decimal(0))
    return value if isinstance(value, Decimal) else Decimal(0)


def totals(record: Record) -> dict[str, Decimal]:
    gross = sum((amount(record, f) for f in INCOMES), Decimal(0))
    reductions = sum((amount(record, f) for f in REDUCTIONS), Decimal(0))
    accrued = gross - reductions
    discounts = amount(record, "income_tax") + amount(record, "other_deductions")
    if record.type == "planilla":
        discounts += amount(record, "employee_social_security") + amount(record, "employee_pension")
        taxable = (
            accrued
            - amount(record, "employee_social_security")
            - amount(record, "employee_pension")
        )
        net = accrued - discounts + amount(record, "travel_or_reimbursements")
    else:
        if record.fees_deductions_in_accrued:
            accrued -= amount(record, "other_deductions")
        taxable = accrued
        net = (
            accrued
            + amount(record, "vat")
            - amount(record, "income_tax")
            + amount(record, "travel_or_reimbursements")
        )
        if not record.fees_deductions_in_accrued:
            net -= amount(record, "other_deductions")
    net += sum(
        (amount(record, f) for f in ("annual_bonus", "termination_payment", "reimbursements")),
        Decimal(0),
    )
    return {
        "gross": gross,
        "reductions": reductions,
        "accrued_amount": accrued,
        "taxable_amount": taxable,
        "discounts": discounts,
        "net_payment": net,
    }


def signed_lines(record: Record) -> list[tuple[str, Decimal]]:
    lines = [(f, amount(record, f)) for f in INCOMES]
    lines += [(f, -amount(record, f)) for f in REDUCTIONS]
    deductions = ["income_tax", "other_deductions"]
    if record.type == "planilla":
        deductions += ["employee_social_security", "employee_pension"]
    else:
        lines.append(("vat", amount(record, "vat")))
    lines += [(f, -amount(record, f)) for f in deductions]
    lines.append(("travel_or_reimbursements", amount(record, "travel_or_reimbursements")))
    lines.extend(
        (field, amount(record, field))
        for field in ("annual_bonus", "termination_payment", "reimbursements")
    )
    return lines


def presentation(record: Record) -> tuple[list[tuple[str, Decimal]], Decimal, Decimal]:
    lines = [(f, rounded(v)) for f, v in signed_lines(record)]
    source_net = rounded(amount(record, "net_payment"))
    residue = source_net - sum((v for _, v in lines), Decimal(0))
    # Preserve the saved source net even when it differs from the detail sum.
    return lines, residue, source_net
