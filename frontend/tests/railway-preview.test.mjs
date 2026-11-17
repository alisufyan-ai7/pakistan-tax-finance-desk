import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const get = name => readFileSync(new URL("../" + name, import.meta.url), "utf8");

test("Railway preview serves fictional allowlisted assets only", () => {
  const docker = get("Dockerfile");
  assert.match(docker, /FROM nginxinc\/nginx-unprivileged:stable-alpine/);
  assert.match(docker, /COPY index\.html ui\.css ui\.mjs demo-data\.mjs document-inbox\.mjs \/usr\/share\/nginx\/html\//);
  assert.doesNotMatch(docker, /COPY\s+\.|legacy-import|\.env|backend|secrets/i);
  assert.match(docker, /EXPOSE 8080/);
  assert.match(get("ui.mjs"), /import \{ renderFictionalDocumentInbox \} from "\.\/document-inbox\.mjs"/);
  assert.match(docker, /document-inbox\.mjs/);
});

test("Railway preview does not accept real uploads, external scripts or data egress", () => {
  const nginx = get("nginx.railway.conf");
  assert.match(nginx, /listen 8080/);
  assert.match(nginx, /connect-src 'self'/);
  assert.match(nginx, /script-src 'self'/);
  assert.match(nginx, /frame-ancestors 'none'/);
  assert.match(nginx, /form-action 'none'/);
  assert.match(nginx, /noindex, nofollow/);
  assert.match(nginx, /X-Content-Type-Options "nosniff"/);
  assert.match(nginx, /location = \/healthz/);
  assert.match(nginx, /location = \/api\/preview\/status/);
  assert.match(nginx, /resolver \[fd12::10\] valid=5s ipv6=off/);
  assert.match(nginx, /set \$private_preview_upstream "personal-cfo-api-preview\.railway\.internal:8000"/);
  assert.match(nginx, /proxy_pass http:\/\/\$private_preview_upstream\/internal\/preview\/status\$is_args\$args/);
  assert.doesNotMatch(nginx, /proxy_pass http:\/\/personal-cfo-api-preview\.railway\.internal/);
  assert.match(nginx, /location = \/api\/preview\/status/);
  assert.match(nginx, /limit_except GET \{ deny all; \}/);
  assert.match(nginx, /X-Personal-CFO-Preview-Key/);
  assert.match(get("Dockerfile"), /NGINX_ENVSUBST_FILTER/);
  assert.doesNotMatch(nginx, /fastcgi_pass|alias\s|autoindex on/);
  // A registered Google redirect URI does NOT open a safe OAuth endpoint.
  // The public synthetic preview must deny callback/start routes until G2.
  assert.doesNotMatch(nginx, /location\s*=\s*\/api\/drive\/oauth\/callback/);
  assert.doesNotMatch(nginx, /proxy_pass[^;]*\/api\/drive\//);
});
