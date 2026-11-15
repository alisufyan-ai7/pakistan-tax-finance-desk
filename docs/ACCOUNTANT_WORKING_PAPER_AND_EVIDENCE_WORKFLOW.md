# Accountant working papers, secure source intake and review workflow

**Status:** generalized engineering requirements (not implemented). **Reviewed:** 2026-11-16. **Privacy:** This file contains NO private document bytes, owner/account identifiers, confidential amounts, document passwords, screenshots, accountant names, transaction details or contact information. It records only reusable product-design lessons.

## Why the personal CFO needs more than transaction import

Financial evidence arrives in several forms, and **source reliability and approval stage differ**:

1. An official **FBR IRIS acknowledgement** can evidence submission of a particular Tax Year return, while a corresponding income/wealth filing and its revisions have distinct provenance.
2. A multi-sheet **accountant working workbook** is a mutable, provisional calculation. Its salary, business, withholding, bank, investments, cash and wealth computations may be incomplete. It is **not filed** until an independently verified filing/acknowledgement supports that state. Do not treat provisional differences as errors or overwrite a prior filed return.
3. **Bank statements** include distinct PDF layouts, content-protected PDFs, varying date formats, multiple accounts and periods, running balance/carry-forward rows, and occasional unreadable or incorrectly named exports. The PDF file extension does not establish that content is a statement.
4. **Correspondence and screenshots** identify unanswered accounting questions or requests for documents. They are not independently verified transaction evidence. Where an image shows an audio message, do not claim its content is known unless the audio is supplied and reviewed.

## Canonical source model

| Concept | Required fields / invariant |
| --- | --- |
| Source document | Encrypted original, checksum/HMAC, owner/entity scope, source type, issue period, upload time, parser profile/version, source status and access log |
| Protected PDF access | Ephemeral **document-opening** password input, never password persistence or logging, no reuse of bank-login/OTP/PIN credentials, quarantined conversion, clear retry/error status |
| Bank statement coverage | Account/entity, statement start/end, opening/closing balances, running-balance proofs, extracted transaction dates and page/row citations, account×period gaps, overlap/duplicate flags |
| Accountant workbook | Immutable uploaded version, workbook hash, author/source type, DRAFT/UNDER_REVIEW/APPROVED states, sheet name/cell references, formula and cached values, external/broken links, source line/item evidence, change log |
| Filed FBR return | Tax Year, filing date and acknowledgement evidence, original/revised version and supersession chain, separately tracked income return and wealth statement; no silent changes |
| Financial exception | Exact source lines, category hypothesis, amount *confidential*, debit/credit semantic sign, potential counterparty, evidence request, review owner/status, linked reply and evidence, certainty and disposition |
| Correspondence | Private message snapshot or other authorized original, source/time, evidence request, response and resolution; **not a replacement** for bank or IRIS evidence |

## Mandatory review logic

- **Bank import:** detect content type (not filename), reject empty/invalid exports safely, support bank-layout adapters by *version*, no opaque guesses, multi-statement coverage, same bank transfers showing on both sides, foreign/PKR account segregation, mark no-data spans **UNKNOWN**, not zero.
- **Cash-flow categories:** distinguish inter-account movements, salary/business/rent/profit/dividends, investments, gifts, zakat/donations, bank cash, borrowed/lent principal and markup, property acquisition, tax paid or withheld, third-party movements and unexplained credits. Do not label a credit taxable income solely because it is an incoming bank entry.
- **Wealth continuity:** compare filed previous-year closing wealth against next-year opening *draft* wealth as a **question** only until revisions, asset ownership, valuation and non-bank evidence are collected. Never present a draft mismatch as a filed error.
- **Spreadsheet review:** check source-sheet dependencies, formula integrity, missing references, inconsistent signs/rounding, wealth schedules, and claimed/unclaimed withholding candidates; keep the actual Excel-native values and third-party parser/recalculation artifacts separate. No automatic advice based on unverified cached formula results.
- **Owner/accountant collaboration:** queue evidence-backed review questions; statuses `OPEN → DOCUMENT_REQUESTED → OWNER_RESPONSE_PENDING → EVIDENCE_RECEIVED → REVIEWED → ACCOUNTANT_ACCEPTED/REJECTED` with dated reason and audit history. The owner decides whether to approve a draft. No auto communication with the accountant without owner consent.
- **Legal/timing:** deadline, owner-confirmed extension and actual FBR submission are distinct attributes with different evidence and trust levels. Do not infer statutory legality or a missed filing solely from message timestamps. No automatic tax filing or credits.

## Privacy, model safety and scalability

- **Current implementation remains synthetic-only** until [G1–G3](DELIVERY_GATES_AND_RELEASE_READINESS.md) pass: protected active finance model, private MFA/backup/restore, and validated genuine bank/FBR layout adapters. Do not put authentic examples in public GitHub or CI.
- Tests use **fictional fixtures** that reproduce *format classes* without copied real transaction rows, IDs, names, numeric values, screenshots, confidential bank account information or document passwords.
- Version parser contracts, tax-year FBR forms, evidence workflows and accountant review states so future household, business, professional adviser and SaaS usage can extend the **same modular monolith** without leaking one owner/entity's evidence.
- A successor chat can learn **these requirements from GitHub** but cannot automatically read private files in another chat. Do not create a public GitHub handoff containing specific amounts or private attachments to compensate.
- Work remains owner-independent for fixture and schema development. Genuine owner files become acceptance evidence only inside an **approved private intake**.

## Next acceptance and linkage

Tracked in [Issue #30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30); related [Issue #29 genuine bank/FBR adapters](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29), [Issue #21 operational confidentiality](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/21), and [Issue #5 legally reviewed tax and historical return reconciliation](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/5).

**Acceptance:** Synthetic password-protected PDF fixtures, malformed/wrong extension cases, bank row/page running-balance parity, duplicate transfers, account×FY gaps, draft Excel formulas and versioning, filed-revision vs draft evidence, cross-year wealth continuity, third-party movement explanation queue, and explicit owner approval boundaries. No case-specific data and no claim that authentic adapters are ready.

**Current article- or sample-derived ideas do not mean their corresponding code has been implemented.**
