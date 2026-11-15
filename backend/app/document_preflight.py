"""Conservative content-signature preflight for synthetic CSV/XLSX imports.

This is a bounded format/ZIP package safety check, NOT a malware scanner,
sandbox, authentic Pakistani bank adapter or permission to ingest real data.
Unknown or potentially active workbook parts fail closed.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
import stat
import zipfile
import xml.etree.ElementTree as ET

MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_ZIP_ENTRIES = 128
MAX_ZIP_UNCOMPRESSED = 32 * 1024 * 1024
MAX_ZIP_MEMBER = 16 * 1024 * 1024
MAX_RELATIONSHIP_BYTES = 256 * 1024


class PreflightError(ValueError):
    """Input is unsupported or unsafe for the strict synthetic tabular parser."""


def _csv(raw: bytes) -> None:
    if raw.startswith((b"%PDF-", b"PK\x03\x04", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", b"SQLite format 3")):
        raise PreflightError("Content signature does not match .csv")
    if b"\x00" in raw:
        raise PreflightError("Binary data is not a supported CSV")
    if any(byte < 32 and byte not in (9, 10, 13) for byte in raw):
        raise PreflightError("CSV contains unsupported control bytes")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        raise PreflightError("CSV must be UTF-8") from None
    head = text.lstrip().lower()
    if head.startswith(("<!doctype", "<html", "<?xml", "<script", "{", "[")):
        raise PreflightError("HTML/XML/JSON error or download stub is not a CSV statement")


def _zip_name(info: zipfile.ZipInfo, seen: set[str]) -> str:
    name = info.filename
    if not name or "\x00" in name or "\\" in name or name.startswith("/") or ":" in name:
        raise PreflightError("Unsafe XLSX ZIP member path")
    parts = PurePosixPath(name).parts
    if not parts or any(part in ("..", ".") for part in name.split("/")):
        raise PreflightError("Unsafe XLSX ZIP member path")
    normalized = name.casefold()
    if normalized in seen:
        raise PreflightError("Duplicate XLSX ZIP member")
    seen.add(normalized)
    mode = (info.external_attr >> 16) & 0o170000
    if mode == stat.S_IFLNK:
        raise PreflightError("Links inside an XLSX are unsupported")
    if info.flag_bits & 0x1:
        raise PreflightError("Encrypted XLSX ZIP entries are unsupported")
    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise PreflightError("Unsupported XLSX ZIP compression")
    if info.file_size > MAX_ZIP_MEMBER:
        raise PreflightError("XLSX member exceeds decompression limit")
    if info.file_size > 1024 * 1024 and info.file_size > 400 * max(info.compress_size, 1):
        raise PreflightError("Suspicious XLSX decompression ratio")
    low = normalized
    disallowed = (
        "xl/externallinks/", "xl/embeddings/", "xl/activex/",
        "xl/macrosheets/", "xl/querytables/", "xl/media/",
        "customxml/", "_xmlsignatures/", "xl/webextensions/",
    )
    if any(low.startswith(prefix) for prefix in disallowed) or any(
        marker in low for marker in ("vbaproject", "vbasignature", "xl/connections.xml")
    ):
        raise PreflightError("Active, linked or embedded workbook parts are unsupported")
    return name


def _xlsx(raw: bytes) -> None:
    if not raw.startswith(b"PK\x03\x04"):
        raise PreflightError("Content signature does not match .xlsx")
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > MAX_ZIP_ENTRIES:
                raise PreflightError("XLSX has too many or no ZIP members")
            seen: set[str] = set()
            names = {}
            total = 0
            for info in entries:
                name = _zip_name(info, seen)
                total += info.file_size
                if total > MAX_ZIP_UNCOMPRESSED:
                    raise PreflightError("XLSX uncompressed size limit exceeded")
                names[name.casefold()] = info
            if "[content_types].xml" not in names or "xl/workbook.xml" not in names:
                raise PreflightError("ZIP is not an OOXML spreadsheet workbook")
            if not any(name.startswith("xl/worksheets/") and name.endswith(".xml") for name in names):
                raise PreflightError("XLSX does not contain a worksheet")
            for name, info in names.items():
                if name.endswith(".rels"):
                    if info.file_size > MAX_RELATIONSHIP_BYTES:
                        raise PreflightError("XLSX relationship manifest too large")
                    xml = archive.read(info)
                    if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                        raise PreflightError("XLSX DTD/entity references are unsupported")
                    try:
                        node = ET.fromstring(xml)
                    except ET.ParseError:
                        raise PreflightError("Malformed XLSX relationship manifest") from None
                    if any(element.attrib.get("TargetMode", "").casefold() == "external" for element in node.iter()):
                        raise PreflightError("External workbook relationships are unsupported")
            content_type = archive.read(names["[content_types].xml"])
            if b"<!DOCTYPE" in content_type.upper() or b"<!ENTITY" in content_type.upper():
                raise PreflightError("XLSX DTD/entity references are unsupported")
            if b"macroenabled" in content_type.lower() or b"vbaproject" in content_type.lower():
                raise PreflightError("Macro-enabled workbook is unsupported")
    except PreflightError:
        raise
    except (zipfile.BadZipFile, EOFError, OSError, RuntimeError, ValueError, ET.ParseError):
        raise PreflightError("Malformed or unsupported XLSX package") from None


def preflight_tabular(raw: bytes, extension: str) -> None:
    """Validate bounded actual content before XLSX extraction or CSV interpretation.

    Synthetic-only; does not decrypt PDF or XLS, retain original bytes, or imply
    production readiness. Raise PreflightError on all unsupported formats.
    """
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise PreflightError("Empty or oversized statement (4 MiB limit)")
    if extension == ".csv":
        _csv(raw)
    elif extension == ".xlsx":
        _xlsx(raw)
    else:
        raise PreflightError("Only synthetic UTF-8 CSV and OOXML XLSX supported; .xls is not accepted")
