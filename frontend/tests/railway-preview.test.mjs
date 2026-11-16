import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const get = name => readFileSync(new URL("../" + name, import.meta.url), "utf8");

test("Railway preview serves fictional allowlisted assets only", () => {
  const docker = get("Dockerfile");
  assert.match(docker, /FROM nginxinc\/nginx-unprivileged:stable-alpine/);
  assert.match(docker, /COPY index\.html ui\.css ui\.mjs demo-data\.mjs \/usr\/share\/nginx\/html\//);
  assert.doesNotMatch(docker, /COPY\s+\.|legacy-import|\.env|backend|secrets/i);
  assert.match(docker, /EXPOSE 8080/);
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
  assert.match(nginx, /proxy_pass http:\/\/personal-cfo-api-preview\.railway\.internal:8000\/internal\/preview\/status/);
  assert.match(nginx, /X-Personal-CFO-Preview-Key/);
  assert.match(get("Dockerfile"), /NGINX_ENVSUBST_FILTER/);
  assert.doesNotMatch(nginx, /fastcgi_pass|alias\s|autoindex on/);
});
