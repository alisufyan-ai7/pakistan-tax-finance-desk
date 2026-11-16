# G3 parallel workstream — synthetic source adapter capability contracts

**Scope:** Owner-independent code only, public GitHub synthetic fixtures, no real bank/FBR uploads, no network/cloud access. Related [G3 issue #29](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/29).

`backend/app/source_contracts.py` provides a **version-pinned, explicitly selected** 6-entry source adapter manifest and narrow source-preflight inspection. Three fictitious CSV bank headers (normalized, synthetic split and synthetic DR/CR), a marker-gated synthetic bank PDF and two marker-gated synthetic IRIS PDF previews. Existing parsers/preflights are reused and their limitations preserved.

Security boundaries: explicit `synthetic_fixture=True` and `APP_DATA_MODE=synthetic`; exact adapter identity+kind+extension matching; no auto-detection or claimed real-bank endorsement; unknown files, web/download stubs and wrong formats reject. No importing, persistent records, FBR totals, tax due or presumed FILED status. Even if an IRIS fixture contains a status label, official acknowledgement is **not** verified. CSV inspection does **not** certify running balances until the caller independently provides a valid opening/closing balance and invokes normalization/reconciliation.

Tests cover all registered capabilities, strict CSV header contracts, binary/html masquerades, unsupported layouts, declared-kind mismatch, alternate formats and real-mode refusal. This unit is independent of G1-c data migration and G2 remote MFA/deployment. **G3 remains BLOCKED** for real input: per-Pakistan-bank format acceptance, isolated PDF/legacy XLS conversion and OCR, encrypted originals, actual file provenance and private source evidence remain required after G1/G2 security acceptance.

This workstream may run in parallel with G1-c and accountant diagnostics on independent files/PRs; only integrate after exact PR-head CI. No additional Docker, VPS, Vercel or Railway infrastructure is authorized or needed.
