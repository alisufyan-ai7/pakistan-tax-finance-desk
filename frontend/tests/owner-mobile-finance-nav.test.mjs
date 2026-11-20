import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const read=n=>readFileSync(new URL("../"+n,import.meta.url),"utf8");
test("compact mobile finance navigation keeps every screen reachable via More menu",()=>{
  const html=read("app.html");
  const nav=html.slice(html.indexOf('<nav id="bottom-nav"'),html.indexOf("</nav>",html.indexOf('<nav id="bottom-nav"')));
  const more=html.slice(html.indexOf('<nav id="mobile-more-menu"'),html.indexOf("</nav>",html.indexOf('<nav id="mobile-more-menu"')));
  const primary=["home","accounts","transactions","investments"];
  const secondary=["spending","tax","documents"];
  assert.deepEqual([...nav.matchAll(/data-view="([a-z]+)"/g)].map(m=>m[1]),primary);
  assert.deepEqual([...more.matchAll(/data-view="([a-z]+)"/g)].map(m=>m[1]),secondary);
  for(const view of [...primary,...secondary])assert.ok(html.includes('id="view-'+view+'"'),view);
  assert.match(nav,/id="mobile-more-toggle"/);
  assert.match(nav,/aria-expanded="false"/);
  assert.match(more,/hidden/);
});
test("mobile navigation is thumb-friendly and preserves session-only selection",()=>{
  const css=read("app.css"),js=read("app.mjs");
  assert.match(css,/\.bottom-nav button\{min-width:44px;min-height:44px/);
  assert.match(js,/for \(const btn of document\.querySelectorAll\("\[data-view\], \[data-go\]"\)\)/);
  assert.match(js,/btn\.addEventListener\("click",\(\)=>go\(/);
  assert.match(js,/mobile-more-toggle/);
  assert.match(js,/closeMobileMore/);
  assert.match(read("owner-premium.css"),/grid-template-columns:repeat\(5,minmax\(0,1fr\)\)/);
  assert.doesNotMatch(js,/localStorage|sessionStorage|innerHTML|console\.log/);
});
