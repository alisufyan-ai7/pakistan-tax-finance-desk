# E3 — source-gated owner-action briefing contract (synthetic only)

Owner priority: make the **first phone screen immediately useful**: What is happening this month? Is spending increasing? What recurring bills need to be paid? Which investments are held, when do contractual return dates or maturity fall, and what follow-ups need attention?

**New pure module:** `backend/app/owner_action_brief.py`. No SQL reads or public API route. Every input must be an explicitly fabricated fixture, `APP_DATA_MODE=synthetic`, legally scoped, bounded and validated. It returns compact domain status data:

- **Calendar-month spending and change:** only show amount/change when all records for current month to date and the equivalent prior-month window have complete source coverage, reviewed categories and excluded own transfers. Incomplete months remain `null`—not zero. A prior period of zero produces unknown growth; March 31 vs February 28 is clamped and must be labeled as such.
- **Recurring bills:** schedule candidate isn't a payable obligation; owner-marked payment isn't source-matched. Urgent/overdue status is not an actual instruction to pay or an accusation of missed payment. No automatic actions.
- **Investments:** principal visible only if source-attested in the fictional fixture; dates may be shown as expected, never guaranteed. Fixed-contract quote is distinguishable from realized profit, variable returns have no fabricated amount, taxes/withholding remain unknown, no trading.
- **Follow-ups:** open/due-soon/overdue case counts with no reminders or messages actually sent.

**Security and scope:** cross-owner input, duplicate IDs, malformed periods, unsupported dates, unexpected fields and real mode blocked. No bank data, accountant messages, account IDs, passwords, or real evidence in this public repository. Test cases use explicitly invented records.

**Important:** this is not yet a source-connected or secure authenticated owner endpoint. It is a vetted contract awaiting G1 encrypted authoritative financial data, G2 private owner MFA and scoped accounts, G3 verified bank/FBR adapters and audited user action workflows. Real financial totals and returns must remain blank until sources meet those gates.

## Boundary corrections — 2026-11-16

- A March 31 vs February 28 month-to-date comparison now returns `comparison_window_clamped=true`, **growth null** and `NOT_COMPARABLE_MONTH_LENGTH` instead of a misleading percent computed from unequal calendar-day coverage. Source-known individual expense amounts may still display separately.
- No bill can be marked source-matched paid using an evidence posting date **after** `as_of`. A matched debit with an unconfirmed recurring schedule retains `SCHEDULE_REVIEW`; a bank debit alone does not certify the bill schedule or obligation.
- Once an expected investment return date passes, status becomes `EXPECTED_DATE_PASSED_NEEDS_SOURCE_RECEIPT`. This triggers a follow-up, not an assumption that profit was received or a tax amount is due.

All checks remain synthetic-only. No actual owner data can be imported or paid through this module.
