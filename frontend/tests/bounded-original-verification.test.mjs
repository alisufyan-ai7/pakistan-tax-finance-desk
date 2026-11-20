import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const read=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");
function el(){
  const listeners=new Map();
  return {
    children:[],disabled:false,hidden:false,textContent:"",value:"",
    addEventListener(type,cb){listeners.set(type,cb);},
    click(){return listeners.get("click")?.();},
    append(...values){this.children.push(...values);},
    appendChild(value){this.children.push(value);},
    replaceChildren(...values){this.children=[...values];},
  };
}
function harness(fetchImpl){
  const js=read("app.mjs");
  const start=js.indexOf('byId("cancel-original-check").addEventListener("click"');
  const end=js.indexOf("\nasync function start()",start);
  assert.ok(start>=0&&end>start);
  const checkOriginals=el(),refreshButton=el(),cancel=el(),hashStatus=el(),hashResults=el();
  const found=new Map([["cancel-original-check",cancel]]);
  let historyRenderCount=0;
  const fake=new Map([["source","private-unchanged"]]);
  const vars={
    byId:id=>{assert.ok(found.has(id));return found.get(id);},
    checkOriginals,refreshButton,hashStatus,hashResults,
    sourceScanActive:false,sourceScanCancelled:false,
    sourceScanVersion:0,sourceCheckedCount:0,sourceExpectedTotal:null,
    nextSourceBatch:0,MAX_SOURCE_BATCHES_PER_CLICK:12,
    seenSourceHmacs:new Set(),historicalBankReports:fake,
    renderHistoricalBankReports:()=>historyRenderCount++,
    ownerReviewEnabled:false,
    csrfToken:"x".repeat(44),safeToken:()=>true,
    requestOptions:{cache:"no-store"},BAHL_FILE:/^SI-.*\.pdf$/,
    validSourcePreflightResult:()=>true,
    document:{createElement:()=>el()},
    buildHistoricalBankAction:()=>el(),buildPrivateReviewEditor:()=>el(),
    fetch:fetchImpl,rejectSession:()=>{throw Error("No unexpected session rejection")},
  };
  vm.runInNewContext(js.slice(start,end),vars);
  return {vars,checkOriginals,refreshButton,cancel,hashStatus,hashResults,fake,
    get historyRenderCount(){return historyRenderCount;}};
}
function batchResult(index,total=39){
  return {
    total_source_files:total,next_batch:index+1<Math.ceil(total/3)?index+1:null,
    results:Array.from({length:Math.min(3,total-index*3)},(_,i)=>({
      source_name:"private-source-"+(index*3+i)+".csv",
      source_hmac:(index*3+i+1).toString(16).padStart(64,"0"),
      byte_hash_verified:true,
      state:"ORIGINAL_BYTES_HASH_VERIFIED",
    })),
  };
}
test("one click checks at most 12 batches, later click resumes and finishes",async()=>{
  const indices=[];
  const h=harness(async(path,opts)=>{
    assert.equal(path,"/api/drive/content/source/preflight");
    assert.equal(opts.method,"POST");
    assert.equal(opts.mode,"cors");
    assert.equal(opts.headers["Content-Type"],"application/json");
    assert.ok(opts.headers["X-CSRF-Token"]);
    const parsed=JSON.parse(opts.body);
    assert.deepEqual(Object.keys(parsed),["batch_index"]);
    indices.push(parsed.batch_index);
    return {ok:true,status:200,json:async()=>batchResult(parsed.batch_index)};
  });
  await h.checkOriginals.click();
  assert.equal(indices.length,12);
  assert.deepEqual(indices,Array.from({length:12},(_,i)=>i));
  assert.equal(h.hashResults.children.length,36);
  assert.equal(h.vars.nextSourceBatch,12);
  assert.match(h.checkOriginals.textContent,/Continue original-file verification/);
  assert.equal(h.refreshButton.disabled,false);
  assert.equal(h.cancel.hidden,true);
  await h.checkOriginals.click();
  assert.equal(indices.length,13);
  assert.equal(h.hashResults.children.length,39);
  assert.equal(h.vars.nextSourceBatch,0);
  assert.match(h.checkOriginals.textContent,/Recheck original documents/);
  assert.match(h.hashStatus.textContent,/source versions may change between checks/);
  assert.equal(h.fake.size,0,"old historical source observations invalidated");
  assert.ok(h.historyRenderCount>0);
});

test("owner can stop after current 3-file batch and resume without rereading it",async()=>{
  const indices=[];
  let h;
  h=harness(async(_path,opts)=>{
    const n=JSON.parse(opts.body).batch_index;
    indices.push(n);
    if(n===0)h.cancel.click();
    return {ok:true,status:200,json:async()=>batchResult(n)};
  });
  await h.checkOriginals.click();
  assert.deepEqual(indices,[0]);
  assert.equal(h.vars.nextSourceBatch,1);
  assert.equal(h.hashResults.children.length,3);
  assert.match(h.hashStatus.textContent,/Paused after 3 original-file checks/);
  await h.checkOriginals.click();
  assert.equal(indices[1],1);
  assert.equal(h.vars.nextSourceBatch,0);
  assert.equal(h.hashResults.children.length,39);
});

test("failed batch does not advance index or corrupt already accepted receipts",async()=>{
  const indices=[];
  let failOnce=true;
  const h=harness(async(_path,opts)=>{
    const n=JSON.parse(opts.body).batch_index;
    indices.push(n);
    if(n===1&&failOnce){failOnce=false;return {ok:false,status:503};}
    return {ok:true,status:200,json:async()=>batchResult(n,6)};
  });
  await h.checkOriginals.click();
  assert.deepEqual(indices,[0,1]);
  assert.equal(h.vars.nextSourceBatch,1);
  assert.equal(h.hashResults.children.length,3);
  assert.match(h.hashStatus.textContent,/stopped after 3 checks/);
  await h.checkOriginals.click();
  assert.deepEqual(indices,[0,1,1]);
  assert.equal(h.vars.nextSourceBatch,0);
  assert.equal(h.hashResults.children.length,6);
});

test("source totals changing mid-scan fail closed; original receipts remain separated",async()=>{
  const h=harness(async(_path,opts)=>{
    const n=JSON.parse(opts.body).batch_index;
    return {ok:true,status:200,json:async()=>batchResult(n,n===0?9:12)};
  });
  await h.checkOriginals.click();
  assert.equal(h.vars.nextSourceBatch,1);
  assert.equal(h.hashResults.children.length,3);
  assert.match(h.hashStatus.textContent,/stopped after 3 checks/);
});

test("accepted new Drive inventory clears prior historical bank evidence and SHA receipts",async()=>{
  const js=read("app.mjs");
  const start=js.indexOf("async function refreshMetadata() {");
  const end=js.indexOf("\nfunction approvedContentConsentUrl",start);
  assert.ok(start>=0&&end>start);
  const hashResults=el(),hashStatus=el(),checkOriginals=el(),refreshButton=el();
  hashResults.append(el(),el());
  const report=new Map([["one",{statement_end:"2025-12-31"}]]);
  let redraw=0;
  const context={
    connected:true,csrfToken:"x".repeat(44),safeToken:()=>true,
    refreshButton,requestOptions:{cache:"no-store"},hashResults,hashStatus,
    checkOriginals,historicalBankReports:report,
    nextSourceBatch:5,sourceCheckedCount:15,sourceExpectedTotal:60,
    seenSourceHmacs:new Set(["old"]),sourceScanVersion:0,bankCsvRefreshEpoch:0,clearBankCsvEvidence:()=>{},
     propertyRefreshEpoch:0,clearPropertyInvestmentEvidence:()=>{},resetFinancialPeriodEvidence:()=>{},closeTransactionDetail:()=>{},
    sourceScanCancelled:false,loadedAt:null,items:[{display_name:"old"}],
    fetch:async(path,opts)=>{
      assert.equal(path,"/api/drive/metadata/refresh");
      assert.equal(opts.method,"POST");
      return {ok:true,status:200,json:async()=>({mock:"authenticated-snapshot"})};
    },
    validateSnapshot:()=>[{display_name:"new"}],
    summarizeSourceReview:()=>({total:1}),
    renderDocuments:()=>{},updateSummary:()=>{},
    renderHistoricalBankReports:()=>redraw++,
    showStatus:()=>{},rejectSession:()=>{throw Error("Unexpected session expiry")},
    Date,
  };
  vm.runInNewContext(js.slice(start,end),context);
  await context.refreshMetadata();
  assert.equal(hashResults.children.length,0);
  assert.equal(report.size,0);
  assert.equal(context.nextSourceBatch,0);
  assert.equal(context.sourceCheckedCount,0);
  assert.equal(context.sourceExpectedTotal,null);
  assert.equal(context.seenSourceHmacs.size,0);
  assert.equal(context.sourceScanVersion,1);
  assert.equal(context.sourceScanCancelled,true);
  assert.equal(redraw,1);
  assert.match(hashStatus.textContent,/Recheck original documents/);
  assert.equal(checkOriginals.textContent,"Check original documents");
  assert.equal(refreshButton.disabled,false);
});

test("the browser sends ordinal batches only and never stores original bytes",()=>{
  const source=read("app.mjs"),html=read("app.html");
  assert.ok(html.includes('id="cancel-original-check"'));
  assert.match(source,/MAX_SOURCE_BATCHES_PER_CLICK = 12/);
  assert.match(source,/if \(batch===0\) \{\s*hashResults\.replaceChildren\(\);\s*historicalBankReports\.clear\(\)/);
  assert.match(source,/sourceScanVersion \+= 1/);
  assert.match(source,/body:JSON.stringify\(\{batch_index:batch\}\)/);
  assert.doesNotMatch(source,/localStorage|sessionStorage|innerHTML|console\.log/);
});
