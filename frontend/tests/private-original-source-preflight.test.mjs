import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const read=n=>readFileSync(new URL("../"+n,import.meta.url),"utf8");

test("owner original-source SHA preflight route is private and defaults closed",()=>{
 const ng=read("nginx.railway.conf"),docker=read("Dockerfile");
 const start=ng.indexOf("location = /api/drive/content/source/preflight {");
 assert.match(ng,/^    location = \/api\/drive\/content\/source\/preflight \{/m);
 assert.doesNotMatch(ng,/\\n    location = \/api\/drive\/content\/source\/preflight/);
 assert.ok(start>0);
 const stop=ng.indexOf("\n    }",start);
 const block=ng.slice(start,stop);
 for(const line of [
   'if ($p5a_source_ingress != "1") { return 404; }',
   'if ($p4c_content_ingress != "1") { return 404; }',
   'if ($p1ao_google_ingress != "1") { return 404; }',
   'if ($p1ak_owner_ingress != "1") { return 404; }',
   'if ($request_method != "POST") { return 405; }',
   'if ($args != "") { return 400; }',
   'access_log off;','error_log /dev/null crit;',
   'proxy_cache_bypass 1;','proxy_no_cache 1;',
   'proxy_pass http://$private_google_upstream/internal/drive/content/source/preflight;',
 ])assert.ok(block.includes(line),line);
 assert.match(ng,/set \$p5a_source_ingress "\$\{P5A_SOURCE_PUBLIC_INGRESS_ENABLED\}";/);
 assert.match(docker,/P5A_SOURCE_PUBLIC_INGRESS_ENABLED=0/);
 assert.match(docker,/P5D_REVIEW_PUBLIC_INGRESS_ENABLED=0/);
 assert.ok(!ng.includes("location /api/"));
});

test("no source IDs, bytes or financial values supplied by browser",()=>{
 const html=read("app.html"),js=read("app.mjs");
 assert.match(html,/id="verify-originals"[^>]*hidden/);
 assert.match(html,/id="source-hash-results"/);
 assert.ok(js.includes('fetch("/api/drive/content/source/preflight"'));
 assert.ok(js.includes('body:JSON.stringify({batch_index:batch})'));
 assert.ok(js.includes('mode:"cors"'));
 assert.ok(js.includes('"X-CSRF-Token":csrfToken'));
 assert.ok(js.includes('data.actual_bank_amounts_available !== false'));
 assert.ok(js.includes('data.source_hashes_persisted !== false'));
 assert.ok(js.includes('x.source_name.length <= 512'));
 assert.ok(js.includes("name.textContent=entry.source_name"));
 assert.ok(!js.includes("innerHTML"));
 assert.ok(!js.includes("localStorage"));
 assert.ok(!js.includes("sessionStorage"));
 assert.ok(!js.includes("file_id"));
});
