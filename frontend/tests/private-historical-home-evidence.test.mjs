import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const read=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");
function element(){
  return {
    textContent:"",hidden:false,className:"",children:[],
    append(...items){this.children.push(...items);},
    appendChild(item){this.children.push(item);},
    replaceChildren(...items){this.children=[...items];},
  };
}
function homeHarness(values){
  const js=read("app.mjs");
  const start=js.indexOf("function renderHomeHistoricalEvidence() {");
  const end=js.indexOf("\nasync function readHistoricalBahl",start);
  assert.ok(start>=0 && end>start,"Isolated authenticated historical home renderer");
  const section=element();
  const list=element();
  const lookup=new Map([
    ["home-historical-evidence",section],
    ["home-historical-evidence-list",list],
  ]);
  const context={
    byId:id=>{
      assert.ok(lookup.has(id),"No unexpected DOM target "+id);
      return lookup.get(id);
    },
    document:{createElement:()=>element()},
    historicalBankReports:new Map(values.map((x,i)=>["fake-private-source-"+i,x])),
    historicalMoney:{format:value=>"PKR "+value.toFixed(2)},
  };
  vm.runInNewContext(js.slice(start,end)+"\nrenderHomeHistoricalEvidence();",context);
  return {section,list,context};
}
function entry(name,end,closing,credits,debits){
  return {
    source_name:name,statement_start:"2025-07-01",statement_end:end,
    historical_closing_minor:closing,gross_bank_credits_minor:credits,
    gross_bank_debits_minor:debits,
  };
}
test("private home shows no source data or invented balances before individual proof",()=>{
  const {section,list}=homeHarness([]);
  assert.equal(section.hidden,true);
  assert.equal(list.children.length,0);
  const html=read("app.html");
  assert.match(html,/id="home-historical-evidence"[^>]*hidden/);
  assert.match(html,/id="home-historical-evidence-list"/);
  assert.match(html,/not today's available cash, personal income or expenses/i);
  for(const value of ["Available bank balances","Income this month","Expenses this month"]){
    assert.ok(html.includes(value));
  }
  assert.ok(html.includes("PKR —"));
});
test("latest genuine statement observation appears as dated, NOT current or aggregated",()=>{
  const older=entry("synthetic one.pdf","2025-08-31",30000,40000,10000);
  const newer=entry("synthetic two.pdf","2026-06-30",50000,70000,20000);
  const {section,list}=homeHarness([older,newer]);
  assert.equal(section.hidden,false);
  assert.equal(list.children.length,2);
  assert.equal(list.children[0].children[0].textContent,"synthetic two.pdf");
  assert.match(list.children[0].children[1].textContent,/Historical balance as of 2026-06-30/);
  assert.match(list.children[0].children[1].textContent,/Original SHA-256 verified/);
  const terms=list.children[0].children[2].children.map(x=>x.textContent);
  assert.deepEqual(terms,[
    "Closing balance at statement end","PKR 500.00",
    "Gross bank debits (not expenses)","PKR 200.00",
    "Gross bank credits (not income)","PKR 700.00",
  ]);
  // There is no misleading sum of balances from unrelated/overlapping periods.
  assert.ok(!terms.includes("PKR 800.00"));
});
test("verified outcome path, source refresh and invalidated session clear home evidence",()=>{
  const js=read("app.mjs");
  assert.match(js,/if \(!verifiedHistoricalBahl\(data,sourceHmac\)\)/);
  assert.ok(js.includes('historicalBankReports.set(entry.source_hmac,outcome)'));
  assert.ok(js.includes("renderHistoricalBankReports();"));
  assert.ok(js.includes("renderHomeHistoricalEvidence();"));
  assert.match(js,/historicalBankReports\.clear\(\);\s*historicalReportList\.replaceChildren\(\);[\s\S]{0,350}home-historical-evidence-list/);
  assert.ok(js.includes('byId("home-historical-evidence").hidden = true;'));
  assert.match(js,/if \(batch===0\) \{[\s\S]{0,140}historicalBankReports\.clear\(\)/);
  assert.doesNotMatch(js,/localStorage|sessionStorage|innerHTML|document\.cookie|console\.log/);
});
