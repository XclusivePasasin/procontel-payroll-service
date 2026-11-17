from io import BytesIO
from pathlib import PurePosixPath
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_multipart.multipart import MultipartCallbacks
from zipfile import ZipFile

from defusedxml.ElementTree import fromstring
from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header
from starlette.requests import Request

from app.config import LIMITS
from app.models import ServiceError


async def receive(request: Request) -> tuple[bytes, str]:
    """Incremental multipart parsing without Starlette's disk-spooling UploadFile."""
    media, params = parse_options_header(request.headers.get("content-type", ""))
    boundary = params.get(b"boundary")
    if media != b"multipart/form-data" or not boundary or len(boundary) > 200:
        raise ServiceError(400, "INVALID_MULTIPART", "Se requiere un archivo y opciones multipart.")
    parts: dict[str, bytes] = {}
    headers: dict[bytes, bytes] = {}
    current = bytearray()
    header_name = bytearray()
    header_value = bytearray()
    part_name = ""
    finished = False
    header_bytes = 0

    def begin() -> None:
        nonlocal part_name, header_bytes
        headers.clear()
        current.clear()
        part_name = ""
        header_bytes = 0

    def header_field(data: bytes, start: int, end: int) -> None:
        nonlocal header_bytes
        header_bytes += end - start
        if header_bytes > 8192:
            raise ServiceError(413, "UPLOAD_LIMIT", "Cabeceras demasiado grandes.")
        header_name.extend(data[start:end])

    def header_data(data: bytes, start: int, end: int) -> None:
        nonlocal header_bytes
        header_bytes += end - start
        if header_bytes > 8192:
            raise ServiceError(413, "UPLOAD_LIMIT", "Cabeceras demasiado grandes.")
        header_value.extend(data[start:end])

    def header_end() -> None:
        headers[bytes(header_name).lower()] = bytes(header_value)
        header_name.clear()
        header_value.clear()

    def headers_finished() -> None:
        nonlocal part_name
        _, disposition = parse_options_header(headers.get(b"content-disposition", b""))
        part_name = disposition.get(b"name", b"").decode("ascii", errors="replace")
        if part_name not in {"file", "options"} or part_name in parts:
            raise ServiceError(
                400, "INVALID_MULTIPART", "Campos multipart desconocidos o repetidos."
            )
        if part_name == "file":
            filename = disposition.get(b"filename", b"").lower()
            if not filename.endswith(b".xlsx"):
                raise ServiceError(415, "UNSUPPORTED_FORMAT", "Carga un archivo .xlsx sin macros.")

    def part_data(data: bytes, start: int, end: int) -> None:
        limit = LIMITS.upload if part_name == "file" else 4 * 1024 * 1024
        if len(current) + end - start > limit:
            raise ServiceError(413, "UPLOAD_LIMIT", "La carga excede el límite permitido.")
        current.extend(data[start:end])

    def part_end() -> None:
        parts[part_name] = bytes(current)
        current.clear()

    def finish() -> None:
        nonlocal finished
        finished = True

    callbacks: MultipartCallbacks = {
        "on_part_begin": begin,
        "on_header_field": header_field,
        "on_header_value": header_data,
        "on_header_end": header_end,
        "on_headers_finished": headers_finished,
        "on_part_data": part_data,
        "on_part_end": part_end,
        "on_end": finish,
    }
    parser = MultipartParser(boundary, callbacks)
    total = 0
    try:
        async for chunk in request.stream():
            total += len(chunk)
            if total > LIMITS.upload + 4 * 1024 * 1024 + 16384:
                raise ServiceError(413, "UPLOAD_LIMIT", "La carga excede el límite permitido.")
            parser.write(chunk)
        parser.finalize()
        if not finished or set(parts) != {"file", "options"}:
            raise ServiceError(400, "INVALID_MULTIPART", "La carga está incompleta.")
        return parts["file"], parts["options"].decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise ServiceError(400, "INVALID_MULTIPART", "No se pudo leer la carga.") from exc
    finally:
        current.clear()
        parts.clear()


def inspect_package(data: bytes) -> None:
    buffer = BytesIO(data)
    try:
        with ZipFile(buffer) as archive:
            entries = archive.infolist()
            names = [e.filename for e in entries]
            if len(entries) > LIMITS.entries or len(names) != len(set(names)):
                raise ServiceError(413, "ZIP_LIMIT", "Paquete excesivo o con entradas duplicadas.")
            required = {"[Content_Types].xml", "xl/workbook.xml", "_rels/.rels"}
            if not required.issubset(names):
                raise ServiceError(415, "INVALID_OOXML", "No es un libro Excel OOXML válido.")
            total = 0
            cells = 0
            for entry in entries:
                path = PurePosixPath(entry.filename)
                name = entry.filename.lower()
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in entry.orig_filename
                    or ":" in entry.orig_filename
                    or "\x00" in entry.orig_filename
                    or entry.flag_bits & 1
                ):
                    raise ServiceError(415, "UNSAFE_PACKAGE", "Paquete cifrado o no permitido.")
                if any(
                    s in name
                    for s in (
                        "vbaproject",
                        "vbadata",
                        "embeddings/",
                        "activex/",
                        "externallinks/",
                        "macrosheets/",
                        "dialogsheets/",
                        "querytables/",
                        "connections.xml",
                        "webextensions/",
                        "customui/",
                    )
                ):
                    raise ServiceError(
                        415, "ACTIVE_CONTENT", "Elimina macros, objetos y enlaces externos."
                    )
                if entry.file_size > LIMITS.expanded or total + entry.file_size > LIMITS.expanded:
                    raise ServiceError(413, "ZIP_LIMIT", "El contenido expandido supera el límite.")
                payload = bytearray()
                with archive.open(entry) as stream:
                    while chunk := stream.read(65536):
                        total += len(chunk)
                        if total > LIMITS.expanded:
                            raise ServiceError(
                                413, "ZIP_LIMIT", "El contenido expandido supera el límite."
                            )
                        if name.endswith((".xml", ".rels")):
                            if len(payload) + len(chunk) > LIMITS.xml:
                                raise ServiceError(
                                    413, "XML_LIMIT", "Un XML supera el límite permitido."
                                )
                            payload.extend(chunk)
                if not payload:
                    continue
                root = fromstring(bytes(payload))
                for node in root.iter():
                    tag = node.tag.rsplit("}", 1)[-1]
                    if (
                        tag == "Relationship"
                        and node.attrib.get("TargetMode", "").lower() == "external"
                    ):
                        raise ServiceError(
                            415, "EXTERNAL_RELATIONSHIP", "Elimina los enlaces externos del libro."
                        )
                    if tag == "Override" and any(
                        content in node.attrib.get("ContentType", "").lower()
                        for content in ("macroenabled", "macrosheet", "activex", "oleobject")
                    ):
                        raise ServiceError(
                            415, "ACTIVE_CONTENT", "No se admiten libros con macros."
                        )
                    if tag == "row" and int(node.attrib.get("r", "0")) > LIMITS.rows:
                        raise ServiceError(413, "ROW_LIMIT", "El libro declara demasiadas filas.")
                    if tag == "c":
                        cells += 1
                        if cells > LIMITS.cells:
                            raise ServiceError(
                                413, "CELL_LIMIT", "El libro contiene demasiadas celdas."
                            )
                    if tag in {"t", "f"} and len(node.text or "") > 2000:
                        raise ServiceError(
                            413, "TEXT_LIMIT", "El libro contiene textos demasiado extensos."
                        )
                    if tag == "f":
                        formula = node.text or ""
                        # Excel may execute these after download even though the server never does.
                        if "|" in formula or re.search(
                            r"\b(?:WEBSERVICE|RTD|HYPERLINK|IMAGE|CALL|REGISTER\.ID|EXEC)\s*\(",
                            formula,
                            flags=re.IGNORECASE,
                        ):
                            raise ServiceError(
                                415,
                                "ACTIVE_FORMULA",
                                "Elimina fórmulas que ejecutan acciones o acceden a recursos externos.",
                            )
                    if tag == "dimension":
                        ref = node.attrib.get("ref", "A1").split(":")[-1]
                        match = re.fullmatch(r"([A-Z]+)(\d+)", ref)
                        if not match or int(match[2]) > LIMITS.rows or len(match[1]) > 2:
                            raise ServiceError(
                                413, "DIMENSION_LIMIT", "Dimensiones del libro no permitidas."
                            )
    except ServiceError:
        raise
    except Exception as exc:
        raise ServiceError(
            400, "UNREADABLE_FILE", "El libro está dañado o no es compatible."
        ) from exc
    finally:
        buffer.close()
