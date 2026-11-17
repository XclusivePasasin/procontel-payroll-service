from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import app
from app.models import Identity, Options, ServiceError
from app.pdf import render_pdf
from app.reconciliation import presentation, rounded, totals
from app.service import build
from tests.fixtures import workbook


def confirmed(data: bytes) -> Options:
    return Options.model_validate(
        {
            "selection": "ambos",
            "file_sha256": sha256(data).hexdigest(),
            "periods": {
                k: {"start": "2026-03-16", "end": "2026-03-31", "confirmed": True}
                for k in ("planilla", "honorarios")
            },
        }
    )


def post(action: str, data: bytes, options: Options):
    with TestClient(app) as client:
        return client.post(
            f"/api/v1/{action}",
            files={
                "file": (
                    "synthetic.xlsx",
                    data,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={"options": options.model_dump_json()},
        )


def test_analysis_and_expected_money():
    data = workbook()
    result, records, _ = build(data, Options())
    assert not result["can_generate"]
    assert [result["types"][k]["count"] for k in ("planilla", "honorarios")] == [1, 1]
    assert totals(records[0])["gross"] == Decimal("1083.75")
    assert presentation(records[0])[2] == Decimal("851.67")
    assert presentation(records[1])[2] == Decimal("927.00")
    assert "provenance" not in result["records"][0]


def test_generate_pdf_zip_and_preview_match():
    data = workbook()
    options = confirmed(data)
    review = post("review", data, options)
    assert review.status_code == 200 and review.json()["can_generate"]
    response = post("generate", data, options)
    assert response.status_code == 200, response.text[:500] if response.status_code != 200 else ""
    assert response.headers["cache-control"] == "no-store, private"
    with ZipFile(BytesIO(response.content)) as archive:
        assert len(archive.namelist()) == 2
        for name in archive.namelist():
            pdf = PdfReader(BytesIO(archive.read(name)))
            assert len(pdf.pages) == 1
            text = pdf.pages[0].extract_text()
            assert "Persona Sintética" in text
            if "honorarios" in name:
                assert "$927.00" in text and "IVA (adición)" in text and "ISSS" not in text
            else:
                assert "$851.67" in text and "Horas extras nocturnas" in text
    options.preview_record = Identity(type="planilla", source_row=7, employee_id="S-001")
    preview = post("preview", data, options)
    assert preview.status_code == 200
    assert "inline" in preview.headers["content-disposition"]


def test_missing_confirmations_no_partial_output():
    data = workbook()
    response = post("generate", data, Options())
    assert response.status_code == 422
    assert response.json()["code"] == "REVIEW_REQUIRED"
    assert response.headers["cache-control"] == "no-store, private"


@pytest.mark.parametrize(
    "cell,value,code",
    [
        ("J7", "=450", "FORMULA_CACHE_MISSING"),
        ("J7", "oops", "INVALID_AMOUNT"),
        ("C7", None, "ROW_INCOMPLETE"),
        ("B8", "S-001", "ROW_INCOMPLETE"),
        ("J6", "shifted", "HEADER_MISMATCH"),
        ("AH7", 800, "SOURCE_RECONCILIATION_FAILED"),
        ("F14", None, "TOTAL_MARKER_INVALID"),
    ],
)
def test_source_errors(cell, value, code):
    data = workbook(lambda b: setattr(b["PLANILLA"][cell], "value", value))
    result, _, _ = build(data, Options())
    assert any(i["code"] == code for i in result["issues"])
    assert not result["can_generate"]


def test_vat_blank_confirmation_does_not_cover_missing_formula_cache():
    data = workbook(lambda b: setattr(b["HONORARIOS"]["AA7"], "value", None))
    result, _, _ = build(data, Options())
    assert any(i["code"] == "IVA_CONFIRMATION_REQUIRED" for i in result["issues"])
    ready, records, _ = build(data, confirmed(data))
    assert ready["can_generate"]
    assert records[1].fields["vat"] == 0
    data = workbook(lambda b: setattr(b["HONORARIOS"]["AA7"], "value", "=0"))
    options = confirmed(data)
    options.zero_vat_confirmations = []
    result, _, _ = build(data, options)
    assert any(i["code"] == "FORMULA_CACHE_MISSING" for i in result["issues"])


def test_rounding_residue_and_half_cent():
    _, records, _ = build(workbook(), Options())
    record = replace(
        records[1],
        fields=records[1].fields
        | {
            "base_payment": Decimal("0.005"),
            "commission": Decimal("0.005"),
            "vat": Decimal(0),
            "income_tax": Decimal(0),
            "accrued_amount": Decimal("0.01"),
            "net_payment": Decimal("0.01"),
        },
    )
    assert rounded(Decimal("0.005")) == Decimal("0.01")
    _, residue, net = presentation(record)
    assert residue == Decimal("-0.01") and net == Decimal("0.01")


def test_inserted_last_person_and_unselected_failures():
    def mutate(book):
        sheet = book["PLANILLA"]
        for col in range(1, 41):
            sheet.cell(13, col).value = sheet.cell(7, col).value
        sheet["A13"] = 2
        sheet["B13"] = "S-002"
        book["HONORARIOS"]["AA7"] = "=0"

    data = workbook(mutate)
    options = confirmed(data)
    options.selection = "planilla"
    result, records, _ = build(data, options)
    assert result["can_generate"] and len(records) == 2
    pdf = PdfReader(BytesIO(render_pdf(records, result["company"], options)))
    assert len(pdf.pages) == 1


def test_package_rejects_external_relationship_and_macros():
    original = workbook()
    for path, payload in [
        ("xl/vbaProject.bin", b"macro"),
        (
            "xl/_rels/evil.rels",
            b'<Relationships><Relationship TargetMode="External" Target="https://example.com"/></Relationships>',
        ),
    ]:
        with BytesIO() as buffer:
            with ZipFile(buffer, "w") as archive:
                with ZipFile(BytesIO(original)) as source:
                    for entry in source.infolist():
                        archive.writestr(entry, source.read(entry.filename))
                archive.writestr(path, payload)
            data = buffer.getvalue()
        with pytest.raises(ServiceError) as exc:
            build(data, Options())
        assert exc.value.status == 415


def test_http_format_and_unknown_options():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyze", files={"file": ("bad.xlsm", b"no")}, data={"options": "{}"}
        )
        assert response.status_code == 415
        assert client.get("/healthz").json() == {"status": "ok"}
    response = post("analyze", workbook(), Options())
    assert response.status_code == 200
