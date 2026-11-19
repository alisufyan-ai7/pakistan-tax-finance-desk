import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const read=n=>readFileSync(new URL("../"+n,import.meta.url),"utf8");
function location(ng,path){
 const start=ng.indexOf("    location = "+path+" {");
 assert.ok(start>0,path);
 const stop=ng.indexOf("\n    }",start);
 assert.ok(stop>start);
 return ng.slice(start,stop+6);
}

test("historical BAHL original route is a single POST, default-off, no-log exact gateway",()=>{
 const ng=read("nginx.railway.conf"),d=read("Dockerfile");
 const path="/api/finance/historical/bahl";
 const b=location(ng,path);
 for(const required of [
   'if ($p5h_bahl_ingress != "1") { return 404; }',
   'if ($p5a_source_ingress != "1") { return 404; }',
   'if ($p4c_content_ingress != "1") { return 404; }',
   'if ($p1ao_google_ingress != "1") { return 404; }',
   'if ($p1ak_owner_ingress != "1") { return 404; }',
   'if ($request_method != "POST") { return 405; }',
   'if ($args != "") { return 400; }',
   "access_log off;", "error_log /dev/null crit;",
   "limit_req zone=cfo_owner_global burst=3 nodelay;",
   "client_max_body_size 1k;",
   "proxy_no_cache 1;", "proxy_cache_bypass 1;",
   'proxy_set_header Forwarded "";',
   'proxy_set_header X-Forwarded-Host "";',
   "proxy_pass http://$private_google_upstream/internal/finance/historical/bahl;",
 ])assert.ok(b.includes(required),required);
 assert.equal(ng.split("location = "+path+" {").length-1,1);
 assert.match(ng,/set \$p5h_bahl_ingress "\$\{P5H_BAHL_PUBLIC_INGRESS_ENABLED\}";/);
 assert.match(d,/P5H_BAHL_PUBLIC_INGRESS_ENABLED=0/);
 assert.match(d,/P5H_BAHL_PUBLIC_INGRESS_ENABLED\)\$"/);
 assert.doesNotMatch(ng,/\\n    location = \/api\/finance\/historical\/bahl/);
 assert.doesNotMatch(ng,/location \/api\//);
});

test("bank observations appear only after source byte receipt; no invented values",()=>{
 const html=read("app.html"),js=read("app.mjs");
 assert.match(html,/id="historical-bahl-reports"/);
 assert.match(html,/id="historical-bahl-readiness"/);
 assert.match(html,/Not current bank balances/);
 assert.ok(js.includes('entry.byte_hash_verified && BAHL_FILE.test(entry.source_name)'));
 assert.ok(js.includes('buildHistoricalBankAction(entry)'));
 assert.ok(js.includes('fetch("/api/finance/historical/bahl"'));
 assert.ok(js.includes('data.current_available_balance_minor !== null'));
 assert.ok(js.includes('data.income_minor !== null'));
 assert.ok(js.includes('data.expenses_minor !== null'));
 assert.ok(js.includes('data.source_sha256_verified !== true'));
 assert.ok(js.includes('data.historical_opening_minor + data.gross_bank_credits_minor'));
 assert.ok(js.includes('result.statement_end'));
 assert.ok(js.includes('Gross bank debits (not expenses)'));
 assert.ok(js.includes('Gross bank credits (not income)'));
 assert.ok(js.includes('historicalBankReports.clear()'));
 assert.ok(js.includes('body=JSON.stringify') || js.includes('body:JSON.stringify') || js.includes('const body=JSON.stringify'));
 assert.ok(!html.includes("PKR 9,251.08"));
 assert.ok(!html.includes("PKR 10,869.87"));
 assert.ok(!html.includes("PKR 0.55"));
 assert.doesNotMatch(js,/localStorage|sessionStorage|innerHTML|document.cookie|console.log/);
});

test("PDF password is typed only in ephemeral form and sent to same-origin no-store POST",()=>{
 const js=read("app.mjs");
 for(const required of [
   'passwordField.type="password"',
   'passwordField.autocomplete="off"',
   'passwordField.value=""',
   'payload.password=null',
   'mode:"cors", method:"POST"',
   'credentials: "same-origin"',
   'cache: "no-store"',
   'redirect: "error"',
   '"X-CSRF-Token":csrfToken',
   'PASSWORD_REQUIRED',
   'PASSWORD_REJECTED',
   'historicalBankReports.set(entry.source_hmac,outcome)',
 ])assert.ok(js.includes(required),required);
 assert.doesNotMatch(js,/window\.location\.assign\([^)]*password/);
 assert.doesNotMatch(js,/password.*localStorage|password.*sessionStorage/i);
});
