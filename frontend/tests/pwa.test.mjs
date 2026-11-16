import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const get = name => readFileSync(new URL("../"+name,import.meta.url));
const source=name=>get(name).toString("utf8");

test("installable manifest is scoped to the fictional public dashboard",()=>{
  const manifest=JSON.parse(source("manifest.webmanifest"));
  assert.equal(manifest.display,"standalone");
  assert.equal(manifest.start_url,"/");
  assert.equal(manifest.scope,"/");
  assert.equal(manifest.lang,"en-PK");
  assert.equal(manifest.prefer_related_applications,false);
  assert.ok(manifest.name.includes("Personal CFO"));
  assert.deepEqual(manifest.icons.map(x=>x.sizes),["192x192","512x512"]);
  assert.ok(manifest.icons.every(x=>x.src.startsWith("/icons/")&&x.type==="image/png"));
  assert.ok(!("shortcuts" in manifest));
});

test("PWA home icons are valid PNG of the advertised dimensions",()=>{
  for(const n of [192,512]){
    const data=get("icons/icon-"+n+".png");
    assert.deepEqual([...data.subarray(0,8)],[137,80,78,71,13,10,26,10]);
    assert.equal(data.readUInt32BE(16),n);
    assert.equal(data.readUInt32BE(20),n);
  }
});

test("no service worker financial data caching, sync, background finance or push",()=>{
  const sw=source("sw.js");
  assert.match(sw,/addEventListener\("install"/);
  assert.match(sw,/addEventListener\("activate"/);
  assert.doesNotMatch(sw,/addEventListener\(["']fetch["']|caches\.open|caches\.match|cache\.put|sync\.register/);
  assert.doesNotMatch(sw,/addEventListener\(["']push["']/);
  assert.doesNotMatch(sw,/\/api\/|localStorage|sessionStorage/);
});

test("install instructions support iOS manual path and Android browser install",()=>{
  const ui=source("pwa.mjs"),html=source("index.html"),css=source("pwa.css");
  assert.match(ui,/beforeinstallprompt/);
  assert.match(ui,/Add to Home Screen/);
  assert.match(ui,/Open as Web App/);
  assert.match(ui,/appinstalled/);
  assert.match(html,/rel="manifest"/);
  assert.match(html,/apple-touch-icon/);
  assert.match(html,/id="installApp"/);
  assert.match(html,/id="installHelp"/);
  assert.match(html,/mobile-bottom-nav/);
  assert.match(css,/safe-area-inset-bottom/);
  assert.match(css,/min-height:51px/);
});

test("Railway Docker allowlists only public PWA files and one private API route remains",()=>{
  const docker=source("Dockerfile"), nginx=source("nginx.railway.conf");
  assert.match(docker,/COPY icons\/ \/usr\/share\/nginx\/html\/icons\//);
  assert.match(docker,/COPY manifest\.webmanifest sw\.js pwa\.mjs pwa\.css/);
  assert.doesNotMatch(docker,/COPY\s+\.|COPY\s+backend\//);
  assert.match(nginx,/manifest-src 'self'/);
  assert.match(nginx,/worker-src 'self'/);
  assert.match(nginx,/location = \/manifest\.webmanifest/);
  assert.match(nginx,/location = \/sw\.js/);
  assert.match(nginx,/location = \/api\/preview\/status/);
  assert.doesNotMatch(nginx,/proxy_pass.*\/api\/accounts/);
});
