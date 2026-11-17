from decimal import Decimal, InvalidOperation

import pytest

from app.numeric_values import empty_or_zero, numeric_value
from app.profile import PROFILES, TEXT, quantity
from app.service import build
from app.models import Provenance
from app.reconciliation import presentation
from tests.fixtures import workbook
from tests.test_workflow import confirmed


@pytest.mark.parametrize(
    "value, expected",
    [
        (" $ 500.00 ", "500"),
        (" $ -   ", "0"),
        ("$ 1,234.56", "1234.56"),
        ("$\u00a015.00", "15"),
        (0, "0"),
    ],
)
def test_accounting_values(value, expected):
    assert numeric_value(value, accounting=True) == Decimal(expected)


@pytest.mark.parametrize("value", ["#REF!", "500,25", "1,23.00", "$ text", "NaN", True])
def test_invalid_accounting_values(value):
    with pytest.raises(InvalidOperation):
        numeric_value(value, accounting=True)


def test_accounting_values_do_not_create_people_or_change_money():
    def accounting(book):
        for kind, profile in PROFILES.items():
            sheet = book[kind.upper()]
            for field, (column, _) in profile.items():
                cell = sheet[f"{column}7"]
                if (
                    field not in TEXT
                    and field != "sequence"
                    and not quantity(field)
                    and isinstance(cell.value, (int, float))
                ):
                    cell.value = f" $ {cell.value} " if cell.value else " $ -   "
            sheet["A8"] = None
            sheet["J8"] = " $ -   "

    data = workbook(accounting)
    result, records, _ = build(data, confirmed(data))
    assert result["can_generate"], result["issues"]
    assert len(records) == 2
    assert empty_or_zero(" $ -   ") and not empty_or_zero("#REF!")


@pytest.mark.parametrize("difference", [Decimal("0.01"), Decimal("-0.01")])
def test_formula_accounting_cache_allows_one_cent_with_explicit_adjustment(difference):
    data = workbook()
    _, records, _ = build(data, confirmed(data))
    record = records[1]
    record.fields["net_payment"] = Decimal("927") + difference
    record.provenance["net_payment"] = Provenance(
        "HONORARIOS", "AD7", "=Y7+Z7-AA7", f" $ {record.fields['net_payment']} "
    )
    _, adjustment, net = presentation(record)
    assert adjustment == difference and net == Decimal("927") + difference
    record.fields["net_payment"] = Decimal("927.02")
    assert presentation(record)[2] == Decimal("927.02")
    record.fields["net_payment"] = Decimal("927.01")
    record.provenance["net_payment"].source = 927.01
    assert presentation(record)[2] == Decimal("927.01")
