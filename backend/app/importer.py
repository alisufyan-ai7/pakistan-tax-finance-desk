"""Conservative synthetic CSV/XLSX parser, exact paisa arithmetic and balance verification."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO, StringIO
import csv
import re
from openpyxl import load_workbook

PARSER_VERSION = "normalized-1"
MAX_BYTES = 4 * 1024 * 1024
MAX_ROWS = 5000
VALID_FORMATS = {"%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"}
HEADERS = ("date", "description", "debit", "credit", "balance", "reference")

class ImportErrorDetail(ValueError):
    pass

@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    posted_on: date
    description: str
    debit_minor: int
    credit_minor: int
    balance_minor: int | None
    reference: str | None

def parse_money(raw: object, *, optional: bool = False) -> int | None:
    if raw is None or str(raw).strip() == "":
        if optional:
            return None
        return 0
    if isinstance(raw, bool):
        raise ImportErrorDetail("Invalid monetary value")
    value = str(raw).strip()
    if value.startswith("="):
        raise ImportErrorDetail("Spreadsheet formula values are not accepted")
    if "," in value and not re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d{1,2})?", value):
        raise ImportErrorDetail("Invalid comma grouping in amount")
    try:
        amount = Decimal(value.replace(",", ""))
    except InvalidOperation:
        raise ImportErrorDetail("Invalid monetary amount") from None
    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        raise ImportErrorDetail("Amounts must be finite with at most two decimals")
    minor = int(amount * 100)
    if abs(minor) > 10**14:
        raise ImportErrorDetail("Amount exceeds supported range")
    return minor

def rows_from_upload(content: bytes, extension: str):
    if not content or len(content) > MAX_BYTES:
        raise ImportErrorDetail("Empty file or file exceeds 4 MiB limit")
    if extension == ".csv":
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ImportErrorDetail("CSV must be UTF-8; export it as UTF-8 CSV") from None
        reader = csv.DictReader(StringIO(decoded, newline=""))
        if not reader.fieldnames:
            raise ImportErrorDetail("CSV header missing")
        headers = [str(x or "").strip().lower() for x in reader.fieldnames]
        if len(set(headers)) != len(headers):
            raise ImportErrorDetail("CSV contains duplicate column names")
        for number, row in enumerate(reader, 2):
            if number > MAX_ROWS + 1:
                raise ImportErrorDetail("File exceeds 5000 transaction rows")
            if None in row:
                raise ImportErrorDetail(f"Malformed CSV at row {number}")
            yield number, {k.strip().lower(): v for k, v in row.items()}
    elif extension == ".xlsx":
        if not content.startswith(b"PK"):
            raise ImportErrorDetail("Not a valid .xlsx workbook")
        try:
            book = load_workbook(BytesIO(content), read_only=True, data_only=False)
            if len(book.sheetnames) != 1:
                raise ImportErrorDetail("Exactly one worksheet is supported")
            sheet = book.active
            iterator = sheet.iter_rows(values_only=True)
            raw_headers = next(iterator, None)
            if raw_headers is None:
                raise ImportErrorDetail("Spreadsheet header missing")
            headers = [str(h or "").strip().lower() for h in raw_headers]
            if len(headers) != len(set(headers)):
                raise ImportErrorDetail("Spreadsheet has duplicate column names")
            for number, values in enumerate(iterator, 2):
                if number > MAX_ROWS + 1:
                    raise ImportErrorDetail("File exceeds 5000 transaction rows")
                if len(values) > len(headers) and any(x is not None for x in values[len(headers):]):
                    raise ImportErrorDetail(f"Unexpected columns at row {number}")
                yield number, dict(zip(headers, values))
        except ImportErrorDetail:
            raise
        except Exception:
            raise ImportErrorDetail("Unable to safely read .xlsx; use normalized CSV") from None
        finally:
            if "book" in locals():
                book.close()
    else:
        raise ImportErrorDetail("Only normalized CSV and XLSX are supported; PDF adapters are pending")

def parse_statement(content: bytes, extension: str, date_format: str, opening_balance: str | None):
    if date_format not in VALID_FORMATS:
        raise ImportErrorDetail("Choose an explicit recognized date format")
    parsed = []
    for row_number, cells in rows_from_upload(content, extension):
        if not {"date", "description", "debit", "credit"}.issubset(cells):
            raise ImportErrorDetail("Required columns: date, description, debit, credit")
        if all(v is None or str(v).strip() == "" for v in cells.values()):
            continue
        raw_date = cells["date"]
        try:
            posted = raw_date.date() if isinstance(raw_date, datetime) else raw_date if isinstance(raw_date, date) else datetime.strptime(str(raw_date).strip(), date_format).date()
        except (ValueError, TypeError):
            raise ImportErrorDetail(f"Invalid date at row {row_number}; choose correct date format") from None
        description = str(cells["description"] or "").strip()
        if not description or len(description) > 500 or description.startswith("="):
            raise ImportErrorDetail(f"Invalid description at row {row_number}")
        debit = parse_money(cells["debit"])
        credit = parse_money(cells["credit"])
        balance = parse_money(cells.get("balance"), optional=True)
        reference = str(cells.get("reference") or "").strip() or None
        if reference and (len(reference) > 120 or reference.startswith("=")):
            raise ImportErrorDetail(f"Invalid reference at row {row_number}")
        if debit < 0 or credit < 0 or (bool(debit) == bool(credit)):
            raise ImportErrorDetail(f"Exactly one nonzero debit or credit is required at row {row_number}")
        if parsed and posted < parsed[-1].posted_on:
            raise ImportErrorDetail("Transactions must be in ascending posting-date order")
        parsed.append(ParsedRow(row_number, posted, description, debit, credit, balance, reference))
    if not parsed:
        raise ImportErrorDetail("No valid transactions found")
    opening = parse_money(opening_balance, optional=True)
    complete_balances = all(p.balance_minor is not None for p in parsed)
    if opening is not None and parsed[0].balance_minor is None:
        raise ImportErrorDetail("Opening balance requires a balance column")
    prior = opening
    checks = 0
    for row in parsed:
        if prior is not None and row.balance_minor is not None:
            expected = prior + row.credit_minor - row.debit_minor
            if expected != row.balance_minor:
                raise ImportErrorDetail(f"Running balance mismatch at row {row.row_number}")
            checks += 1
        prior = row.balance_minor
    status = "opening_and_running_verified" if opening is not None and complete_balances else "internal_running_verified" if complete_balances and len(parsed) > 1 else "not_fully_verifiable"
    warnings = []
    if not complete_balances:
        warnings.append("Some balances absent; complete reconciliation is not possible")
    if opening is None:
        warnings.append("Opening balance not provided; initial balance not independently verified")
    if any(p.balance_minor is None and not p.reference for p in parsed):
        warnings.append("Rows lacking reference and balance cannot be confidently deduplicated across differently exported files")
    return parsed, status, warnings

def fingerprint(account_id: str, row: ParsedRow, document_hash: str, occurrence: int) -> str:
    """Cross-document matching only when reference or running balance supplies an anchor."""
    normal = " ".join(row.description.lower().split())
    if row.reference:
        # Reference survives exports with/without an explicit running balance.
        identifying = f"ref|{account_id}|{row.posted_on}|{row.debit_minor}|{row.credit_minor}|{normal}|{row.reference.lower()}|{occurrence}"
    elif row.balance_minor is not None:
        identifying = f"balance|{account_id}|{row.posted_on}|{row.debit_minor}|{row.credit_minor}|{normal}|{row.balance_minor}|{occurrence}"
    else:
        identifying = f"document|{account_id}|{document_hash}|{row.row_number}"
    return sha256(identifying.encode("utf-8")).hexdigest()

def fingerprint_base(row: ParsedRow) -> str:
    normal = " ".join(row.description.lower().split())
    anchor = "ref:" + row.reference.lower() if row.reference else "balance:" + str(row.balance_minor)
    return f"{row.posted_on}|{row.debit_minor}|{row.credit_minor}|{normal}|{anchor}"
