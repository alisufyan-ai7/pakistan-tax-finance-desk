import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {DEMO,formatPKR,yearFromDate,transactionsForYear,summaryForYear,
  coverageSummary,monthlyMovement,hypotheticalBuffer} from "../demo-data.mjs";

function sibling(name){return readFileSync(new URL("../"+name,import.meta.url),"utf8");}

test("July to June Pakistan tax-year labels do not shift year boundaries",()=>{
  assert.equal(yearFromDate("2025-06-30"),2025);
  assert.equal(yearFromDate("2025-07-01"),2026);
  assert.equal(yearFromDate("2026-11-16"),2027);
  assert.throws(()=>yearFromDate("bad"),TypeError);
  assert.throws(()=>yearFromDate("2026-13-01"),TypeError);
});

test("synthetic movements exclude own-account transfers from income and expenses",()=>{
  const rows=transactionsForYear(2027);
  assert.ok(rows.length>2);
  const summary=summaryForYear(2027);
  assert.equal(summary.transferCount,1);
  assert.equal(summary.incomeMinor,
    rows.filter(x=>x.direction==="in").reduce((sum,x)=>sum+x.amountMinor,0));
  assert.equal(summary.outflowMinor,
    rows.filter(x=>x.direction==="out").reduce((sum,x)=>sum+x.amountMinor,0));
  assert.equal(transactionsForYear(2026,"insurance").length,1);
  assert.equal(transactionsForYear(2027,"INSURANCE").length,0);
});

test("coverage does not treat missing, partial or unsupported as verified balances",()=>{
  for(const y of DEMO.years){
    const status=coverageSummary(y);
    assert.equal(status.accountMonths,36);
    assert.ok(status.counts.missing+status.counts.partial+status.counts.unsupported>0);
  }
  assert.equal(coverageSummary(2027).counts.observed>0,true);
  assert.throws(()=>coverageSummary(2028),RangeError);
});

test("hypothetical buffer shortfall is not an observed bank balance",()=>{
  assert.deepEqual(hypotheticalBuffer({
    openingMinor:null,monthlyEssentialMinor:6000000,months:3
  }),{targetMinor:18000000,shortfallMinor:null,
    coverageVerified:false,scenarioOnly:true});
  const result=hypotheticalBuffer({
    openingMinor:8000000,monthlyEssentialMinor:6000000,months:3
  });
  assert.equal(result.shortfallMinor,10000000);
  assert.equal(result.scenarioOnly,true);
  assert.throws(()=>formatPKR(12.5),TypeError);
  assert.throws(()=>hypotheticalBuffer({openingMinor:100,monthlyEssentialMinor:500,months:13}),RangeError);
});

test("cashflow chart months are July through June and source-led",()=>{
  assert.deepEqual(monthlyMovement(2027).map(x=>x.label),
    ["Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun"]);
  assert.ok(monthlyMovement(2027).every(x=>Number.isSafeInteger(x.incoming)&&Number.isSafeInteger(x.outgoing)));
});

test("frontend has seven navigable sections, a visible synthetic warning and no upload field",()=>{
  const html=sibling("index.html"),ui=sibling("ui.mjs");
  for(const view of ["overview","accounts","transactions","accountant","tax","planning","security"])
    assert.ok(html.includes('data-view="'+view+'"'),view);
  for(const warning of ["synthetic","Do not enter personal financial information","Checking private synthetic backend"])
    assert.match(html,new RegExp(warning,"i"));
  assert.ok(html.includes('id="app"'));
  assert.ok(html.includes('type="module" src="./ui.mjs"'));
  assert.ok(html.includes('aria-live'));
  assert.doesNotMatch(html,/type=["']file["']/i);
  assert.match(ui,/fetch\("\/api\/preview\/status\?tax_year=2027"/);
  assert.match(ui,/credentials:"omit"/);
  assert.doesNotMatch(ui,/\blocalStorage\b|\bsessionStorage\b/);
  assert.doesNotMatch(ui,/fetch\(["']https?:/);
  assert.doesNotMatch(html,/https?:\/\//i);
});

test("Vercel configuration is a zero-dependency static site with no API access",()=>{
  const config=JSON.parse(sibling("vercel.json"));
  const headers=config.headers[0].headers;
  const csp=headers.find(x=>x.key==="Content-Security-Policy").value;
  assert.ok(csp.includes("connect-src 'self'"));
  assert.ok(csp.includes("script-src 'self'"));
  assert.ok(csp.includes("frame-ancestors 'none'"));
  assert.ok(headers.some(x=>x.key==="X-Robots-Tag"&&x.value.includes("noindex")));
  assert.ok(!("builds" in config)&&!("functions" in config));
});

test("legacy local synthetic import prototype remains in GitHub history and repository",()=>{
  const source=sibling("legacy-import.html");
  assert.ok(source.includes("DEVELOPMENT ONLY"));
  assert.ok(source.includes("Import & reconcile"));
});
