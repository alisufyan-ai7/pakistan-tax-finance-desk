import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import {readFileSync} from "node:fs";
import {periodMonths,periodTitle} from "../finance-period.mjs";

const read = name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");
function node(tag="div"){
  return {
    tag,children:[],textContent:"",hidden:false,disabled:false,value:"",
    append(...xs){this.children.push(...xs);},
    appendChild(x){this.children.push(x);},
    replaceChildren(...xs){this.children=[...xs];},
    setAttribute(k,v){this[k]=v;},
  };
}
const source=(id,name,months)=>({
  source_hmac:id,source_name:name,statement_end:"2026-06-30",
  months:months.map(([month,cr,dr])=>({
    month,transaction_count:2,
    gross_bank_credits_minor:cr,gross_bank_debits_minor:dr,
    last_reported_balance_minor:43210,
  })),
});
function harness(period,bankSources){
  const src=read("app.mjs"),a=src.indexOf("function renderMonthlyBankTrend(){"),
    b=src.indexOf("function renderFinancialPeriodEvidence(){",a);
  assert.ok(a>=0&&b>a);
  const ids=new Map(["monthly-trend-source","monthly-trend-rows",
    "monthly-trend-coverage"].map(x=>[x,node()]));
  const ctx={
    byId:id=>{assert.ok(ids.has(id),id);return ids.get(id);},
    document:{createElement:node},
    financialPeriod:period,
    periodEvidence:{bankReports:bankSources},
    periodMonths,periodTitle,
    historicalMoney:{format:n=>"PKR "+n.toFixed(2)},
  };
  vm.runInNewContext(src.slice(a,b),ctx);
  return {ctx,ids};
}
test("tax-year trend shows every month with missing source months as UNKNOWN not zero",()=>{
  const {ctx,ids}=harness({mode:"tax-year",value:"2025"},[
    source("a".repeat(64),"fictional-A.csv",[
      ["2025-07",10000,6000],["2026-06",4000,2500],
    ]),
  ]);
  ctx.renderMonthlyBankTrend();
  const rows=ids.get("monthly-trend-rows").children;
  assert.equal(rows.length,12);
  assert.equal(rows[0].children[0].textContent,"July 2025");
  assert.equal(rows[0].children[1].children[2].textContent,"PKR 100.00");
  assert.equal(rows[0].children[2].children[2].textContent,"PKR 60.00");
  assert.equal(rows[1].children.length,2);
  assert.match(rows[1].children[1].textContent,/Unknown, not zero/);
  assert.equal(rows[11].children[0].textContent,"June 2026");
  assert.match(ids.get("monthly-trend-coverage").textContent,/2 of 12 displayed month/);
  assert.match(ids.get("monthly-trend-coverage").textContent,/Other banks are not included/);
});
test("source picker never sums overlapping sources; calendar month selector remains exact",()=>{
  const {ctx,ids}=harness({mode:"month",value:"2026-01"},[
    source("a".repeat(64),"fictional-A.csv",[["2026-01",2000,1000]]),
    source("b".repeat(64),"fictional-B.csv",[["2026-01",6000,7000]]),
  ]);
  ctx.renderMonthlyBankTrend();
  assert.equal(ids.get("monthly-trend-rows").children.length,1);
  assert.equal(ids.get("monthly-trend-rows").children[0].children[1].children[2].textContent,"PKR 20.00");
  ids.get("monthly-trend-source").value="b".repeat(64);
  ctx.renderMonthlyBankTrend();
  assert.equal(ids.get("monthly-trend-rows").children.length,1);
  assert.equal(ids.get("monthly-trend-rows").children[0].children[1].children[2].textContent,"PKR 60.00");
  assert.match(ids.get("monthly-trend-coverage").textContent,/fictional-B.csv/);
});
test("no source resets bank chart rather than leaving stale private evidence",()=>{
  const {ctx,ids}=harness({mode:"all",value:"all"},[]);
  ctx.renderMonthlyBankTrend();
  assert.equal(ids.get("monthly-trend-source").disabled,true);
  assert.equal(ids.get("monthly-trend-rows").children.length,0);
  assert.match(ids.get("monthly-trend-coverage").textContent,/No verified monthly CSV transaction evidence/);
});
test("app includes mobile responsive, accessible source-only chart; no fake data",()=>{
  const html=read("app.html"),css=read("app.css"),js=read("app.mjs");
  for(const id of ["monthly-trend-source","monthly-trend-rows","monthly-trend-coverage"])
    assert.ok(html.includes('id="'+id+'"'));
  assert.match(css,/@media\(max-width:720px\).*monthly-trend-controls/s);
  assert.match(css,/min-height:44px/);
  assert.match(js,/renderMonthlyBankTrend/);
  for(const forbidden of ["localStorage","sessionStorage","innerHTML","console.log"])
    assert.ok(!js.includes(forbidden));
});
