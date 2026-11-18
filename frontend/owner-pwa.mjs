/* Owner-only install prompt. Never caches private API or keeps sessions. */
const installButton = document.getElementById("install-owner-app");
const installHelp = document.getElementById("owner-install-help");
let pending = null;
function standalone() {
  return window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
}
function instructions() {
  return /iPhone|iPad|iPod/.test(navigator.userAgent)
    ? "On iPhone: in Safari select Share → Add to Home Screen, then Open as Web App."
    : "On Android or desktop: use the browser menu and select Install app or Add to Home screen.";
}
function update() { if (installButton) installButton.hidden = standalone(); }
if ("serviceWorker" in navigator && window.isSecureContext) {
  // Existing worker has NO fetch handler, no Cache API and no background
  // document synchronization. Owner source data must never be cached.
  navigator.serviceWorker.register("/sw.js", {scope:"/"}).catch(()=>{});
}
window.addEventListener("beforeinstallprompt",event=>{
  event.preventDefault();
  pending=event;
  update();
});
window.addEventListener("appinstalled",()=>{
  pending=null;
  update();
  if (installHelp) installHelp.hidden=true;
});
if (installButton && installHelp) {
  installButton.addEventListener("click",async()=>{
    if (pending) {
      const event=pending;
      pending=null;
      try {
        await event.prompt();
        await event.userChoice;
        update();
        return;
      } catch { /* Show ordinary native browser installation steps. */ }
    }
    installHelp.textContent=instructions();
    installHelp.hidden=false;
  });
}
update();
