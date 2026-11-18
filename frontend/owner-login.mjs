/* One-owner, same-origin MFA only. No browser storage, telemetry, query
 * parameters, third-party scripts, form serialization, or secret logging. */
const form = document.getElementById("owner-login-form");
const session = document.getElementById("owner-session");
const password = document.getElementById("owner-password");
const code = document.getElementById("owner-code");
const submit = document.getElementById("owner-submit");
const feedback = document.getElementById("owner-feedback");
const logout = document.getElementById("owner-logout");
const googleStatus = document.getElementById("owner-google-status");
const googleConnect = document.getElementById("owner-google-connect");
const documentsPanel = document.getElementById("owner-documents");
const documentsStatus = document.getElementById("owner-document-status");
const documentsList = document.getElementById("owner-document-list");
const documentsRefresh = document.getElementById("owner-documents-refresh");
const documentsMore = document.getElementById("owner-documents-more");
let nextDocumentsPage = null;

let csrfToken = null;

function show(message) {
  feedback.textContent = message;
}

async function request(path, body, csrf) {
  const headers = { "Content-Type": "application/json" };
  if (csrf) headers["X-CSRF-Token"] = csrf;
  return fetch(path, {
    method: "POST",
    credentials: "same-origin",
    mode: "same-origin",
    cache: "no-store",
    redirect: "error",
    referrerPolicy: "no-referrer",
    headers,
    body,
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const token = code.value.trim();
  if (!/^[0-9]{6}$/.test(token)) return;
  const body = JSON.stringify({ password: password.value, totp_code: token });
  password.value = "";
  code.value = "";
  submit.disabled = true;
  show("Checking your private sign-in…");
  try {
    const response = await request("/api/owner/login", body, null);
    if (!response.ok) throw new Error("Private sign-in unavailable or rejected");
    const data = await response.json();
    if (data?.authenticated !== true ||
        typeof data.csrf_token !== "string" ||
        !/^[A-Za-z0-9_-]{40,128}$/.test(data.csrf_token) ||
        data.real_financial_data_enabled !== false) {
      throw new Error("Private sign-in response rejected");
    }
    csrfToken = data.csrf_token; // Memory only, never persisted or placed in URL.
    form.hidden = true;
    session.hidden = false;
    show("Signed in securely. Your account session is active.");
    await refreshGoogleStatus();
  } catch {
    csrfToken = null;
    form.hidden = false;
    session.hidden = true;
    show("Sign-in failed or is not activated. Check your credentials or try again later.");
  } finally {
    submit.disabled = false;
  }
});

logout.addEventListener("click", async () => {
  const csrf = csrfToken;
  if (!csrf) return;
  logout.disabled = true;
  try {
    const response = await request("/api/owner/logout", "{}", csrf);
    if (!response.ok) throw new Error("Sign out unavailable");
    const data = await response.json();
    if (data?.authenticated !== false) throw new Error("Sign out denied");
    csrfToken = null;
    session.hidden = true;
    form.hidden = false;
    show("Signed out.");
    googleStatus.textContent = "Not connected";
    documentsPanel.hidden = true;
    documentsList.replaceChildren();
    nextDocumentsPage = null;
  } catch {
    show("Sign-out confirmation unavailable. Close the tab and let the 15-minute session expire.");
  } finally {
    logout.disabled = false;
  }
});


function validCsrf(value) {
  return typeof value === "string" && /^[A-Za-z0-9_-]{40,128}$/.test(value);
}

async function refreshGoogleStatus() {
  googleConnect.disabled = true;
  googleStatus.textContent = "Checking Google Drive connection…";
  try {
    const response = await fetch("/api/drive/oauth/status", {
      credentials: "same-origin",
      mode: "same-origin",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
    });
    if (!response.ok) throw new Error("Google connection not active");
    const data = await response.json();
    if (data?.metadata_scope !== "DRIVE_METADATA_ONLY" ||
        data.original_content_import_enabled !== false ||
        data.financial_data_enabled !== false ||
        typeof data.google_drive_app_connected !== "boolean") {
      throw new Error("Untrusted Google connection status");
    }
    const connected = data.google_drive_app_connected;
    googleStatus.textContent = connected
      ? "Connected for file metadata only. Source files have not been imported."
      : "Not connected. You may authorize your approved Drive folder.";
    googleConnect.textContent = connected ? "Reconnect Google Drive" : "Connect Google Drive";
    googleConnect.disabled = !csrfToken;
    documentsPanel.hidden = !connected;
    if (connected && csrfToken) await loadDocumentsPage(false);
  } catch {
    googleStatus.textContent = "Google Drive connection is not activated yet.";
    googleConnect.disabled = true;
  }
}

function approvedGoogleConsentUrl(raw) {
  if (typeof raw !== "string" || raw.length > 4096) return null;
  try {
    const url = new URL(raw);
    if (url.origin !== "https://accounts.google.com" ||
        url.pathname !== "/o/oauth2/v2/auth" ||
        url.username || url.password || url.hash ||
        url.searchParams.get("response_type") !== "code" ||
        url.searchParams.get("scope") !== "https://www.googleapis.com/auth/drive.metadata.readonly" ||
        url.searchParams.get("code_challenge_method") !== "S256" ||
        url.searchParams.get("redirect_uri") !==
          "https://personal-cfo-frontend-preview-development.up.railway.app/api/drive/oauth/callback" ||
        !/^[A-Za-z0-9_-]{40,128}$/.test(url.searchParams.get("state") || "") ||
        url.searchParams.getAll("state").length !== 1 ||
        url.searchParams.getAll("redirect_uri").length !== 1) {
      return null;
    }
    return url;
  } catch {
    return null;
  }
}

googleConnect.addEventListener("click", async () => {
  if (!validCsrf(csrfToken)) return;
  googleConnect.disabled = true;
  googleStatus.textContent = "Preparing your Google consent…";
  try {
    const response = await request("/api/drive/oauth/start", "", csrfToken);
    if (!response.ok) throw new Error("Google consent cannot start");
    const data = await response.json();
    if (data?.scope !== "DRIVE_METADATA_ONLY" ||
        data.google_drive_app_connected !== false ||
        data.content_download_enabled !== false ||
        data.financial_data_enabled !== false) {
      throw new Error("Private metadata scope not accepted");
    }
    const url = approvedGoogleConsentUrl(data.authorization_url);
    if (!url) throw new Error("Invalid authorization destination");
    csrfToken = null; // Will be reissued on session resume after callback.
    window.location.assign(url.href);
  } catch {
    googleStatus.textContent = "Google consent is not available yet.";
    googleConnect.disabled = !csrfToken;
  }
});

// Google's same-tab callback retains only the Secure HttpOnly session cookie.
// Retrieve a freshly authenticated CSRF proof after the full-page redirect;
// never persist it in localStorage, sessionStorage, URL or a non-HttpOnly cookie.
async function resumePrivateOwnerSession() {
  try {
    const response = await fetch("/api/owner/session", {
      credentials: "same-origin",
      mode: "same-origin",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
    });
    if (!response.ok) return;
    const data = await response.json();
    if (data?.authenticated !== true ||
        data.real_financial_data_enabled !== false ||
        !validCsrf(data.csrf_token)) return;
    csrfToken = data.csrf_token;
    form.hidden = true;
    session.hidden = false;
    show("Your private owner session is active.");
    await refreshGoogleStatus();
  } catch {
    // No sensitive error details, no credential logging.
  }
}
void resumePrivateOwnerSession();


async function loadDocumentsPage(next) {
  if (!validCsrf(csrfToken) || (next && !nextDocumentsPage)) return;
  const pageToken = next ? nextDocumentsPage : null;
  documentsRefresh.disabled = true;
  documentsMore.disabled = true;
  documentsStatus.textContent = "Reading approved folder metadata…";
  try {
    const response = await request(
      "/api/drive/metadata/page", JSON.stringify({ page_token: pageToken }),
      csrfToken,
    );
    if (!response.ok) throw new Error("Private folder not available");
    const data = await response.json();
    if (data?.contract !== "personal_cfo_private_live_folder_metadata_v1" ||
        data.metadata_only !== true ||
        data.one_pinned_folder_only !== true ||
        data.original_file_bytes_imported !== false ||
        data.financial_data_enabled !== false ||
        data.background_sync_active !== false ||
        !Array.isArray(data.files) || data.files.length > 100 ||
        (data.next_page_token !== null &&
         (typeof data.next_page_token !== "string" ||
          data.next_page_token.length > 1024))) {
      throw new Error("Untrusted Drive metadata response");
    }
    if (!next) documentsList.replaceChildren();
    for (const file of data.files) {
      if (typeof file?.name !== "string" || file.name.length > 512 ||
          typeof file?.mime_type !== "string") {
        throw new Error("Invalid folder metadata entry");
      }
      const li = document.createElement("li");
      const name = document.createElement("strong");
      name.textContent = file.name; // No HTML interpretation of filenames.
      const meta = document.createElement("span");
      const type = file.mime_type.split("/").pop() || "file";
      const date = typeof file.modified_time === "string"
        ? " · " + file.modified_time.slice(0, 10) : "";
      meta.textContent = type + date;
      li.append(name, meta);
      documentsList.appendChild(li);
    }
    nextDocumentsPage = data.next_page_token;
    documentsStatus.textContent = documentsList.children.length +
      " document names shown. No file content has been downloaded.";
    documentsMore.hidden = !nextDocumentsPage;
  } catch {
    nextDocumentsPage = null;
    documentsMore.hidden = true;
    documentsStatus.textContent = "Drive filenames are not available yet. Please try refreshing.";
  } finally {
    documentsRefresh.disabled = false;
    documentsMore.disabled = false;
  }
}
documentsRefresh.addEventListener("click", () => void loadDocumentsPage(false));
documentsMore.addEventListener("click", () => void loadDocumentsPage(true));
