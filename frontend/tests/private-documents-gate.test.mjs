import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = path => readFileSync(new URL("../" + path, import.meta.url), "utf8");
const parts = source => new Map(
  [...source.matchAll(/location = ([^ ]+) \{([\s\S]*?)\n    \}/g)]
    .map(match => [match[1], match[2]]),
);

test("one-folder Documents is an exact default-off owner-only HTTPS gateway", () => {
  const nginx = read("nginx.railway.conf"), docker = read("Dockerfile");
  const block = parts(nginx).get("/api/drive/documents/queue");
  assert.ok(block, "Metadata-only Documents route");
  assert.ok(nginx.includes('set $p1ap_documents_ingress "${P1AP_DOCUMENTS_INGRESS_ENABLED}";'));
  assert.ok(docker.includes("P1AP_DOCUMENTS_INGRESS_ENABLED"));
  assert.ok(docker.includes("P1AP_DOCUMENTS_INGRESS_ENABLED=0"));
  for (const guard of [
    'if ($p1ap_documents_ingress != "1") { return 404; }',
    'if ($p1ao_google_ingress != "1") { return 404; }',
    'if ($p1ak_owner_ingress != "1") { return 404; }',
    'if ($p1ak_gateway_token = "") { return 503; }',
    'if ($request_method != "GET") { return 405; }',
    'if ($args != "") { return 400; }',
    'access_log off;',
    'error_log /dev/null crit;',
    'client_max_body_size 1k;',
    'proxy_request_buffering on;',
    'proxy_set_header Host personal-cfo-api-preview.railway.internal;',
    'proxy_set_header X-Forwarded-Proto https;',
    'proxy_set_header X-Personal-CFO-Private-Gateway $p1ak_gateway_token;',
    'proxy_pass http://$private_documents_upstream/internal/drive/documents/queue;',
    'limit_req zone=cfo_owner_ip burst=2 nodelay;',
    'limit_req zone=cfo_owner_global burst=12 nodelay;',
  ]) {
    assert.ok(block.includes(guard), guard);
  }
  for (const h of [
    "Forwarded", "X-Forwarded-For", "X-Real-IP", "X-Original-URI",
    "X-Original-URL", "X-Rewrite-URL", "X-Forwarded-Prefix",
    "X-Personal-CFO-Preview-Key",
  ]) {
    assert.ok(block.includes('proxy_set_header ' + h + ' "";'), h);
  }
  assert.ok(!block.includes("$request_uri"));
  assert.ok(!block.includes("alt=media"));
  assert.ok(!nginx.includes("location /api/"));
  assert.ok(!nginx.includes("location = /api/drive/files/download"));
});

test("mobile one-owner Documents panel is session-only, text-only and metadata-only", () => {
  const html = read("owner-login.html"), js = read("owner-login.mjs");
  assert.ok(html.includes('id="owner-documents" hidden'));
  assert.ok(html.includes('id="owner-documents-refresh"'));
  assert.ok(html.includes('id="owner-documents-list"'));
  assert.ok(js.includes('fetch("/api/drive/documents/queue"'));
  assert.ok(js.includes('item.display_name'));
  assert.ok(js.includes('title.textContent = item.display_name;'));
  assert.ok(js.includes('data.source_bytes_downloaded !== false'));
  assert.ok(js.includes('data.background_sync_active !== false'));
  assert.ok(js.includes('data.snapshot_persisted !== false'));
  assert.ok(js.includes('documentsList.replaceChildren()'));
  assert.ok(js.includes('documentsPanel.hidden = true'));
  for (const forbidden of [
    "localStorage.setItem", "sessionStorage.setItem",
    "innerHTML", "document.cookie", "console.log", "alt=media",
    "files.download", "export_file", "Authorization: Bearer",
  ]) {
    assert.ok(!js.includes(forbidden), forbidden);
  }
});
