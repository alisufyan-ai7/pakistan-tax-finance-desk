/* Personal CFO P1B — MOBILE-FIRST FICTIONAL document review.
   No Google token, private folder URL/ID, genuine filename, document bytes,
   financial values or live owner connection is present in this build.
   This is a UI contract for a future authenticated, encrypted review queue.
*/
export const FICTIONAL_INBOX = Object.freeze([
  {id:"fictional-doc-1",type:"Bank statement candidate",status:"new",
    collection:"Bank statements",detail:"Fictional PDF · Source verification required",
    action:"Confirm statement period after private parsing"},
  {id:"fictional-doc-2",type:"Accountant worksheet candidate",status:"changed",
    collection:"Accountant working papers",detail:"Fictional XLSX · Revision not reviewed",
    action:"Compare revision with prior draft"},
  {id:"fictional-doc-3",type:"Possible duplicate statement",status:"duplicate",
    collection:"Bank statements",detail:"Fictional PDF · Hash match not yet proven",
    action:"Verify contents before linking any rows"},
  {id:"fictional-doc-4",type:"Unsupported legacy format",status:"quarantine",
    collection:"Needs format review",detail:"Fictional XLS · Opening the original is blocked",
    action:"Use approved isolated conversion, not a workbook macro"},
  {id:"fictional-doc-5",type:"Earlier statement not visible",status:"missing",
    collection:"Bank statements",detail:"Fictional source · Retained for investigation",
    action:"Check access; do not remove historical evidence"},
  {id:"fictional-doc-6",type:"FBR return candidate",status:"review",
    collection:"Tax & wealth",detail:"Fictional PDF · Filing acknowledgment unverified",
    action:"Check official acknowledgment; draft does not mean filed"},
]);

const FILTERS = Object.freeze([
  {id:"all",label:"All"},
  {id:"attention",label:"Needs attention"},
  {id:"new",label:"New"},
  {id:"changed",label:"Changed"},
  {id:"duplicate",label:"Duplicates"},
  {id:"missing",label:"Missing"},
]);
const STATUS_LABELS=Object.freeze({
  new:"New · unverified",
  changed:"Changed · reverify",
  duplicate:"Possible duplicate",
  quarantine:"Quarantined",
  missing:"No longer visible",
  review:"Awaiting verification",
});
const NEEDS_ACTION = new Set(["changed","duplicate","quarantine","missing","review"]);

function escape(value) {
  return String(value ?? "").replace(/[&<>"']/g, c =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
export function selectFictionalInbox(filter="all",rows=FICTIONAL_INBOX) {
  if(!FILTERS.some(f=>f.id===filter))throw new RangeError("Unsupported document filter");
  if(!Array.isArray(rows))throw new TypeError("Document rows must be an array");
  return rows.filter(item=>filter==="all" || (filter==="attention"
    ? NEEDS_ACTION.has(item.status) : item.status===filter));
}
export function summarizeFictionalInbox(rows=FICTIONAL_INBOX) {
  return Object.freeze({
    sampleFiles:rows.length,
    needingAttention:rows.filter(x=>NEEDS_ACTION.has(x.status)).length,
    possibleDuplicates:rows.filter(x=>x.status==="duplicate").length,
    verifiedOriginals:0,
    realFinancialRecordsImported:0,
  });
}
export function renderFictionalDocumentInbox(filter="all") {
  const stats=summarizeFictionalInbox();
  const entries=selectFictionalInbox(filter);
  const filters=FILTERS.map(item=>
    '<button type="button" class="doc-filter'+(item.id===filter?' selected':'')+
    '" data-doc-filter="'+item.id+'" aria-pressed="'+String(item.id===filter)+'">'+
    escape(item.label)+'</button>').join("");
  const cards=entries.map(item=>
    '<article class="doc-entry" aria-label="'+escape(item.type)+'">'+
    '<div class="doc-symbol" aria-hidden="true">▤</div>'+
    '<div class="doc-entry-body"><div class="doc-entry-head"><strong>'+escape(item.type)+'</strong>'+
    '<span class="doc-stage doc-stage-'+escape(item.status)+'">'+escape(STATUS_LABELS[item.status]??"Review")+'</span></div>'+
    '<div class="doc-detail">'+escape(item.collection)+' · '+escape(item.detail)+'</div>'+
    '<div class="doc-action">Next: '+escape(item.action)+'</div></div></article>'
  ).join("") || '<div class="doc-empty">No fictional files match this filter.</div>';
  return '<section class="doc-inbox" aria-labelledby="docInboxHeading">'+
    '<div class="doc-connection"><div class="doc-connection-icon" aria-hidden="true">☁</div>'+
    '<div><span class="doc-step">GOOGLE DRIVE · APP CONNECTION PENDING</span>'+
    '<h2 id="docInboxHeading">One folder. Everything organized here.</h2>'+
    '<p>Upload all your files into one private Google Drive folder. Personal CFO will sort them virtually and flag missing or changed evidence — no renaming needed.</p>'+
    '<div class="doc-unavailable" role="status">The ChatGPT Drive connection is separate. Personal CFO has no owner OAuth connection or live document sync yet.</div>'+
    '</div></div>'+
    '<div class="doc-kpis" aria-label="Clearly fictional document preview counts">'+
    '<div><strong>'+stats.sampleFiles+'</strong><span>Sample files</span></div>'+
    '<div><strong>'+stats.needingAttention+'</strong><span>Sample reviews</span></div>'+
    '<div><strong>Not available</strong><span>Actual synced files</span></div>'+
    '</div>'+
    '<div class="doc-queue"><div class="doc-queue-head"><div>'+
    '<h3>Document inbox <span class="doc-demo-tag">FICTIONAL PREVIEW</span></h3>'+
    '<p>Suggested file types only. Names are not proof of balances, expenses, or filed tax returns.</p></div></div>'+
    '<div class="doc-filterbar" role="group" aria-label="Filter fictional document reviews">'+filters+'</div>'+
    '<div class="doc-list" aria-live="polite">'+cards+'</div></div>'+
    '<section class="doc-next"><h3>What happens next?</h3>'+
    '<ol><li>Complete private Google authorization for the dedicated upload folder.</li>'+
    '<li>Synchronize new and changed file metadata safely without touching originals.</li>'+
    '<li>Verify genuine contents only in the approved isolated private processor, then reconcile financial sources.</li></ol>'+
    '<p>No financial data is imported, no background application sync is running, and nothing is deleted in this demonstration.</p></section>'+
    '</section>';
}
