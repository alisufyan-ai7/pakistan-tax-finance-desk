/* Personal CFO synthetic preview smoke probe.
 * PUBLIC non-sensitive endpoints ONLY. Never request private Railway API
 * hostnames, connect to Postgres, save payloads or print response bodies.
 * This deliberately runs separately from the fast frontend unit tests.
 */
import {fileURLToPath} from "node:url";

const BASE = "https://personal-cfo-frontend-preview-development.up.railway.app";
const TIMEOUT_MS = 9000;
export const CHECKS = Object.freeze([
  {name:"frontend health", path:"/healthz"},
  {name:"installable manifest", path:"/manifest.webmanifest"},
  {name:"no-cache worker", path:"/sw.js"},
  {name:"synthetic private-backed API", path:"/api/preview/status?tax_year=2027"},
  {name:"private finance API stays blocked", path:"/api/accounts"},
]);

export async function checkPublicSyntheticPreview({fetcher=fetch,baseUrl=BASE}={}) {
  const origin=new URL(baseUrl);
  if(origin.protocol!=="https:" ||
     origin.hostname!=="personal-cfo-frontend-preview-development.up.railway.app" ||
     origin.username || origin.password || origin.pathname!=="/" ||
     origin.search || origin.hash || origin.port)
    throw new TypeError("Only the approved public synthetic preview origin is accepted");
  const outcomes=[];
  for(const check of CHECKS){
    const response=await fetcher(new URL(check.path,origin),{
      method:"GET",redirect:"error",cache:"no-store",
      signal:AbortSignal.timeout(TIMEOUT_MS),
      headers:{"Accept":"application/json, text/plain; q=0.8"},
    });
    let ok=false;
    if(check.name==="frontend health"){
      ok=response.status===200 && (await response.text()).trim()==="ok";
    }else if(check.name==="installable manifest"){
      if(response.status===200){
        const m=await response.json();
        ok=m.name?.startsWith("Personal CFO") && m.display==="standalone" &&
           m.scope==="/" && m.start_url==="/" && Array.isArray(m.icons) &&
           ["192x192","512x512"].every(size=>
             m.icons.some(x=>x.sizes===size&&x.type==="image/png"));
      }
    }else if(check.name==="no-cache worker"){
      if(response.status===200){
        const sw=await response.text();
        ok=sw.includes('addEventListener("install"') &&
           !/addEventListener\(["']fetch["']|caches\.open|caches\.match|cache\.put/.test(sw);
      }
    }else if(check.name==="synthetic private-backed API"){
      if(response.status===200){
        const p=await response.json();
        const ws=p.owner_workspace;
        ok=p.contract==="personal_cfo_private_preview_status_v1" &&
           p.synthetic_only===true && p.real_data_authorized===false &&
           p.backend==="connected" && p.postgresql==="private_connected" &&
           p.canonical_finance_schema==="NOT_CERTIFIED" &&
           ws?.contract==="owner_workspace_status_v1" &&
           ws?.coverage?.state==="UNAVAILABLE" &&
           ws?.financial_facts && Object.values(ws.financial_facts).every(x=>x===null) &&
           ws?.required_gates && Object.values(ws.required_gates).every(x=>x===false);
      }
    }else if(check.name==="private finance API stays blocked"){
      ok=response.status===404;
    }
    outcomes.push({check:check.name,pass:Boolean(ok),httpStatus:response.status});
  }
  return {passed:outcomes.every(x=>x.pass),checks:outcomes};
}

if(process.argv[1] && fileURLToPath(import.meta.url)===process.argv[1]){
  try{
    const result=await checkPublicSyntheticPreview();
    for(const x of result.checks){
      console.log((x.pass?"PASS ":"FAIL ")+x.check+" (HTTP "+x.httpStatus+")");
    }
    if(!result.passed)process.exitCode=1;
  }catch{
    // Do not leak DSNs, headers, token values or unexpected upstream bodies.
    console.error("FAIL public synthetic preview network or contract check");
    process.exitCode=1;
  }
}
