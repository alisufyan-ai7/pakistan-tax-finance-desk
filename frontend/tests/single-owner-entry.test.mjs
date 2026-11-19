import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const read = file => readFileSync(new URL("../"+file,import.meta.url),"utf8");
const locations = text => new Map([...text.matchAll(/location = ([^ ]+) \{([\s\S]*?)\n    \}/g)].map(m=>[m[1],m[2]]));

test("owner Railway root redirects only into guarded private app, never synthetic HTML",()=>{
 const config=read("nginx.railway.conf"),routes=locations(config);
 const root=routes.get("/");
 assert.ok(root);
 assert.match(root,/return 302 \/app;/);
 assert.match(root,/if \(\$request_method != "GET"\) \{ return 405; \}/);
 assert.match(root,/if \(\$args != ""\) \{ return 400; \}/);
 assert.ok(!root.includes("index.html"));
 assert.match(routes.get("/index.html")||"",/return 404;/);
 const app=routes.get("/app"),login=routes.get("/owner-login");
 assert.match(app,/if \(\$p1ak_owner_ingress != "1"\) \{ return 404; \}/);
 assert.match(app,/try_files \/app.html =404;/);
 assert.match(login,/try_files \/owner-login.html =404;/);
 assert.match(routes.get("/app.html")||"",/return 404;/);
 assert.match(routes.get("/owner-login.html")||"",/return 404;/);
 assert.match(config,/Cache-Control "no-store" always;/);
});

test("public install manifest is retired while existing private PWA manifest survives",()=>{
 const config=read("nginx.railway.conf"),routes=locations(config);
 assert.match(routes.get("/manifest.webmanifest")||"",/return 404;/);
 const privateManifest=routes.get("/owner-manifest.webmanifest");
 assert.match(privateManifest||"",/if \(\$p1ak_owner_ingress != "1"\) \{ return 404; \}/);
 assert.match(privateManifest,/try_files \/owner-manifest.webmanifest =404;/);
 const manifest=JSON.parse(read("owner-manifest.webmanifest"));
 assert.equal(manifest.id,"/app");
 assert.equal(manifest.start_url,"/app");
 assert.equal(manifest.display,"standalone");
 const owner=read("app.html");
 assert.match(owner,/href="\/owner-manifest.webmanifest"/);
 assert.doesNotMatch(owner,/href="\/manifest.webmanifest"/);
 const worker=read("sw.js");
 assert.doesNotMatch(worker,/addEventListener\(["']fetch["']|caches\.open|caches\.match|cache\.put/);
});

test("owner login and root do not link back to fictional public preview",()=>{
 const login=read("owner-login.html"),app=read("app.html");
 assert.match(login,/href="\/app" class="back">Return to Personal CFO/);
 assert.doesNotMatch(login,/Return to Personal CFO preview/);
 assert.doesNotMatch(app,/demo-data.mjs|manifest.webmanifest"[^>]*href="\/manifest/);
 assert.match(login,/name="totp_code"/);
 assert.match(login,/type="password"/);
 const config=read("nginx.railway.conf");
 assert.match(config,/location = \/api\/owner\/login/);
 assert.match(config,/location = \/api\/owner\/session/);
 assert.match(config,/location = \/api\/owner\/logout/);
 assert.doesNotMatch(config,/location \/api\//);
});
