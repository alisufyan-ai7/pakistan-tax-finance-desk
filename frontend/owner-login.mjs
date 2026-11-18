/* One-owner, same-origin MFA only. No browser storage, telemetry, query
 * parameters, third-party scripts, form serialization, or secret logging. */
const form = document.getElementById("owner-login-form");
const session = document.getElementById("owner-session");
const password = document.getElementById("owner-password");
const code = document.getElementById("owner-code");
const submit = document.getElementById("owner-submit");
const feedback = document.getElementById("owner-feedback");
const logout = document.getElementById("owner-logout");

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
  } catch {
    show("Sign-out confirmation unavailable. Close the tab and let the 15-minute session expire.");
  } finally {
    logout.disabled = false;
  }
});
