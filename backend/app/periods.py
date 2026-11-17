from datetime import date
import re

from app.profile import normalize

MONTHS = {
    name: index
    for index, name in enumerate(
        (
            "ENERO",
            "FEBRERO",
            "MARZO",
            "ABRIL",
            "MAYO",
            "JUNIO",
            "JULIO",
            "AGOSTO",
            "SEPTIEMBRE",
            "OCTUBRE",
            "NOVIEMBRE",
            "DICIEMBRE",
        ),
        1,
    )
}


def suggest_period(value: object) -> dict[str, str] | None:
    match = re.fullmatch(r"DEL (\d{1,2}) AL\s*(\d{1,2}) DE ([A-Z]+) DEL? (\d{4})", normalize(value))
    if not match or match[3] not in MONTHS:
        return None
    try:
        start = date(int(match[4]), MONTHS[match[3]], int(match[1]))
        end = date(int(match[4]), MONTHS[match[3]], int(match[2]))
    except ValueError:
        return None
    if start > end:
        return None
    return {"start": start.isoformat(), "end": end.isoformat()}
