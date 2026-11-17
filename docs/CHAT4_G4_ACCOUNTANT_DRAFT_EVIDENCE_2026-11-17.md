# Chat 04 — G4 accountant DRAFT versus FBR filed-evidence lineage

**2026-11-17 · Priority 5 · independent synthetic pure rules lane.**

`backend/app/fake_accountant_evidence_lineage.py` tracks only invented HMAC source identities, Tax Year, immutable revision/supersession sequence, source kind and draft/review/filing-claim flags. It refuses duplicate/conflicting evidence IDs, revision gaps, cross-TY input, forged FBR acknowledgments not linked to the corresponding fictional filing, and a mere accountant workbook marked `FILING_CLAIMED`. Even an apparent filed receipt remains **unverified** until an independently corroborated official FBR IRIS acknowledgment/filing revision chain in a private approved environment.

Missing statement coverage, IRIS original/wealth sources, ambiguous accountant working papers and acknowledgment need owner/accountant follow-up; actual income, tax due, balances and wealth remain `None`, not zero. There is no FBR login, tax filing service, bank importer or genuine owner data read by this code.

The owner's FY25–26 accountant worksheet is an **unfinished working DRAFT**, not a final return. This source-safe generic model encodes that distinction, without publishing amounts or source details. Final financial reconciliation and lawful tax recommendations require G1 encrypted owner/account×Tax-Year authority, G2 security, G3 certified sources, official FBR evidence, and accountant/owner approval.
