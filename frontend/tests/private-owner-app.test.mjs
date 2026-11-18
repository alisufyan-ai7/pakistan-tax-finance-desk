import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const read = name => readFileSync(new URL("../"+name, import.meta.url),"utf8");
const locations = conf => new Map([...conf.matchAll(/location = ([^ ]+) \{([\s\S]*?)\n    \}/g)].map(m=>[m[1],m[2]]));

test("owner /app is a separate exact gated, non-cacheable route",()=>{
  const ng=read("nginx.railway.conf"), docker=read("Dockerfile");
  const blocks=locations(ng), app=blocks.get("/app");
  assert.ok(app);
  assert.ok(blocks.get("/app.html").includes("return 404;"));
  for(const rule of [
    "access_log off;","error_log /dev/null crit;",
    'if ($p1ak_owner_ingress != "1") { return 404; }',
    'if ($request_method != "GET") { return 405; }',
    'if ($args != "") { return 400; }',
    'try_files /app.html =404;',
    "personal-cfo-frontend-preview-development.up.railway.app",
  ]) assert.ok(app.includes(rule),rule);
  assert.ok(docker.includes("COPY app.html app.mjs app.css"));
  assert.ok(ng.includes('Cache-Control "no-store" always;'));
  assert.ok(!ng.includes("location /api/"));
  assert.ok(!app.includes("proxy_pass"));
});
test("single-owner dashboard has mobile and desktop navigation, never synthetic amounts",()=>{
  const html=read("app.html"),js=read("app.mjs"),css=read("app.css");
  assert.match(html,/id="app-gate"/);
  assert.match(html,/id="owner-app" class="app" hidden/);
  assert.match(html,/id="bottom-nav" class="bottom-nav"/);
  assert.match(html,/id="view-home"/);
  for(const view of ["documents","accounts","spending","investments","tax"])
    assert.ok(html.includes('id="view-'+view+'"'),view);
  assert.ok(html.includes("PKR —"));
  assert.ok(!html.includes("180000") && !html.includes("85000"));
  assert.ok(!js.includes("demo-data.mjs"));
  assert.ok(!html.includes("demo-data.mjs"));
  assert.ok(css.includes("@media(max-width:720px)"));
  assert.ok(css.includes(".bottom-nav"));
  for(const forbidden of ["localStorage","sessionStorage","document.cookie","console.log",
    "innerHTML","postMessage(","/api/finance","drive/v3/files","imported_financial_amount"]) {
    assert.ok(!js.includes(forbidden),forbidden);
  }
});
test("metadata display waits for real cookie-bound MFA/CSRF, no original bytes",()=>{
  const js=read("app.mjs");
  assert.ok(js.includes('get("/api/owner/session")'));
  assert.ok(js.includes('session?.authenticated !== true'));
  assert.ok(js.includes('session.real_financial_data_enabled !== false'));
  assert.ok(js.includes('window.location.replace("/owner-login")'));
  assert.ok(js.includes('get("/api/drive/oauth/status")'));
  assert.ok(js.includes('google.google_drive_app_connected'));
  assert.ok(js.includes('fetch("/api/drive/metadata/refresh"'));
  assert.ok(js.includes('"X-CSRF-Token":csrfToken'));
  assert.ok(js.includes('credentials: "same-origin"'));
  assert.ok(js.includes('cache: "no-store"'));
  assert.ok(js.includes('data.snapshot_complete !== true'));
  assert.ok(js.includes('data.source_bytes_downloaded !== false'));
  assert.ok(js.includes('data.real_financial_data_enabled !== false'));
  assert.ok(js.includes('title.textContent = item.display_name'));
  assert.ok(js.includes('documents.replaceChildren()'));
  assert.ok(js.includes('Missing') || js.includes('unavailable'));
  const login=read("owner-login.mjs"), loginHtml=read("owner-login.html");
  assert.ok(login.includes('window.location.assign("/app")'));
  assert.ok(loginHtml.includes('id="owner-open-app" href="/app"'));
  assert.ok(login.includes('await refreshGoogleStatus();')); // oauth resume remains
});
