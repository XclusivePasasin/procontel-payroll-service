"""Patch only receipt worksheet parts; retain source XML, formula caches and resources."""

from copy import deepcopy
from io import BytesIO
import posixpath
from typing import cast
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from defusedxml.ElementTree import fromstring, iterparse

from app.models import ServiceError

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"
Namespaces = list[tuple[str, str]]


def read_xml(payload: bytes) -> tuple[ET.Element, Namespaces]:
    namespaces: Namespaces = []
    with BytesIO(payload) as stream:
        for _, binding in iterparse(stream, events=("start-ns",)):
            prefix, uri = cast(tuple[str | None, str], binding)
            pair = (prefix or "", uri)
            if pair not in namespaces:
                namespaces.append(pair)
    return fromstring(payload), namespaces


def xml_bytes(root: ET.Element, namespaces: Namespaces) -> bytes:
    for prefix, uri in namespaces:
        if not prefix.startswith("ns") or not prefix[2:].isdigit():
            ET.register_namespace(prefix, uri)
    if root.tag.startswith("{"):
        ET.register_namespace("", root.tag[1:].split("}", 1)[0])
    payload = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    # Excel extension prefixes may appear only inside mc:Ignorable attribute values.
    for prefix, uri in namespaces:
        declaration = f"xmlns{':' + prefix if prefix else ''}"
        if f"{declaration}=".encode() not in payload:
            root.set(declaration, uri)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def target_path(target: str) -> str:
    return posixpath.normpath(
        target.lstrip("/") if target.startswith("/") else posixpath.join("xl", target)
    )


def relationships(root: ET.Element) -> dict[str, str]:
    return {node.attrib["Id"]: target_path(node.attrib["Target"]) for node in root}


def merge_styles(original: bytes, generated: bytes) -> tuple[bytes, dict[int, int]]:
    root, namespaces = read_xml(original)
    incoming, _ = read_xml(generated)
    order = [
        "numFmts",
        "fonts",
        "fills",
        "borders",
        "cellStyleXfs",
        "cellXfs",
        "cellStyles",
        "dxfs",
        "tableStyles",
        "colors",
        "extLst",
    ]

    def section(name: str) -> ET.Element:
        node = root.find(f"{{{MAIN}}}{name}")
        if node is None:
            node = ET.Element(f"{{{MAIN}}}{name}")
            index = next(
                (
                    i
                    for i, child in enumerate(root)
                    if child.tag.rsplit("}", 1)[-1] in order
                    and order.index(child.tag.rsplit("}", 1)[-1]) > order.index(name)
                ),
                len(root),
            )
            root.insert(index, node)
        return node

    number_ids: dict[int, int] = {}
    source_numbers = incoming.find(f"{{{MAIN}}}numFmts")
    if source_numbers is not None and len(source_numbers):
        destination = section("numFmts")
        next_id = max([163] + [int(node.attrib["numFmtId"]) for node in destination]) + 1
        for node in source_numbers:
            copied = deepcopy(node)
            number_ids[int(node.attrib["numFmtId"])] = next_id
            copied.set("numFmtId", str(next_id))
            destination.append(copied)
            next_id += 1
        destination.set("count", str(len(destination)))
    offsets: dict[str, int] = {}
    for name in ("fonts", "fills", "borders"):
        destination = section(name)
        offsets[name] = len(destination)
        source = incoming.find(f"{{{MAIN}}}{name}")
        if source is not None:
            destination.extend(deepcopy(list(source)))
        destination.set("count", str(len(destination)))
    if root.find(f"{{{MAIN}}}cellStyleXfs") is None:
        source = incoming.find(f"{{{MAIN}}}cellStyleXfs")
        if source is not None:
            destination = section("cellStyleXfs")
            destination.extend(deepcopy(list(source)))
            destination.set("count", str(len(destination)))
    destination = section("cellXfs")
    source = incoming.find(f"{{{MAIN}}}cellXfs")
    style_ids: dict[int, int] = {}
    if source is None:
        raise ServiceError(500, "EXPORT_STYLE_ERROR", "No se pudo preparar el formato del Excel.")
    for index, node in enumerate(source):
        copied = deepcopy(node)
        for attribute, name in (("fontId", "fonts"), ("fillId", "fills"), ("borderId", "borders")):
            copied.set(attribute, str(int(node.attrib.get(attribute, "0")) + offsets[name]))
        number = int(node.attrib.get("numFmtId", "0"))
        copied.set("numFmtId", str(number_ids.get(number, number)))
        copied.set("xfId", "0")
        style_ids[index] = len(destination)
        destination.append(copied)
    destination.set("count", str(len(destination)))
    return xml_bytes(root, namespaces), style_ids


def patch_receipt_sheets(
    original_data: bytes, generated_data: bytes, receipt_sources: dict[str, str] | None = None
) -> bytes:
    with BytesIO(original_data) as source_buffer, BytesIO(generated_data) as generated_buffer:
        with ZipFile(source_buffer) as source, ZipFile(generated_buffer) as generated:
            replacements: dict[str, bytes] = {}
            removed: set[str] = set()
            workbook, wb_ns = read_xml(source.read("xl/workbook.xml"))
            rels, rel_ns = read_xml(source.read("xl/_rels/workbook.xml.rels"))
            content, content_ns = read_xml(source.read("[Content_Types].xml"))
            new_workbook, _ = read_xml(generated.read("xl/workbook.xml"))
            new_rels, _ = read_xml(generated.read("xl/_rels/workbook.xml.rels"))
            sheets = workbook.find(f"{{{MAIN}}}sheets")
            new_sheets = new_workbook.find(f"{{{MAIN}}}sheets")
            if sheets is None or new_sheets is None:
                raise ServiceError(
                    422, "UNKNOWN_STRUCTURE", "No se pudo localizar las hojas del libro."
                )
            original_order = [node.attrib["sheetId"] for node in sheets]
            receipt_sources = receipt_sources or {
                "BOLETA PLANILLA": "PLANILLA",
                "BOLETA HONORARIOS": "HONORARIOS",
            }
            paths = relationships(rels)
            new_paths = relationships(new_rels)
            existing = {node.attrib["name"].casefold(): node for node in sheets}
            used_ids = {node.attrib["Id"] for node in rels}
            all_paths = set(source.namelist())
            rels_changed = False
            content_changed = False

            def add_relationship(path: str, kind: str) -> str:
                nonlocal rels_changed
                index = 1
                while f"rId{index}" in used_ids:
                    index += 1
                identifier = f"rId{index}"
                used_ids.add(identifier)
                ET.SubElement(
                    rels,
                    f"{{{PACKAGE_REL}}}Relationship",
                    {"Id": identifier, "Type": f"{REL}/{kind}", "Target": "/" + path},
                )
                paths[identifier] = path
                rels_changed = True
                return identifier

            def add_content_type(path: str, content_type: str) -> None:
                nonlocal content_changed
                if not any(node.attrib.get("PartName") == "/" + path for node in content):
                    ET.SubElement(
                        content,
                        f"{{{CONTENT}}}Override",
                        {"PartName": "/" + path, "ContentType": content_type},
                    )
                    content_changed = True

            styles_rel = next(
                (node for node in rels if node.attrib.get("Type", "").endswith("/styles")), None
            )
            styles_path = (
                paths[styles_rel.attrib["Id"]] if styles_rel is not None else "xl/styles.xml"
            )
            if styles_path in all_paths:
                replacements[styles_path], style_ids = merge_styles(
                    source.read(styles_path), generated.read("xl/styles.xml")
                )
            else:
                replacements[styles_path] = generated.read("xl/styles.xml")
                style_root, _ = read_xml(replacements[styles_path])
                style_xfs = style_root.find(f"{{{MAIN}}}cellXfs")
                style_ids = {i: i for i in range(len(style_xfs) if style_xfs is not None else 0)}
                if styles_rel is None:
                    add_relationship(styles_path, "styles")
                add_content_type(
                    styles_path,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml",
                )
            touched: dict[str, int] = {}
            for new_sheet in new_sheets:
                name = new_sheet.attrib["name"]
                if name not in receipt_sources:
                    raise ServiceError(
                        500, "EXPORT_SHEET_ERROR", "No se pudo preparar las hojas de boletas."
                    )
                if name.casefold() in existing:
                    destination = existing[name.casefold()]
                    path = paths[destination.attrib[f"{{{REL}}}id"]]
                else:
                    number = 1
                    while f"xl/worksheets/sheet{number}.xml" in all_paths:
                        number += 1
                    path = f"xl/worksheets/sheet{number}.xml"
                    all_paths.add(path)
                    sheet_id = max([0] + [int(node.attrib["sheetId"]) for node in sheets]) + 1
                    destination = ET.SubElement(
                        sheets,
                        f"{{{MAIN}}}sheet",
                        {
                            "name": name,
                            "sheetId": str(sheet_id),
                            f"{{{REL}}}id": add_relationship(path, "worksheet"),
                        },
                    )
                    add_content_type(
                        path,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
                    )
                touched[name] = int(destination.attrib["sheetId"])
                source_name = receipt_sources[name]
                source_node = next(
                    (
                        node
                        for node in sheets
                        if node.attrib["name"].casefold() == source_name.casefold()
                    ),
                    None,
                )
                if source_node is None:
                    raise ServiceError(
                        422,
                        "EXPORT_SOURCE_MISSING",
                        "No se encontró la hoja fuente de las boletas.",
                    )
                sheets.remove(destination)
                sheets.insert(list(sheets).index(source_node) + 1, destination)
                xml, sheet_ns = read_xml(
                    generated.read(new_paths[new_sheet.attrib[f"{{{REL}}}id"]])
                )
                for cell in xml.iter(f"{{{MAIN}}}c"):
                    cell.set("s", str(style_ids[int(cell.attrib.get("s", "0"))]))
                replacements[path] = xml_bytes(xml, sheet_ns)

            # Inserting tabs shifts local name scopes and view indices, not stable sheetIds.
            new_indices = {node.attrib["sheetId"]: i for i, node in enumerate(sheets)}
            index_map = {i: new_indices[identifier] for i, identifier in enumerate(original_order)}
            for scoped in workbook.iter():
                if "localSheetId" in scoped.attrib:
                    previous = int(scoped.attrib["localSheetId"])
                    if previous in index_map:
                        scoped.set("localSheetId", str(index_map[previous]))
                if scoped.tag == f"{{{MAIN}}}workbookView":
                    for attribute in ("activeTab", "firstSheet"):
                        if (
                            attribute in scoped.attrib
                            and int(scoped.attrib[attribute]) in index_map
                        ):
                            scoped.set(attribute, str(index_map[int(scoped.attrib[attribute])]))
            names = workbook.find(f"{{{MAIN}}}definedNames")
            if names is None:
                names = ET.Element(f"{{{MAIN}}}definedNames")
                next_node = next(
                    (
                        i
                        for i, node in enumerate(workbook)
                        if node.tag in {f"{{{MAIN}}}calcPr", f"{{{MAIN}}}extLst"}
                    ),
                    len(workbook),
                )
                workbook.insert(next_node, names)
            for generated_name in new_workbook.findall(
                f"{{{MAIN}}}definedNames/{{{MAIN}}}definedName"
            ):
                if generated_name.attrib.get("name") != "_xlnm.Print_Area":
                    continue
                generated_index = int(generated_name.attrib["localSheetId"])
                sheet_name = list(new_sheets)[generated_index].attrib["name"]
                original_index = next(
                    i
                    for i, node in enumerate(sheets)
                    if node.attrib["name"].casefold() == sheet_name.casefold()
                )
                for old in list(names):
                    if (
                        old.attrib.get("localSheetId") == str(original_index)
                        and old.attrib.get("name") == "_xlnm.Print_Area"
                    ):
                        names.remove(old)
                copied = deepcopy(generated_name)
                copied.set("localSheetId", str(original_index))
                names.append(copied)

            chain_rel = next(
                (node for node in rels if node.attrib.get("Type", "").endswith("/calcChain")), None
            )
            if chain_rel is not None:
                chain_path = paths[chain_rel.attrib["Id"]]
                chain, chain_ns = read_xml(source.read(chain_path))
                current_sheet: str | None = None
                last_kept: str | None = None
                changed = False
                for cell in list(chain):
                    current_sheet = cell.attrib.get("i", current_sheet)
                    if current_sheet in {str(value) for value in touched.values()}:
                        chain.remove(cell)
                        changed = True
                    else:
                        if (
                            current_sheet is not None
                            and current_sheet != last_kept
                            and "i" not in cell.attrib
                        ):
                            cell.set("i", current_sheet)
                        last_kept = current_sheet
                if changed:
                    if len(chain):
                        replacements[chain_path] = xml_bytes(chain, chain_ns)
                    else:
                        removed.add(chain_path)
                        rels.remove(chain_rel)
                        rels_changed = True
                        for node in list(content):
                            if node.attrib.get("PartName") == "/" + chain_path:
                                content.remove(node)
                                content_changed = True
            replacements["xl/workbook.xml"] = xml_bytes(workbook, wb_ns)
            if rels_changed:
                replacements["xl/_rels/workbook.xml.rels"] = xml_bytes(rels, rel_ns)
            if content_changed:
                replacements["[Content_Types].xml"] = xml_bytes(content, content_ns)
            with BytesIO() as output:
                with ZipFile(output, "w", ZIP_DEFLATED) as archive:
                    archive.comment = source.comment
                    for entry in source.infolist():
                        if entry.filename not in removed:
                            archive.writestr(
                                deepcopy(entry),
                                replacements.pop(entry.filename, source.read(entry.filename)),
                            )
                    for path, payload in replacements.items():
                        archive.writestr(path, payload)
                return output.getvalue()
