import test from "node:test";
import assert from "node:assert/strict";
import {CHECKS,checkPublicSyntheticPreview} from "../preview-smoke.mjs";

const fakeWorkspace={
 contract:"owner_workspace_status_v1",
 coverage:{state:"UNAVAILABLE"},
 financial_facts:{bank_balance_minor:null,net_worth_minor:null,tax_due_minor:null},
 required_gates:{G1_confidential_active_ledger:false,G2_private_runtime_mfa:false},
};
const status={
 contract:"personal_cfo_private_preview_status_v1",
 synthetic_only:true,real_data_authorized:false,
 backend:"connected",postgresql:"private_connected",canonical_finance_schema:"NOT_CERTIFIED",
 owner_workspace:fakeWorkspace,
};
const manifest={
 name:"Personal CFO — Financial Desk",display:"standalone",scope:"/",start_url:"/",
 icons:[{sizes:"192x192",type:"image/png"},{sizes:"512x512",type:"image/png"}],
};
const worker='self.addEventListener("install", event=>{}); self.addEventListener("activate", event=>{});';
const router=(options={})=>async(url,request)=>{
  assert.equal(url.origin,"https://personal-cfo-frontend-preview-development.up.railway.app");
  assert.equal(request.method,"GET");
  assert.equal(request.redirect,"error");
  const key=url.pathname+url.search;
  const overrides=options;
  if(key in overrides)return overrides[key];
  if(key==="/healthz")return new Response("ok",{status:200});
  if(key==="/manifest.webmanifest")return Response.json(manifest);
  if(key==="/sw.js")return new Response(worker,{status:200});
  if(key==="/api/preview/status?tax_year=2027")return Response.json(status);
  if(key==="/api/accounts")return new Response("Not Found",{status:404});
  throw Error("Unexpected public route "+key);
};

test("synthetic live probe checks exactly five approved public routes",async()=>{
  assert.equal(CHECKS.length,5);
  const out=await checkPublicSyntheticPreview({fetcher:router()});
  assert.equal(out.passed,true);
  assert.ok(out.checks.every(x=>x.pass));
});
test("stale nginx private IP 502/504 must fail despite frontend health 200",async()=>{
  for(const code of [502,504]){
    const out=await checkPublicSyntheticPreview({fetcher:router({
      "/api/preview/status?tax_year=2027":new Response("proxy unavailable",{status:code}),
    })});
    assert.equal(out.passed,false);
    assert.equal(out.checks.find(x=>x.check==="synthetic private-backed API").httpStatus,code);
  }
});
test("a public leaked finance endpoint fails even if synthetic status healthy",async()=>{
  const out=await checkPublicSyntheticPreview({fetcher:router({
    "/api/accounts":Response.json({accounts:[]}),
  })});
  assert.equal(out.passed,false);
  assert.equal(out.checks.at(-1).httpStatus,200);
});
test("real mode or claimed private production financial values fail smoke",async()=>{
  const forbidden=structuredClone(status);
  forbidden.real_data_authorized=true;
  const result=await checkPublicSyntheticPreview({fetcher:router({
    "/api/preview/status?tax_year=2027":Response.json(forbidden),
  })});
  assert.equal(result.passed,false);
  forbidden.real_data_authorized=false;
  forbidden.owner_workspace.financial_facts.bank_balance_minor=0;
  const r2=await checkPublicSyntheticPreview({fetcher:router({
    "/api/preview/status?tax_year=2027":Response.json(forbidden),
  })});
  assert.equal(r2.passed,false);
});
test("no customer-directed or private DNS probes can be injected",async()=>{
 await assert.rejects(()=>checkPublicSyntheticPreview({
   baseUrl:"https://personal-cfo-api-preview.railway.internal",
   fetcher:router(),
 }),TypeError);
 await assert.rejects(()=>checkPublicSyntheticPreview({
   baseUrl:"https://example.org",
   fetcher:router(),
 }),TypeError);
});
test("a manifest missing 512 image is not install-ready",async()=>{
 const incomplete=structuredClone(manifest);
 incomplete.icons.pop();
 const result=await checkPublicSyntheticPreview({fetcher:router({
   "/manifest.webmanifest":Response.json(incomplete),
 })});
 assert.equal(result.passed,false);
});
