import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const read=n=>readFileSync(new URL("../"+n,import.meta.url),"utf8");
test("every finance screen is reachable directly on mobile without desktop sidebar",()=>{
  const html=read("app.html");
  const nav=html.slice(html.indexOf('<nav id="bottom-nav"'),html.indexOf("</nav>",html.indexOf('<nav id="bottom-nav"')));
  const names=["home","accounts","transactions","investments","spending","tax","documents"];
  const actual=[...nav.matchAll(/data-view="([a-z]+)"/g)].map(m=>m[1]);
  assert.deepEqual(actual,names);
  assert.equal(new Set(actual).size,7);
  for(const name of actual)assert.ok(html.includes('id="view-'+name+'"'),name);
  assert.ok(actual.indexOf("documents")>actual.indexOf("tax"));
  assert.ok(actual.indexOf("transactions")<actual.indexOf("documents"));
});
test("mobile navigation is thumb-friendly and preserves session-only selection",()=>{
  const css=read("app.css"),js=read("app.mjs");
  assert.match(css,/\.bottom-nav button\{min-width:44px;min-height:44px/);
  assert.match(js,/for \(const btn of document\.querySelectorAll\("\[data-view\], \[data-go\]"\)\)/);
  assert.match(js,/btn\.addEventListener\("click",\(\)=>go\(/);
  assert.doesNotMatch(js,/localStorage|sessionStorage|innerHTML|console\.log/);
});
