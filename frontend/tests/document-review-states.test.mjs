import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {FICTIONAL_HEALTH_STATES, selectedFictionalReviewState,
        renderFictionalReviewHealth} from "../document-review-states.mjs";
import {renderFictionalDocumentInbox} from "../document-inbox.mjs";

const source=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");

test("six distinct fictional scan/review states explain actionable followups",()=>{
  assert.deepEqual(FICTIONAL_HEALTH_STATES.map(x=>x.id),
    ["never","stale","revoked","changed","missing","duplicates"]);
  for(const state of FICTIONAL_HEALTH_STATES){
    const view=renderFictionalReviewHealth(state.id);
    assert.match(view,/SIMULATED SCAN STATES/);
    assert.match(view,/Demo scenarios only/);
    assert.match(view,/No running scan/);
    assert.match(view,/UNKNOWN|UNVERIFIED/);
    assert.match(view,/Follow-up:/);
    assert.match(view,new RegExp(state.id+'".*aria-pressed="true"'));
    assert.doesNotMatch(view, /(?:access_token|refresh_token|Bearer|apps.googleusercontent.com)/);
    assert.equal(selectedFictionalReviewState(state.id),state);
  }
  assert.throws(()=>renderFictionalReviewHealth("<script>alert(1)</script>"),RangeError);
  assert.throws(()=>selectedFictionalReviewState({label:"connected"}),RangeError);
});

test("never-scanned and access-lost never claim latest owner data",()=>{
  const never=renderFictionalDocumentInbox("all","never");
  const revoked=renderFictionalDocumentInbox("missing","revoked");
  assert.match(never,/No verified scan yet/);
  assert.match(never,/No actual file coverage/);
  assert.match(revoked,/Reauthorization required/);
  assert.match(revoked,/Earlier statement not visible/);
  assert.match(revoked,/No longer visible/);
  for(const html of [never,revoked]){
    assert.match(html,/APP CONNECTION PENDING/);
    assert.match(html,/FICTIONAL PREVIEW/);
    assert.match(html,/Actual synced files/);
    assert.match(html,/Not available/);
    assert.match(html,/No financial data is imported/);
    assert.doesNotMatch(html,/<script|type="file"|upload="true"/i);
  }
});

test("mobile and keyboard support clear UI state and no network",()=>{
  const css=source("pwa.css"),ui=source("ui.mjs");
  const html=source("index.html"),sw=source("sw.js");
  assert.match(ui,/docHealth:"never"/);
  assert.match(ui,/state\.docHealth=name;render\(\)/);
  assert.match(ui,/data-doc-health/);
  assert.match(css,/\.doc-health-option:focus-visible/);
  assert.match(css,/min-height:44px/);
  assert.match(css,/@media\(max-width:610px\)/);
  assert.match(html,/data-view="documents"/);
  assert.match(html,/\<noscript\>/);
  assert.match(sw,/NO fetch handler/);
  assert.doesNotMatch(ui,/fetch\(["']https?:/i);
  assert.doesNotMatch(source("document-review-states.mjs"), /\bfetch\(/);
});

test("no real file names or balance claims enter scenario data",()=>{
  for(const state of FICTIONAL_HEALTH_STATES){
    assert.ok(Object.isFrozen(state));
    assert.ok(!/real synced|connected successfully|payment confirmed|filed return verified/i
      .test(JSON.stringify(state)));
    assert.match(state.evidence,/^(UNKNOWN|UNVERIFIED) /);
  }
  assert.ok(Object.isFrozen(FICTIONAL_HEALTH_STATES));
});
