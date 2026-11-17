import unicodedata
from app.verified_headers import VERIFIED_HEADERS

# A fixed coordinate contract: aliases are explicit, never fuzzy column matching.
COMMON = {
    "sequence": ("A", "N°|Nº|NO|N|CORRELATIVO"),
    "employee_id": ("B", "CODIGO|CODIGO EMPLEADO"),
    "name": ("C", "NOMBRE|NOMBRE DEL EMPLEADO|NOMBRE COMPLETO|NOMBRES Y APELLIDOS"),
    "dui": ("D", "DUI"),
}
PAYROLL = {
    "pension_provider": ("E", "AFP"),
    "area": ("F", "AREA"),
    "role": ("G", "CARGO"),
    "contracted_amount": ("H", "SALARIO|SALARIO CONTRATADO|SUELDO CONTRATADO"),
    "worked_days": ("I", "DIAS|DIAS TRABAJADOS"),
    "base_payment": ("J", "SUELDO QUINCENAL|SALARIO QUINCENAL"),
    "daytime_overtime_hours": ("K", "HORAS EXTRAS DIURNAS|H.E. DIURNAS|HED"),
    "daytime_overtime_amount": (
        "L",
        "MONTO HORAS EXTRAS DIURNAS|VALOR H.E. DIURNAS|PAGO HORAS EXTRAS DIURNAS",
    ),
    "nighttime_overtime_hours": ("M", "HORAS EXTRAS NOCTURNAS|H.E. NOCTURNAS|HEN"),
    "nighttime_overtime_amount": (
        "N",
        "MONTO HORAS EXTRAS NOCTURNAS|VALOR H.E. NOCTURNAS|PAGO HORAS EXTRAS NOCTURNAS",
    ),
    "night_hours": ("O", "HORAS NOCTURNAS|HORAS NOCTURNIDAD|HORAS NORTURNIDAD"),
    "night_amount": ("P", "NOCTURNIDAD|NORTURNIDAD"),
    "holiday_days": ("Q", "DIAS ASUETO|DIAS DE ASUETO|ASUETOS"),
    "holiday_amount": ("R", "ASUETO|PAGO ASUETO|MONTO ASUETO"),
    "vacation_days": ("S", "DIAS VACACIONES|DIAS DE VACACIONES"),
    "vacation_amount": ("T", "VACACIONES|VACACION|VACACION 30%"),
    "sick_days": ("U", "DIAS INCAPACIDAD|DIAS DE INCAPACIDAD"),
    "sick_amount": ("V", "INCAPACIDAD|MONTO INCAPACIDAD"),
    "personal_leave_days": ("W", "DIAS PERMISO|DIAS DE PERMISO"),
    "personal_leave_amount": ("X", "PERMISOS|PERMISO|MONTO PERMISO"),
    "commission": ("Y", "COMISION|COMISIONES"),
    "bonus": ("Z", "BONIFICACION|BONIFICACIONES"),
    "accrued_amount": ("AA", "DEVENGADO|TOTAL DEVENGADO"),
    "employee_social_security": ("AB", "ISSS"),
    "employee_pension": ("AC", "AFP"),
    "taxable_amount": ("AD", "SALARIO SUJETO|SALARIO SUJETO A RENTA"),
    "income_tax": ("AE", "RENTA|ISR"),
    "other_deductions": ("AF", "OTROS DESCUENTOS"),
    "travel_or_reimbursements": ("AG", "VIATICOS|VIATICOS O REINTEGROS"),
    "net_payment": ("AH", "LIQUIDO|LIQUIDO A PAGAR"),
    "employer_training": ("AK", "INCAF"),
    "employer_social_security": ("AL", "ISSS PATRONAL"),
    "employer_pension": ("AM", "AFP PATRONAL"),
    "employer_total": ("AN", "TOTAL PATRONAL|TOTAL"),
}
FEES_COLUMNS = {
    "area": "E",
    "role": "F",
    "contracted_amount": "G",
    "worked_days": "H",
    "base_payment": "I",
    "daytime_overtime_hours": "J",
    "daytime_overtime_amount": "K",
    "nighttime_overtime_hours": "L",
    "nighttime_overtime_amount": "M",
    "night_hours": "N",
    "night_amount": "O",
    "holiday_days": "P",
    "holiday_amount": "Q",
    "vacation_amount": "R",
    "sick_days": "S",
    "sick_amount": "T",
    "personal_leave_days": "U",
    "personal_leave_amount": "V",
    "commission": "W",
    "bonus": "X",
    "other_deductions": "Y",
    "accrued_amount": "Z",
    "vat": "AA",
    "income_tax": "AB",
    "travel_or_reimbursements": "AC",
    "net_payment": "AD",
    "employer_training": "AG",
    "employer_social_security": "AH",
    "employer_pension": "AI",
    "employer_total": "AJ",
}
FEES = {k: (v, PAYROLL[k][1] if k in PAYROLL else "IVA") for k, v in FEES_COLUMNS.items()}
PROFILES = {"planilla": COMMON | PAYROLL, "honorarios": COMMON | FEES}
for _kind, _profile in PROFILES.items():
    for _field, (_column, _aliases) in list(_profile.items()):
        _profile[_field] = (_column, _aliases + "|" + VERIFIED_HEADERS[_kind][_field])
TEXT = {"name", "dui", "pension_provider", "area", "role", "employee_id"}
DERIVED = {
    "accrued_amount",
    "taxable_amount",
    "net_payment",
    "employer_training",
    "employer_social_security",
    "employer_pension",
    "employer_total",
}
INCOMES = [
    "base_payment",
    "daytime_overtime_amount",
    "nighttime_overtime_amount",
    "night_amount",
    "holiday_amount",
    "vacation_amount",
    "commission",
    "bonus",
]
REDUCTIONS = ["sick_amount", "personal_leave_amount"]
LABELS = {
    "name": "Nombre",
    "area": "Área",
    "role": "Cargo",
    "dui": "DUI",
    "pension_provider": "AFP",
    "contracted_amount": "Salario contratado",
    "worked_days": "Días trabajados",
    "base_payment": "Pago base",
    "daytime_overtime_hours": "Horas extras diurnas",
    "daytime_overtime_amount": "Extras diurnas",
    "nighttime_overtime_hours": "Horas extras nocturnas",
    "nighttime_overtime_amount": "Extras nocturnas",
    "night_hours": "Horas de nocturnidad",
    "night_amount": "Nocturnidad",
    "holiday_days": "Días de asueto",
    "holiday_amount": "Asuetos",
    "vacation_days": "Días de vacaciones",
    "vacation_amount": "Vacaciones",
    "sick_days": "Días de incapacidad",
    "sick_amount": "Incapacidad",
    "personal_leave_days": "Días de permiso",
    "personal_leave_amount": "Permisos",
    "commission": "Comisión",
    "bonus": "Bonificación",
    "employee_social_security": "ISSS",
    "employee_pension": "AFP",
    "income_tax": "Renta",
    "other_deductions": "Otros descuentos",
    "vat": "IVA",
    "travel_or_reimbursements": "Viáticos o reintegros",
    "accrued_amount": "Devengado",
    "taxable_amount": "Salario sujeto",
    "net_payment": "Líquido",
}


def normalize(value: object) -> str:
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", str(value or ""))
            if not unicodedata.combining(c)
        )
        .upper()
        .split()
    )


def quantity(field: str) -> bool:
    return field.endswith("_days") or field.endswith("_hours")
