import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const read=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");

test("private installed app opens authenticated dashboard, not fictional preview",()=>{
  const m=JSON.parse(read("owner-manifest.webmanifest"));
  const historical=JSON.parse(read("manifest.webmanifest"));
  assert.equal(m.id,"/app");
  assert.equal(m.start_url,"/app");
  assert.equal(m.scope,"/");
  assert.equal(m.display,"standalone");
  assert.match(m.description,/private|verified/i);
  assert.equal(historical.start_url,"/"); // public synthetic PWA left unchanged
  assert.deepEqual(m.icons.map(x=>x.src),["/icons/icon-192.png","/icons/icon-512.png"]);
  const html=read("app.html");
  assert.match(html,/rel="manifest" href="\/owner-manifest.webmanifest"/);
  assert.match(html,/id="install-owner-app"/);
  assert.match(html,/id="owner-install-help"/);
  assert.match(html,/src="\/owner-pwa.mjs"/);
});
test("private install never caches authenticated API or leaves PWA in fictional mode",()=>{
  const js=read("owner-pwa.mjs"),sw=read("sw.js"),docker=read("Dockerfile");
  for(const s of ["beforeinstallprompt","appinstalled","Add to Home Screen",
    'navigator.serviceWorker.register("/sw.js"']) assert.ok(js.includes(s),s);
  assert.ok(docker.includes("owner-pwa.mjs owner-manifest.webmanifest"));
  for(const forbidden of ["localStorage","sessionStorage","document.cookie",
    "caches.open","caches.match","cache.put","/api/owner/","/api/drive/"]) {
    assert.ok(!js.includes(forbidden),forbidden);
  }
  assert.ok(!sw.includes('addEventListener("fetch"'));
  assert.ok(!sw.includes("caches.open"));
});
test("owner install manifest is an exact gated Nginx location",()=>{
  const ng=read("nginx.railway.conf");
  const match=ng.match(/location = \/owner-manifest\.webmanifest \{([\s\S]*?)\n    \}/);
  assert.ok(match);
  const b=match[1];
  for(const v of ['if ($p1ak_owner_ingress != "1") { return 404; }',
    'if ($request_method != "GET") { return 405; }',
    'try_files /owner-manifest.webmanifest =404;',
    'access_log off;', 'personal-cfo-frontend-preview-development.up.railway.app'])
    assert.ok(b.includes(v),v);
  assert.ok(!ng.includes("location /api/"));
});
