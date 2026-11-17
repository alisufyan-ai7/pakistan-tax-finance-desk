"""G3: public-repo-only synthetic bank/IRIS container triage.

This does NOT parse real bank/FBR records, approve an OCR engine, certify
formats or import original bytes. Even clean fixtures remain quarantined
pending independent private malware, sandbox and source-layout acceptance.
"""
from __future__ import annotations

import csv
from io import StringIO
import os
import re

from .private_adapter_registry import (
    GenuineFormatBlocked, inspect_candidate_evidence,
)
from .synthetic_document_threat_preflight import (
    SyntheticThreatBlocked, inspect_synthetic_pdf_threats,
    inspect_synthetic_ooxml_threats,
)

_CSV_MARK = b"PERSONAL_CFO_SYNTHETIC_BANK_CSV_V1\n"
_CSV_HEADER = ["date","description","debit","credit","balance","reference"]
_EXTS = {".csv", ".xlsx", ".pdf"}


class SyntheticFormatTriageBlocked(ValueError):
    """Unapproved or ambiguous file requires private review, never a guess."""


def triage_fake_document_container(
    *, raw: bytes, claimed_extension: str, candidate_key: str,
    document_kind: str, synthetic_fixture: bool,
) -> dict:
    """Cheap structural triage under a separate explicit synthetic flag.

    No user source values, balance amounts, row text or original bytes
    are returned; the accepted result is always still G3-quarantined.
    """
    if (os.getenv("APP_DATA_MODE") != "synthetic"
        or os.getenv("G3_FAKE_FORMAT_TRIAGE_ONLY") != "1"
        or synthetic_fixture is not True
        or type(raw) is not bytes or type(claimed_extension) is not str
        or claimed_extension not in _EXTS
        or not 20 <= len(raw) <= 512*1024):
        raise SyntheticFormatTriageBlocked("Real or ambiguous file triage unavailable")
    try:
        profile=inspect_candidate_evidence(
            key=candidate_key,kind=document_kind,extension=claimed_extension,
            synthetic_fixture=True,
        )
    except GenuineFormatBlocked:
        raise SyntheticFormatTriageBlocked("Unknown candidate format profile") from None
    kind=None
    try:
        if claimed_extension==".pdf":
            if (not raw.startswith(b"%PDF-")
                or b"PERSONAL_CFO_SYNTHETIC_FIXTURE" not in raw):
                raise SyntheticThreatBlocked("Only fictional PDF fixtures allowed")
            preflight=inspect_synthetic_pdf_threats(raw,synthetic_fixture=True)
            kind="synthetic_pdf_structural"
        elif claimed_extension==".xlsx":
            preflight=inspect_synthetic_ooxml_threats(raw,synthetic_fixture=True)
            kind="synthetic_xlsx_container"
        else:
            if (not raw.startswith(_CSV_MARK)
                or len(raw)>65536 or b"\x00" in raw or b"\r" in raw
                or b"\xef\xbb\xbf" in raw
                or any(x in raw.lower() for x in (
                    b"javascript:", b"file://", b"hyperlink(", b"cmd|"))):
                raise SyntheticThreatBlocked("Unsafe or unrecognized fictional CSV")
            decoded=raw[len(_CSV_MARK):].decode("utf-8","strict")
            rows=list(csv.reader(StringIO(decoded),strict=True))
            if (not 2 <= len(rows) <= 101 or rows[0] != _CSV_HEADER
                or any(len(row)!=6 for row in rows[1:])
                or any(not value or len(value)>180 or
                       value.lstrip().startswith(("=","+","@","\t"))
                       for row in rows[1:] for value in row)):
                raise SyntheticThreatBlocked("Unbounded, formula-like or malformed CSV")
            kind="synthetic_csv_structure"
            preflight={"basic_structural_preflight":True,
                       "private_malware_scan_passed":False}
    except (SyntheticThreatBlocked, UnicodeError, csv.Error, ValueError):
        raise SyntheticFormatTriageBlocked("Unsafe fictional document quarantined") from None
    return {
        "synthetic_only":True,
        "candidate_key":profile["candidate_key"],
        "candidate_kind":profile["document_kind"],
        "preflight_kind":kind,
        "basic_structure_checked":preflight["basic_structural_preflight"] is True,
        "independent_malware_scan_verified":False,
        "original_document_imported":False,
        "source_rows_parsed_for_finance":False,
        "real_bank_fbr_layout_certified":False,
        "g3_private_review_required":True,
        "quarantine_policy":"QUARANTINE_PENDING_G3",
        "actual_fbr_filing_verified":False,
        "real_data_authorized":False,
    }
