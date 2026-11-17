# Chat 04 — G3 fictional PDF/XLSX/CSV format triage

**2026-11-17 · Priority 2 and G3 · independent synthetic fixture lane.**

`backend/app/synthetic_format_triage.py` composes existing fictional `synthetic_document_threat_preflight` and `private_adapter_registry` without creating another full bank/FBR parser. It requires an explicitly synthetic bounded buffer, a strict candidate profile (bank, IRIS income or wealth) and matching extension under `G3_FAKE_FORMAT_TRIAGE_ONLY=1` + `APP_DATA_MODE=synthetic`. PDF requires the artificial marker and structural active-content rejection; OOXML validates ZIP member allowlist/size/external references; CSV requires a hardcoded **fictional** marker/header and rejects dangerous formulas, active content, oversized/malformed content and unknown byte structure.

**Any clean-looking candidate is still quarantined** with `QUARANTINE_PENDING_G3`; no malware proof, bank layout acceptance, OCR, sandboxed actual document conversion, original-byte import, real account balance or official FBR filing is certified by a public test. Tests deliberately cover PDF actions, XLSX macro/XXE/path/links, CSV spreadsheet formula injection, mismatched or unidentified profiles and real-mode refusal.

Genuine source ingestion requires owner-approved private vault, isolated worker with pinned executable/resource/network controls, independent malware/document-layout sample certification, exact source-row reconciliation and G1/G2/G3 acceptance. No actual owner bank/FBR files or passwords were accessed.
