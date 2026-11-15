# M2k — Encrypted investment/property/gold/vehicle/liability snapshots

**Scope:** single-user, synthetic-only **declared** asset records, covering equities, mutual funds, crypto, gold, real estate, vehicles, fixed deposits, other assets and separately tracked other liabilities. Nothing is automatically verified by a broker, land registry, bank, exchange or FBR.

## Privacy by construction

- The database `asset_snapshots` table stores only random row IDs, an AES-256-GCM encrypted JSON payload, and a technical row-creation timestamp. The encrypted payload includes **all personally meaningful fields**: position identifier, kind, labels, as-of date, acquired-on date, quantity, cost basis, declared value, ownership, currency and evidence basis.
- A dedicated existing field-envelope domain `asset_snapshots.payload_json` provides authenticated encryption and external keyring rotation. Offline synthetic-only key rotation scans the new table; no raw user records in GitHub.
- Values are reconstructed in memory for the single-user app; this is **not** a scalable searchable encrypted database design. There is no automated ingestion of sensitive real records and no claim of full encryption for the older bank ledger.

## Behavior

- `POST /api/finance/assets/snapshots`: an explicitly marked synthetic owner declaration; new position or new as-of snapshot. Same position/date identical replay is idempotent; conflicting same-day valuation returns 409 and requires a future audited amendment workflow. Original snapshots are immutable.
- `GET /api/finance/assets/position?as_of=YYYY-MM-DD`: latest declared snapshot for each position on/before that date. Missing valuation in any included position yields `null` for declared aggregated components. Liability is reported separately; investment purchase is **not** investment profit and source statements do not automatically create holdings.
- Full net worth, market-verified position value, realized capital gain, FBR wealth reconciliation, tax due, and legal deduction remain **null/unverified**. It is improper to infer gains from two owner-declared values without acquisition/corporate actions/trade fees, and improper to count bank money twice as an investment.

## Follow-ups

Evidence-linked valuation method and custodian integration; historical cost basis/units lots, gifts/inheritance/purchased dates, PKR FX when relevant; asset-position-specific reversals/corrections; comprehensive property and bullion proof; protection for **existing** legacy ledger amounts/dates/metadata; full secure private ingestion/MFA/offsite recovery. Genuine bank and filed tax documents are NOT required for this synthetic engineering work.