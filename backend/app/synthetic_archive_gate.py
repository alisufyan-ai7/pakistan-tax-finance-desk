"""B4/F1: bounded ZIP central-directory preflight for fabricated source archives.

It NEVER extracts, opens or imports a member, never decrypts, never handles
actual owner data or claims supported bank formats. All input test fixtures
must be explicitly synthetic. A private isolated conversion worker is STILL
required before genuine ZIP/XLSX/PDF parsing can be authorized.
"""
from __future__ import annotations

from collections import Counter
from io import BytesIO
from pathlib import PurePosixPath
import os
import stat
from zipfile import ZipFile, BadZipFile


class SyntheticArchiveBlocked(ValueError):
    """An archive is unsafe or outside the synthetic-only source contract."""


MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_FILES = 30
MAX_TOTAL_UNCOMPRESSED = 24 * 1024 * 1024
MAX_PER_FILE = 8 * 1024 * 1024
MAX_RATIO = 100
ALLOWED = {".pdf", ".xlsx", ".csv"}


def inspect_synthetic_zip(raw: bytes, *, fabricated_fixture: bool) -> dict:
    """Read just archive metadata, reject ambiguous or dangerous structures."""
    if os.getenv("APP_DATA_MODE", "synthetic") != "synthetic":
        raise SyntheticArchiveBlocked("Genuine financial archive mode is not authorized")
    if fabricated_fixture is not True or type(raw) is not bytes:
        raise SyntheticArchiveBlocked("Only immutable fabricated ZIP test input is supported")
    if not 1 <= len(raw) <= MAX_ARCHIVE_BYTES:
        raise SyntheticArchiveBlocked("Archive exceeds synthetic preview limits")
    try:
        with ZipFile(BytesIO(raw), "r") as archive:
            entries = archive.infolist()
            if not 1 <= len(entries) <= MAX_FILES:
                raise SyntheticArchiveBlocked("Unsupported archive member count")
            known = set()
            sizes = 0
            counts = Counter()
            for member in entries:
                name = member.filename
                if (
                    not isinstance(name, str) or not name or len(name) > 180
                    or "\x00" in name or "\\" in name
                    or name.startswith(("/", "~"))
                ):
                    raise SyntheticArchiveBlocked("Invalid source filename")
                path = PurePosixPath(name)
                if path.is_absolute() or len(path.parts) > 3 or any(
                    segment in (".", "..") or segment.strip() != segment
                    for segment in name.split("/")
                ):
                    raise SyntheticArchiveBlocked("Unsafe source archive path")
                if any(ord(c) < 32 for c in name):
                    raise SyntheticArchiveBlocked("Control character in source path")
                is_directory = member.is_dir()
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise SyntheticArchiveBlocked("Archive symlinks are prohibited")
                if member.flag_bits & 1:
                    raise SyntheticArchiveBlocked("Encrypted source files require private review")
                if is_directory:
                    continue
                key = name.casefold()
                if key in known:
                    raise SyntheticArchiveBlocked("Ambiguous duplicate source path")
                known.add(key)
                ext = path.suffix.lower()
                if ext not in ALLOWED:
                    raise SyntheticArchiveBlocked("Unsupported source extension")
                if not 1 <= member.file_size <= MAX_PER_FILE:
                    raise SyntheticArchiveBlocked("Invalid source member size")
                if member.compress_size <= 0 or member.file_size > member.compress_size * MAX_RATIO:
                    raise SyntheticArchiveBlocked("Suspicious ZIP decompression ratio")
                sizes += member.file_size
                if sizes > MAX_TOTAL_UNCOMPRESSED:
                    raise SyntheticArchiveBlocked("Total inflated size exceeds limits")
                counts[ext] += 1
            if not known:
                raise SyntheticArchiveBlocked("Empty archive has no supported sources")
            return {
                "synthetic_only": True,
                "preflight_only": True,
                "extraction_performed": False,
                "import_performed": False,
                "real_data_authorized": False,
                "source_count": len(known),
                "extension_counts": dict(sorted(counts.items())),
                "source_names_exported": False,
                "source_bytes_exported": False,
                "bank_layout_certified": False,
                "tax_due_minor": None,
            }
    except SyntheticArchiveBlocked:
        raise
    except (BadZipFile, ValueError, UnicodeError, OSError):
        raise SyntheticArchiveBlocked("Invalid synthetic source ZIP container") from None
