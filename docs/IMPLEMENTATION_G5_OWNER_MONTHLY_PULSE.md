# G5 owner-first monthly glance — visual and data contract (synthetic)

**Owner's requested primary experience (Nov 16 2026):** immediately understandable mobile home screen saying how this month is going, whether expenses are rising, upcoming recurring bills, investments and approximate dates of expected payments, and follow-up questions. It should be expressive without hiding uncertainty or guessing tax/savings.

This PR changes only the existing public synthetic dashboard demo model and its UI/CSS (independent from PWA PR #64 and backend source-gated brief PR #65):

- **Mobile top:** dark green contrast-led month pulse, big plain-language heading, four metric tiles (example spending, bills to check, sample invested capital and follow-ups). Layout changes to two-per-row then stacked as needed on a phone. No horizontal scroll.
- **Bills to check:** due dates/amounts and payment-unconfirmed vs schedule-candidate labels, never automatically claiming unpaid bank bills. Detailed examples available from Transactions.
- **Investments & next returns:** principal examples, fixed-term quoted amount and expected return date vs variable yield/date unknown. No guaranteed profit, received return, investment advice, tax due or real market value. Detailed examples available from Planning.
- **Expense comparison:** readable category bars and 19% hypothetical change clearly labeled **example only**; actual observed growth is `null` because no genuine complete comparable bank data exists.
- **Follow-ups:** sample missing statement, bill confirmation and accountant draft review. No reminders/notifications have actually been scheduled.
- **Older evidence/ledger charts remain accessible** below the prioritized snapshot and clearly identified as a **separate fictional ledger dataset**.

Every displayed number is from `DEMO.monthPulse`, a static **fictional November 16, 2026 snapshot**, not today's live bank data. It is deliberately NOT reconciled with the separate existing synthetic ledger sample; the UI explicitly calls them separate illustrations. Model helpers validate reconciled category sums, unique IDs, dates, variable vs fixed quoted returns, and refuse any assertion that actual owner sources are verified. Fiscal-year selector still controls the older sample ledger, not the fixed example snapshot.

Next owner-private acceptance: G1 authoritative encrypted data, G2 user MFA/session boundaries, G3 certified bank/broker/IRIS evidence; then connect `owner_action_brief_v1` from backend PR #65 to authenticated private API with explicit unknown/missing source semantics. Do not connect public demo to genuine owner money, bills or investments.
