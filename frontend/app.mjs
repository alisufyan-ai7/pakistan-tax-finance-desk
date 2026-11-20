/* P2A one-owner private workspace: cookie-bound MFA session, in-memory CSRF,
 * real one-folder Drive metadata only. NO demo financial figures or local storage.
 * Every provider filename becomes textContent, never HTML. */
import { summarizeSourceReview } from "./document-review-summary.mjs";
const byId = id => document.getElementById(id);
const allowedViews = new Set(["home","documents","accounts","spending","investments","tax"]);
const viewTitles = {
  home:"Overview",documents:"Documents",accounts:"Accounts & balances",
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
// Private, no-cache source-backed CSV bank observations, not personal income
// or expenses. Exact schema/amount continuity is validated again in browser.
const CSV_BANK_CONTRACT="personal_cfo_owner_bank_csv_overview_v1";
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
    result.statement_end.startsWith(last);
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
    data.reports.length+data.csv_sources_requiring_review===data.csv_sources_found &&
    data.reports.every(validBankCsvSource) &&
    new Set(data.reports.map(x=>x.source_hmac)).size===data.reports.length);
}
function clearBankCsvEvidence() {
  byId("home-bank-csv-list").replaceChildren();
  byId("account-bank-csv-list").replaceChildren();
  byId("home-bank-csv-evidence").hidden=true;
  byId("account-bank-csv-section").hidden=true;
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
    summary.textContent="Entire statement: gross credits "+
      historicalMoney.format(report.gross_bank_credits_minor/100)+
      "; gross debits "+historicalMoney.format(report.gross_bank_debits_minor/100)+
      ". These are bank movements, not classified income or expenses.";
    const table=document.createElement("table");
    table.className="bank-csv-monthly";
    const head=document.createElement("thead");
    const heading=document.createElement("tr");
    for(const label of ["Month","Gross credits","Gross debits","Month-end observed"]) {
      const th=document.createElement("th");th.scope="col";th.textContent=label;
      heading.appendChild(th);
    }
    head.appendChild(heading);table.appendChild(head);
    const body=document.createElement("tbody");
    for(const month of report.months){
      const tr=document.createElement("tr");
      for(const value of [month.month, historicalMoney.format(month.gross_bank_credits_minor/100),
          historicalMoney.format(month.gross_bank_debits_minor/100),
          historicalMoney.format(month.last_reported_balance_minor/100)]){
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
  if(!safeToken(csrfToken))return;
  try {
    const data=await get("/api/finance/bank/csv-overview");
    if(epoch!==bankCsvRefreshEpoch || !safeToken(csrfToken))return;
    if(!validBankCsvOverview(data))throw Error("Untrusted source-backed bank overview");
    if(!data.reports.length)return;
    renderBankCsvReportList("home-bank-csv-list",data.reports);
    renderBankCsvReportList("account-bank-csv-list",data.reports);
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
byId("document-search").addEventListener("input",renderDocuments);
refreshButton.addEventListener("click",async()=>{
  await refreshMetadata();
  await loadBankCsvOverview();
});
void start();
