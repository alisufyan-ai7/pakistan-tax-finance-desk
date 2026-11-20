import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {
  safePeriod,periodContainsMonth,periodContainsDate,periodMonths,periodTitle,
  observedPeriods,sourcePeriodSummary,candidatePeriodEvidence,
} from "../finance-period.mjs";

const historical=(month,credit,debit,profit=0)=>({
  month,transaction_count:2,gross_bank_credits_minor:credit,
  gross_bank_debits_minor:debit,last_reported_balance_minor:43210,
  bank_labelled_profit_minor:profit,bank_labelled_profit_tax_minor:0,
});
const source=()=>({
  source_hmac:"a".repeat(64),source_name:"fictional.csv",
  statement_start:"2025-06-01",statement_end:"2026-07-02",
  months:[historical("2025-06",5000,1000),
    historical("2025-07",7000,2000,50),
    historical("2026-06",9000,3000,60),
    historical("2026-07",4000,1000)],
});
test("Pakistan Jul-Jun tax-year boundaries are exact, not calendar years",()=>{
  const p=safePeriod("tax-year","2025");
  assert.deepEqual(periodMonths(p),[
    "2025-07","2025-08","2025-09","2025-10","2025-11","2025-12",
    "2026-01","2026-02","2026-03","2026-04","2026-05","2026-06"]);
  assert.equal(periodContainsMonth("2025-06",p),false);
  assert.equal(periodContainsMonth("2025-07",p),true);
  assert.equal(periodContainsMonth("2026-06",p),true);
  assert.equal(periodContainsMonth("2026-07",p),false);
  assert.equal(periodTitle(p),"Pakistan tax year 2025–26");
});
test("calendar year, month, all-evidence and invalid selector semantics",()=>{
  const p=safePeriod("year","2026");
  assert.equal(periodContainsMonth("2025-12",p),false);
  assert.equal(periodContainsMonth("2026-01",p),true);
  assert.equal(periodContainsMonth("2026-12",p),true);
  assert.equal(periodContainsMonth("2027-01",p),false);
  assert.deepEqual(periodMonths(safePeriod("month","2026-02")),["2026-02"]);
  assert.equal(periodTitle(safePeriod("month","2026-02")),"February 2026");
  assert.equal(periodContainsDate("2026-02-29",p),true);
  assert.equal(periodContainsMonth("2026-13",p),false);
  assert.equal(safePeriod("tax-year","no"),null);
  assert.equal(safePeriod("month","2025-13"),null);
  assert.equal(periodContainsMonth("2026-01",safePeriod("all","all")),true);
  assert.deepEqual(periodMonths(safePeriod("all","all")),[]);
});
test("source dated observations remain within each individual source, never falsely totalled",()=>{
  const p=safePeriod("tax-year","2025");
  const results=sourcePeriodSummary([source()],p);
  assert.equal(results.length,1);
  assert.deepEqual(results[0].covered_months,["2025-07","2026-06"]);
  assert.equal(results[0].credits_minor,16000);
  assert.equal(results[0].debits_minor,5000);
  assert.equal(results[0].bank_profit_minor,110);
  assert.equal(results[0].last_observed_balance_minor,43210);
  const july=sourcePeriodSummary([source()],safePeriod("month","2026-07"));
  assert.equal(july[0].credits_minor,4000);
  assert.equal(sourcePeriodSummary([source()],safePeriod("month","2024-01")).length,0);
});
test("candidate partner evidence filtered by date and keeps incoming distinct from repayment",()=>{
  const groups=[{group_id:"synthetic-venture",rows:[
    {date:"2025-06-30",direction:"OUTBOUND",amount_minor:5000},
    {date:"2025-07-01",direction:"OUTBOUND",amount_minor:2000},
    {date:"2026-06-30",direction:"INBOUND",amount_minor:1000},
    {date:"2026-07-01",direction:"INBOUND",amount_minor:4000},
  ]}];
  const items=candidatePeriodEvidence(groups,safePeriod("tax-year","2025"));
  assert.equal(items.length,1);
  assert.equal(items[0].rows.length,2);
  assert.equal(items[0].outgoing_minor,2000);
  assert.equal(items[0].incoming_minor,1000);
  assert.equal(candidatePeriodEvidence(groups,safePeriod("month","2024-01")).length,0);
});
test("period choices emerge from observed source months and candidate dates, not guessed years",()=>{
  const periods=observedPeriods({reports:[source()],candidates:[
    {date:"2023-11-14"}],properties:[{sale_date:"2024-08-12"}]});
  assert.ok(periods.month.includes("2023-11"));
  assert.ok(periods.taxYear.includes("2023"));
  assert.ok(periods.taxYear.includes("2025"));
  assert.ok(periods.year.includes("2026"));
  assert.equal(periods.year.includes("2022"),false);
});
test("deployed app has one shared selector and no browser persistence, fake money, or additional VM",()=>{
  const read=n=>readFileSync(new URL("../"+n,import.meta.url),"utf8");
  const html=read("app.html"),js=read("app.mjs"),css=read("app.css"),docker=read("Dockerfile");
  for(const value of ["month","year","tax-year","all"])
    assert.ok(html.includes('value="'+value+'"'));
  for(const id of ["finance-period-mode","finance-period-value","home-financial-period-list",
    "account-period-list","investment-period-list","finance-period-status"])
    assert.ok(html.includes('id="'+id+'"'));
  assert.match(js,/renderFinancialPeriodEvidence/);
  assert.match(js,/resetFinancialPeriodEvidence/);
  assert.match(js,/periodContainsDate/);
  assert.ok(docker.includes("finance-period.mjs"));
  assert.ok(css.includes("min-height:44px"));
  for(const forbidden of ["localStorage","sessionStorage","innerHTML","console.log"])
    assert.ok(!js.includes(forbidden));
});
