/* Personal CFO owner setup — factual public-preview presentation only.
   This file MUST NOT contain credential forms or enable a live Google request.
   The first-run enrollment and provider consent are private workflows, not
   possible from this public demo. No local storage, cookies or network here. */

export const OWNER_SETUP_STEPS = Object.freeze([
  Object.freeze({
    id: "owner",
    title: "Secure your one-owner account",
    detail: "You will set a private password and enroll an authenticator on a verified secure setup screen. Personal CFO will have one owner account, not staff accounts.",
    status: "Not activated",
  }),
  Object.freeze({
    id: "recovery",
    title: "Save your recovery kit",
    detail: "One-time recovery codes and an independent device-replacement check protect you if your phone is lost. Keep the recovery kit off the phone.",
    status: "Not activated",
  }),
  Object.freeze({
    id: "google",
    title: "Connect your Google Drive folder",
    detail: "After secure sign-in is live, you will approve Google consent in your browser. The app requests file metadata for your approved folder; it does not scan the rest of your Drive.",
    status: "Waiting for secure sign-in",
  }),
  Object.freeze({
    id: "review",
    title: "Review incoming documents",
    detail: "New, changed, duplicate and missing files will appear in your mobile Documents queue once real synchronization is verified.",
    status: "Waiting for Google connection",
  }),
]);

export const OWNER_SETUP_STATUS = Object.freeze({
  role: "One owner",
  accountProvisioned: false,
  secureEnrollmentActive: false,
  recoveryValidated: false,
  googleConnected: false,
  financialSourcesImported: false,
  developerPreviewOnly: true,
});

function escape(value) {
  return String(value ?? "").replace(/[&<>"']/g, character =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[character]));
}

export function renderOwnerSetup(status = OWNER_SETUP_STATUS) {
  if (!status || status.developerPreviewOnly !== true ||
      status.googleConnected !== false || status.financialSourcesImported !== false) {
    throw new TypeError("Owner setup requires the documented synthetic preview state");
  }
  const steps = OWNER_SETUP_STEPS.map((step, i) =>
    '<li class="setup-step"><div class="setup-step-count" aria-hidden="true">'+(i+1)+'</div>'+
    '<div class="setup-step-content"><div class="setup-step-heading"><h3>'+escape(step.title)+'</h3>'+
    '<span class="setup-step-status">'+escape(step.status)+'</span></div>'+
    '<p>'+escape(step.detail)+'</p></div></li>'
  ).join("");
  return '<section class="setup-landing" aria-label="Your private owner setup">'+
    '<div class="setup-intro"><div class="setup-eyebrow">YOUR PRIVATE WORKSPACE</div>'+
    '<h2>One account. Yours.</h2>'+
    '<p>Your Personal CFO will have a single owner login with password, authenticator and recovery protection. You will not need to manage employees, invitations or extra roles.</p>'+
    '<div class="setup-chips"><span>One owner account</span><span>Authenticator protected</span><span>Private Google folder</span></div></div>'+
    '<div class="setup-status-bar" role="status"><span class="setup-status-dot" aria-hidden="true"></span>'+
    '<div><strong>Secure enrollment is not live yet</strong>'+
    '<p>The source code is being integrated, but this public development preview cannot accept passwords, recovery codes or Google authorization. No personal data has been connected.</p></div></div>'+
    '<div class="layout-2 setup-columns"><section class="panel">'+
    '<div class="panel-head"><div><h2 class="panel-title">Your setup journey</h2>'+
    '<p class="panel-desc">Four clear steps, with each activation verified before the next.</p></div></div>'+
    '<ol class="setup-steps">'+steps+'</ol></section>'+
    '<section class="panel setup-next-panel"><div class="panel-head"><div>'+
    '<h2 class="panel-title">What you will see after connection</h2>'+
    '<p class="panel-desc">The real dashboard will replace examples only after source verification.</p>'+
    '</div></div><div class="setup-feature-list">'+
    '<div><span aria-hidden="true">▣</span><strong>Accounts and balances</strong><p>What is covered, missing or unverified across your statements.</p></div>'+
    '<div><span aria-hidden="true">⇄</span><strong>This month’s expenses</strong><p>Spending changes, upcoming recurring bills and potential gaps.</p></div>'+
    '<div><span aria-hidden="true">◎</span><strong>Investments and returns</strong><p>Documented holdings, expected dates and follow-ups—not guaranteed income.</p></div>'+
    '<div><span aria-hidden="true">▤</span><strong>Documents and accountant</strong><p>One upload folder, organized review and verified tax-year evidence.</p></div>'+
    '</div><button class="setup-doc-link" type="button" data-go="documents">'+
    'See the fictional Documents preview</button></section></div>'+
    '<div class="setup-disclaimer"><strong>Security and privacy:</strong> '+
    'The real enrollment page will be opened only over an approved private route. '+
    'Do not send your password, authenticator seed, recovery codes or Google client secret in ChatGPT or GitHub. '+
    'Full database disaster recovery and wider financial-document access are separate release steps.</div>'+
    '</section>';
}
