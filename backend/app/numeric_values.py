"""Read numeric values and explicit dollar accounting strings without rounding."""

from decimal import Decimal, InvalidOperation
import re


def numeric_value(value: object, *, accounting: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise InvalidOperation
    text = str(value).strip()
    if accounting and isinstance(value, str):
        text = text.replace("\u00a0", " ").strip()
        if text.startswith("$"):
            text = text[1:].strip()
            if text == "-":
                return Decimal(0)
        # Commas are accepted only as correctly grouped thousands separators.
        if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", text):
            raise InvalidOperation
        text = text.replace(",", "")
    return Decimal(text)


def empty_or_zero(value: object) -> bool:
    if value is None or value == "":
        return True
    try:
        return numeric_value(value, accounting=True) == 0
    except InvalidOperation:
        return False
