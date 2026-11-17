import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {renderFictionalDocumentInbox} from "../document-inbox.mjs";
import {FICTIONAL_HEALTH_STATES} from "../document-review-states.mjs";

const source=p=>readFileSync(new URL("../"+p,import.meta.url),"utf8");

test("merged Documents views remain fictional after security and scan lease branches",()=>{
  assert.equal(FICTIONAL_HEALTH_STATES.length,6);
  const html=renderFictionalDocumentInbox("attention","revoked");
  assert.match(html,/APP CONNECTION PENDING/);
  assert.match(html,/No financial data is imported/);
  assert.match(html,/Reauthorization required/);
  assert.match(html,/SIMULATED SCAN STATES/);
  assert.doesNotMatch(html,/background job started|Google Drive connected/i);
});

test("combined frontend still has no public OAuth, owner-login or sync path",()=>{
  const nginx=source("nginx.railway.conf");
  const ui=source("ui.mjs"),sw=source("sw.js");
  assert.match(nginx,/location = \/api\/preview\/status/);
  assert.doesNotMatch(nginx,/location = \/api\/drive\/oauth\/callback/);
  assert.doesNotMatch(nginx,/location \/api\//);
  assert.doesNotMatch(nginx,/location = \/api\/owner\/login/);
  assert.doesNotMatch(ui,/fetch\(["']https?:/);
  assert.match(sw,/NO fetch handler/);
});
