"""G3: strict synthetic PDF and OOXML active-content/size threat preflight.

This is a deliberately conservative *structural* admission check used for
fictional test fixtures. A byte scan and ZIP inspection are NOT malware
detection, production isolation, safe XML parser approval, or bank/FBR format
certification. Never feed real files, passwords, owners or bank data here.
"""
from __future__ import annotations

import io
import os
from pathlib import PurePosixPath
import re
import zipfile

MAX_PDF_BYTES = 512 * 1024
MAX_OOXML_BYTES = 512 * 1024
MAX_OOXML_UNPACKED = 2 * 1024 * 1024
MAX_ZIP_ENTRIES = 48
MAX_ZIP_RATIO = 30


class SyntheticThreatBlocked(ValueError):
    """Untrusted, active or excessive synthetic fixture rejected without echoing content."""


def _synthetic(raw: bytes, synthetic_fixture: bool, minimum: int, limit: int) -> None:
    if (os.getenv("APP_DATA_MODE","synthetic") != "synthetic"
        or synthetic_fixture is not True or type(raw) is not bytes
        or not minimum <= len(raw) <= limit):
        raise SyntheticThreatBlocked("Unapproved synthetic document")


def inspect_synthetic_pdf_threats(raw: bytes, *, synthetic_fixture: bool) -> dict:
    """Conservative preflight: known active names and obfuscation are quarantined.

    A real PDF parser may hide actions in compressed/obfuscated object streams.
    This check cannot attest safety: actual sandbox + private acceptance remain.
    """
    _synthetic(raw,synthetic_fixture,60,MAX_PDF_BYTES)
    if not raw.startswith(b"%PDF-"):
        raise SyntheticThreatBlocked("Unsupported synthetic PDF structure")
    # Active content in object syntax. False positives quarantine deliberately.
    hazardous = (
        b"/javascript",b"/js",b"/openaction",b"/aa",b"/launch",
        b"/embeddedfile",b"/embeddedfiles",b"/richmedia",b"/xfa",
        b"/acroform",b"/submitform",b"/importdata",b"/uri",b"/filespec",
    )
    lower = raw.lower()
    if any(re.search(re.escape(token) + rb"(?![a-z0-9])", lower)
           for token in hazardous):
        raise SyntheticThreatBlocked("Potentially active PDF document quarantined")
    if b"/#" in lower or b"%00" in lower:
        raise SyntheticThreatBlocked("Obfuscated synthetic PDF names quarantined")
    return {
        "synthetic_only": True, "basic_structural_preflight": True,
        "known_active_content_markers_absent": True,
        "private_malware_scan_passed": False,
        "genuine_source_certified": False,
        "import_performed": False,
    }


_ALLOWED_XML = re.compile(
    r"^(?:\[Content_Types\]\.xml|_rels/\.rels|docProps/(?:app|core)\.xml|"
    r"xl/(?:workbook|styles|sharedStrings)\.xml|"
    r"xl/_rels/workbook\.xml\.rels|"
    r"xl/worksheets/sheet[0-9]{1,2}\.xml)$",
    re.I,
)
_FORBIDDEN_NAMES = (
    "vbaproject", "externallinks", "embeddings", "activex",
    "connections.xml", "querytables", "drawings", "printersettings",
    "pivotcache", "metadata.xml",
)
_FORBIDDEN_XML = (
    b"<!doctype", b"<!entity", b"targetmode=\"external\"",
    b"targetmode='external'", b"webservice(", b"hyperlink(",
    b"dde(", b"cmd|", b"powershell", b"file://",
    b"<externallinks", b"<externallink",
)


def inspect_synthetic_ooxml_threats(raw: bytes, *, synthetic_fixture: bool) -> dict:
    """No extract-to-filesystem. Reject unknown ZIP members, bombs and XML actions.

    An authentic spreadsheet is not accepted: these checks recognize only a
    tiny, explicitly fictional workbook structure and emit counts, not data.
    """
    _synthetic(raw,synthetic_fixture,50,MAX_OOXML_BYTES)
    if not raw.startswith(b"PK\x03\x04"):
        raise SyntheticThreatBlocked("Unsupported synthetic workbook")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            files = archive.infolist()
            if not 2 <= len(files) <= MAX_ZIP_ENTRIES:
                raise SyntheticThreatBlocked("Unbounded synthetic workbook archive")
            names = set()
            unpacked = 0
            for member in files:
                name = member.filename
                path = PurePosixPath(name)
                if (not isinstance(name,str) or not name or len(name)>150
                    or path.is_absolute() or "\\" in name or
                    any(part in (".","..") for part in name.split("/"))):
                    raise SyntheticThreatBlocked("Unsafe workbook archive member")
                lowered = name.lower()
                if (lowered in names
                    or any(keyword in lowered for keyword in _FORBIDDEN_NAMES)
                    or _ALLOWED_XML.fullmatch(name) is None or member.is_dir()):
                    raise SyntheticThreatBlocked("Unsupported workbook member quarantined")
                names.add(lowered)
                if member.flag_bits & 1 or member.file_size <= 0:
                    raise SyntheticThreatBlocked("Encrypted/empty workbook member refused")
                unpacked += member.file_size
                if (unpacked > MAX_OOXML_UNPACKED
                    or member.file_size > MAX_ZIP_RATIO * max(1,member.compress_size)):
                    raise SyntheticThreatBlocked("Workbook resource amplification refused")
                payload = archive.read(member)
                if len(payload) != member.file_size:
                    raise SyntheticThreatBlocked("Incomplete compressed workbook")
                low = payload.lower()
                if any(marker in low for marker in _FORBIDDEN_XML):
                    raise SyntheticThreatBlocked("Active/XML external workbook content refused")
            if "[content_types].xml" not in names or "xl/workbook.xml" not in names:
                raise SyntheticThreatBlocked("Required workbook structure missing")
        return {
            "synthetic_only": True, "zip_members_scanned": len(files),
            "basic_structural_preflight": True,
            "external_links_allowed": False,
            "macros_allowed": False,
            "private_malware_scan_passed": False,
            "real_excel_or_bank_layout_certified": False,
            "import_performed": False,
        }
    except SyntheticThreatBlocked:
        raise
    except Exception:
        raise SyntheticThreatBlocked("Synthetic workbook cannot be safely preflighted") from None
