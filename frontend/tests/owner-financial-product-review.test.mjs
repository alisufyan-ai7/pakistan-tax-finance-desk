import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const read=n=>readFileSync(new URL("../"+n,import.meta.url),"utf8");
function element(){return {children:[],hidden:true,textContent:"",
  append(...items){this.children.push(...items);},
  appendChild(item){this.children.push(item);},
  replaceChildren(...items){this.children=[...items];}};
}
function harness(){
  const js=read("app.mjs"),a=js.indexOf("function renderOwnerReviewQueue(){"),
    b=js.indexOf("function go(view) {",a);
  assert.ok(a>=0&&b>a);
  const ids=new Map([
    "home-review-list","home-review-coverage",
    "spending-source-list","tax-source-list","spending-observation-heading",
    "tax-period-heading","spending-source-coverage","tax-source-coverage",
  ].map(k=>[k,element()]));
  const data={
    bankReports:[{source_name:"fictional-verified.csv",classification:{
      months:[{month:"2026-01",bank_profit_received_minor:150,
        bank_fees_and_combined_levies_minor:55,
        bank_profit_withholding_tax_minor:15,pending_review_count:2}]} }],
    transactionSources:[{source_name:"fictional-verified.csv",
      transactions:{rows:[{review_required:true,date:"2026-01-02",
        direction:"OUTBOUND",amount_minor:2400,source_hmac:"a".repeat(64),
        ordinal:1,description:"Fictional transfer",category:"TRANSFER_CANDIDATE"}]}}],
  };
  const ctx={
    periodEvidence:data,financialPeriod:{mode:"month",value:"2026-01"},
    periodTitle:()=> "January 2026",
    periodContainsDate:date=>date.startsWith("2026-01"),
    periodContainsMonth:m=>m==="2026-01",
    byId:id=>{assert.ok(ids.has(id),id);return ids.get(id);},
    historicalMoney:{format:v=>"PKR "+v.toFixed(2)},
    document:{createElement:()=>element()},
  };
  vm.runInNewContext(js.slice(a,b),ctx);
  return {ctx,ids};
}
test("Home review queue highlights actual ambiguous entries without claiming saved classification",()=>{
  const {ctx,ids}=harness();
  ctx.renderOwnerReviewQueue();
  assert.match(ids.get("home-review-coverage").textContent,/1 source-verified CSV entries/);
  assert.match(ids.get("home-review-coverage").textContent,/not saved/i);
  const row=ids.get("home-review-list").children[0];
  assert.match(row.children[0].textContent,/PKR 24.00/);
  assert.match(row.children[1].textContent,/possible transfer/);
  ctx.periodEvidence.transactionSources=[];
  ctx.renderOwnerReviewQueue();
  assert.match(ids.get("home-review-list").children[0].textContent,/No pending entries/);
});
test("Spending and Tax distinguish exact bank profit/levy/withholding from unverified household spending",()=>{
  const {ctx,ids}=harness();
  ctx.renderSourceSpendingAndTax();
  const entry=ids.get("spending-source-list").children[0];
  assert.match(entry.children[1].textContent,/Bank-labelled profit PKR 1.50/);
  assert.match(entry.children[1].textContent,/bank fees\/levies PKR 0.55/);
  assert.match(entry.children[1].textContent,/withholding PKR 0.15/);
  assert.match(entry.children[2].textContent,/2 entries still unclassified/);
  const tax=ids.get("tax-source-list").children[0];
  assert.match(tax.children[1].textContent,/PKR 0.15/);
  assert.match(tax.children[1].textContent,/not an income-tax liability/);
  assert.match(ids.get("spending-source-coverage").textContent,/Missing accounts\/months/);
  ctx.periodContainsMonth=()=>false;
  ctx.renderSourceSpendingAndTax();
  assert.match(ids.get("tax-source-list").children[0].textContent,/not zero expenses, tax or income/);
});
test("end-user navigation contains visible review, position and honest missing period states",()=>{
  const html=read("app.html"),js=read("app.mjs");
  for(const id of ["home-review-list","investment-position-panel","investment-position-list",
    "spending-source-list","tax-source-list"])
    assert.ok(html.includes('id="'+id+'"'));
  assert.match(js,/renderInvestmentPositionCards/);
  assert.match(js,/renderOwnerReviewQueue/);
  assert.match(js,/renderSourceSpendingAndTax/);
  assert.doesNotMatch(js,/localStorage|sessionStorage|innerHTML|console\.log/);
});
