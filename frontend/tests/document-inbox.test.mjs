import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {
  FICTIONAL_INBOX,selectFictionalInbox,summarizeFictionalInbox,
  renderFictionalDocumentInbox,
} from "../document-inbox.mjs";

const sibling=(name)=>readFileSync(new URL("../"+name,import.meta.url),"utf8");

test("one-folder mobile documents navigation is visible in desktop and phone",()=>{
  const html=sibling("index.html"),main=sibling("ui.mjs"),css=sibling("ui.css"),pwa=sibling("pwa.css");
  assert.match(html,/data-view="documents"/);
  assert.match(html,/>Docs<\/button>/);
  assert.match(main,/documents:\(\)=>renderFictionalDocumentInbox\(state\.docFilter\)/);
  assert.match(main,/data-doc-filter/);
  assert.match(css,/doc-inbox/);
  assert.match(pwa,/grid-template-columns:repeat\(5,minmax\(0,1fr\)\)/);
  assert.doesNotMatch(html,/type=["']file["']/i);
  assert.doesNotMatch(main, /fetch\(["']https?:/);
});

test("only fictional documents can enter demo inventory",()=>{
  const info=summarizeFictionalInbox();
  assert.equal(info.sampleFiles,FICTIONAL_INBOX.length);
  assert.equal(info.verifiedOriginals,0);
  assert.equal(info.realFinancialRecordsImported,0);
  assert.ok(info.needingAttention>0);
  assert.ok(FICTIONAL_INBOX.every(item=>item.id.startsWith("fictional-doc-")));
  const html=renderFictionalDocumentInbox();
  assert.match(html,/FICTIONAL PREVIEW/);
  assert.match(html,/APP CONNECTION PENDING/);
  assert.match(html,/The ChatGPT Drive connection is separate/);
  assert.match(html,/Actual synced files/);
  assert.match(html,/Not available/);
  assert.match(html,/No financial data is imported/);
  assert.doesNotMatch(html,/1ilpwMGNRP2JCUcdtsBfqanF4-ULDSeA5/);
  assert.doesNotMatch(html,/Authorization: Bearer|refresh_token|\.apps\.googleusercontent\.com/);
});

test("review filters keep changed, duplicate and missing distinct",()=>{
  assert.equal(selectFictionalInbox("all").length,FICTIONAL_INBOX.length);
  assert.equal(selectFictionalInbox("new").length,1);
  assert.equal(selectFictionalInbox("changed").length,1);
  assert.equal(selectFictionalInbox("duplicate").length,1);
  assert.equal(selectFictionalInbox("missing").length,1);
  assert.ok(selectFictionalInbox("attention").every(x=>x.status!=="new"));
  assert.throws(()=>selectFictionalInbox("untrusted_filter"),RangeError);
  assert.match(renderFictionalDocumentInbox("missing"),/No longer visible/);
  assert.doesNotMatch(renderFictionalDocumentInbox("missing"),/Possible duplicate statement/);
});

test("untrusted status and titles cannot form XSS from future queue input",()=>{
  const html=renderFictionalDocumentInbox("all");
  assert.ok(html.includes('aria-pressed="true"'));
  assert.ok(!html.includes("<script"));
  // The public component never accepts external records at all.
  assert.throws(()=>selectFictionalInbox("all",{}),TypeError);
});

test("local authenticated backend has module route, public preview does not add document intake",()=>{
  const app=sibling("../backend/app/main.py");
  assert.ok(app.includes('@app.get("/document-inbox.mjs"'));
  const publicPreview=sibling("../backend/app/preview_api.py");
  assert.ok(!publicPreview.includes("@app.get(\"/api/drive"));
  const nginx=sibling("nginx.railway.conf");
  assert.ok(nginx.includes("location ~* \\.mjs$"));
  assert.match(sibling("sw.js"),/NO fetch handler/);
});
