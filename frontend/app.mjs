/* P2A one-owner private workspace: cookie-bound MFA session, in-memory CSRF,
 * real one-folder Drive metadata only. NO demo financial figures or local storage.
 * Every provider filename becomes textContent, never HTML. */
import { summarizeSourceReview } from "./document-review-summary.mjs";
import {safePeriod,periodContainsDate,periodTitle,periodMonths,observedPeriods,sourcePeriodSummary,candidatePeriodEvidence} from "./finance-period.mjs";
const byId = id => document.getElementById(id);
const allowedViews = new Set(["home","documents","accounts","transactions","spending","investments","tax"]);
const viewTitles = {
  home:"Overview",documents:"Documents",accounts:"Accounts & balances",transactions:"Transactions",
  spending:"Spending & bills",investments:"Investments",tax:"Tax & wealth",
};
const gate = byId("app-gate");
const app = byId("owner-app");
const status = byId("app-status");
const documents = byId("documents-list");
const refreshButton = byId("refresh-all");
const connectReadOnly = byId("connect-readonly-documents");
const readOnlyStatus = byId("readonly-connection-status");
const checkOriginals = byId("verify-originals");
const hashStatus = byId("source-hash-status");
const hashResults = byId("source-hash-results");
const historicalReportList = byId("historical-bahl-reports");
const historicalReadiness = byId("historical-bahl-readiness");
const historicalBankReports = new Map();
let bankCsvRefreshEpoch = 0;
let propertyRefreshEpoch = 0;
let nextSourceBatch = 0;
let sourceCheckedCount = 0;
let sourceExpectedTotal = null;
let sourceScanActive = false;
let sourceScanCancelled = false;
let sourceScanVersion = 0;
const seenSourceHmacs = new Set();
const MAX_SOURCE_BATCHES_PER_CLICK = 12; // up to 36 sources, avoid unbounded Drive traffic
let ownerReviewEnabled = false;
let reviewEditorNumber = 0;
const reviewReadiness = byId("owner-review-readiness");

// Owner-private evidence is held in RAM only and never survives session expiry.
const periodEvidence = {bankReports:[],candidateGroups:[],registryGroups:[],properties:[],transactionSources:[]};
let transactionVisibleLimit=200;
let financialPeriod = {mode:"all",value:"all"};
let csrfToken = null;
let connected = false;
let items = [];
let loadedAt = null;

const requestOptions = {
  credentials: "same-origin",
  mode: "same-origin",
  cache: "no-store",
  redirect: "error",
  referrerPolicy: "no-referrer",
};

function safeToken(token) {
  return typeof token === "string" && /^[A-Za-z0-9_-]{40,128}$/.test(token);
}
function toLabel(value) {
  return value.replaceAll("_"," ").replace(/\b\w/g, c => c.toUpperCase());
}
// P7: source-bound, shared reporting period for Home/Accounts/Investments.
// Broad statement PDF receipts are historical snapshots, not monthly rows.
function resetFinancialPeriodEvidence(){
  periodEvidence.bankReports=[];
  periodEvidence.candidateGroups=[];
  periodEvidence.registryGroups=[];
  periodEvidence.properties=[];
  periodEvidence.transactionSources=[];
  transactionVisibleLimit=200;
  updateTransactionSourceChoices();
  updateFinancialPeriod();
}
function periodOptions(){
  return observedPeriods({
    reports:periodEvidence.bankReports,
    candidates:periodEvidence.candidateGroups.flatMap(g=>g.rows||[]),
    properties:periodEvidence.properties,
  });
}
function updateFinancialPeriod(){
  const types=periodOptions(),mode=byId("finance-period-mode").value;
  const valueSelect=byId("finance-period-value");
  const field=byId("finance-period-value-label");
  const choices=mode==="month"?types.month:
    mode==="year"?types.year:mode==="tax-year"?types.taxYear:[];
  valueSelect.replaceChildren();
  const needChoice=mode!=="all";
  field.hidden=!needChoice;
  valueSelect.disabled=!needChoice || !choices.length;
  if(needChoice && choices.length){
    for(const value of choices){
      const option=document.createElement("option");
      option.value=value;
      option.textContent=periodTitle({mode,value});
      valueSelect.appendChild(option);
    }
    const selected=financialPeriod.mode===mode&&choices.includes(financialPeriod.value)
      ?financialPeriod.value:choices[0];
    valueSelect.value=selected;
    financialPeriod={mode,value:selected};
  } else {
    financialPeriod={mode:"all",value:"all"};
    if(needChoice)byId("finance-period-status").textContent=
      "No verified dated observations available for that period type.";
  }
  renderFinancialPeriodEvidence();
}
function renderFinancialPeriodEvidence(){
  const period=financialPeriod;
  const title=periodTitle(period);
  const snapshots=sourcePeriodSummary(periodEvidence.bankReports,period);
  const selectedMonths=periodMonths(period);
  const monthsSeen=new Set(snapshots.flatMap(s=>s.covered_months));
  const coverage=selectedMonths.length
    ? monthsSeen.size+" of "+selectedMonths.length+" selected months have verified CSV movements."
    : monthsSeen.size+" distinct months of available verified CSV bank movements.";
  const summary=coverage+" Bank accounts and missing dates are not fully covered. Gross movements are not personal income/expenses.";
  byId("finance-period-status").textContent=title+" · "+coverage+
    " Historical source evidence only.";
  byId("home-financial-period-heading").textContent=title+" · bank activity";
  byId("account-period-heading").textContent=title+" · accounts";
  for(const id of ["home-financial-period-coverage","account-period-coverage"])
    byId(id).textContent=summary;
  for(const id of ["home-financial-period-list","account-period-list"]){
    const list=byId(id);
    list.replaceChildren();
    for(const source of snapshots){
      const row=document.createElement("li");
      const heading=document.createElement("strong");
      heading.textContent=source.source_name+" · "+source.covered_months.length+
        " observed month"+(source.covered_months.length===1?"":"s");
      const movement=document.createElement("small");
      movement.textContent="Gross bank credits "+historicalMoney.format(source.credits_minor/100)+
        " · gross bank debits "+historicalMoney.format(source.debits_minor/100)+
        " · "+source.movements+" reconciled transactions";
      const dates=document.createElement("small");
      dates.textContent="Bank-labelled profit "+historicalMoney.format(source.bank_profit_minor/100)+
        " · last observed month-end/transaction balance "+
        historicalMoney.format(source.last_observed_balance_minor/100)+
        " (historical, not today's cash) · "+"source dated "+source.statement_end;
      row.append(heading,movement,dates);
      list.appendChild(row);
    }
    if(!snapshots.length){
      const no=document.createElement("li");
      no.textContent="No reconciled CSV bank activity for "+title+
        ". Missing evidence is not zero income, zero spending or a current balance.";
      list.appendChild(no);
    }
  }
  const invest=byId("investment-period-list");
  invest.replaceChildren();
  byId("investment-period-heading").textContent=title+" · investment-related candidates";
  const candidates=candidatePeriodEvidence(periodEvidence.candidateGroups,period);
  const names=new Map(periodEvidence.registryGroups.map(g=>[g.id,g.title]));
  for(const group of candidates){
    const li=document.createElement("li");
    const header=document.createElement("strong");
    header.textContent=(names.get(group.group_id)||"Declared investment partner")+
      " · "+group.rows.length+" candidate movements";
    const details=document.createElement("small");
    details.textContent="Outgoing "+historicalMoney.format(group.outgoing_minor/100)+
      " · incoming "+historicalMoney.format(group.incoming_minor/100)+
      ". Neither principal invested nor repaid/profit is confirmed.";
    li.append(header,details);
    const events=document.createElement("ul");
    for(const item of group.rows){
      const row=document.createElement("li");
      row.textContent=item.date+" · "+(item.direction==="INBOUND"?"Incoming ":"Outgoing ")+
        historicalMoney.format(item.amount_minor/100)+
        " · transaction purpose awaiting review";
      events.appendChild(row);
    }
    li.appendChild(events);
    invest.appendChild(li);
  }
  if(!candidates.length){
    const no=document.createElement("li");
    no.textContent="No candidate investment transfers recorded for "+title+
      " in supported CSV sources. No conclusion about complete investment activity.";
    invest.appendChild(no);
  }
  const saleRows=periodEvidence.properties.filter(p=>
    p.source_status==="SOLD_IN_SOURCE_REGISTER" &&
    periodContainsDate(p.sale_date,period));
  if(saleRows.length){
    const li=document.createElement("li");
    const head=document.createElement("strong");
    head.textContent="Property register · "+saleRows.length+" recorded sale(s)";
    const details=document.createElement("small");
    const amount=saleRows.reduce((n,p)=>n+p.recorded_owner_profit_share_minor,0);
    details.textContent="Owner's allocated register profit "+
      historicalMoney.format(amount/100)+
      " · accounting record only, not confirmed cash receipt";
    li.append(head,details);
    invest.appendChild(li);
  }
  byId("investment-period-coverage").textContent=
    "The period applies to dated bank candidates and recorded property sales. "+
    "Held-property costs and all-time partner/venture records below are not period market values.";
  renderTransactionExplorer();
}
function go(view) {
  if (!allowedViews.has(view)) return;
  for (const element of document.querySelectorAll(".view")) {
    element.hidden = element.id !== "view-" + view;
  }
  for (const btn of document.querySelectorAll("[data-view]")) {
    const active = btn.dataset.view === view;
    btn.classList.toggle("selected", active);
    if (active) btn.setAttribute("aria-current", "page");
    else btn.removeAttribute("aria-current");
  }
  byId("view-heading").textContent = viewTitles[view];
}
function showStatus(message) { status.textContent = message; }
function rejectSession() {
  csrfToken = null;
  items = [];
  nextSourceBatch = 0;
  sourceCheckedCount = 0;
  sourceExpectedTotal = null;
  seenSourceHmacs.clear();
  sourceScanCancelled = true;
  sourceScanVersion += 1;
  byId("cancel-original-check").hidden = true;
  ownerReviewEnabled = false;
  hashResults.replaceChildren();
  historicalBankReports.clear();
  historicalReportList.replaceChildren();
  // Never leave a previously authenticated financial observation onscreen
  // after a private session expires or the source evidence is invalidated.
  byId("home-historical-evidence-list").replaceChildren();
  byId("home-historical-evidence").hidden = true;
  bankCsvRefreshEpoch++;
  clearBankCsvEvidence();
  propertyRefreshEpoch++;
  clearPropertyInvestmentEvidence();
  resetFinancialPeriodEvidence();
  // Source inventory is owner-private: drop every filename from the Home queue
  // when the MFA session is no longer authorized.
  byId("home-document-priority-list").replaceChildren();
  byId("home-document-priorities").hidden = true;
  checkOriginals.hidden = true;
  app.hidden = true;
  byId("bottom-nav").hidden = true;
  gate.hidden = false;
  gate.textContent = "Owner sign-in required. Opening secure sign in…";
  window.location.replace("/owner-login");
}
async function get(path) {
  const response = await fetch(path, requestOptions);
  if (response.status === 401) { rejectSession(); throw Error("Owner session expired"); }
  if (!response.ok) throw Error("Private API unavailable");
  return response.json();
}
function validDocument(item) {
  return item && typeof item === "object" &&
    typeof item.display_name === "string" &&
    item.display_name.length >= 1 && item.display_name.length <= 512 &&
    typeof item.virtual_collection === "string" &&
    /^[a-z_]{3,48}$/.test(item.virtual_collection) &&
    item.financial_claims_verified === false &&
    item.original_content_imported === false &&
    (item.modified_time === null ||
      (typeof item.modified_time === "string" && item.modified_time.length <= 50));
}
function validateSnapshot(data) {
  if (!data || data.contract !== "personal_cfo_owner_metadata_review_preview_v1" ||
      data.connection !== "APPROVED_METADATA_GRANT_USED" ||
      data.folder !== "ONE_OWNER_APPROVED_FOLDER" ||
      data.snapshot_complete !== true ||
      data.snapshot_persisted !== false ||
      data.background_sync_active !== false ||
      data.source_bytes_downloaded !== false ||
      data.financial_claims_verified !== false ||
      data.real_financial_data_enabled !== false ||
      !Number.isInteger(data.total) || data.total < 0 || data.total > 1000 ||
      !Array.isArray(data.items) || data.items.length !== data.total ||
      !data.items.every(validDocument)) {
    throw Error("Incomplete or untrusted Drive metadata");
  }
  return data.items;
}
function renderDocuments() {
  const q = byId("document-search").value.trim().toLocaleLowerCase();
  const visible = items.filter(item => item.display_name.toLocaleLowerCase().includes(q));
  documents.replaceChildren();
  for (const item of visible) {
    const li = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = item.display_name;
    const sub = document.createElement("small");
    const date = typeof item.modified_time === "string" ?
      item.modified_time.slice(0,10) : "Date unavailable";
    sub.textContent = toLabel(item.virtual_collection) + " · " + date +
      " · Metadata only";
    li.append(title,sub);
    documents.appendChild(li);
  }
  byId("document-total").textContent = visible.length + " of " + items.length + " documents";
  if (!visible.length) {
    const li=document.createElement("li");
    li.textContent=items.length ? "No filenames match your search." : "No file metadata found.";
    documents.appendChild(li);
  }
}
// Derived solely from authenticated, complete Drive metadata already validated
// by validateSnapshot and summarizeSourceReview. No source text is trusted HTML,
// no financial amount is inferred, and no document data is stored in the browser.
function renderHomeDocumentPriorities(review) {
  const panel=byId("home-document-priorities");
  const list=byId("home-document-priority-list");
  const state=byId("home-document-priority-summary");
  list.replaceChildren();
  if (!items.length) {
    panel.hidden=true;
    state.textContent="";
    return;
  }
  panel.hidden=false;
  state.textContent=review.reviewCount + " of " + review.total +
    " files need filename or format review; " + review.quarantineCount +
    " have an unsupported format or size. Suggestions are based on metadata, not verified balances or transactions.";
  const chosen=review.priorityItems.slice(0,5);
  for (const item of chosen) {
    const li=document.createElement("li");
    const title=document.createElement("strong");
    title.textContent=item.name;
    const reason=document.createElement("small");
    reason.textContent=item.reason;
    const open=document.createElement("button");
    open.type="button";
    open.className="text-button home-file-action";
    open.textContent="Find in Documents";
    open.addEventListener("click",()=>{
      // The filename remains inside the authenticated DOM; no query string,
      // URL path, analytics event or browser storage contains source metadata.
      byId("document-search").value=item.name;
      renderDocuments();
      go("documents");
      byId("document-search").focus();
    });
    li.append(title,reason,open);
    list.appendChild(li);
  }
  if (!chosen.length) {
    const li=document.createElement("li");
    li.textContent="No filename or format exceptions in this inventory. Original document contents and financial figures still require verification.";
    list.appendChild(li);
  }
}
function updateSummary(review = summarizeSourceReview(items)) {
  const counts = new Map(review.categories.map(category=>[category.key,category.count]));
  byId("document-count").textContent = String(items.length);
  byId("category-count").textContent = String(counts.size);
  const box = byId("category-summary");
  box.replaceChildren();
  for (const [category,count] of [...counts].sort((a,b)=>b[1]-a[1] || a[0].localeCompare(b[0]))) {
    const row = document.createElement("div");
    row.className = "category-row";
    const name = document.createElement("span");
    name.textContent = toLabel(category);
    const value = document.createElement("strong");
    value.textContent = String(count);
    row.append(name,value);
    box.append(row);
  }
  const reviewSummary = byId("document-review-summary");
  reviewSummary.textContent = review.total + " filenames inventoried · " +
    review.reviewCount + " require metadata or format review · " +
    review.quarantineCount + " quarantined. No original content processed.";
  const queue=byId("document-review-queue");
  queue.replaceChildren();
  for (const item of review.priorityItems) {
    const li=document.createElement("li");
    const name=document.createElement("strong");
    name.textContent=item.name;
    const reason=document.createElement("small");
    reason.textContent=item.reason;
    li.append(name,reason);
    queue.appendChild(li);
  }
  if (!review.priorityItems.length) {
    const li=document.createElement("li");
    li.textContent="No additional metadata-format exceptions. Source contents remain unverified.";
    queue.appendChild(li);
  }
  for(const [key,count] of Object.entries(review.suggestions)) {
    const target=byId("review-suggested-"+key);
    if(target) target.textContent=String(count);
  }
  byId("source-updated").textContent = loadedAt
    ? "Checked during this session at " + loadedAt.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}) +
      ". This is not a background sync or verified financial statement."
    : "No document check completed.";
  renderHomeDocumentPriorities(review);
}
async function refreshMetadata() {
  if (!connected || !safeToken(csrfToken)) { showStatus("Connect Google Drive first."); return; }
  refreshButton.disabled = true;
  showStatus("Reading approved-folder filenames and metadata…");
  try {
    const response = await fetch("/api/drive/metadata/refresh", {
      ...requestOptions,
      method:"POST",
      // Preserve a genuine Origin on iOS/WebKit while keeping no-referrer;
      // same-origin credentials, exact private route and CSRF stay enforced.
      mode:"cors",
      headers:{"Content-Type":"application/json","X-CSRF-Token":csrfToken},
      body:"",
    });
    if (response.status === 401) { rejectSession(); return; }
    if (!response.ok) throw Error("Metadata temporarily unavailable");
    const data = await response.json();
    const validated = validateSnapshot(data);
    // Validate all classifications before replacing a previously good view.
    const review = summarizeSourceReview(validated);
    // A newly accepted inventory may have changed source identities/versions.
    // Never leave old pinned bytes or historical figures visible after refresh.
    nextSourceBatch = 0;
    sourceCheckedCount = 0;
    sourceExpectedTotal = null;
    seenSourceHmacs.clear();
    sourceScanVersion += 1;
    sourceScanCancelled = true;
    hashResults.replaceChildren();
    historicalBankReports.clear();
    renderHistoricalBankReports();
    bankCsvRefreshEpoch++;
    clearBankCsvEvidence();
    propertyRefreshEpoch++;
    clearPropertyInvestmentEvidence();
    resetFinancialPeriodEvidence();
    hashStatus.textContent =
      "Drive metadata refreshed. Recheck original documents to verify current file bytes.";
    checkOriginals.textContent = "Check original documents";
    items = validated;
    loadedAt = new Date();
    renderDocuments();
    updateSummary(review);
    showStatus("Verified " + items.length +
      " filenames from your approved Drive folder. No original content downloaded.");
  } catch {
    // Keep previous valid snapshot in memory if a later refresh fails.
    showStatus("Could not complete the document check. Previous on-screen metadata may be out of date.");
  } finally { refreshButton.disabled = false; }
}

function approvedContentConsentUrl(raw) {
  if (typeof raw !== "string" || raw.length > 4096) return null;
  try {
    const url = new URL(raw);
    if (url.origin !== "https://accounts.google.com" ||
        url.pathname !== "/o/oauth2/v2/auth" ||
        url.username || url.password || url.hash ||
        url.searchParams.get("response_type") !== "code" ||
        url.searchParams.get("scope") !== "https://www.googleapis.com/auth/drive.readonly" ||
        url.searchParams.get("include_granted_scopes") !== "false" ||
        url.searchParams.get("code_challenge_method") !== "S256" ||
        url.searchParams.get("redirect_uri") !==
          "https://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/callback" ||
        !/^[A-Za-z0-9_-]{40,128}$/.test(url.searchParams.get("state") || "") ||
        url.searchParams.getAll("state").length !== 1 ||
        url.searchParams.getAll("scope").length !== 1 ||
        url.searchParams.getAll("redirect_uri").length !== 1) return null;
    return url;
  } catch { return null; }
}
async function loadReadOnlyGrantStatus() {
  // Content OAuth is independently gated. No new button until backend and
  // Nginx BOTH confirm the authenticated exact read-only content route.
  connectReadOnly.hidden = true;
  readOnlyStatus.hidden = true;
  try {
    const data = await get("/api/drive/content/oauth/status");
    if (data?.content_scope !== "DRIVE_READONLY_CONTENT" ||
        typeof data.google_content_grant_stored !== "boolean" ||
        data.source_bytes_downloaded !== false ||
        data.financial_data_enabled !== false) throw Error("Untrusted content grant status");
    readOnlyStatus.hidden = false;
    readOnlyStatus.textContent = data.google_content_grant_stored
      ? "Google read-only permission saved · document analysis not yet complete"
      : "Document content permission not granted";
    const readiness = byId("original-document-readiness");
    if (readiness) readiness.textContent = data.google_content_grant_stored
      ? "Google read-only permission is saved. Secure statement verification and isolated parsing are next; no financial figures have been imported."
      : "Metadata is connected. Original file verification requires separate Google read-only permission and an isolated parser.";
    checkOriginals.hidden = !data.google_content_grant_stored;
    connectReadOnly.hidden = false;
    connectReadOnly.disabled = !safeToken(csrfToken);
    connectReadOnly.textContent = data.google_content_grant_stored
      ? "Reconnect read-only documents" : "Connect read-only documents";
  } catch { /* No content endpoint: keep metadata-only app functional. */ }
}
connectReadOnly.addEventListener("click",async()=>{
  if (!safeToken(csrfToken) || connectReadOnly.hidden) return;
  connectReadOnly.disabled = true;
  readOnlyStatus.textContent = "Preparing Google read-only permission…";
  try {
    const response = await fetch("/api/drive/content/oauth/start", {
      ...requestOptions, method:"POST", mode:"cors",
      headers:{"Content-Type":"application/json","X-CSRF-Token":csrfToken},
      body:"",
    });
    if (response.status===401) { rejectSession(); return; }
    if (!response.ok) throw Error("Content permission cannot start");
    const data = await response.json();
    if (data?.scope !== "DRIVE_READONLY_CONTENT" ||
        data.google_content_grant_stored !== false ||
        data.source_bytes_downloaded !== false ||
        data.financial_data_enabled !== false) throw Error("Untrusted content request");
    const url = approvedContentConsentUrl(data.authorization_url);
    if (!url) throw Error("Google content destination refused");
    csrfToken = null;
    window.location.assign(url.href);
  } catch {
    readOnlyStatus.textContent = "Read-only Google connection unavailable; metadata remains connected.";
    connectReadOnly.disabled = false;
  }
});


function validSourcePreflightResult(data, expectedBatch) {
  const statuses = new Set([
    "NEEDS_SIZE_REVIEW","OVERSIZED_ISOLATED_REVIEW",
    "UNSUPPORTED_FORMAT_REVIEW","ORIGINAL_BYTES_HASH_VERIFIED",
    "ORIGINAL_HASH_VERIFIED_FORMAT_REVIEW",
    "ORIGINAL_HASH_VERIFIED_NEEDS_ISOLATED_PARSER",
    "READ_OR_REVISION_REVIEW",
  ]);
  if (!data || data.contract !== "personal_cfo_private_original_byte_preflight_v1" ||
      data.approved_source_folder !== true || data.metadata_complete !== true ||
      data.originals_modified !== false ||
      data.source_bytes_returned_to_browser !== false ||
      data.bytes_persisted !== false || data.source_hashes_persisted !== false ||
      data.financial_figures_verified !== false ||
      data.actual_bank_amounts_available !== false ||
      data.real_pdf_parser_active !== false ||
      data.batch_index !== expectedBatch || data.batch_size !== 3 ||
      !Number.isInteger(data.total_source_files) || data.total_source_files < 0 ||
      data.total_source_files > 1000 ||
      !(data.next_batch === null || (Number.isInteger(data.next_batch) &&
          data.next_batch === expectedBatch + 1)) ||
      !Array.isArray(data.results) || data.results.length > 3 ||
      !data.results.every(x=>x && typeof x.source_name === "string" &&
        x.source_name.length > 0 && x.source_name.length <= 512 &&
        /^[a-f0-9]{64}$/.test(x.source_hmac) &&
        /^[a-f0-9]{64}$/.test(x.revision_hmac) &&
        statuses.has(x.state) && typeof x.byte_hash_verified === "boolean" &&
        (x.byte_hash_verified !== true ||
          (/^[a-f0-9]{64}$/.test(x.source_content_hmac) &&
            Number.isInteger(x.byte_count) && x.byte_count > 0 &&
            x.byte_count <= 4*1024*1024)))) return false;
  return true;
}

async function loadOwnerReviewReadiness() {
  ownerReviewEnabled=false;
  try {
    const proof=await get("/api/finance/review/status");
    if (proof?.contract !== "personal_cfo_owner_review_ready_v1" ||
        proof.review_enabled !== true ||
        proof.target_kind !== "document" ||
        proof.append_only_encrypted !== true ||
        proof.auto_resolve !== false ||
        proof.financial_figures_verified !== false) throw Error("Invalid review authority");
    ownerReviewEnabled=true;
    reviewReadiness.textContent =
      "Private encrypted document comments are enabled. Your explanations remain pending review until matched to financial evidence.";
  } catch {
    reviewReadiness.textContent =
      "Encrypted document comments will appear after secure review storage is activated. No originals or balances are changed.";
  }
}
async function postOwnerReview(path,subject,payload={}) {
  if(!safeToken(csrfToken)||!ownerReviewEnabled||
      !/^[a-f0-9]{64}$/.test(subject))throw Error("Review input not accepted");
  const response=await fetch(path,{
    ...requestOptions,method:"POST",mode:"cors",
    headers:{"Content-Type":"application/json","X-CSRF-Token":csrfToken},
    body:JSON.stringify({subject_hmac:subject,subject_kind:"document",...payload}),
  });
  if(response.status===401){rejectSession();throw Error("Owner session expired");}
  if(!response.ok)throw Error("Private financial review unavailable");
  return response.json();
}
function buildPrivateReviewEditor(subject) {
  const frame=document.createElement("section");
  frame.className="owner-review-editor";
  const caption=document.createElement("label");
  caption.textContent="Your comment or clarification";
  const field=document.createElement("textarea");
  field.id="owner-review-note-"+(++reviewEditorNumber);
  caption.htmlFor=field.id;
  field.rows=3;field.maxLength=1500;
  field.placeholder="Example: This transfer may be between accounts I own; please verify both sides.";
  const actions=document.createElement("div");actions.className="owner-review-actions";
  const save=document.createElement("button");
  save.type="button";save.textContent="Save comment";
  const history=document.createElement("button");
  history.type="button";history.textContent="View comments";
  const feedback=document.createElement("p");
  feedback.className="muted";feedback.setAttribute("aria-live","polite");
  const entries=document.createElement("ul");entries.className="owner-review-history";
  async function loadHistory() {
    const data=await postOwnerReview("/api/finance/review/history",subject);
    if(data?.contract!=="personal_cfo_owner_encrypted_review_comments_v1" ||
       data.subject_hmac!==subject || data.subject_kind!=="document" ||
       data.original_source_unchanged!==true ||
       data.financial_values_changed!==false ||
       data.automatic_resolution_performed!==false ||
       !Array.isArray(data.comments) || data.comments.length>50 ||
       !data.comments.every(item=>item &&
         item.subject_hmac===subject && item.subject_kind==="document" &&
         item.review_state==="PENDING_EVIDENCE_RECONCILIATION" &&
         item.analysis_pending===true &&
         typeof item.comment==="string" && item.comment.length<=2000)) {
       throw Error("Untrusted private review history");
    }
    entries.replaceChildren();
    for(const item of data.comments) {
      const li=document.createElement("li");
      li.textContent="Comment "+String(item.revision)+": "+item.comment;
      entries.append(li);
    }
  }
  save.addEventListener("click",async()=>{
    const note=field.value.trim();
    if(!note || note.length>1500){
      feedback.textContent="Enter a clarification of up to 1,500 characters.";
      return;
    }
    save.disabled=true;history.disabled=true;
    feedback.textContent="Saving encrypted owner comment…";
    try {
      const result=await postOwnerReview(
        "/api/finance/review/comment",subject,{comment:note});
      if(result?.contract!=="personal_cfo_owner_review_comment_saved_v1" ||
        result.saved_encrypted!==true ||
        result.review_state!=="PENDING_EVIDENCE_RECONCILIATION" ||
        result.automatically_resolved!==false ||
        result.original_transaction_changed!==false)throw Error();
      field.value="";
      feedback.textContent="Saved privately. Your clarification is pending evidence reconciliation; figures remain unchanged.";
      await loadHistory();
    } catch {
      feedback.textContent="Could not save or retrieve review history. Check your session; no figures were updated.";
    } finally {save.disabled=false;history.disabled=false;}
  });
  history.addEventListener("click",async()=>{
    history.disabled=true;
    try {await loadHistory();feedback.textContent="Private comment history loaded; review pending.";}
    catch {feedback.textContent="Private history unavailable.";}
    finally {history.disabled=false;}
  });
  actions.append(save,history);frame.append(caption,field,actions,feedback,entries);
  return frame;
}

const BAHL_FILE = /^SI-[0-9]{9} BAH eStatement\([0-9]{8}\)\.pdf$/;
const HMAC_SHA = /^[a-f0-9]{64}$/;
const historicalMoney = new Intl.NumberFormat("en-PK", {
  style:"currency", currency:"PKR", minimumFractionDigits:2,
  maximumFractionDigits:2,
});
function verifiedHistoricalBahl(data, subject) {
  if (!data || typeof data !== "object" ||
      data.contract !== "personal_cfo_private_historical_bahl_http_v1" ||
      data.source_hmac !== subject || !HMAC_SHA.test(subject) ||
      !HMAC_SHA.test(data.source_content_hmac) ||
      typeof data.source_name !== "string" || !BAHL_FILE.test(data.source_name) ||
      data.original_source_modified !== false ||
      data.content_retained_on_server !== false ||
      data.financial_values_verified !== false ||
      data.income_minor !== null || data.expenses_minor !== null ||
      data.current_available_balance_minor !== null ||
      data.historical_only !== true) return false;
  if (data.status === "PASSWORD_REQUIRED" ||
      data.status === "PASSWORD_REJECTED") {
    return !["historical_opening_minor","historical_closing_minor",
       "gross_bank_debits_minor","gross_bank_credits_minor","transaction_count"]
      .some(key => key in data);
  }
  if (data.status !== "SOURCE_STATEMENT_RECONCILED" ||
      data.source_sha256_verified !== true ||
      data.running_balance_reconciled !== true ||
      data.printed_gross_totals_match_transactions !== true ||
      data.owner_review_required !== true ||
      data.transfers_excluded !== false ||
      data.all_account_coverage_verified !== false ||
      data.ledger_mutated !== false ||
      !/^20\d{2}-\d{2}-\d{2}$/.test(data.statement_start) ||
      !/^20\d{2}-\d{2}-\d{2}$/.test(data.statement_end) ||
      data.statement_start > data.statement_end) return false;
  const keys=["historical_opening_minor","historical_closing_minor",
      "gross_bank_debits_minor","gross_bank_credits_minor"];
  if (!keys.every(key=>Number.isSafeInteger(data[key]) &&
       data[key]>=0 && data[key]<=1e15) ||
      !Number.isSafeInteger(data.transaction_count) ||
      data.transaction_count<1 || data.transaction_count>5000 ||
      data.historical_opening_minor + data.gross_bank_credits_minor -
        data.gross_bank_debits_minor !== data.historical_closing_minor) return false;
  return true;
}
function renderHistoricalBankReports() {
  historicalReportList.replaceChildren();
  for (const result of historicalBankReports.values()) {
    const li=document.createElement("li");
    const title=document.createElement("strong");
    title.textContent=result.source_name;
    const scope=document.createElement("small");
    scope.textContent="Historical statement · "+result.statement_start+
      " to "+result.statement_end+" · source SHA-256 verified";
    const details=document.createElement("dl");
    details.className="bank-statement-facts";
    for (const [label,key] of [
      ["Closing balance at statement end","historical_closing_minor"],
      ["Opening balance at statement start","historical_opening_minor"],
      ["Gross bank debits (not expenses)","gross_bank_debits_minor"],
      ["Gross bank credits (not income)","gross_bank_credits_minor"],
    ]) {
      const dt=document.createElement("dt");
      dt.textContent=label;
      const dd=document.createElement("dd");
      dd.textContent=historicalMoney.format(result[key]/100);
      details.append(dt,dd);
    }
    const count=document.createElement("small");
    count.textContent=String(result.transaction_count)+" reconciled statement entries. Internal transfers and financial categories still need review.";
    li.append(title,scope,details,count);
    historicalReportList.appendChild(li);
  }
  historicalReadiness.textContent=historicalBankReports.size
    ? "These balances are historical source observations only, not available cash or classified spending. Reports stay in this browser session and are not cached."
    : "In Documents, verify original statements and select a Bank AL Habib statement to analyze.";
  renderHomeHistoricalEvidence();
}
// Home uses ONLY the existing strict verifiedHistoricalBahl-accepted results.
// Never sum dated statements (period overlap/ownership may be unresolved),
// label historical closing as current cash, or cache values in browser storage.
// Source-backed investment costs and realized sales: never inferred market value
// or cash earnings. Strict client response contract for authenticated-only values.
// Owner-declared partner names are served from private Railway configuration,
// never embedded in public JS. No unverified principal, valuation or profit.
function validInvestmentRelationshipRegistry(reg, hasPropertyReport) {
  if(!reg || reg.contract!=="personal_cfo_p6_owner_investment_registry_v1" ||
     reg.source!=="PRIVATE_OWNER_DECLARATION" ||
     reg.current_market_values_verified!==false ||
     reg.all_investment_contributions_reconciled!==false ||
     !Array.isArray(reg.groups) || reg.groups.length>10 ||
     !(reg.property_register_group_id===null ||
        typeof reg.property_register_group_id==="string"))return false;
  if(reg.groups.length===0)return reg.property_register_group_id===null;
  if(!/^[a-z][a-z0-9_]{2,39}$/.test(reg.property_register_group_id||""))return false;
  const seen=new Set();
  let sourceFound=0;
  for(const group of reg.groups){
    if(!group || typeof group.id!=="string" ||
       !/^[a-z][a-z0-9_]{2,39}$/.test(group.id) ||
       seen.has(group.id) ||
       typeof group.title!=="string" ||
       group.title.length<2 || group.title.length>96 ||
       group.owner_declared!==true ||
       !Array.isArray(group.ventures) ||
       !group.ventures.length || group.ventures.length>4)return false;
    seen.add(group.id);
    const seenVentures=new Set();
    for(const venture of group.ventures){
      if(!venture || typeof venture.id!=="string" ||
         !/^[a-z][a-z0-9_]{2,39}$/.test(venture.id) ||
         seenVentures.has(venture.id) ||
         typeof venture.title!=="string" || venture.title.length<2 ||
         venture.title.length>96 ||
         !["property","business","education","other"].includes(venture.category) ||
         venture.confirmed_invested_principal_minor!==null ||
         venture.current_market_value_minor!==null ||
         venture.realized_cash_return_minor!==null ||
         venture.expected_return_minor!==null ||
         typeof venture.property_register_linked!=="boolean")return false;
      seenVentures.add(venture.id);
      const sourceCandidate=group.id===reg.property_register_group_id &&
        venture.category==="property";
      if(sourceCandidate)sourceFound++;
      if(venture.property_register_linked!==(sourceCandidate&&hasPropertyReport))return false;
      if(venture.evidence_status!==(
          sourceCandidate&&hasPropertyReport
          ? "PROPERTY_REGISTER_RECONCILED_HISTORICAL_COSTS_ONLY"
          : "OWNER_DECLARED_AWAITING_TRANSACTION_ALLOCATION"))return false;
    }
  }
  return sourceFound===1;
}
// Private server-matched bank transfers are CANDIDATES, never classified
// capital, repayments, realized profit, or outstanding investment value.
function validInvestmentBankCandidates(evidence,registry){
  if(!evidence || evidence.contract!=="personal_cfo_p6_investment_bank_candidates_v1" ||
     evidence.all_investment_sources_covered!==false ||
     evidence.personal_investment_principal_verified!==false ||
     evidence.repayments_verified!==false ||
     evidence.outstanding_investment_balance_minor!==null ||
     evidence.realized_investment_return_minor!==null ||
     evidence.source_data_retained!==false ||
     evidence.owner_review_required!==true ||
     typeof evidence.source_reconciliation_verified!=="boolean" ||
     !Array.isArray(evidence.groups) ||
     evidence.groups.length>registry.groups.length ||
     (!evidence.source_reconciliation_verified && evidence.groups.length!==0))return false;
  const groups=new Set(registry.groups.map(g=>g.id)),seen=new Set(),ids=new Set();
  for(const item of evidence.groups){
    if(!item || typeof item.group_id!=="string" || !groups.has(item.group_id) ||
       seen.has(item.group_id) || !Number.isInteger(item.candidate_count) ||
       item.candidate_count<0 || item.candidate_count>100 ||
       !Number.isSafeInteger(item.incoming_bank_movements_minor) ||
       !Number.isSafeInteger(item.outgoing_bank_movements_minor) ||
       item.incoming_bank_movements_minor<0 || item.outgoing_bank_movements_minor<0 ||
       !Array.isArray(item.rows) || item.rows.length!==item.candidate_count)return false;
    seen.add(item.group_id);
    let incoming=0,outgoing=0,last="";
    for(const row of item.rows){
      if(!row || !HMAC_SHA.test(row.event_hmac) ||
         !HMAC_SHA.test(row.source_hmac) || ids.has(row.event_hmac) ||
         !/^20[0-4][0-9]-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])$/.test(row.date) ||
         (last && row.date<last) ||
         !["INBOUND","OUTBOUND"].includes(row.direction) ||
         !Number.isSafeInteger(row.amount_minor) ||
         row.amount_minor<=0 || row.amount_minor>1000000000000000 ||
         row.interpretation!=="COUNTERPARTY_BANK_MOVEMENT_NEEDS_PURPOSE_REVIEW")return false;
      ids.add(row.event_hmac);last=row.date;
      if(row.direction==="INBOUND")incoming+=row.amount_minor;
      else outgoing+=row.amount_minor;
    }
    if(incoming!==item.incoming_bank_movements_minor ||
       outgoing!==item.outgoing_bank_movements_minor)return false;
  }
  return true;
}
function renderInvestmentRelationshipRegistry(reg, evidence) {
  byId("investment-partner-list").replaceChildren();
  for(const group of reg.groups){
    const li=document.createElement("li");
    const heading=document.createElement("strong");
    heading.textContent=group.title;
    li.appendChild(heading);
    const list=document.createElement("ul");
    for(const venture of group.ventures){
      const entry=document.createElement("li");
      const title=document.createElement("strong");
      title.textContent=venture.title;
      const note=document.createElement("small");
      note.textContent=venture.property_register_linked
        ? "Original property register reconciled · costs and sale profits below · current valuation unknown"
        : "Owner-declared investment · transactions and allocation need review · balance and returns unknown";
      entry.append(title,note);
      list.appendChild(entry);
    }
    li.appendChild(list);
    const matched=evidence?.groups?.find(g=>g.group_id===group.id);
    if(matched && matched.candidate_count>0){
      const note=document.createElement("small");
      note.textContent="Potential bank matches: "+
        matched.candidate_count+" · outgoing "+
        historicalMoney.format(matched.outgoing_bank_movements_minor/100)+
        " · incoming "+
        historicalMoney.format(matched.incoming_bank_movements_minor/100)+
        ". Source-reconciled bank movements, NOT verified invested capital or repayments.";
      li.appendChild(note);
      const details=document.createElement("details");
      const summary=document.createElement("summary");
      summary.textContent="Review dated bank movements ("+matched.candidate_count+")";
      details.appendChild(summary);
      const sub=document.createElement("ul");
      for(const event of matched.rows){
        const row=document.createElement("li");
        row.textContent=event.date+" · "+
          (event.direction==="OUTBOUND"?"Outgoing":"Incoming")+" "+
          historicalMoney.format(event.amount_minor/100)+
          " · investment purpose/repayment not established";
        sub.appendChild(row);
      }
      details.appendChild(sub);
      li.appendChild(details);
    }else{
      const note=document.createElement("small");
      note.textContent="No match established in the currently supported bank CSV. "+
        "PDF statements and other accounts are not yet included in this view.";
      li.appendChild(note);
    }
    byId("investment-partner-list").appendChild(li);
  }
  byId("investment-partner-groups").hidden=reg.groups.length===0;
  const source=reg.groups.find(g=>g.id===reg.property_register_group_id);
  if(source)byId("property-investment-detail-heading").textContent=
    source.title+" · property register breakdown";
}

function validPrivatePropertyOverview(data) {
  if(!data || data.contract!=="personal_cfo_owner_property_inventory_overview_v1" ||
     data.approved_source_folder!==true || data.inventory_complete!==true ||
     data.originals_modified!==false || data.content_retained_on_server!==false ||
     data.current_market_values_verified!==false ||
     data.owner_review_required!==true ||
     !Number.isInteger(data.xlsx_sources_examined) ||
     data.xlsx_sources_examined<0 || data.xlsx_sources_examined>10 ||
     !Array.isArray(data.reports) || data.reports.length>1 ||
     data.property_register_sources_verified!==data.reports.length ||
    (data.owner_relationships!==undefined &&
      !validInvestmentRelationshipRegistry(data.owner_relationships,data.reports.length===1)) ||
    (data.candidate_bank_movements!==undefined &&
      (!data.owner_relationships ||
       !validInvestmentBankCandidates(data.candidate_bank_movements,data.owner_relationships))))
    return false;
  for(const report of data.reports){
    if(report.contract!=="personal_cfo_p6_property_inventory_v1" ||
       report.source_type!=="PROPERTY_COST_AND_SALES_REGISTER" ||
       !HMAC_SHA.test(report.source_hmac) || !HMAC_SHA.test(report.source_content_hmac) ||
       report.source_sha256_verified!==true ||
       report.content_retained_on_server!==false ||
       report.original_source_modified!==false ||
       report.owner_review_required!==true ||
       report.market_value_minor!==null ||
       report.owner_total_net_worth_minor!==null ||
       report.cash_proceeds_verified!==false ||
       report.property_count!==12 ||
       !Array.isArray(report.properties) || report.properties.length!==12)return false;
    const keys=["held_recorded_investment_cost_minor","all_recorded_sale_profit_minor",
      "owner_recorded_sale_profit_share_minor","other_party_recorded_share_minor"];
    if(!keys.every(k=>Number.isSafeInteger(report[k]) && report[k]>=0))return false;
    if(report.owner_recorded_sale_profit_share_minor+
       report.other_party_recorded_share_minor!==report.all_recorded_sale_profit_minor)return false;
    let held=0,sold=0,heldCost=0,profit=0,ownerProfit=0;
    for(const [i,p] of report.properties.entries()){
      if(!p || p.ordinal!==i+1 || typeof p.property_label!=="string" ||
         p.property_label.length<1 || p.property_label.length>100 ||
         typeof p.purchase_date!=="string" ||
         !/^20[0-4][0-9]-[01][0-9]-[0-3][0-9]$/.test(p.purchase_date) ||
         !Number.isSafeInteger(p.recorded_purchase_cost_minor) ||
         p.recorded_purchase_cost_minor<=0)return false;
      if(p.source_status==="HELD_COST_NOT_MARKET_VALUE"){
        held++;heldCost+=p.recorded_purchase_cost_minor;
        if(p.sale_date!==null || p.net_sale_proceeds_minor!==null ||
           p.recorded_profit_minor!==null || p.recorded_owner_profit_share_minor!==null)return false;
      }else if(p.source_status==="SOLD_IN_SOURCE_REGISTER"){
        sold++;
        for(const k of ["net_sale_proceeds_minor","recorded_profit_minor",
          "recorded_owner_profit_share_minor"])
          if(!Number.isSafeInteger(p[k]) || p[k]<0)return false;
        if(p.sale_date===null || !/^20[0-4][0-9]-[01][0-9]-[0-3][0-9]$/.test(p.sale_date) ||
           p.net_sale_proceeds_minor-p.recorded_purchase_cost_minor!==p.recorded_profit_minor ||
           p.recorded_owner_profit_share_minor*5!==p.recorded_profit_minor*3)return false;
        profit+=p.recorded_profit_minor;ownerProfit+=p.recorded_owner_profit_share_minor;
      }else return false;
    }
    if(held!==report.held_property_count ||
       sold!==report.sold_property_count ||
       held+sold!==report.property_count ||
       heldCost!==report.held_recorded_investment_cost_minor ||
       profit!==report.all_recorded_sale_profit_minor ||
       ownerProfit!==report.owner_recorded_sale_profit_share_minor)return false;
  }
  return true;
}
function clearPropertyInvestmentEvidence(){
  for(const id of ["home-property-investment-list","property-investment-detail-list",
      "property-cost-chart","investment-partner-list"])
    byId(id).replaceChildren();
  byId("investment-partner-groups").hidden=true;
  byId("property-investment-detail-heading").textContent="Source-verified property register breakdown";
  byId("home-property-investments").hidden=true;
  byId("property-investment-detail").hidden=true;
  byId("home-held-property-cost").textContent="PKR —";
  byId("home-held-property-context").textContent="No source-reconciled property register currently available.";
  byId("home-property-profit-share").textContent="PKR —";
  byId("home-property-profit-context").textContent="Recorded sale profits require original source verification.";
}
function renderPropertyInvestments(report){
  clearPropertyInvestmentEvidence();
  const summary=document.createElement("li");
  const title=document.createElement("strong");
  title.textContent=String(report.held_property_count)+
    " held properties · recorded purchase costs "+
    historicalMoney.format(report.held_recorded_investment_cost_minor/100);
  const gain=document.createElement("small");
  gain.textContent=String(report.sold_property_count)+
    " sold-property entries · recorded gross sale profit "+
    historicalMoney.format(report.all_recorded_sale_profit_minor/100)+
    " · owner's recorded share "+
    historicalMoney.format(report.owner_recorded_sale_profit_share_minor/100);
  const note=document.createElement("small");
  note.textContent="Latest registered sale "+report.latest_sale_date+
    " · Original SHA-256 verified · Market values and actual cash receipts not established";
  summary.append(title,gain,note);
  byId("home-property-investment-list").appendChild(summary);
  for(const p of report.properties){
    const li=document.createElement("li");
    const name=document.createElement("strong");
    name.textContent=p.property_label;
    const state=document.createElement("small");
    state.textContent=p.source_status==="SOLD_IN_SOURCE_REGISTER"
      ? "Sold in register "+p.sale_date+" · cost "+historicalMoney.format(p.recorded_purchase_cost_minor/100)+
        " · net proceeds "+historicalMoney.format(p.net_sale_proceeds_minor/100)+
        " · recorded owner's profit share "+historicalMoney.format(p.recorded_owner_profit_share_minor/100)
      : "Held in register · purchase cost "+historicalMoney.format(p.recorded_purchase_cost_minor/100)+
        " · current market price unknown";
    li.append(name,state);
    byId("property-investment-detail-list").appendChild(li);
  }
  // Compact relative-cost chart for HELD property records only.
  // No portfolio-wide pie while the other ventures lack confirmed values.
  const held=report.properties.filter(x=>x.source_status==="HELD_COST_NOT_MARKET_VALUE");
  const maxCost=Math.max(0,...held.map(x=>x.recorded_purchase_cost_minor));
  byId("property-cost-chart").replaceChildren();
  if(maxCost>0){
    for(const p of held){
      const li=document.createElement("li");
      const label=document.createElement("span");
      label.textContent=p.property_label+" · "+
        historicalMoney.format(p.recorded_purchase_cost_minor/100);
      const bar=document.createElement("meter");
      bar.min=0;bar.max=maxCost;bar.value=p.recorded_purchase_cost_minor;
      bar.textContent=label.textContent;
      li.append(label,bar);
      byId("property-cost-chart").appendChild(li);
    }
  }
  byId("home-property-investments").hidden=false;
  byId("property-investment-detail").hidden=false;
  byId("home-held-property-cost").textContent=
    historicalMoney.format(report.held_recorded_investment_cost_minor/100);
  byId("home-held-property-context").textContent=
    report.held_property_count+" held entries · purchase-cost register, not market value.";
  byId("home-property-profit-share").textContent=
    historicalMoney.format(report.owner_recorded_sale_profit_share_minor/100);
  byId("home-property-profit-context").textContent=
    report.sold_property_count+" sold entries · register allocation only, not confirmed cash.";
}
async function loadPropertyInvestments(){
  const epoch=++propertyRefreshEpoch;
  clearPropertyInvestmentEvidence();
  periodEvidence.properties=[];
  periodEvidence.candidateGroups=[];
  periodEvidence.registryGroups=[];
  if(!safeToken(csrfToken))return;
  try{
    const data=await get("/api/finance/investments/overview");
    if(epoch!==propertyRefreshEpoch || !safeToken(csrfToken))return;
    if(!validPrivatePropertyOverview(data))throw Error("Untrusted property evidence");
    if(data.reports.length)renderPropertyInvestments(data.reports[0]);
    if(data.owner_relationships?.groups?.length)
      renderInvestmentRelationshipRegistry(
        data.owner_relationships,data.candidate_bank_movements);
    periodEvidence.properties=data.reports[0]?.properties||[];
    periodEvidence.registryGroups=data.owner_relationships?.groups||[];
    periodEvidence.candidateGroups=data.candidate_bank_movements?.groups||[];
    updateFinancialPeriod();
  }catch{
    clearPropertyInvestmentEvidence();
    periodEvidence.properties=[];
    periodEvidence.registryGroups=[];
    periodEvidence.candidateGroups=[];
    updateFinancialPeriod();
  }
}

// Private, no-cache source-backed CSV bank observations, not personal income
// or expenses. Exact schema/amount continuity is validated again in browser.
const CSV_BANK_CONTRACT="personal_cfo_owner_bank_csv_overview_v1";
// Only bank-labeled profit, withholding and fee/tax charges are confirmed.
// A source credit is not automatically income; a debit is not automatically an expense.
function validBankCsvClassification(data,report) {
  if(!data || data.contract!=="personal_cfo_p6_bank_cashflow_classification_v1" ||
     data.classification_basis!=="EXACT_BANK_LABELS_AFTER_FULL_BALANCE_RECONCILIATION" ||
     data.all_movements_accounted_for!==true ||
     data.all_personal_income_classified!==false ||
     data.all_personal_expenses_classified!==false ||
     data.all_account_coverage_verified!==false ||
     data.personal_monthly_income_minor!==null ||
     data.personal_monthly_expenses_minor!==null ||
     data.owner_review_required!==true ||
     data.original_source_modified!==false ||
     data.transaction_count!==report.transaction_count ||
     !Array.isArray(data.months) ||
     data.months.length!==report.months.length)return false;
  const money=["bank_profit_received_minor","bank_profit_withholding_tax_minor",
    "bank_fees_and_combined_levies_minor","unclassified_credit_minor",
    "unclassified_debit_minor"];
  const counts=["pending_review_count","transfer_candidate_count",
    "confirmed_bank_event_count"];
  const sums=Object.fromEntries([...money,...counts].map(k=>[k,0]));
  for(const k of money)
    if(!Number.isSafeInteger(data[k]) || data[k]<0 ||
       data[k]>1000000000000000)return false;
  for(const k of counts)
    if(!Number.isInteger(data[k]) || data[k]<0 ||
       data[k]>report.transaction_count)return false;
  if(data.confirmed_bank_event_count+data.pending_review_count!==data.transaction_count ||
     data.transfer_candidate_count>data.pending_review_count ||
     data.bank_profit_received_minor+data.unclassified_credit_minor!==report.gross_bank_credits_minor ||
     data.bank_profit_withholding_tax_minor+data.bank_fees_and_combined_levies_minor+
       data.unclassified_debit_minor!==report.gross_bank_debits_minor)return false;
  for(const [i,row] of data.months.entries()){
    const original=report.months[i];
    if(!row || row.month!==original.month ||
       row.source_transaction_count!==original.transaction_count)return false;
    for(const k of money) {
      if(!Number.isSafeInteger(row[k]) || row[k]<0 ||
         row[k]>1000000000000000)return false;
      sums[k]+=row[k];
    }
    for(const k of counts){
      if(!Number.isInteger(row[k]) || row[k]<0 ||
         row[k]>original.transaction_count)return false;
      sums[k]+=row[k];
    }
    if(row.bank_profit_received_minor!==original.bank_labelled_profit_minor ||
       row.bank_profit_withholding_tax_minor!==original.bank_labelled_profit_tax_minor ||
       row.bank_profit_received_minor+row.unclassified_credit_minor!==original.gross_bank_credits_minor ||
       row.bank_profit_withholding_tax_minor+row.bank_fees_and_combined_levies_minor+
         row.unclassified_debit_minor!==original.gross_bank_debits_minor ||
       row.confirmed_bank_event_count+row.pending_review_count!==original.transaction_count ||
       row.transfer_candidate_count>row.pending_review_count)return false;
  }
  return [...money,...counts].every(k=>sums[k]===data[k]);
}

function validBankCsvTransactionRows(tx,report){
  if(!tx || tx.contract!=="personal_cfo_p7_reconciled_bank_csv_rows_v1" ||
    tx.source_hmac!==report.source_hmac ||
    tx.transaction_count!==report.transaction_count ||
    tx.all_running_balances_reconciled!==true ||
    tx.source_pinned_by_parent!==true ||
    tx.source_description_account_references_masked!==true ||
    tx.historical_only!==true || tx.current_available_balance_minor!==null ||
    tx.personal_income_minor!==null || tx.personal_expenses_minor!==null ||
    tx.all_rows_returned!==true ||
    !Array.isArray(tx.rows) || tx.rows.length!==report.transaction_count ||
    tx.rows.length>600)return false;
  let running=report.opening_minor,credit=0,debit=0,last="";
  const seen=new Set(),months=new Map();
  const cats=new Set(["BANK_PROFIT","BANK_WITHHOLDING","BANK_CHARGE",
    "TRANSFER_CANDIDATE","NEEDS_REVIEW"]);
  for(const [i,row] of tx.rows.entries()){
    if(!row || !HMAC_SHA.test(row.event_hmac) ||
       row.source_hmac!==report.source_hmac ||
       row.ordinal!==i+1 || seen.has(row.event_hmac) ||
       !/^20[0-4][0-9]-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])$/.test(row.date) ||
       (last && row.date<last) || row.date<report.statement_start ||
       row.date>report.statement_end || !["INBOUND","OUTBOUND"].includes(row.direction) ||
       !Number.isSafeInteger(row.amount_minor) || row.amount_minor<=0 ||
       !Number.isSafeInteger(row.balance_after_minor) ||
       row.balance_after_minor<0 || !Number.isSafeInteger(row.ordinal) ||
       typeof row.description!=="string" || row.description.length<1 ||
       row.description.length>180 || !cats.has(row.category) ||
       row.review_required!==["TRANSFER_CANDIDATE","NEEDS_REVIEW"].includes(row.category) ||
       row.classified_as_personal_income!==false ||
       row.classified_as_personal_expense!==false ||
       row.investment_purpose_verified!==false)return false;
    const incoming=row.direction==="INBOUND";
    running+=incoming?row.amount_minor:-row.amount_minor;
    if(running!==row.balance_after_minor)return false;
    if(incoming)credit+=row.amount_minor;else debit+=row.amount_minor;
    const m=row.date.slice(0,7);
    months.set(m,(months.get(m)||0)+1);
    last=row.date;seen.add(row.event_hmac);
  }
  return running===report.closing_minor &&
    credit===report.gross_bank_credits_minor &&
    debit===report.gross_bank_debits_minor &&
    report.months.every(m=>months.get(m.month)===m.transaction_count) &&
    months.size===report.months.length;
}
function updateTransactionSourceChoices(){
  const picker=byId("transaction-source-filter");
  const previous=picker.value||"all";
  picker.replaceChildren();
  const all=document.createElement("option");
  all.value="all";all.textContent="All available CSV sources";
  picker.appendChild(all);
  for(const source of periodEvidence.transactionSources){
    const option=document.createElement("option");
    option.value=source.source_hmac;
    option.textContent=source.source_name;
    picker.appendChild(option);
  }
  picker.value=periodEvidence.transactionSources.some(s=>s.source_hmac===previous)
    ?previous:"all";
}
function renderTransactionExplorer(){
  const list=byId("transaction-rows");
  list.replaceChildren();
  const query=byId("transaction-search").value.trim().toLocaleLowerCase();
  const direction=byId("transaction-direction-filter").value||"all";
  const category=byId("transaction-category-filter").value||"all";
  const source=byId("transaction-source-filter").value||"all";
  const entries=periodEvidence.transactionSources.flatMap(report=>
    report.transactions.rows.map(row=>({...row,source_name:report.source_name})));
  const filtered=entries.filter(row=>
    periodContainsDate(row.date,financialPeriod) &&
    (direction==="all" || row.direction===direction) &&
    (category==="all" || row.category===category) &&
    (source==="all" || row.source_hmac===source) &&
    (!query || [row.description,row.date,row.source_name,String(row.amount_minor/100)]
      .some(text=>text.toLocaleLowerCase().includes(query))));
  filtered.sort((a,b)=>b.date.localeCompare(a.date) ||
    a.source_hmac.localeCompare(b.source_hmac) || b.ordinal-a.ordinal);
  const categories={
    BANK_PROFIT:"Bank-labelled profit",
    BANK_WITHHOLDING:"Bank withholding tax",
    BANK_CHARGE:"Verified bank fee",
    TRANSFER_CANDIDATE:"Possible transfer · needs your classification",
    NEEDS_REVIEW:"Purpose needs your classification",
  };
  for(const tx of filtered.slice(0,transactionVisibleLimit)){
    const li=document.createElement("li");li.className="transaction-card";
    const title=document.createElement("strong");
    title.textContent=(tx.direction==="INBOUND"?"Money in ":"Money out ")+
      historicalMoney.format(tx.amount_minor/100)+" · "+tx.description;
    const date=document.createElement("small");
    date.textContent=tx.date+" · "+categories[tx.category];
    const evidence=document.createElement("small");
    evidence.textContent="Bank: "+tx.source_name+" · statement row "+
      tx.ordinal+" · historical after-transaction balance "+
      historicalMoney.format(tx.balance_after_minor/100)+
      " · SHA-verified source, no purpose assumed";
    li.append(title,date,evidence);
    list.appendChild(li);
  }
  const allAvailable=entries.length>0;
  byId("transactions-coverage").textContent=
    filtered.length+" matching transactions · "+periodTitle(financialPeriod)+
    " · "+entries.length+" available source-proved CSV rows."+
    (allAvailable
      ? " More accounts and unimported PDF-only rows may be missing; transfers are not expenses."
      : " Transaction rows are not active or not yet supported; no empty-month claim.")+
    (filtered.length>transactionVisibleLimit
      ? " Showing the first "+transactionVisibleLimit+"; select Show more or refine filters.":"");
  byId("transaction-show-more").hidden=filtered.length<=transactionVisibleLimit;
  if(!filtered.length){
    const empty=document.createElement("li");
    empty.textContent="No verified CSV rows match this selection. This does not prove no transactions occurred.";
    list.appendChild(empty);
  }
}
function validBankCsvSource(result) {
  if (!result || result.contract!=="personal_cfo_p6_reconciled_bank_csv_v1" ||
      result.source_type!=="BANK_CSV_EXACT_RUNNING_BALANCES" ||
      !HMAC_SHA.test(result.source_hmac) || !HMAC_SHA.test(result.source_content_hmac) ||
      typeof result.source_name!=="string" || !result.source_name.toLowerCase().endsWith(".csv") ||
      result.source_name.length>512 || result.source_sha256_verified!==true ||
      result.content_retained_on_server!==false || result.original_source_modified!==false ||
      result.all_running_balances_reconciled!==true || result.printed_closing_reconciled!==true ||
      result.historical_only!==true || result.owner_review_required!==true ||
      result.current_available_balance_minor!==null || result.personal_income_minor!==null ||
      result.personal_expenses_minor!==null || result.investment_current_market_value_minor!==null ||
      !/^20[0-4][0-9]-[01][0-9]-[0-3][0-9]$/.test(result.statement_start) ||
      !/^20[0-4][0-9]-[01][0-9]-[0-3][0-9]$/.test(result.statement_end) ||
      result.statement_start>result.statement_end ||
      !Number.isInteger(result.transaction_count) || result.transaction_count<1 ||
      result.transaction_count>5000 || !Array.isArray(result.months) || result.months.length<1 ||
      result.months.length>120) return false;
  const money=["opening_minor","closing_minor","gross_bank_debits_minor","gross_bank_credits_minor"];
  if(!money.every(key=>Number.isSafeInteger(result[key]) && result[key]>=0 &&
      result[key]<=1000000000000000))return false;
  if(result.opening_minor+result.gross_bank_credits_minor-
      result.gross_bank_debits_minor!==result.closing_minor)return false;
  let debit=0,credit=0,count=0,last="",lastBalance=null;
  for(const month of result.months){
    if(!month || typeof month.month!=="string" ||
        !/^20[0-4][0-9]-(?:0[1-9]|1[0-2])$/.test(month.month) ||
        month.month<=last ||
        !Number.isInteger(month.transaction_count) || month.transaction_count<1 ||
        month.transaction_count>5000)return false;
    for(const key of ["gross_bank_debits_minor","gross_bank_credits_minor",
        "last_reported_balance_minor","bank_labelled_profit_minor","bank_labelled_profit_tax_minor"])
      if(!Number.isSafeInteger(month[key]) || month[key]<0 ||
          month[key]>1000000000000000)return false;
    if(month.bank_labelled_profit_minor>month.gross_bank_credits_minor ||
       month.bank_labelled_profit_tax_minor>month.gross_bank_debits_minor)return false;
    debit+=month.gross_bank_debits_minor;credit+=month.gross_bank_credits_minor;
    count+=month.transaction_count;lastBalance=month.last_reported_balance_minor;
    last=month.month;
  }
  return debit===result.gross_bank_debits_minor &&
    credit===result.gross_bank_credits_minor &&
    count===result.transaction_count && lastBalance===result.closing_minor &&
    result.statement_end.startsWith(last) &&
    (result.classification===undefined ||
      validBankCsvClassification(result.classification,result)) &&
    (result.transactions===undefined ||
      validBankCsvTransactionRows(result.transactions,result));
}

function validOfflineBahlPdfOverview(bundle){
  if(!bundle || bundle.contract!=="personal_cfo_p6d_offline_pdf_overview_v1" ||
     bundle.all_account_coverage_verified!==false ||
     bundle.current_available_balance_minor!==null ||
     bundle.personal_income_minor!==null || bundle.personal_expenses_minor!==null ||
     !Array.isArray(bundle.reports) || bundle.reports.length>3 ||
     !Number.isInteger(bundle.sources_configured) || bundle.sources_configured<0 ||
     bundle.sources_configured>3 ||
     !Number.isInteger(bundle.sources_requiring_review) ||
     bundle.sources_requiring_review<0 ||
     bundle.sources_configured!==bundle.reports.length+bundle.sources_requiring_review)
    return false;
  const seen=new Set();
  for(const r of bundle.reports){
    if(!r || r.contract!=="personal_cfo_p6d_offline_pdf_observation_v1" ||
       !/^SI-[0-9]{9} BAH eStatement\([0-9]{8}\)\.pdf$/.test(r.source_name) ||
       !HMAC_SHA.test(r.source_hmac) || !HMAC_SHA.test(r.source_content_hmac) ||
       seen.has(r.source_hmac) ||
       !/^20[0-4][0-9]-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])$/.test(r.statement_start) ||
       !/^20[0-4][0-9]-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])$/.test(r.statement_end) ||
       r.statement_start>r.statement_end ||
       r.source_sha256_verified!==true ||
       r.offline_reconciliation_attested!==true ||
       r.automatic_pdf_parsing_performed!==false ||
       r.isolation_runtime_accepted!==false ||
       r.historical_only!==true ||
       r.current_available_balance_minor!==null ||
       r.personal_income_minor!==null || r.personal_expenses_minor!==null ||
       r.owner_review_required!==true ||
       !Number.isInteger(r.transaction_count) || r.transaction_count<1 ||
       r.transaction_count>5000 ||
       !Number.isInteger(r.page_count) || r.page_count<1 || r.page_count>100)
      return false;
    const monetary=["opening_minor","closing_minor",
      "gross_bank_credits_minor","gross_bank_debits_minor"];
    if(monetary.some(k=>!Number.isSafeInteger(r[k]) || r[k]<0 ||
       r[k]>1000000000000000))return false;
    if(r.opening_minor+r.gross_bank_credits_minor-
       r.gross_bank_debits_minor!==r.closing_minor)return false;
    seen.add(r.source_hmac);
  }
  return true;
}
function renderOfflineBahlPdfEvidence(bundle){
  const home=byId("home-attested-bahl-list");
  const account=byId("account-attested-bahl-list");
  const note=byId("home-attested-bahl-review");
  home.replaceChildren();account.replaceChildren();
  const reports=[...bundle.reports].sort((a,b)=>
    b.statement_end.localeCompare(a.statement_end) ||
    a.source_name.localeCompare(b.source_name));
  for(const report of reports){
    for(const list of [home,account]){
      const li=document.createElement("li");
      const title=document.createElement("strong");
      title.textContent=report.source_name;
      const date=document.createElement("small");
      date.textContent="Historical closing "+historicalMoney.format(report.closing_minor/100)+
        " as of "+report.statement_end+" · "+report.transaction_count+
        " independently reconciled entries · current original Drive SHA verified";
      const gross=document.createElement("small");
      gross.textContent="Gross credits "+historicalMoney.format(report.gross_bank_credits_minor/100)+
        " · gross debits "+historicalMoney.format(report.gross_bank_debits_minor/100)+
        " · offline-reviewed, not automatically parsed or classified as income/expenses";
      li.append(title,date,gross);
      list.appendChild(li);
    }
  }
  byId("home-attested-bahl-pdf").hidden=reports.length===0;
  byId("account-attested-bahl-pdf").hidden=reports.length===0;
  note.hidden=bundle.sources_requiring_review===0;
  note.textContent=bundle.sources_requiring_review+
    " offline observations withheld: current source SHA/version needs review.";
}
function validBankCsvOverview(data) {
  return !!(data && data.contract===CSV_BANK_CONTRACT &&
    data.source_inventory_complete===true &&
    data.approved_source_folder===true &&
    data.originals_modified===false &&
    data.content_retained_on_server===false &&
    data.historical_only===true &&
    data.all_account_coverage_verified===false &&
    data.personal_income_minor===null &&
    data.personal_expenses_minor===null &&
    data.current_available_balance_minor===null &&
    Number.isInteger(data.csv_sources_found) && data.csv_sources_found>=0 &&
    data.csv_sources_found<=10 &&
    Number.isInteger(data.csv_sources_requiring_review) &&
    data.csv_sources_requiring_review>=0 &&
    Array.isArray(data.reports) && data.reports.length<=10 &&
    (data.offline_pdf===undefined || validOfflineBahlPdfOverview(data.offline_pdf)) &&
    data.reports.length+data.csv_sources_requiring_review===data.csv_sources_found &&
    data.reports.every(validBankCsvSource) &&
    new Set(data.reports.map(x=>x.source_hmac)).size===data.reports.length);
}
function clearBankCsvEvidence() {
  byId("home-bank-csv-list").replaceChildren();
  byId("account-bank-csv-list").replaceChildren();
  byId("home-bank-csv-evidence").hidden=true;
  byId("account-bank-csv-section").hidden=true;
  byId("home-latest-bank-balance").textContent="PKR —";
  byId("home-latest-bank-context").textContent="No verified source statement available; current cash is unknown.";
  byId("home-bank-profit").textContent="PKR —";
  byId("home-bank-profit-context").textContent="No reconciled bank profit observation available.";
  for(const id of ["home-attested-bahl-list","account-attested-bahl-list"])
    byId(id).replaceChildren();
  for(const id of ["home-attested-bahl-pdf","account-attested-bahl-pdf",
      "home-attested-bahl-review"])byId(id).hidden=true;
}
function renderHomeBankCsvMetrics(reports) {
  // The newest source is shown, never sum possibly overlapping statements.
  const latest=[...reports].sort((a,b)=>
    b.statement_end.localeCompare(a.statement_end) ||
    a.source_hmac.localeCompare(b.source_hmac))[0];
  if(!latest) return;
  byId("home-latest-bank-balance").textContent=
    historicalMoney.format(latest.closing_minor/100);
  byId("home-latest-bank-context").textContent=
    "As of "+latest.statement_end+" · most recent CSV statement only · not today's cash.";
  if(latest.classification){
    byId("home-bank-profit").textContent=
      historicalMoney.format(latest.classification.bank_profit_received_minor/100);
    byId("home-bank-profit-context").textContent=
      "Bank label in the "+latest.statement_start+"–"+latest.statement_end+
      " statement · not total personal income.";
  }
}
function renderBankCsvReportList(id,reports) {
  const list=byId(id);
  list.replaceChildren();
  for(const report of reports) {
    const li=document.createElement("li");
    const name=document.createElement("strong");
    name.textContent=report.source_name;
    const dated=document.createElement("small");
    dated.textContent="Historical closing balance "+
      historicalMoney.format(report.closing_minor/100)+" as of "+report.statement_end+
      " · "+report.transaction_count+" reconciled transactions · source SHA-256 verified";
    const summary=document.createElement("small");
    const classified=report.classification;
    summary.textContent="Entire statement: gross credits "+
      historicalMoney.format(report.gross_bank_credits_minor/100)+
      "; gross debits "+historicalMoney.format(report.gross_bank_debits_minor/100)+
      ". These are bank movements, not classified income or expenses."+
      (classified ? " Verified bank profit "+historicalMoney.format(classified.bank_profit_received_minor/100)+
      "; profit withholding "+historicalMoney.format(classified.bank_profit_withholding_tax_minor/100)+
      "; bank fees and levies "+historicalMoney.format(classified.bank_fees_and_combined_levies_minor/100)+
      ". "+classified.pending_review_count+" transactions still need classification." : "");
    const table=document.createElement("table");
    table.className="bank-csv-monthly";
    const head=document.createElement("thead");
    const heading=document.createElement("tr");
    const columns=["Month","Gross credits","Gross debits","Last observed in month"];
    if(classified)columns.push("Verified bank profit","Profit withholding","Bank fees / levies");
    for(const label of columns) {
      const th=document.createElement("th");th.scope="col";th.textContent=label;
      heading.appendChild(th);
    }
    head.appendChild(heading);table.appendChild(head);
    const body=document.createElement("tbody");
    for(const month of report.months){
      const tr=document.createElement("tr");
      const amounts=[month.month, historicalMoney.format(month.gross_bank_credits_minor/100),
        historicalMoney.format(month.gross_bank_debits_minor/100),
        historicalMoney.format(month.last_reported_balance_minor/100)];
      if(classified){
        const item=classified.months.find(x=>x.month===month.month);
        amounts.push(historicalMoney.format(item.bank_profit_received_minor/100),
          historicalMoney.format(item.bank_profit_withholding_tax_minor/100),
          historicalMoney.format(item.bank_fees_and_combined_levies_minor/100));
      }
      for(const value of amounts){
        const td=document.createElement("td");td.textContent=value;tr.appendChild(td);
      }
      body.appendChild(tr);
    }
    table.appendChild(body);
    li.append(name,dated,summary,table);
    list.appendChild(li);
  }
}
async function loadBankCsvOverview() {
  const epoch=++bankCsvRefreshEpoch;
  clearBankCsvEvidence();
  periodEvidence.bankReports=[];
  periodEvidence.transactionSources=[];
  transactionVisibleLimit=200;
  updateTransactionSourceChoices();
  updateFinancialPeriod();
  if(!safeToken(csrfToken))return;
  try {
    const data=await get("/api/finance/bank/csv-overview");
    if(epoch!==bankCsvRefreshEpoch || !safeToken(csrfToken))return;
    if(!validBankCsvOverview(data))throw Error("Untrusted source-backed bank overview");
    periodEvidence.bankReports=data.reports;
    periodEvidence.transactionSources=data.reports.filter(r=>r.transactions);
    updateTransactionSourceChoices();
    updateFinancialPeriod();
    if(data.offline_pdf && data.offline_pdf.reports.length)
      renderOfflineBahlPdfEvidence(data.offline_pdf);
    if(!data.reports.length)return;
    renderBankCsvReportList("home-bank-csv-list",data.reports);
    renderBankCsvReportList("account-bank-csv-list",data.reports);
    renderHomeBankCsvMetrics(data.reports);
    byId("home-bank-csv-evidence").hidden=false;
    byId("account-bank-csv-section").hidden=false;
  }catch{
    // Default-off source route, expired grant, unsupported format, or
    // unverified original: do not invent a figure or disclose source bytes.
    clearBankCsvEvidence();
  }
}

function renderHomeHistoricalEvidence() {
  const section=byId("home-historical-evidence");
  const list=byId("home-historical-evidence-list");
  list.replaceChildren();
  const observations=[...historicalBankReports.values()].sort(
    (a,b)=>b.statement_end.localeCompare(a.statement_end) ||
           a.source_name.localeCompare(b.source_name)
  );
  for (const result of observations) {
    const li=document.createElement("li");
    const title=document.createElement("strong");
    title.textContent=result.source_name;
    const period=document.createElement("small");
    period.textContent="Historical balance as of "+result.statement_end+
      " · Statement covers "+result.statement_start+" to "+result.statement_end+
      " · Original SHA-256 verified";
    const details=document.createElement("dl");
    details.className="bank-statement-facts";
    for (const [label,key] of [
      ["Closing balance at statement end","historical_closing_minor"],
      ["Gross bank debits (not expenses)","gross_bank_debits_minor"],
      ["Gross bank credits (not income)","gross_bank_credits_minor"],
    ]) {
      const dt=document.createElement("dt");
      dt.textContent=label;
      const dd=document.createElement("dd");
      dd.textContent=historicalMoney.format(result[key]/100);
      details.append(dt,dd);
    }
    li.append(title,period,details);
    list.appendChild(li);
  }
  section.hidden=observations.length===0;
}
async function readHistoricalBahl(sourceHmac, providedPassword) {
  if (!safeToken(csrfToken) || !HMAC_SHA.test(sourceHmac))
    throw Error("Historical source not authorized");
  const payload={source_hmac:sourceHmac};
  if (typeof providedPassword==="string") payload.password=providedPassword;
  const body=JSON.stringify(payload);
  if ("password" in payload) payload.password=null;
  const response=await fetch("/api/finance/historical/bahl",{
    ...requestOptions, mode:"cors", method:"POST",
    headers:{"Content-Type":"application/json","X-CSRF-Token":csrfToken},
    body,
  });
  if (response.status===401){rejectSession();throw Error("Owner session expired");}
  if (response.status===404 || response.status===503)
    throw Error("Historical statement reader is not activated or requires source review");
  if (!response.ok) throw Error("Private historical reader unavailable");
  const data=await response.json();
  if (!verifiedHistoricalBahl(data,sourceHmac))
    throw Error("Unverified historical bank result rejected");
  return data;
}
function buildHistoricalBankAction(entry) {
  const frame=document.createElement("section");
  frame.className="bank-report-action";
  const run=document.createElement("button");
  run.type="button";
  run.textContent="Review historical bank balance";
  const feedback=document.createElement("p");
  feedback.className="muted";feedback.setAttribute("aria-live","polite");
  const passwordArea=document.createElement("div");
  passwordArea.className="bank-password-form";passwordArea.hidden=true;
  const passwordLabel=document.createElement("label");
  const passwordField=document.createElement("input");
  passwordField.type="password";passwordField.autocomplete="off";
  passwordField.spellcheck=false;passwordField.maxLength=128;
  passwordField.setAttribute("aria-label","Private PDF password for this statement");
  passwordLabel.textContent="PDF password (only sent to the private document reader)";
  const unlock=document.createElement("button");
  unlock.type="button";unlock.textContent="Analyze with password";
  passwordArea.append(passwordLabel,passwordField,unlock);
  const analyze=async withPassword=>{
    run.disabled=true;unlock.disabled=true;
    feedback.textContent="Reconciling this historical statement from the approved original…";
    let pw=withPassword?passwordField.value:null;
    passwordField.value="";
    passwordField.autocomplete="off";
    try {
      if (withPassword && (!pw || pw.length>128 || /[^\x21-\x7e]/.test(pw))) {
        feedback.textContent="Enter the PDF password, without spaces or control characters.";
        return;
      }
      const outcome=await readHistoricalBahl(entry.source_hmac,pw);
      pw=null;
      if (outcome.status==="PASSWORD_REQUIRED" ||
          outcome.status==="PASSWORD_REJECTED") {
        passwordArea.hidden=false;
        feedback.textContent=outcome.status==="PASSWORD_REQUIRED"
          ? "This PDF is password protected. Enter its password to analyze it privately."
          : "The PDF password was rejected. Enter a valid password and try again.";
        return;
      }
      passwordArea.hidden=true;
      passwordField.value="";
      historicalBankReports.set(entry.source_hmac,outcome);
      renderHistoricalBankReports();
      feedback.textContent="Historical statement reconciled. View it under Accounts & balances; current cash and spending are still unverified.";
    } catch {
      feedback.textContent="Historical bank analysis is unavailable or needs source review. Your original Drive file is unchanged.";
    } finally {
      pw=null;passwordField.value="";
      run.disabled=false;unlock.disabled=false;
    }
  };
  run.addEventListener("click",()=>void analyze(false));
  unlock.addEventListener("click",()=>void analyze(true));
  frame.append(run,feedback,passwordArea);
  return frame;
}
// One owner action verifies up to 36 originals sequentially. Server decides
// which 3 sources to read in each batch; browser sends ONLY an ordinal index.
// Every read re-verifies the pinned original, and nothing is cached persistently.
byId("cancel-original-check").addEventListener("click",()=>{
  sourceScanCancelled = true;
  byId("cancel-original-check").disabled = true;
  hashStatus.textContent = "Stopping after the current private file batch…";
});
checkOriginals.addEventListener("click",async()=>{
  if (!safeToken(csrfToken) || checkOriginals.hidden || sourceScanActive) return;
  sourceScanActive=true;
  sourceScanCancelled=false;
  const version=sourceScanVersion;
  checkOriginals.disabled = true;
  refreshButton.disabled = true;
  const cancel=byId("cancel-original-check");
  cancel.hidden=false;
  cancel.disabled=false;
  hashStatus.textContent = "Checking original bytes in the approved Drive folder…";
  try {
    for (let n=0; n<MAX_SOURCE_BATCHES_PER_CLICK; n++) {
      if(sourceScanCancelled) break;
      const batch=nextSourceBatch;
      const response=await fetch("/api/drive/content/source/preflight",{
        ...requestOptions,mode:"cors",method:"POST",
        headers:{"Content-Type":"application/json","X-CSRF-Token":csrfToken},
        body:JSON.stringify({batch_index:batch}),
      });
      if (version!==sourceScanVersion) return;
      if (response.status===401) { rejectSession(); return; }
      if (!response.ok) throw Error("Private original preflight unavailable");
      const data=await response.json();
      if (version!==sourceScanVersion || !safeToken(csrfToken)) return;
      if (!validSourcePreflightResult(data,batch) ||
          (data.next_batch!==null && data.results.length===0))
        throw Error("Invalid source proof");
      if (batch===0) {
        hashResults.replaceChildren();
        historicalBankReports.clear();
        renderHistoricalBankReports();
        seenSourceHmacs.clear();
        sourceExpectedTotal=data.total_source_files;
        sourceCheckedCount=0;
      }
      if (data.total_source_files!==sourceExpectedTotal ||
          data.results.some(entry=>seenSourceHmacs.has(entry.source_hmac))) {
        throw Error("Folder inventory changed during verification");
      }
      for (const entry of data.results) {
        seenSourceHmacs.add(entry.source_hmac);
        const li=document.createElement("li");
        const name=document.createElement("strong");
        name.textContent=entry.source_name;
        const state=document.createElement("small");
        state.textContent=entry.byte_hash_verified
          ? "Original bytes SHA-256 verified · document analysis pending"
          : ({
              NEEDS_SIZE_REVIEW:"Size unavailable; manual review",
              OVERSIZED_ISOLATED_REVIEW:"Exceeds current safe importer limit",
              UNSUPPORTED_FORMAT_REVIEW:"Unsupported file type; manual review",
              READ_OR_REVISION_REVIEW:"Source version/authorization requires review",
            }[entry.state] || "Original requires format review");
        li.append(name,state);
        if (entry.byte_hash_verified && BAHL_FILE.test(entry.source_name)) {
          li.appendChild(buildHistoricalBankAction(entry));
        }
        if (ownerReviewEnabled) li.appendChild(buildPrivateReviewEditor(entry.source_hmac));
        hashResults.appendChild(li);
      }
      sourceCheckedCount+=data.results.length;
      nextSourceBatch=data.next_batch===null?0:data.next_batch;
      // Individual source receipts, NOT an atomic whole-folder financial audit.
      hashStatus.textContent="Checked "+sourceCheckedCount+" of "+
        data.total_source_files+
        " originals in this session. No file bytes or financial amounts returned to the browser.";
      if(data.next_batch===null) {
        hashStatus.textContent+=" All available batches visited; source versions may change between checks.";
        break;
      }
    }
    if(sourceScanCancelled && version===sourceScanVersion)
      hashStatus.textContent="Paused after "+sourceCheckedCount+
        " original-file checks. Select Continue to resume; no data was stored.";
    if(version===sourceScanVersion)
      checkOriginals.textContent=nextSourceBatch===0
        ? "Recheck original documents" : "Continue original-file verification";
  } catch {
    if(version===sourceScanVersion) {
      hashStatus.textContent="Original-file verification stopped after "+
        sourceCheckedCount+" checks; retry the current batch or review your source connection. Results on screen are only individual receipts.";
      checkOriginals.textContent=nextSourceBatch===0
        ? "Check original documents" : "Continue original-file verification";
    }
  } finally {
    if(version===sourceScanVersion) {
      sourceScanActive=false;
      checkOriginals.disabled=false;
      refreshButton.disabled=false;
      cancel.hidden=true;
      cancel.disabled=false;
    }
  }
});

async function start() {
  // Nothing private, even document filenames, appears until session checked.
  try {
    const session = await get("/api/owner/session");
    if (session?.authenticated !== true ||
        session.real_financial_data_enabled !== false ||
        !safeToken(session.csrf_token)) {
      rejectSession(); return;
    }
    csrfToken = session.csrf_token;
    app.hidden = false;
    byId("bottom-nav").hidden = false;
    gate.hidden = true;
    go("home");
    let google;
    try {
      google = await get("/api/drive/oauth/status");
      if (google?.metadata_scope !== "DRIVE_METADATA_ONLY" ||
          typeof google.google_drive_app_connected !== "boolean" ||
          google.original_content_import_enabled !== false ||
          google.financial_data_enabled !== false) {
        throw Error("Invalid Drive status contract");
      }
    } catch {
      byId("connection-pill").textContent = "Drive status unavailable";
      showStatus("Your login is active, but the Google Drive metadata service is unavailable.");
      return;
    }
    connected = google.google_drive_app_connected;
    byId("connection-pill").textContent = connected ? "Drive metadata connected" : "Drive not connected";
    await loadReadOnlyGrantStatus();
    await loadOwnerReviewReadiness();
    if (connected) {
      await refreshMetadata();
      await loadBankCsvOverview();
      await loadPropertyInvestments();
    }
    else showStatus("Your owner session is active. Connect the approved Google Drive folder from Manage account.");
  } catch {
    if (!app.hidden) showStatus("Cannot verify your private session right now.");
    else rejectSession();
  }
}
for (const btn of document.querySelectorAll("[data-view], [data-go]")) {
  btn.addEventListener("click",()=>go(btn.dataset.view || btn.dataset.go));
}
byId("finance-period-mode").addEventListener("change",()=>{
  updateFinancialPeriod();
});
byId("finance-period-value").addEventListener("change",()=>{
  const mode=byId("finance-period-mode").value;
  const value=byId("finance-period-value").value;
  if(safePeriod(mode,value)){
    financialPeriod={mode,value};
    renderFinancialPeriodEvidence();
  }
});
updateFinancialPeriod();
for(const id of ["transaction-search","transaction-direction-filter",
    "transaction-category-filter","transaction-source-filter"]){
  byId(id).addEventListener(id==="transaction-search"?"input":"change",()=>{
    transactionVisibleLimit=200;
    renderTransactionExplorer();
  });
}
byId("transaction-show-more").addEventListener("click",()=>{
  transactionVisibleLimit+=200;
  renderTransactionExplorer();
});
byId("document-search").addEventListener("input",renderDocuments);
refreshButton.addEventListener("click",async()=>{
  await refreshMetadata();
  await loadBankCsvOverview();
  await loadPropertyInvestments();
});
void start();
