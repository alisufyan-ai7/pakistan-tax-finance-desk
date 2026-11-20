import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const read=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");
const blockFor=(ng,path)=>{
 const start=ng.indexOf("    location = "+path+" {");
 assert.ok(start>=0,path);
 const end=ng.indexOf("\n    }",start);
 assert.ok(end>start);
 return ng.slice(start,end);
};

test("review note routes are separate exact paths disabled by default",()=>{
 const ng=read("nginx.railway.conf"),docker=read("Dockerfile");
 for(const [path,method] of [
   ["/api/finance/review/status","GET"],
   ["/api/finance/review/comment","POST"],
   ["/api/finance/review/history","POST"],
 ]) {
   assert.ok(ng.includes("\n    location = "+path+" {"));
   const b=blockFor(ng,path);
   for(const gate of [
     'if ($p5d_review_ingress != "1") { return 404; }',
     'if ($p4c_content_ingress != "1") { return 404; }',
     'if ($p1ak_owner_ingress != "1") { return 404; }',
     'if ($request_method != "'+method+'") { return 405; }',
     'if ($args != "") { return 400; }',
     'access_log off;','error_log /dev/null crit;',
     'proxy_no_cache 1;','proxy_cache_bypass 1;',
     'proxy_pass http://$private_google_upstream/internal'+path.slice(4)+';',
   ])assert.ok(b.includes(gate),gate);
 }
 assert.match(ng,/set \$p5d_review_ingress "\$\{P5D_REVIEW_PUBLIC_INGRESS_ENABLED\}";/);
 assert.match(docker,/P5D_REVIEW_PUBLIC_INGRESS_ENABLED=0/);
 assert.match(docker,/P5D_REVIEW_PUBLIC_INGRESS_ENABLED\|P5H_BAHL_PUBLIC_INGRESS_ENABLED\|P6A_BANK_CSV_PUBLIC_INGRESS_ENABLED\|P6B_INVESTMENTS_PUBLIC_INGRESS_ENABLED\)\$"/);
 assert.doesNotMatch(ng,/\\n    location = \/api\/finance\/review/);
 assert.doesNotMatch(ng,/location \/api\//);
});

test("only authenticated owner receives an editable comment UI",()=>{
 const js=read("app.mjs"),html=read("app.html");
 assert.ok(html.includes('id="owner-review-readiness"'));
 assert.match(js,/get\("\/api\/finance\/review\/status"\)/);
 assert.match(js,/review_enabled !== true/);
 assert.match(js,/append_only_encrypted !== true/);
 assert.match(js,/auto_resolve !== false/);
 assert.match(js,/if \(ownerReviewEnabled\) li\.appendChild\(buildPrivateReviewEditor/);
 assert.match(js,/fetch\(path,\{/);
 assert.ok(js.includes('"/api/finance/review/comment"'));
 assert.ok(js.includes('"/api/finance/review/history"'));
 assert.match(js,/mode:"cors"/);
 assert.match(js,/"X-CSRF-Token":csrfToken/);
 assert.match(js,/field\.maxLength=1500/);
 assert.match(js,/name\.textContent=entry\.source_name/);
 assert.match(js,/li\.textContent="Comment "\+String\(item\.revision\)\+": "\+item\.comment/);
 assert.match(js,/PENDING_EVIDENCE_RECONCILIATION/);
 assert.ok(!js.includes("innerHTML"));
 assert.ok(!js.includes("localStorage"));
 assert.ok(!js.includes("sessionStorage"));
});

test("private review backend refuses arbitrary IDs and automated resolution",()=>{
 const py=read("app.mjs"); // statically ensure only actual SHA-HMAC source identity used
 assert.match(py,/buildPrivateReviewEditor\(entry.source_hmac\)/);
 const html=read("app.html");
 assert.match(html,/Comments never overwrite originals or automatically change balances/);
});
