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
let nextSourceBatch = 0;
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
  ownerReviewEnabled = false;
  hashResults.replaceChildren();
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
checkOriginals.addEventListener("click",async()=>{
  if (!safeToken(csrfToken) || checkOriginals.hidden) return;
  checkOriginals.disabled = true;
  hashStatus.textContent = "Checking original bytes in the approved Drive folder…";
  try {
    const batch=nextSourceBatch;
    const response=await fetch("/api/drive/content/source/preflight",{
      ...requestOptions,mode:"cors",method:"POST",
      headers:{"Content-Type":"application/json","X-CSRF-Token":csrfToken},
      body:JSON.stringify({batch_index:batch}),
    });
    if (response.status===401) { rejectSession(); return; }
    if (!response.ok) throw Error("Private original preflight unavailable");
    const data=await response.json();
    if (!validSourcePreflightResult(data,batch)) throw Error("Invalid source proof");
    if (batch===0) hashResults.replaceChildren();
    for (const entry of data.results) {
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
      if (ownerReviewEnabled) li.appendChild(buildPrivateReviewEditor(entry.source_hmac));
      hashResults.appendChild(li);
    }
    nextSourceBatch=data.next_batch===null?0:data.next_batch;
    checkOriginals.textContent=data.next_batch===null
      ? "Recheck original documents":"Check next source batch";
    hashStatus.textContent="Checked "+data.results.length+
      " originals from a complete "+data.total_source_files+
      "-file inventory. No private document bytes or financial amounts were returned.";
  } catch {
    hashStatus.textContent="Original-file verification unavailable. Existing Drive metadata and consent remain unchanged.";
  } finally {checkOriginals.disabled=false;}
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
    if (connected) await refreshMetadata();
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
refreshButton.addEventListener("click",()=>void refreshMetadata());
void start();
