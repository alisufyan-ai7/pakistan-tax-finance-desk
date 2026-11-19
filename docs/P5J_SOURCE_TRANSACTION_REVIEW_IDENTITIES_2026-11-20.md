# P5J — source-bound transaction review identities (synthetic only)

20 November 2026. Owner requires a place to clarify uncertain transactions, with comments analyzed as contextual evidence and status kept pending until independent reconciliation. Parent [#218](https://github.com/alisufyan-ai7/pakistan-tax-finance-desk/issues/218).

## Implemented, not activated

`backend/app/private_transaction_review_subjects.py` is an unmounted deterministic source-row proof planner. It requires a true original source byte-hash HMAC, pinned owner/account/source HMACs, complete date interval, every row's ordered page+ordinal, debit/credit direction, exact running balances, gross debit/credit and printed closing. It fails closed if a row is duplicated, source/content version changes, evidence is missing, a statement is truncated, transaction totals conflict, or source ownership is uncertain. The resulting unique HMAC identities are tied to original byte proof + page/row + account/owner and therefore cannot be taken as arbitrary user-submitted IDs.

Every suggested target remains `NEEDS_OWNER_CONTEXT`, and no classification, transfer exclusion, financial posting, income/expense inference or note saving takes place. Synthetic tests only; no original account names, money, file bytes or owner passwords in GitHub.

## Next gate to genuine per-transaction comments

First independently certify source-format PDF/CSV/XLSX row parsers with isolated owner-private originals and a full authenticated encrypted document/transaction ledger. Bind stable row identities in the private DB with no duplicate or overlap, and expose targets from server-authorized imported sources only. After migration 0024 full encrypted off-device backup/disposable restore and exact MFA/CSRF/Origin/no-sensitive-log ingress, connect only actual owner-verified row HMACs to the existing encrypted append-only review comment service. Suggest classifications as hypotheses; only a separate independently reconciled and audited event may mark `RESOLVED_WITH_EVIDENCE`.

This code is deliberately not a live transaction UI, a bank statement importer, a financial values release or a substitute for the G1/G2/G3 acceptance gates.
