from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Kind = Literal["planilla", "honorarios"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Identity(StrictModel):
    type: Kind
    source_row: int
    employee_id: str
    source_sheet: str | None = None


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: date
    end: date
    confirmed: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def ordered(self) -> "Period":
        if self.start > self.end:
            raise ValueError("La fecha inicial debe ser anterior a la final.")
        return self


class VatConfirmation(StrictModel):
    sheet: str
    row: int


class Options(StrictModel):
    selection: Literal["planilla", "honorarios", "ambos"] = "ambos"
    schema_version: str = "procontel_fixed_v1"
    file_sha256: str | None = None
    periods: dict[Kind, Period] = Field(default_factory=dict)
    zero_vat_confirmations: list[VatConfirmation] = Field(default_factory=list)
    selected_records: list[Identity] | None = None
    preview_record: Identity | None = None
    output_format: Literal["pdf", "xlsx", "both"] = "pdf"

    def kinds(self) -> list[Kind]:
        return ["planilla", "honorarios"] if self.selection == "ambos" else [self.selection]


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    type: str | None = None
    sheet: str | None = None
    cell: str | None = None
    row: int | None = None
    field: str | None = None


@dataclass
class Provenance:
    sheet: str
    cell: str
    formula: str | None
    source: object


@dataclass
class Record:
    type: Kind
    source_row: int
    sequence: int
    employee_id: str
    fields: dict[str, str | Decimal]
    provenance: dict[str, Provenance] = field(default_factory=dict)
    source_sheet: str = ""
    profile_id: str = "fixed_v1"
    fees_deductions_in_accrued: bool = True


class ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str, issues: list[Issue] | None = None):
        self.status, self.code, self.message, self.issues = status, code, message, issues or []
        super().__init__(code)
