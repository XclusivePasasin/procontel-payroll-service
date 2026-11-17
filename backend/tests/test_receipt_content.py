from app.receipt_content import receipt_lines
from app.service import build
from tests.fixtures import workbook
from tests.test_workflow import confirmed


def test_receipt_fields_and_source_totals():
    data = workbook()
    options = confirmed(data)
    result, records, _ = build(data, options)
    payroll = receipt_lines(records[0], result["company"], options)
    fees = receipt_lines(records[1], result["company"], options)
    for rows in (payroll, fees):
        labels = {row.label for row in rows}
        assert {
            "Nombre del colaborador",
            "Cargo",
            "Área",
            "Empresa",
            "Período de pago",
            "Salario contratado",
            "Días trabajados",
            "Horas extras diurnas",
            "Días de asueto",
            "Días de vacaciones",
            "INGRESOS",
            "DESCUENTOS",
            "LÍQUIDO A RECIBIR",
        }.issubset(labels)
        assert all(
            row.value == "—"
            for row in rows
            if row.label in {"Aguinaldo", "Reintegros", "Otros ingresos"}
        )
    assert payroll[-1].value == "$851.67"
    assert fees[-1].value == "$927.00"
    assert (
        next(
            row.value
            for row in payroll
            if row.label == "Horas extras nocturnas" and row.kind == "detail"
        )
        == "$168.75"
    )
    assert next(row.value for row in fees if row.label == "Días de vacaciones") == "—"
    assert next(row.value for row in fees if row.label == "IVA (adición)") == "$117.00"
    assert not any(row.label in {"ISSS", "AFP"} for row in fees)
