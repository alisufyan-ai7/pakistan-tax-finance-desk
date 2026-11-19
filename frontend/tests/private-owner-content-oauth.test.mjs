import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const read=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");
const route=(ng,path)=>{
  const at=ng.indexOf("location = "+path+" {");
  assert.ok(at>=0,path);
  const end=ng.indexOf("\n    }",at);
  assert.ok(end>at);
  return ng.slice(at,end);
};

test("content permission is invisible until separate exact frontend ingress opt-in",()=>{
  const ng=read("nginx.railway.conf"),docker=read("Dockerfile");
  for(const [path,method] of [
    ["/api/drive/content/oauth/start","POST"],
    ["/api/drive/content/oauth/status","GET"],
  ]) {
    const block=route(ng,path);
    for(const expected of [
      'if ($p4c_content_ingress != "1") { return 404; }',
      'if ($p1ao_google_ingress != "1") { return 404; }',
      'if ($p1ak_owner_ingress != "1") { return 404; }',
      'if ($p1ak_gateway_token = "") { return 503; }',
      'if ($args != "") { return 400; }',
      'if ($request_method != "'+method+'") { return 405; }',
      "access_log off;","error_log /dev/null crit;",
      "proxy_no_cache 1;","proxy_cache_bypass 1;",
      "X-Personal-CFO-Private-Gateway $p1ak_gateway_token;",
    ]) assert.ok(block.includes(expected),expected);
    assert.ok(block.includes("proxy_pass http://$private_google_upstream/internal"+path.slice(4)+";"));
  }
  assert.match(ng,/set \$p4c_content_ingress "\$\{P4C_CONTENT_PUBLIC_INGRESS_ENABLED\}";/);
  assert.match(docker,/P4C_CONTENT_PUBLIC_INGRESS_ENABLED=0/);
  assert.match(docker,/P4C_CONTENT_PUBLIC_INGRESS_ENABLED\|P5A_SOURCE_PUBLIC_INGRESS_ENABLED\|P5D_REVIEW_PUBLIC_INGRESS_ENABLED\)\$"/);
  assert.ok(!ng.includes("location /api/"));
});

test("app never shows consent button without authenticated private scope status",()=>{
  const html=read("app.html"),js=read("app.mjs");
  assert.match(html,/id="connect-readonly-documents"[^>]+hidden/);
  assert.match(html,/id="readonly-connection-status"[^>]+hidden/);
  assert.ok(js.includes('get("/api/owner/session")'));
  assert.ok(js.includes('get("/api/drive/content/oauth/status")'));
  assert.ok(js.includes('content_scope !== "DRIVE_READONLY_CONTENT"'));
  assert.ok(js.includes('google_content_grant_stored'));
  assert.ok(js.includes('source_bytes_downloaded !== false'));
  assert.ok(js.includes('fetch("/api/drive/content/oauth/start"'));
  assert.ok(js.includes('mode:"cors"'));
  assert.ok(js.includes('"X-CSRF-Token":csrfToken'));
  assert.ok(js.includes('url.pathname !== "/o/oauth2/v2/auth"'));
  assert.ok(js.includes('url.searchParams.get("scope") !== "https://www.googleapis.com/auth/drive.readonly"'));
  assert.ok(js.includes('include_granted_scopes'));
  assert.ok(!js.includes("innerHTML"));
  assert.ok(!js.includes("localStorage"));
  // P5D owner-only review notes are separately gated from Google consent.
  assert.ok(js.includes('get("/api/finance/review/status")'));
  assert.ok(!js.includes("/api/finance/ledger"));
  assert.ok(!js.includes("/api/finance/import"));
});

test("old owner metadata route and original Drive links unchanged",()=>{
  const login=read("owner-login.mjs"),ng=read("nginx.railway.conf");
  assert.ok(login.includes('get("')===false || !login.includes("drive.readonly"));
  assert.ok(login.includes("/api/drive/oauth/start"));
  assert.ok(login.includes("drive.metadata.readonly"));
  const old=route(ng,"/api/drive/oauth/start");
  assert.ok(!old.includes("$p4c_content_ingress"));
  assert.ok(route(ng,"/api/drive/oauth/callback"));
  assert.ok(route(ng,"/api/drive/metadata/refresh"));
});

test("owner UI acknowledges saved content permission without claiming successful statement import",()=>{
  const html=read("app.html"),js=read("app.mjs"),owner=read("owner-login.html");
  assert.ok(html.includes('id="original-document-readiness"'));
  assert.ok(js.includes('data.google_content_grant_stored'));
  assert.ok(js.includes('Google read-only permission is saved. Secure statement verification'));
  assert.ok(js.includes('no financial figures have been imported'));
  assert.ok(owner.includes('metadata connection is separate from your Google read-only document permission'));
  assert.ok(owner.includes('original documents are never changed'));
});
