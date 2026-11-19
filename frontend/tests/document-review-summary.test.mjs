import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {summarizeSourceReview} from "../document-review-summary.mjs";

const read = name => readFileSync(new URL("../"+name,import.meta.url),"utf8");
function fake(name="fictional.pdf",collection="bank_statements",
  state="awaiting_private_document_verification"){
  return {display_name:name,virtual_collection:collection,review_status:state,
    modified_time:"2026-11-19T10:00:00Z",financial_claims_verified:false,
    original_content_imported:false};
}

test("all source counts are only filename suggestions, not real finances",()=>{
  const report=summarizeSourceReview([
    fake("salary-bank.pdf"),
    fake("filed-return.pdf","tax_returns"),
    fake("draft-working.xlsx","accountant_working"),
    fake("investment.pdf","investments"),
    fake("bill.pdf","bills_and_receipts"),
  ]);
  assert.equal(report.total,5);
  assert.deepEqual(report.suggestions,{bank:1,tax:1,investments:1,bills:1});
  assert.equal(report.financialFiguresVerified,false);
  assert.equal(report.contentProcessedCount,0);
  assert.equal(report.allReportsComplete,false);
  assert.equal(report.backgroundSyncActive,false);
  assert.equal(report.quarantineCount,0);
});

test("unsupported/missing-size/unknown sources go into prioritized review",()=>{
  const q=summarizeSourceReview([
    fake("unknown.pdf","unclassified","needs_type_review"),
    fake("virus.xlsm","unclassified","quarantined_unsupported_format"),
    fake("no-size.pdf","bank_statements","needs_size_or_content_review"),
    fake("okay.pdf","bank_statements"),
  ]);
  assert.equal(q.total,4);
  assert.equal(q.quarantineCount,1);
  assert.equal(q.reviewCount,3);
  assert.equal(q.priorityItems[0].name,"virus.xlsm");
  assert.ok(q.priorityItems[0].reason.includes("Unsupported"));
  assert.equal(q.suggestions.bank,2);
  assert.equal(q.financialFiguresVerified,false);
});

test("strange filename stays data and cannot inject rendering",()=>{
  const userSupplied='<img src=x onerror=alert(1)>';
  const q=summarizeSourceReview([fake(userSupplied,"unclassified","needs_type_review")]);
  assert.equal(q.priorityItems[0].name,userSupplied);
  const js=read("app.mjs");
  assert.match(js,/name.textContent=item.name;/);
  assert.match(js,/reason.textContent=item.reason;/);
  assert.ok(!js.includes("innerHTML"));
  assert.ok(!js.includes("localStorage"));
  assert.ok(!js.includes("console.log"));
});

test("fail closed when provider starts claiming financial verification",()=>{
  for(const candidate of [
    {...fake(),financial_claims_verified:true},
    {...fake(),original_content_imported:true},
    {...fake(),review_status:"verified-finance"},
    {...fake(),virtual_collection:"user_injected"},
    {...fake(),display_name:""},
  ]) assert.throws(()=>summarizeSourceReview([candidate]));
  assert.throws(()=>summarizeSourceReview(Array.from({length:1001},()=>fake())));
});

test("owner app loads module only after gated session and keeps no source cache",()=>{
  const html=read("app.html"),js=read("app.mjs"),docker=read("Dockerfile");
  assert.match(js,/import \{ summarizeSourceReview \} from "\.\/document-review-summary.mjs"/);
  assert.match(js,/const validated = validateSnapshot\(data\)/);
  assert.match(js,/const review = summarizeSourceReview\(validated\)/);
  assert.match(js,/items = validated/);
  for(const id of [
    "document-review-summary","document-review-queue","review-suggested-bank",
    "review-suggested-tax","review-suggested-investments","review-suggested-bills",
  ]) assert.ok(html.includes('id="'+id+'"'),id);
  assert.match(docker,/COPY app.html app.mjs app.css document-review-summary.mjs/);
  assert.ok(js.includes('get("/api/owner/session")'));
  assert.ok(js.includes('get("/api/drive/oauth/status")'));
  assert.ok(js.includes('fetch("/api/drive/metadata/refresh"'));
  assert.doesNotMatch(js,/\/api\/finance|localStorage|sessionStorage|innerHTML/);
});
