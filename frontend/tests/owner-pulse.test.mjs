import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {DEMO,formatPKR,monthPulseSummary} from "../demo-data.mjs";

const source=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");

test("month pulse displays only a clearly fictional scenario, never verified actual expenses",()=>{
 const p=monthPulseSummary();
 assert.equal(p.asOf,"2026-11-16");
 assert.equal(p.monthLabel,"November 2026");
 assert.equal(p.exampleCurrentExpenseMinor,24800000);
 assert.equal(p.examplePriorExpenseMinor,20900000);
 assert.equal(p.exampleGrowthPct,19);
 assert.equal(p.verifiedCurrentExpenseMinor,null);
 assert.equal(p.verifiedExpenseGrowthPct,null);
 assert.equal(p.coverageComplete,false);
 assert.equal(p.sourceStatus,"DEMO_ONLY_NOT_CONNECTED_TO_OWNER");
 assert.equal(p.taxesAndActualReturnsReady,false);
 assert.match(formatPKR(p.exampleCurrentExpenseMinor),/248,000/);
});

test("bill status is a follow-up, never an assertion that an actual invoice is unpaid",()=>{
 const p=monthPulseSummary();
 assert.equal(p.billReviewCount,2);
 assert.equal(p.dueBy,"2026-11-23");
 assert.equal(p.bills.find(x=>x.id==="sample-rent").needsChecking,false);
 assert.ok(p.bills.some(x=>x.state==="SCHEDULE_CANDIDATE"&&x.amountVerified===false));
 assert.ok(p.bills.every(x=>x.paymentConfirmed===false));
 assert.equal(p.bills.filter(x=>x.needsChecking).length,2);
});

test("investment return quotes are not guaranteed, realized or taxable amounts",()=>{
 const p=monthPulseSummary();
 assert.equal(p.investments.length,3);
 assert.equal(p.exampleInvestedPrincipalMinor,865000000);
 assert.equal(p.verifiedInvestedPrincipalMinor,null);
 assert.ok(p.investments.every(x=>x.principalVerified===false && x.returnGuaranteed===false));
 assert.ok(p.investments.every(x=>x.actualReturnMinor===null && x.withholdingTaxMinor===null));
 const variable=p.investments.find(x=>x.quoteKind==="VARIABLE_UNKNOWN");
 assert.equal(variable.quotedReturnMinor,null);
 assert.equal(variable.nextReturnOn,null);
 const fixed=p.investments.find(x=>x.id==="sample-term");
 assert.equal(fixed.nextReturnOn,"2026-12-20");
 assert.equal(fixed.quotedReturnMinor,12500000);
});

test("inconsistent scenarios and falsely complete evidence fail closed",()=>{
 const data=structuredClone(DEMO.monthPulse);
 data.expenses.categories[0].currentMinor+=100;
 assert.throws(()=>monthPulseSummary(data),RangeError);
 data.expenses.categories[0].currentMinor-=100;
 data.actualSourceComplete=true;
 assert.throws(()=>monthPulseSummary(data),TypeError);
});

test("no fabricated fixed expected return may be attached to variable fund",()=>{
 const data=structuredClone(DEMO.monthPulse);
 data.investments.find(x=>x.id==="sample-fund").quotedReturnMinor=90000;
 assert.throws(()=>monthPulseSummary(data),RangeError);
});

test("dashboard prioritizes plain-language spending, bills, investments and followups",()=>{
 const js=source("ui.mjs"),css=source("ui.css");
 for(const text of ["Your month, in one look.","Bills to check","Investments & next returns",
                   "Where the example money goes","What needs your attention",
                   "Your money, at a glance."])
   assert.ok(js.includes(text),text);
 assert.match(js,/data-go="transactions"/);
 assert.match(js,/data-go="planning"/);
 assert.match(js,/not guaranteed/i);
 assert.match(js,/This is not a payment reminder from your bank/i);
 assert.match(css,/\.pulse-hero/);
 assert.match(css,/\.pulse-stats/);
 assert.match(css,/@media\(max-width:610px\)/);
 assert.doesNotMatch(js,/\bfetch\(["']https?:/);
});
