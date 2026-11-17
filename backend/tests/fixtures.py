"""Synthetic workbooks only. No employee data from the source workbook."""

from io import BytesIO
from typing import Callable

from openpyxl import Workbook

from app.profile import PROFILES


def workbook(mutate: Callable[[Workbook], None] | None = None) -> bytes:
    book = Workbook()
    book.remove(book.active)
    for kind, profile in PROFILES.items():
        sheet = book.create_sheet(kind.upper())
        sheet["A1"] = "EMPRESA SINTÉTICA S.A. DE C.V."
        sheet["A2"] = "SEGUNDA QUINCENA DE FEBRERO 2026"
        sheet["A4"] = "DEL 16 AL 31 DE MARZO DE 2026"
        for field, (column, aliases) in profile.items():
            sheet[f"{column}6"] = aliases.split("|")[0]
            sheet[f"{column}7"] = 0
        values: dict[str, str | int | float] = {
            "sequence": 1,
            "employee_id": "S-001" if kind == "planilla" else "H-001",
            "name": "Persona Sintética",
            "dui": "00000000-0",
            "area": "Administración",
            "role": "Especialista de pruebas",
            "contracted_amount": 900,
            "worked_days": 15,
        }
        if kind == "planilla":
            values |= {
                "pension_provider": "AFP de prueba",
                "base_payment": 450,
                "daytime_overtime_amount": 15,
                "nighttime_overtime_amount": 168.75,
                "vacation_amount": 450,
                "accrued_amount": 1083.75,
                "employee_social_security": 15,
                "employee_pension": 78.571875,
                "taxable_amount": 990.178125,
                "income_tax": 138.511625,
                "net_payment": 851.6665,
            }
        else:
            values |= {
                "base_payment": 900,
                "accrued_amount": 900,
                "vat": 117,
                "income_tax": 90,
                "net_payment": 927,
            }
        for field, value in values.items():
            sheet[f"{profile[field][0]}7"] = value
        sheet[f"{'F' if kind == 'planilla' else 'E'}14"] = "Total Planilla"
        # Preloaded zero formulas must not create a person.
        sheet[f"{profile['base_payment'][0]}8"] = "=0"
    if mutate:
        mutate(book)
    with BytesIO() as buffer:
        book.save(buffer)
        data = buffer.getvalue()
    book.close()
    return data
