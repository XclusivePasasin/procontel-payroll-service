from dataclasses import replace
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest
from fastapi.testclient import TestClient

from app import security
from app.main import app
from app.models import Options, ServiceError
from app.service import build
from tests.fixtures import workbook
from app.verified_headers import VERIFIED_HEADERS
from app.profile import PROFILES


def test_effective_expansion_limit(monkeypatch):
    data = workbook()
    monkeypatch.setattr(security, "LIMITS", replace(security.LIMITS, expanded=100))
    with pytest.raises(ServiceError) as exc:
        security.inspect_package(data)
    assert exc.value.status == 413


def test_entry_limit_and_xml_entities(monkeypatch):
    data = workbook()
    monkeypatch.setattr(security, "LIMITS", replace(security.LIMITS, entries=1))
    with pytest.raises(ServiceError):
        security.inspect_package(data)


def test_compressed_bomb_and_hardened_xml():
    data = workbook()
    for payload in [
        b"x" * (17 * 1024 * 1024),
        b'<!DOCTYPE root [<!ENTITY x "sensitive">]><root>&x;</root>',
    ]:
        with BytesIO() as buffer:
            with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
                with ZipFile(BytesIO(data)) as original:
                    for entry in original.infolist():
                        archive.writestr(entry, original.read(entry.filename))
                archive.writestr("xl/extra.xml", payload)
            with pytest.raises(ServiceError):
                security.inspect_package(buffer.getvalue())


def test_no_upload_spooling_and_request_limits(monkeypatch):
    monkeypatch.setattr(security, "LIMITS", replace(security.LIMITS, upload=32))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyze", files={"file": ("test.xlsx", b"x" * 33)}, data={"options": "{}"}
        )
        assert response.status_code == 413
        assert response.headers["cache-control"] == "no-store, private"
        assert "request_id" in response.json()
        response = client.post(
            "/api/v1/analyze", content=b"bad", headers={"content-type": "application/json"}
        )
        assert response.status_code == 400


@pytest.mark.parametrize(
    "mutation,expected",
    [
        (
            lambda b: setattr(b["PLANILLA"]["F15"], "value", "Total Planilla"),
            "TOTAL_MARKER_INVALID",
        ),
        (lambda b: setattr(b["PLANILLA"]["J9"], "value", 1), "ROW_INCOMPLETE"),
        (lambda b: setattr(b["PLANILLA"]["I7"], "value", 32), "QUANTITY_LIMIT"),
        (lambda b: setattr(b["PLANILLA"]["J7"], "value", -1), "INVALID_AMOUNT"),
    ],
)
def test_additional_source_errors(mutation, expected):
    result, _, _ = build(workbook(mutation), Options())
    assert any(issue["code"] == expected for issue in result["issues"])


def test_saved_formula_cache_read_without_evaluation():
    data = workbook()
    with BytesIO() as buffer:
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            with ZipFile(BytesIO(data)) as original:
                for entry in original.infolist():
                    payload = original.read(entry.filename)
                    if entry.filename == "xl/worksheets/sheet1.xml":
                        payload = payload.replace(
                            b'<c r="J7" t="n"><v>450</v></c>',
                            b'<c r="J7"><f>H7/30*I7</f><v>450</v></c>',
                        )
                    archive.writestr(entry, payload)
        result, records, _ = build(buffer.getvalue(), Options())
    assert records[0].provenance["base_payment"].formula == "=H7/30*I7"
    assert result["records"][0]["fields"]["base_payment"] == "450"
    assert "H7/30" not in str(result)


def test_capacity_and_origin_rejection():
    import asyncio
    from app import main

    original = main.slots
    main.slots = asyncio.Semaphore(0)
    try:
        with TestClient(app) as client:
            assert client.post("/api/v1/analyze").status_code == 429
            assert (
                client.post(
                    "/api/v1/analyze", headers={"Origin": "https://untrusted.invalid"}
                ).status_code
                == 403
            )
    finally:
        main.slots = original


def test_verified_source_headers_are_accepted_at_fixed_coordinates():
    def apply_headers(book):
        for kind, headers in VERIFIED_HEADERS.items():
            for field, label in headers.items():
                column = PROFILES[kind][field][0]
                book[kind.upper()][f"{column}6"] = label

    result, _, _ = build(workbook(apply_headers), Options())
    assert not any(issue["code"] == "HEADER_MISMATCH" for issue in result["issues"])


@pytest.mark.parametrize(
    "part",
    [
        "xl/connections.xml",
        "xl/queryTables/query1.xml",
        "xl/macrosheets/sheet1.xml",
        "customUI/customUI.xml",
        "xl\\outside.xml",
        "C:payload.xml",
    ],
)
def test_active_parts_and_ambiguous_paths_are_rejected(part):
    data = workbook()
    output = BytesIO()
    with ZipFile(BytesIO(data)) as original, ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for entry in original.infolist():
            archive.writestr(entry, original.read(entry.filename))
        entry = ZipInfo("placeholder")
        entry.filename = part
        entry.orig_filename = part
        archive.writestr(entry, b"<root/>")
    with pytest.raises(ServiceError) as caught:
        security.inspect_package(output.getvalue())
    assert caught.value.status == 415


@pytest.mark.parametrize(
    "formula",
    [
        '=WEBSERVICE("https://example.invalid")',
        '=HYPERLINK("https://example.invalid","link")',
        "=cmd|' /C example'!A0",
        '=_xlfn.IMAGE("https://example.invalid")',
        '=RTD("server",,"topic")',
    ],
)
def test_active_formulas_are_rejected_before_parsing(formula):
    data = workbook(lambda book: setattr(book["PLANILLA"]["J7"], "value", formula))
    with pytest.raises(ServiceError) as caught:
        security.inspect_package(data)
    assert caught.value.code == "ACTIVE_FORMULA"


def test_cross_site_requests_without_origin_are_rejected():
    with TestClient(app) as client:
        response = client.post("/api/v1/analyze", headers={"Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 403


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "http://payroll.example",
        "https://payroll.example/path",
        "https://user:secret@payroll.example",
        "https://payroll.example#fragment",
    ],
)
def test_production_requires_explicit_https_origin(monkeypatch, origin):
    from app.config import validate_production_origin

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_ORIGIN", origin)
    with pytest.raises(RuntimeError):
        validate_production_origin()
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://payroll.example")
    validate_production_origin()
