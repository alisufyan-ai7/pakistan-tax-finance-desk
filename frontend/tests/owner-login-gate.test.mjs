import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = filename =>
  readFileSync(new URL("../" + filename, import.meta.url), "utf8");

const publicRoutes = new Map([
  ["/api/owner/login", ["POST", "/internal/drive/auth/login"]],
  ["/api/owner/session", ["GET", "/internal/drive/auth/session"]],
  ["/api/owner/logout", ["POST", "/internal/drive/auth/logout"]],
]);
const host = "personal-cfo-frontend-preview-development.up.railway.app";

function locations(config) {
  return new Map([...config.matchAll(/location = ([^ ]+) \{([\s\S]*?)\n    \}/g)]
    .map(m => [m[1], m[2]]));
}

test("exact three public login routes are disabled unless independently enabled", () => {
  const conf = read("nginx.railway.conf"), blocks = locations(conf);
  assert.ok(conf.includes('set $p1ak_owner_ingress "${P1AK_OWNER_INGRESS_ENABLED}";'));
  assert.ok(conf.includes('set $p1ak_gateway_token "${P1Q_PRIVATE_GATEWAY_SHARED_TOKEN}";'));
  assert.ok(!conf.includes('location /api/'));
  assert.equal([...blocks.keys()].filter(k => k.startsWith("/api/")).length, 7);
  for (const [path, [method, internal]] of publicRoutes) {
    const b = blocks.get(path);
    assert.ok(b, path);
    assert.ok(b.includes('if ($p1ak_owner_ingress != "1") { return 404; }'));
    assert.ok(b.includes('if ($p1ak_gateway_token = "") { return 503; }'));
    assert.ok(b.includes('if ($host != "' + host + '") { return 403; }'));
    assert.ok(b.includes('if ($request_method != "' + method + '") { return 405; }'));
    assert.ok(b.includes('if ($args != "") { return 400; }'));
    assert.ok(b.includes("access_log off;"));
    assert.ok(b.includes("error_log /dev/null crit;"));
    assert.ok(b.includes("client_max_body_size 4k;"));
    assert.ok(b.includes("proxy_pass http://$private_auth_upstream" + internal + ";"));
    assert.ok(b.includes("proxy_request_buffering on;"));
    assert.ok(b.includes("proxy_set_header Host personal-cfo-api-preview.railway.internal;"));
    assert.ok(b.includes("proxy_set_header X-Forwarded-Proto https;"));
    assert.ok(b.includes("proxy_set_header X-Personal-CFO-Private-Gateway $p1ak_gateway_token;"));
    assert.ok(b.includes("proxy_set_header X-Personal-CFO-Preview-Key \"\";"));
    assert.ok(!b.includes("$http_x_personal_cfo_private_gateway"));
    assert.ok(!b.includes("$request_uri"));
    for (const h of ["Forwarded", "X-Forwarded-Host", "X-Forwarded-For",
                    "X-Real-IP", "X-Original-URI", "X-Original-URL",
                    "X-Rewrite-URL", "X-Forwarded-Prefix"]) {
      assert.ok(b.includes('proxy_set_header ' + h + ' "";'), h);
    }
    assert.ok(!b.includes("add_header ")); // inherit server-wide security headers
  }
  for (const route of ["/api/drive/oauth/disconnect",
                       "/api/finance", "/internal/drive/oauth/start"]) {
    assert.ok(!blocks.has(route));
  }
  const login = blocks.get("/api/owner/login");
  assert.ok(login.includes("limit_req zone=cfo_owner_ip burst=3 nodelay;"));
  for (const route of publicRoutes.keys()) {
    assert.ok(blocks.get(route).includes("limit_req zone=cfo_owner_global burst=12 nodelay;"));
  }
  const zones = read("nginx.owner-rate-zones.conf");
  assert.ok(zones.includes("limit_req_zone $binary_remote_addr zone=cfo_owner_ip:10m rate=8r/m;"));
  assert.ok(zones.includes("limit_req_zone $server_name zone=cfo_owner_global:1m rate=120r/m;"));
});

test("owner page is only available through gated URL, not its direct filename", () => {
  const conf = read("nginx.railway.conf"), blocks = locations(conf);
  assert.ok(blocks.get("/owner-login.html").includes("return 404;"));
  const guarded = blocks.get("/owner-login");
  assert.ok(guarded.includes('if ($p1ak_owner_ingress != "1") { return 404; }'));
  assert.ok(guarded.includes("try_files /owner-login.html =404;"));
  assert.ok(conf.includes("script-src 'self'"));
  assert.ok(conf.includes("connect-src 'self'"));
  assert.ok(conf.includes("form-action 'none'"));
  assert.ok(conf.includes("Cache-Control \"no-store\" always;"));
});

test("mobile owner login never persists credentials, uses only own exact login/logout", () => {
  const html = read("owner-login.html");
  const js = read("owner-login.mjs");
  const docker = read("Dockerfile");
  assert.ok(html.includes('type="password"'));
  assert.ok(html.includes('autocomplete="one-time-code"'));
  assert.ok(html.includes('type="module"'));
  assert.ok(html.includes('href="/owner-login.css"'));
  assert.ok(js.includes('"/api/owner/login"'));
  assert.ok(js.includes('"/api/owner/logout"'));
  for (const disallowed of ["localStorage.setItem", "localStorage.getItem",
                            "sessionStorage.setItem", "sessionStorage.getItem",
                            "console.log", "document.cookie",
                            "postMessage("]) {
    assert.ok(!js.includes(disallowed), disallowed);
  }
  for (const expected of ['credentials: "same-origin"', 'cache: "no-store"',
                         'redirect: "error"', 'referrerPolicy: "no-referrer"']) {
    assert.ok(js.includes(expected), expected);
  }
  assert.ok(docker.includes("COPY owner-login.html owner-login.mjs owner-login.css"));
  assert.ok(docker.includes("COPY nginx.owner-rate-zones.conf"));
  assert.ok(docker.includes("P1AK_OWNER_INGRESS_ENABLED"));
  assert.ok(!docker.includes("ENV P1AK_OWNER_INGRESS_ENABLED=1"));
  // Without defined defaults envsubst leaves a literal dollar variable
  // expression and Nginx refuses to start. Keep runtime safe defaults.
  assert.ok(docker.includes('ENV P1AK_OWNER_INGRESS_ENABLED=0 P1AO_GOOGLE_INGRESS_ENABLED=0 P1Q_PRIVATE_GATEWAY_SHARED_TOKEN=""'));
  assert.ok(!docker.includes('P1AK_OWNER_INGRESS_ENABLED=1'));

  assert.ok(docker.includes("P1Q_PRIVATE_GATEWAY_SHARED_TOKEN"));
  assert.ok(!docker.includes("ENV P1Q_PRIVATE_GATEWAY_SHARED_TOKEN="));
});


test("Google consent has exactly three independently gated metadata-only HTTP routes", () => {
  const nginx = read("nginx.railway.conf");
  const blocks = locations(nginx);
  const routes = new Map([
    ["/api/drive/oauth/start", ["POST", "/internal/drive/oauth/start"]],
    ["/api/drive/oauth/callback", ["GET", "/internal/drive/oauth/callback"]],
    ["/api/drive/oauth/status", ["GET", "/internal/drive/oauth/status"]],
  ]);
  assert.ok(nginx.includes('set $p1ao_google_ingress "${P1AO_GOOGLE_INGRESS_ENABLED}";'));
  for (const [path,[method,internal]] of routes) {
    const b = blocks.get(path);
    assert.ok(b, path);
    for(const gate of [
      'if ($p1ao_google_ingress != "1") { return 404; }',
      'if ($p1ak_owner_ingress != "1") { return 404; }',
      'if ($p1ak_gateway_token = "") { return 503; }',
      'if ($host != "'+host+'") { return 403; }',
      'if ($request_method != "'+method+'") { return 405; }',
      'proxy_set_header X-Personal-CFO-Private-Gateway $p1ak_gateway_token;',
      'proxy_set_header X-Forwarded-Proto https;',
      'proxy_set_header Forwarded "";',
      'access_log off;',
      'error_log /dev/null crit;',
    ]) assert.ok(b.includes(gate), path+" missing "+gate);
    const suffix = path.endsWith("/callback") ? "$is_args$args" : "";
    assert.ok(b.includes("proxy_pass http://$private_google_upstream"+internal+suffix+";"));
    assert.ok(b.includes("client_max_body_size 1k;"));
    assert.ok(b.includes("limit_req zone=cfo_owner_global burst=12 nodelay;"));
    assert.ok(!b.includes("$request_uri"));
    if (path.endsWith("/callback")) {
      assert.ok(!b.includes('if ($args != "") { return 400; }'));
    } else {
      assert.ok(b.includes('if ($args != "") { return 400; }'));
    }
  }
  for (const blocked of ["/api/drive/oauth/disconnect","/api/drive/files",
                         "/api/finance", "/api/owner/recovery"]) {
    assert.ok(!blocks.has(blocked));
  }
  const docker = read("Dockerfile");
  assert.ok(docker.includes('ENV P1AK_OWNER_INGRESS_ENABLED=0 P1AO_GOOGLE_INGRESS_ENABLED=0 P1Q_PRIVATE_GATEWAY_SHARED_TOKEN=""'));
  assert.ok(!docker.includes("P1AO_GOOGLE_INGRESS_ENABLED=1"));
});

test("post-redirect session resumes Google status with memory-only CSRF", () => {
  const js = read("owner-login.mjs");
  const html = read("owner-login.html");
  assert.ok(html.includes('id="owner-google-status"'));
  assert.ok(html.includes('id="owner-google-connect"'));
  assert.ok(js.includes('"/api/owner/session"'));
  assert.ok(js.includes('"/api/drive/oauth/status"'));
  assert.ok(js.includes('"/api/drive/oauth/start"'));
  assert.ok(js.includes("approvedGoogleConsentUrl"));
  assert.ok(js.includes('url.origin !== "https://accounts.google.com"'));
  assert.ok(js.includes('url.pathname !== "/o/oauth2/v2/auth"'));
  assert.ok(js.includes('"https://www.googleapis.com/auth/drive.metadata.readonly"'));
  assert.ok(js.includes("window.location.assign(url.href)"));
  assert.ok(js.includes("void resumePrivateOwnerSession()"));
  for (const forbidden of ["localStorage.setItem","sessionStorage.setItem",
                           "document.cookie =", "console.log"]) {
    assert.ok(!js.includes(forbidden), forbidden);
  }
});
