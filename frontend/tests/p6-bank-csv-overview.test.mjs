import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const read=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");
function node() {
  return {children:[],hidden:true,textContent:"",
    append(...children){this.children.push(...children);},
    appendChild(child){this.children.push(child);},
    replaceChildren(...children){this.children=[...children];},
  };
}
function report() {
  return {
    contract:"personal_cfo_p6_reconciled_bank_csv_v1",
    source_type:"BANK_CSV_EXACT_RUNNING_BALANCES",
    source_hmac:"a".repeat(64),
    source_content_hmac:"b".repeat(64),
    source_name:"fictional.csv",
    source_sha256_verified:true,
    content_retained_on_server:false,original_source_modified:false,
    all_running_balances_reconciled:true,
    printed_closing_reconciled:true,
    historical_only:true,owner_review_required:true,
    current_available_balance_minor:null,personal_income_minor:null,
    personal_expenses_minor:null,investment_current_market_value_minor:null,
    statement_start:"2026-01-01",statement_end:"2026-01-02",
    transaction_count:2, opening_minor:10000, closing_minor:12500,
    gross_bank_credits_minor:5000,gross_bank_debits_minor:2500,
    months:[{month:"2026-01",transaction_count:2,gross_bank_credits_minor:5000,
      gross_bank_debits_minor:2500,last_reported_balance_minor:12500,
      bank_labelled_profit_minor:0,bank_labelled_profit_tax_minor:0}],
  };
}
function harness(){
  const src=read("app.mjs"),a=src.indexOf('const CSV_BANK_CONTRACT=');
  const b=src.indexOf("\nfunction renderHomeHistoricalEvidence()",a);
  assert.ok(a>=0&&b>a);
  const lookup=new Map([
    ["home-bank-csv-list",node()],["account-bank-csv-list",node()],
    ["home-bank-csv-evidence",node()],["account-bank-csv-section",node()],
  ]);
  const ctx={
    HMAC_SHA:/^[a-f0-9]{64}$/,
    byId:id=>{assert.ok(lookup.has(id),id);return lookup.get(id);},
    document:{createElement:()=>node()},
    historicalMoney:{format:n=>"PKR "+n.toFixed(2)},
    bankCsvRefreshEpoch:0,
    safeToken:()=>true,
    csrfToken:"x".repeat(50),
    get:async()=>null,
    Map,Set,
  };
  vm.runInNewContext(src.slice(a,b),ctx);
  return {ctx,lookup};
}
test("strict genuine bank source schema displays dated balance, not current account total",()=>{
  const x=harness();
  const data={contract:"personal_cfo_owner_bank_csv_overview_v1",
    reports:[report()],csv_sources_found:1,csv_sources_requiring_review:0,
    source_inventory_complete:true,approved_source_folder:true,
    originals_modified:false,content_retained_on_server:false,
    historical_only:true,all_account_coverage_verified:false,
    personal_income_minor:null,personal_expenses_minor:null,
    current_available_balance_minor:null};
  assert.equal(x.ctx.validBankCsvOverview(data),true);
  x.ctx.renderBankCsvReportList("home-bank-csv-list",data.reports);
  const row=x.lookup.get("home-bank-csv-list").children[0];
  assert.equal(row.children[0].textContent,"fictional.csv");
  assert.match(row.children[1].textContent,/PKR 125.00 as of 2026-01-02/);
  assert.match(row.children[2].textContent,/not classified income or expenses/i);
  const table=row.children[3];
  assert.equal(table.children[1].children[0].children[1].textContent,"PKR 50.00");
  const original=report();
  assert.equal(x.ctx.validBankCsvSource({...original,closing_minor:12600}),false);
  assert.equal(x.ctx.validBankCsvSource({...original,personal_income_minor:10000}),false);
  assert.equal(x.ctx.validBankCsvSource({...original,source_sha256_verified:false}),false);
  assert.equal(x.ctx.validBankCsvSource({...original,months:[{...original.months[0],gross_bank_debits_minor:2501}]}),false);
});
test("redacted private source metadata never enters HTML, storage or script console",()=>{
  const js=read("app.mjs"),html=read("app.html"),
        ng=read("nginx.railway.conf"),docker=read("Dockerfile");
  assert.ok(html.includes('id="home-bank-csv-evidence"'));
  assert.ok(html.includes('id="account-bank-csv-section"'));
  assert.match(js,/get\("\/api\/finance\/bank\/csv-overview"\)/);
  assert.match(js,/name.textContent=report.source_name/);
  assert.match(js,/clearBankCsvEvidence\(\)/);
  assert.doesNotMatch(js,/localStorage|sessionStorage|innerHTML|document\.cookie|console\.log/);
  assert.match(ng,/location = \/api\/finance\/bank\/csv-overview \{/);
  assert.match(ng,/if \(\$p6a_bank_csv_ingress != "1"\) \{ return 404; \}/);
  assert.match(ng,/proxy_pass http:\/\/\$private_google_upstream\/internal\/finance\/bank\/csv-overview/);
  assert.match(ng,/access_log off;/);
  assert.match(docker,/P6A_BANK_CSV_PUBLIC_INGRESS_ENABLED=0/);
});

test("strict source classifier distinguishes unknown transfers from actual bank fees, no invented P&L",()=>{
  const x=harness(),source=report();
  const c={
    contract:"personal_cfo_p6_bank_cashflow_classification_v1",
    classification_basis:"EXACT_BANK_LABELS_AFTER_FULL_BALANCE_RECONCILIATION",
    transaction_count:2,
    bank_profit_received_minor:0,
    bank_profit_withholding_tax_minor:0,
    bank_fees_and_combined_levies_minor:0,
    unclassified_credit_minor:5000,
    unclassified_debit_minor:2500,
    pending_review_count:2,
    transfer_candidate_count:2,
    confirmed_bank_event_count:0,
    all_movements_accounted_for:true,all_personal_income_classified:false,
    all_personal_expenses_classified:false,all_account_coverage_verified:false,
    personal_monthly_income_minor:null,personal_monthly_expenses_minor:null,
    original_source_modified:false,owner_review_required:true,
    months:[{month:"2026-01",source_transaction_count:2,
      bank_profit_received_minor:0,bank_profit_withholding_tax_minor:0,
      bank_fees_and_combined_levies_minor:0,
      unclassified_credit_minor:5000,unclassified_debit_minor:2500,
      confirmed_bank_event_count:0,pending_review_count:2,transfer_candidate_count:2}]
  };
  assert.equal(x.ctx.validBankCsvClassification(c,source),true);
  const classified={...source,classification:c};
  assert.equal(x.ctx.validBankCsvSource(classified),true);
  x.ctx.renderBankCsvReportList("home-bank-csv-list",[classified]);
  const entry=x.lookup.get("home-bank-csv-list").children[0];
  assert.match(entry.children[2].textContent,/2 transactions still need classification/);
  assert.match(entry.children[2].textContent,/not classified income or expenses/);
  assert.equal(entry.children[3].children[0].children[0].children.length,7);
  assert.equal(x.ctx.validBankCsvSource({...classified,classification:{...c,
    unclassified_credit_minor:4999}}),false);
  assert.equal(x.ctx.validBankCsvSource({...classified,classification:{...c,
    personal_monthly_income_minor:5000}}),false);
  assert.equal(x.ctx.validBankCsvSource({...classified,classification:{...c,
    pending_review_count:0}}),false);
  assert.equal(x.ctx.validBankCsvSource({...classified,classification:{...c,
    months:[{...c.months[0],unclassified_debit_minor:0}]}}),false);
});
