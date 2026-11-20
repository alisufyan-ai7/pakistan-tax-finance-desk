import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const read=n=>readFileSync(new URL("../"+n,import.meta.url),"utf8");

test("premium financial Home shows the source-backed answers first and folds technical evidence",()=>{
  const html=read("app.html"),css=read("owner-premium.css"),docker=read("Dockerfile");
  assert.ok(html.includes('<link rel="stylesheet" href="/owner-premium.css">'));
  assert.ok(docker.includes("owner-premium.css"));
  for(const phrase of [
    "Know where your money stands.",
    "Latest available bank snapshot",
    "Bank profit · chosen period",
    "Recorded property cost",
    "Property sale profit · chosen period",
  ])assert.ok(html.includes(phrase),phrase);
  const home=html.indexOf('id="view-home"');
  const metrics=html.indexOf('id="home-source-evidence-metrics"',home);
  const evidence=html.indexOf('id="home-financial-period-panel"',home);
  const review=html.indexOf('id="home-owner-review"',home);
  const audit=html.indexOf('id="home-source-drawer"',home);
  assert.ok(home<metrics&&metrics<evidence&&evidence<review&&review<audit);
  assert.ok(html.includes('<details class="advanced-source-drawer"'));
  assert.ok(html.includes('<summary>Original source evidence and verification'));
  assert.ok(!html.includes('Financial timeline</h3>'));
  for(const id of ["home-historical-evidence","home-bank-csv-evidence",
    "home-attested-bahl-pdf","home-property-investments","document-count",
    "home-document-priorities"]) assert.ok(html.includes('id="'+id+'"'),id);
  assert.ok(css.includes("grid-template-columns:minmax(0,1.3fr) minmax(285px,.95fr)"));
  assert.ok(css.includes("@media(prefers-reduced-motion:reduce)"));
});

test("mobile app exposes four thumb tabs and More without losing Tax, Spending, Docs or Account",()=>{
  const html=read("app.html"),css=read("owner-premium.css"),js=read("app.mjs");
  assert.ok(html.includes('id="mobile-more-toggle" aria-controls="mobile-more-menu" aria-expanded="false"'));
  assert.ok(html.includes('id="mobile-more-menu" class="mobile-more-menu"'));
  assert.ok(html.includes('class="mobile-account-link" href="/owner-login"'));
  assert.ok(css.includes("grid-template-columns:repeat(5,minmax(0,1fr))"));
  assert.ok(css.includes("min-height:53px"));
  assert.ok(js.includes('byId("mobile-more-toggle").addEventListener("click"'));
  assert.ok(js.includes('byId("mobile-more-toggle").setAttribute('));
  assert.ok(js.includes('if(event.key==="Escape")closeMobileMore()'));
  assert.ok(js.includes('btn.addEventListener("click",closeMobileMore)'));
  assert.ok(js.includes('byId("bottom-nav").hidden = true'));
});

test("transaction detail sheet is source-only, never edits or stores money and is keyboard dismissable",()=>{
  const html=read("app.html"),js=read("app.mjs"),css=read("owner-premium.css");
  assert.ok(html.includes('<dialog id="transaction-detail-dialog"'));
  assert.ok(html.includes('aria-labelledby="transaction-detail-title"'));
  for(const id of ["transaction-detail-amount","transaction-detail-date",
    "transaction-detail-description","transaction-detail-source","transaction-detail-row",
    "transaction-detail-balance","transaction-detail-category","transaction-detail-review",
    "transaction-detail-close","transaction-detail-documents"])
    assert.ok(html.includes('id="'+id+'"'),id);
  assert.ok(js.includes("function openTransactionDetail(tx){"));
  assert.ok(js.includes('inspect.addEventListener("click",()=>openTransactionDetail(tx))'));
  assert.ok(js.includes("dialog.showModal()"));
  assert.ok(js.includes("dialog.close()"));
  assert.ok(js.includes('byId("transaction-detail-description").textContent=tx.description'));
  assert.ok(js.includes('closeTransactionDetail();\n  clearBankCsvEvidence();'));
  assert.ok(css.includes("dialog.transaction-dialog::backdrop"));
  for(const forbidden of ["localStorage","sessionStorage","innerHTML","document.cookie","console.log"])
    assert.ok(!js.includes(forbidden),forbidden);
});

test("modern owner login preserves strong native auth inputs and no public marketing or credential links",()=>{
  const html=read("owner-login.html"),style=read("owner-login.css"),
    js=read("owner-login.mjs");
  assert.ok(html.includes('id="owner-login-form"'));
  assert.ok(html.includes('type="password"'));
  assert.ok(html.includes('autocomplete="one-time-code"'));
  assert.ok(html.includes('pattern="[0-9]{6}"'));
  assert.ok(html.includes("Welcome back."));
  assert.ok(html.includes("auth-brand"));
  assert.ok(style.includes("min-height:100dvh"));
  assert.ok(style.includes("input:focus-visible"));
  assert.ok(html.includes('href="/app"'));
  assert.ok(html.includes('href="/app" class="back">Return to Personal CFO'));
  for(const forbidden of ["localStorage.setItem","localStorage.getItem",
      "sessionStorage.setItem","sessionStorage.getItem","console.log"])
    assert.ok(!js.includes(forbidden),forbidden);
});
