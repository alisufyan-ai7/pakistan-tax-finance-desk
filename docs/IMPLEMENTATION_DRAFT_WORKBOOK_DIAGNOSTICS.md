# Accountant workstream — read-only synthetic DRAFT workbook formula diagnostics

**Scope:** Owner-independent, synthetic XLSX only; [accountant workflow Issue #30](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/30), [v2 plan](PRODUCT_PLAN_ACCOUNTANT_READY_CFO_2026-11-16.md). No accountant's private workbook or conversation is used in code/tests/CI.

`backend/app/workbook_diagnostics.py` checks an in-memory XLSX after strict OOXML content-signature preflight; uses two read-only openpyxl views (`data_only=False` formulas and `data_only=True` cached values). Bounded at 4MiB input via preflight, 16 sheets and 12,000 declared cells per sheet. It reports structural sheet-index/cell-coordinate issue codes (`BROKEN_REFERENCE`, `MISSING_CACHED_RESULT`, `CACHE_PRESENT_UNVERIFIED`) with counts, never source values/formulas, sheet titles or personal financial numbers.

**Critical:** Excel cached results can be stale even when present. The diagnostic does NOT calculate formulas, authenticate financial figures, prove complete source coverage, verify an FBR filing, modify workbook, or change stored records. A claimed FILLED/FILED/FINALIZED status is refused: source remains **DRAFT**, verified filing requires separate official acknowledgement. External formulas, malformed packages and uncontrolled workbook dimensions block.

Tests create entirely fictitious in-memory workbooks and inject a fake XML cached value to assert the cache remains untrusted. No real bank/FBR records, no passwords and no network/cloud. This is a parallel structural review primitive, NOT production document sandboxing or permission to accept actual accountant files. The owner-facing review queue, source-to-cell traceability, independent formula recalc and G1–G3 private ingestion gates remain pending.

No Docker or new remote provider. Verify exact-head hosted CI before merging.
