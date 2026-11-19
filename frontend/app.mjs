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
