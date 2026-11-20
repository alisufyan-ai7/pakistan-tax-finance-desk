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
    ["home-latest-bank-balance",node()],["home-latest-bank-context",node()],
    ["home-bank-profit",node()],["home-bank-profit-context",node()],
    ["home-attested-bahl-list",node()],["account-attested-bahl-list",node()],
    ["home-attested-bahl-pdf",node()],["account-attested-bahl-pdf",node()],
    ["home-attested-bahl-review",node()],
    ["transaction-rows",node()],["transactions-coverage",node()],
    ["transaction-search",node()],["transaction-source-filter",node()],
    ["transaction-category-filter",node()],["transaction-direction-filter",node()],
    ["transaction-show-more",node()],
  ]);
  const ctx={
    HMAC_SHA:/^[a-f0-9]{64}$/,
    byId:id=>{assert.ok(lookup.has(id),id);return lookup.get(id);},
    document:{createElement:()=>node()},
    historicalMoney:{format:n=>"PKR "+n.toFixed(2)},
    periodEvidence:{transactionSources:[]},
    financialPeriod:{mode:"all",value:"all"},
    periodContainsDate:()=>true,
    periodTitle:()=>"All available evidence",
    transactionVisibleLimit:200,
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


test("Home uses only latest reconciled statement, not an all-bank current balance",()=>{
  const {ctx,lookup}=harness(),first=report();
  const older={...first,source_hmac:"c".repeat(64),source_content_hmac:"d".repeat(64),
    statement_start:"2025-01-01",statement_end:"2025-01-31",
    opening_minor:20000,closing_minor:25000,
    gross_bank_debits_minor:0,gross_bank_credits_minor:5000,
    months:[{...first.months[0],month:"2025-01",
      gross_bank_debits_minor:0,gross_bank_credits_minor:5000,
      last_reported_balance_minor:25000}]};
  ctx.renderHomeBankCsvMetrics([older,first]);
  assert.equal(lookup.get("home-latest-bank-balance").textContent,"PKR 125.00");
  assert.match(lookup.get("home-latest-bank-context").textContent,/2026-01-02/);
  assert.match(lookup.get("home-latest-bank-context").textContent,/not today's cash/);
  assert.equal(lookup.get("home-bank-profit").textContent,"");
  const classified={...first,classification:{bank_profit_received_minor:321}};
  ctx.renderHomeBankCsvMetrics([classified]);
  assert.equal(lookup.get("home-bank-profit").textContent,"PKR 3.21");
  assert.match(lookup.get("home-bank-profit-context").textContent,/not total personal income/);
  ctx.clearBankCsvEvidence();
  assert.equal(lookup.get("home-latest-bank-balance").textContent,"PKR —");
  assert.equal(lookup.get("home-bank-profit").textContent,"PKR —");
  const html=read("app.html");
  assert.match(html,/home-latest-bank-balance/);
  assert.match(html,/home-bank-profit/);
  assert.match(html,/today's total available cash/);
});


test("only privately validated original-SHA-bound historical PDF observations appear in Home/Accounts",()=>{
  const {ctx,lookup}=harness();
  const pdf={
    contract:"personal_cfo_p6d_offline_pdf_observation_v1",
    source_name:"SI-111222333 BAH eStatement(26092026).pdf",
    source_hmac:"d".repeat(64),source_content_hmac:"e".repeat(64),
    statement_start:"2025-07-01",statement_end:"2026-06-30",
    opening_minor:1000,closing_minor:1500,
    gross_bank_debits_minor:500,gross_bank_credits_minor:1000,
    transaction_count:2,page_count:1,source_sha256_verified:true,
    offline_reconciliation_attested:true,
    automatic_pdf_parsing_performed:false,isolation_runtime_accepted:false,
    historical_only:true,current_available_balance_minor:null,
    personal_income_minor:null,personal_expenses_minor:null,
    owner_review_required:true,
  };
  const source={
    contract:"personal_cfo_p6d_offline_pdf_overview_v1",
    reports:[pdf],sources_configured:1,sources_requiring_review:0,
    all_account_coverage_verified:false,current_available_balance_minor:null,
    personal_income_minor:null,personal_expenses_minor:null,
  };
  assert.equal(ctx.validOfflineBahlPdfOverview(source),true);
  ctx.renderOfflineBahlPdfEvidence(source);
  assert.equal(lookup.get("home-attested-bahl-pdf").hidden,false);
  assert.equal(lookup.get("account-attested-bahl-pdf").hidden,false);
  const row=lookup.get("home-attested-bahl-list").children[0];
  assert.match(row.children[1].textContent,/PKR 15.00 as of 2026-06-30/);
  assert.match(row.children[2].textContent,/not automatically parsed/);
  assert.equal(ctx.validOfflineBahlPdfOverview({
    ...source,reports:[{...pdf,closing_minor:1501}],
  }),false);
  assert.equal(ctx.validOfflineBahlPdfOverview({
    ...source,reports:[{...pdf,source_sha256_verified:false}],
  }),false);
  assert.equal(ctx.validOfflineBahlPdfOverview({
    ...source,reports:[{...pdf,isolation_runtime_accepted:true}],
  }),false);
  assert.equal(ctx.validOfflineBahlPdfOverview({
    ...source,reports:[{...pdf,personal_income_minor:5}],
  }),false);
  ctx.clearBankCsvEvidence();
  assert.equal(lookup.get("home-attested-bahl-pdf").hidden,true);
  assert.equal(lookup.get("home-attested-bahl-list").children.length,0);
  const html=read("app.html");
  assert.match(html,/home-attested-bahl-pdf/);
  assert.match(html,/account-attested-bahl-list/);
});


test("source-proved transaction rows stay distinct from expenses, with period/account filters",()=>{
  const {ctx,lookup}=harness();
  const data=report();
  const rows=[
    {event_hmac:"c".repeat(64),source_hmac:data.source_hmac,ordinal:1,
      date:"2026-01-01",direction:"INBOUND",amount_minor:5000,
      balance_after_minor:15000,description:"Money Received from Fictional [account]",
      category:"TRANSFER_CANDIDATE",review_required:true,
      classified_as_personal_income:false,classified_as_personal_expense:false,
      investment_purpose_verified:false},
    {event_hmac:"d".repeat(64),source_hmac:data.source_hmac,ordinal:2,
      date:"2026-01-02",direction:"OUTBOUND",amount_minor:2500,
      balance_after_minor:12500,description:"Fictional outward payment [account]",
      category:"NEEDS_REVIEW",review_required:true,
      classified_as_personal_income:false,classified_as_personal_expense:false,
      investment_purpose_verified:false},
  ];
  const tx={contract:"personal_cfo_p7_reconciled_bank_csv_rows_v1",
    source_hmac:data.source_hmac,transaction_count:2,
    all_running_balances_reconciled:true,source_pinned_by_parent:true,
    source_description_account_references_masked:true,historical_only:true,
    current_available_balance_minor:null,personal_income_minor:null,
    personal_expenses_minor:null,all_rows_returned:true,rows};
  assert.equal(ctx.validBankCsvTransactionRows(tx,data),true);
  assert.equal(ctx.validBankCsvSource({...data,transactions:tx}),true);
  assert.equal(ctx.validBankCsvTransactionRows({...tx,rows:[
    rows[0],{...rows[1],balance_after_minor:12501}]},data),false);
  assert.equal(ctx.validBankCsvTransactionRows({...tx,rows:[
    {...rows[0],classified_as_personal_income:true},rows[1]]},data),false);
  assert.equal(ctx.validBankCsvTransactionRows({...tx,rows:[
    {...rows[0],review_required:false},rows[1]]},data),false);
  ctx.periodEvidence.transactionSources=[{...data,transactions:tx}];
  lookup.get("transaction-search").value="";
  for(const id of ["transaction-source-filter","transaction-category-filter",
      "transaction-direction-filter"])lookup.get(id).value="all";
  ctx.renderTransactionExplorer();
  assert.equal(lookup.get("transaction-rows").children.length,2);
  assert.match(lookup.get("transactions-coverage").textContent,/2 matching transactions/);
  assert.match(lookup.get("transaction-rows").children[0].children[2].textContent,/SHA-verified/);
  lookup.get("transaction-search").value="fictional outward";
  ctx.renderTransactionExplorer();
  assert.equal(lookup.get("transaction-rows").children.length,1);
  assert.match(lookup.get("transaction-rows").children[0].children[0].textContent,/Money out/);
  lookup.get("transaction-category-filter").value="BANK_PROFIT";
  ctx.renderTransactionExplorer();
  assert.match(lookup.get("transaction-rows").children[0].textContent,/No verified CSV rows/);
  const html=read("app.html");
  assert.match(html,/id="view-transactions"/);
  assert.match(html,/id="transaction-search"/);
  assert.match(html,/id="transaction-show-more"/);
});
