/* P1I: static fictional review-health scenarios for phone-first Documents.
 * Not a network adapter: never accepts owner payloads, filenames, folder IDs,
 * access tokens, verified financial numbers, or time from a real Google scan.
 */
export const FICTIONAL_HEALTH_STATES = Object.freeze([
  Object.freeze({id:"never",label:"Not scanned",heading:"No verified scan yet",
    detail:"Personal CFO has not connected to your Google Drive folder. No documents or balances have been checked.",
    action:"Next: complete owner authentication and approved Google consent when available.",
    evidence:"UNKNOWN · No actual file coverage",
    followup:"Owner connection required"}),
  Object.freeze({id:"stale",label:"Out of date",heading:"Example scan is out of date",
    detail:"Fictional last-success evidence is old. Keep the previous complete review snapshot; do not assume newer files are missing.",
    action:"Next: check the connection and rerun a complete metadata scan after approval.",
    evidence:"UNKNOWN · Current folder coverage unavailable",
    followup:"Rescan after authorization"}),
  Object.freeze({id:"revoked",label:"Access lost",heading:"Example folder permission is unavailable",
    detail:"Stop retrying when permission is denied. The previous fictional review history is retained instead of being deleted.",
    action:"Next: the owner would need to reauthorize the same approved folder.",
    evidence:"UNKNOWN · Reauthorization required",
    followup:"Ask owner to reauthorize"}),
  Object.freeze({id:"changed",label:"Changed",heading:"Changed document candidates",
    detail:"A changed revision needs a new source check. Filenames cannot prove expenses, balances or a filed tax return.",
    action:"Next: compare the revision with earlier evidence in an approved private processor.",
    evidence:"UNVERIFIED · Revision review pending",
    followup:"Recheck changed sources"}),
  Object.freeze({id:"missing",label:"Not visible",heading:"Earlier source not visible",
    detail:"A missing source remains in the review history. This does not prove that a document was deleted or a bill was paid.",
    action:"Next: review folder access and source period, without removing original history.",
    evidence:"UNKNOWN · Earlier evidence retained",
    followup:"Check access and history"}),
  Object.freeze({id:"duplicates",label:"Duplicates",heading:"Possible duplicate files",
    detail:"Matching hints can be wrong. Do not merge amounts, remove originals or conclude two statements are identical.",
    action:"Next: verify authentic content fingerprints in the private processor.",
    evidence:"UNVERIFIED · Duplicate suspicion only",
    followup:"Compare source evidence"}),
]);

const IDS=new Set(FICTIONAL_HEALTH_STATES.map(x=>x.id));
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

export function selectedFictionalReviewState(id="never"){
  if(typeof id!=="string" || !IDS.has(id))throw new RangeError("Unsupported fictional review health state");
  return FICTIONAL_HEALTH_STATES.find(x=>x.id===id);
}

export function renderFictionalReviewHealth(id="never"){
  const selected=selectedFictionalReviewState(id);
  const buttons=FICTIONAL_HEALTH_STATES.map(s=>
    '<button type="button" class="doc-health-option'+(s.id===id?' selected':'')+
    '" data-doc-health="'+s.id+'" aria-pressed="'+String(s.id===id)+'">'+esc(s.label)+'</button>'
  ).join("");
  return '<section class="doc-health" aria-labelledby="docHealthHeading">'+
    '<div class="doc-health-heading"><div><span class="doc-demo-tag">SIMULATED SCAN STATES</span>'+
    '<h3 id="docHealthHeading">What your document inbox might need</h3></div>'+
    '<p>Choose an example to see how Personal CFO would explain incomplete evidence on your phone.</p></div>'+
    '<div class="doc-health-options" role="group" aria-label="Explore fictional document scan states">'+buttons+'</div>'+
    '<div class="doc-health-detail" aria-live="polite" aria-atomic="true">'+
    '<strong>'+esc(selected.heading)+'</strong>'+
    '<p>'+esc(selected.detail)+'</p>'+
    '<p class="doc-health-evidence">'+esc(selected.evidence)+'</p>'+
    '<p class="doc-health-followup">Follow-up: '+esc(selected.followup)+'</p>'+
    '<p>'+esc(selected.action)+'</p></div>'+
    '<p class="doc-health-disclaimer">Demo scenarios only · No running scan, owner account, background sync or verified finance data.</p>'+
    '</section>';
}
