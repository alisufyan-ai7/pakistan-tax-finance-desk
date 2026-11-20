import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {safePeriod} from "../finance-period.mjs";
import {repeatingBankCandidates} from "../finance-patterns.mjs";

const read=n=>readFileSync(new URL("../"+n,import.meta.url),"utf8");
const ha="a".repeat(64),hb="b".repeat(64);
const row=(date,amount=5500,description="Fictional monthly standing payment",
  source_hmac=ha,direction="OUTBOUND",ordinal=1)=>({
  date,amount_minor:amount,description,source_hmac,direction,ordinal,
});
const source=(source_hmac,name,rows)=>({
  source_hmac,source_name:name,transactions:{rows}
});
const past=[
  row("2025-07-11"),row("2025-08-12"),row("2025-09-13"),
  row("2025-09-20",3000,"One-off transfer"),
];
test("three distinct statement months give only a candidate, never a due bill",()=>{
  const out=repeatingBankCandidates([source(ha,"Fictional bank.csv",past)],
    safePeriod("tax-year","2025"));
  assert.equal(out.length,1);
  assert.equal(out[0].observed_month_count,3);
  assert.equal(out[0].amount_minor,5500);
  assert.equal(out[0].source_hmac,ha);
  assert.equal(out[0].first_observed,"2025-07-11");
  assert.equal(out[0].last_observed,"2025-09-13");
  assert.equal(out[0].purpose_verified,false);
  assert.equal(out[0].upcoming_due_date,null);
  assert.equal(out[0].observed_in_selected_period,true);
});
test("never combine different bank sources or opposite money directions",()=>{
  const data=[
    source(ha,"Fictional A.csv",[
      row("2025-07-11"),row("2025-08-11"),
    ]),
    source(hb,"Fictional B.csv",[
      row("2025-09-11",5500,"Fictional monthly standing payment",hb),
      row("2025-10-11",5500,"Fictional monthly standing payment",hb),
    ]),
    source(ha,"Fictional A.csv",[
      row("2025-09-11",5500,"Fictional monthly standing payment",ha,"INBOUND"),
    ]),
  ];
  const out=repeatingBankCandidates(data,safePeriod("all","all"));
  assert.equal(out.length,0);
});
test("require repeated months, not repeated transactions in the same month",()=>{
  const data=[source(ha,"Fictional.csv",[
    row("2026-01-01"),row("2026-01-10"),row("2026-01-18"),
    row("2026-02-01"),
  ])];
  assert.equal(repeatingBankCandidates(data,safePeriod("year","2026")).length,0);
});
test("selected period contains real matching row but detection can use earlier history",()=>{
  const src=source(ha,"Fictional.csv",[
    row("2025-11-01"),row("2025-12-01"),row("2026-01-01"),
  ]);
  assert.equal(repeatingBankCandidates([src],safePeriod("month","2026-01")).length,1);
  assert.equal(repeatingBankCandidates([src],safePeriod("month","2026-03")).length,0);
  assert.equal(repeatingBankCandidates([src],safePeriod("tax-year","2024")).length,0);
});
test("malformed event and empty source never create bills or fabricated zeros",()=>{
  const bad=source(ha,"Fictional.csv",[
    {...row("2026-01-11"),amount_minor:-100},
    {...row("2026-02-11"),source_hmac:hb},
    {...row("2026-03-11"),direction:"UNKNOWN"},
  ]);
  assert.deepEqual(repeatingBankCandidates([bad],safePeriod("all","all")),[]);
  assert.deepEqual(repeatingBankCandidates([],safePeriod("all","all")),[]);
  assert.deepEqual(repeatingBankCandidates([bad],safePeriod("month","2026-01"),{minimumMonths:0}),[]);
});
test("new recurring section and one-tap review are read only, accessible and source-labelled",()=>{
  const html=read("app.html"),js=read("app.mjs"),docker=read("Dockerfile"),
    css=read("owner-premium.css");
  for(const id of ["spending-recurring-heading","spending-recurring-list",
    "spending-recurring-coverage","home-review-open-all"])
    assert.ok(html.includes('id="'+id+'"'),id);
  assert.ok(html.includes('value="REVIEW_REQUIRED"'));
  assert.ok(html.includes("A repeated bank debit is not necessarily a household bill"));
  assert.ok(js.includes("repeatingBankCandidates("));
  assert.ok(js.includes("View matching bank entries"));
  assert.ok(js.includes('byId("transaction-source-filter").value=item.source_hmac'));
  assert.ok(js.includes('byId("home-review-open-all").addEventListener("click"'));
  assert.ok(js.includes('byId("transaction-category-filter").value="REVIEW_REQUIRED"'));
  assert.ok(docker.includes("finance-patterns.mjs"));
  assert.ok(css.includes(".recurring-candidate-list"));
  for(const forbidden of ["localStorage","sessionStorage","innerHTML","console.log"])
    assert.ok(!js.includes(forbidden),forbidden);
});
