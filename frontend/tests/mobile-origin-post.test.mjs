import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";

// Regression for iOS WebKit / Chrome iOS: mode=same-origin combined with
// referrerPolicy=no-referrer can send Origin:null on POST, but the private
// gateway correctly rejects a missing/non-HTTPS Origin. Keep that gateway.
const read = name => readFileSync(new URL("../"+name,import.meta.url),"utf8");

test("owner password+MFA POST preserves a real browser Origin without referrer leakage",async()=>{
  const js=read("owner-login.mjs");
  const requestSrc=js.match(/^async function request\(path, body, csrf\) \{[\s\S]*?^\}/m)?.[0];
  assert.ok(requestSrc,"extract the exact private request helper");
  let called;
  const request=runInNewContext("("+requestSrc+")",{
    fetch:async(path,options)=>{
      called={path,options};
      return {ok:true};
    },
  });
  const payload='{"password":"SYNTHETIC_ONLY","totp_code":"000000"}';
  await request("/api/owner/login",payload,null);
  assert.equal(called.path,"/api/owner/login");
  assert.equal(called.options.method,"POST");
  assert.equal(called.options.mode,"cors");
  assert.equal(called.options.credentials,"same-origin");
  assert.equal(called.options.referrerPolicy,"no-referrer");
  assert.equal(called.options.redirect,"error");
  assert.equal(called.options.cache,"no-store");
  assert.equal(called.options.headers["Content-Type"],"application/json");
  assert.equal(called.options.body,payload);
  assert.equal(called.options.headers["X-CSRF-Token"],undefined);
  await request("/api/owner/logout","{}","SYNTHETIC_CSRF");
  assert.equal(called.options.mode,"cors");
  assert.equal(called.options.headers["X-CSRF-Token"],"SYNTHETIC_CSRF");
  assert.ok(!js.includes("localStorage")&&!js.includes("sessionStorage"));
});

test("private metadata refresh also preserves Origin and existing CSRF/session protection",()=>{
  const js=read("app.mjs");
  const block=js.match(/fetch\("\/api\/drive\/metadata\/refresh", \{([\s\S]*?)\n    \}\);/)?.[1];
  assert.ok(block,"bounded exact same-origin metadata POST");
  assert.match(block,/\.\.\.requestOptions/);
  assert.match(block,/method:"POST"/);
  assert.match(block,/mode:"cors"/);
  assert.match(block,/X-CSRF-Token":csrfToken/);
  assert.match(js,/credentials: "same-origin"/);
  assert.match(js,/referrerPolicy: "no-referrer"/);
  assert.match(js,/mode: "same-origin"/); // GET remains strict same-origin
  assert.ok(!js.includes("localStorage")&&!js.includes("sessionStorage"));
});

test("only fix browser Origin serialization; never weaken exact private gateway",()=>{
  const login=read("owner-login.mjs"),nginx=read("nginx.railway.conf");
  assert.match(login,/fetch\(path, \{/);
  for(const exact of ['"/api/owner/login"','"/api/owner/logout"','"/api/drive/oauth/start"']){
    assert.ok(login.includes(exact));
  }
  assert.match(nginx,/location = \/api\/owner\/login/);
  assert.match(nginx,/proxy_set_header X-Personal-CFO-Private-Gateway \$p1ak_gateway_token/);
  assert.match(nginx,/if \(\$host != "personal-cfo-frontend-preview-development.up.railway.app"\) \{ return 403; \}/);
});
