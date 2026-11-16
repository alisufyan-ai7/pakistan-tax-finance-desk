/* Personal CFO install shell — synthetic ONLY. No offline data caching.
 * Do not cache real bank/FBR data, authenticated API responses, secrets,
 * investment holdings, balances, owner notes, or uploaded evidence.
 * This no-fetch service worker makes the public demonstration installable;
 * it cannot display private financial information offline.
 */
const SW_ID="personal-cfo-synthetic-v1";
self.addEventListener("install",event=>{
  event.waitUntil(self.skipWaiting());
});
self.addEventListener("activate",event=>{
  event.waitUntil(self.clients.claim());
});
// Intentionally NO fetch handler, Cache API, push notifications or background sync.
