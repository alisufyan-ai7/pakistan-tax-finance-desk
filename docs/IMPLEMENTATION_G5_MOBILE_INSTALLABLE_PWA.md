# G5 mobile-first installability — Progressive Web App (PWA)

**Owner request:** open Personal CFO on a phone, add it to the home/app screen, and launch it like a standalone application. This is called a **Progressive Web App (PWA)**. No separate native Android/iOS app store is needed for the installable web experience.

## Implemented in the existing Railway synthetic preview

- Manifest `frontend/manifest.webmanifest`: consistent name, standalone mode, app color, `/start_url`, 192×192 and 512×512 PNG icons; no financial deep-link shortcuts, personal data or related-app registration.
- Safe no-cache `frontend/sw.js` with install/activate only. **No fetch interception, API caching, persistence, background sync, push, financial notifications or offline owner data.** The installed app still requires network access. This is intentional until a strong private-data offline threat model exists.
- `frontend/pwa.mjs`: button uses `beforeinstallprompt` where browser supports it; otherwise provides manual instructions, including iPhone Safari Share → Add to Home Screen → Open as Web App. When installed the button disappears. No prompts for permissions or owner secrets.
- Safe static Nginx MIME types for `.webmanifest`, `.js`, and icons; `manifest-src 'self'` and `worker-src 'self'`, all other CSP, privacy and exact-route API restrictions preserved. Docker image allowlists only public demo assets.
- Mobile viewport and status bar meta included; no automatic phone notification enrollment or financial uploads.

**Platform expectations:** Chrome on Android can promote installation with manifest and HTTPS; Safari on iPhone supports Add to Home Screen/Open as Web App manually. Browser support varies; iOS does not use the Chromium `beforeinstallprompt` event. Official references: [MDN PWA installability](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) and [Apple iPhone web apps](https://support.apple.com/guide/iphone/turn-a-website-into-an-app-iphea86e5236/ios).

**Security boundary:** the app remains publicly reachable and **synthetic-only**, with a private Railway Postgres status check but no true owner login, accounts or money. Installing it is **not** evidence that G1 encrypted ledger, G2 MFA/host, G3 certified statement formats, G4 tax law or G5 complete owner experience is accepted. Future production PWA must revisit SW caching, logout invalidation, notification consent, mobile device loss and offline data handling before storing any actual financial information.
