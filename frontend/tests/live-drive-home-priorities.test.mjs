import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
import {summarizeSourceReview} from "../document-review-summary.mjs";

const read=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");
function element() {
  const listeners=new Map();
  return {
    children:[],textContent:"",value:"",hidden:false,focusCount:0,
    append(...kids){this.children.push(...kids);},
    appendChild(kid){this.children.push(kid);},
    replaceChildren(...kids){this.children=[...kids];},
    addEventListener(event,handler){listeners.set(event,handler);},
    click(){listeners.get("click")?.();},
    focus(){this.focusCount++;},
  };
}
function record(name,state="needs_type_review",category="unclassified"){
  return {display_name:name,review_status:state,virtual_collection:category,
    financial_claims_verified:false,original_content_imported:false,
    modified_time:"2026-11-19T10:00:00Z"};
}
function harness(items){
  const source=read("app.mjs");
  const start=source.indexOf("function renderHomeDocumentPriorities(review) {");
  const end=source.indexOf("\nfunction updateSummary(",start);
  assert.ok(start>=0 && end>start);
  const view=new Map([
    ["home-document-priorities",element()],
    ["home-document-priority-list",element()],
    ["home-document-priority-summary",element()],
    ["document-search",element()],
  ]);
  const visits=[];
  let searches=0;
  const context={
    items,
    byId:key=>{assert.ok(view.has(key),"Unexpected DOM lookup "+key);return view.get(key);},
    document:{createElement:()=>element()},
    renderDocuments:()=>{searches++;},
    go:view=>visits.push(view),
  };
  vm.runInNewContext(source.slice(start,end)+"\nrenderHomeDocumentPriorities(summarized);",
    {...context,summarized:summarizeSourceReview(items)});
  return {view,visits,get searches(){return searches;}};
}

test("no inventory means home does not show an invented live-document queue",()=>{
  const x=harness([]);
  assert.equal(x.view.get("home-document-priorities").hidden,true);
  assert.equal(x.view.get("home-document-priority-list").children.length,0);
  assert.equal(x.view.get("home-document-priority-summary").textContent,"");
});

test("real source metadata produces sorted actionable filenames, not money",()=>{
  const x=harness([
    record("ordinary.csv","awaiting_private_document_verification","bank_statements"),
    record("unknown.pdf"),
    record("quarantined.xlsm","quarantined_unsupported_format"),
  ]);
  assert.equal(x.view.get("home-document-priorities").hidden,false);
  const summary=x.view.get("home-document-priority-summary").textContent;
  assert.match(summary,/2 of 3 files need filename or format review/);
  assert.match(summary,/1 have an unsupported format or size/);
  const rows=x.view.get("home-document-priority-list").children;
  assert.equal(rows.length,2);
  assert.equal(rows[0].children[0].textContent,"quarantined.xlsm");
  rows[0].children[2].click();
  assert.equal(x.view.get("document-search").value,"quarantined.xlsm");
  assert.equal(x.view.get("document-search").focusCount,1);
  assert.equal(x.searches,1);
  assert.deepEqual(x.visits,["documents"]);
});

test("malicious filenames are text only and priority list bounded to five",()=>{
  const name='<svg onload=alert("x")>';
  const x=harness([record(name,"quarantined_unsupported_format"),
    ...Array.from({length:8},(_,i)=>record("q"+i+".xlsm","quarantined_unsupported_format"))]);
  const li=x.view.get("home-document-priority-list").children;
  assert.equal(li.length,5);
  assert.ok(li.some(row=>row.children[0].textContent===name));
  const js=read("app.mjs"),html=read("app.html");
  assert.match(js,/title.textContent=item.name/);
  assert.match(js,/reason.textContent=item.reason/);
  assert.match(js,/renderHomeDocumentPriorities\(review\)/);
  for(const id of ["home-document-priorities","home-document-priority-list","home-document-priority-summary"])
    assert.ok(html.includes('id="'+id+'"'));
  assert.match(js,/byId\("home-document-priority-list"\)\.replaceChildren\(\)/);
  assert.match(js,/byId\("home-document-priorities"\)\.hidden = true/);
  assert.doesNotMatch(js,/localStorage|sessionStorage|innerHTML|console\.log/);
});

test("unflagged inventory stays truthful: no metadata exceptions != verified contents",()=>{
  const x=harness([record("bank.pdf","awaiting_private_document_verification","bank_statements")]);
  assert.equal(x.view.get("home-document-priorities").hidden,false);
  assert.match(x.view.get("home-document-priority-summary").textContent,/0 of 1 files/);
  assert.match(x.view.get("home-document-priority-list").children[0].textContent,
    /Original document contents and financial figures still require verification/);
});
