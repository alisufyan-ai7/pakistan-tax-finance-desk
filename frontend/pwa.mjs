/* Install UX for the public fictional dashboard. No financial state is saved. */
const button=document.getElementById("installApp");
const help=document.getElementById("installHelp");
const helpText=document.getElementById("installHelpText");
const close=document.getElementById("installClose");
let deferredPrompt=null;
const standalone=()=>window.matchMedia("(display-mode: standalone)").matches ||
  window.navigator.standalone===true;
const isiOS=()=>/iPhone|iPad|iPod/.test(navigator.userAgent);
function reflect(){
  if(!button)return;
  button.hidden=standalone();
  if(button.hidden&&help)help.hidden=true;
}
if("serviceWorker" in navigator && window.isSecureContext){
  navigator.serviceWorker.register("/sw.js",{scope:"/"}).catch(()=>{
    // Installability varies by browser; never block the dashboard.
  });
}
window.addEventListener("beforeinstallprompt",event=>{
  event.preventDefault();
  deferredPrompt=event;
  reflect();
});
window.addEventListener("appinstalled",()=>{
  deferredPrompt=null;
  reflect();
});
function instructions(){
  if(isiOS())
    return "On iPhone: open in Safari, tap Share, then Add to Home Screen. Switch on Open as Web App and tap Add.";
  return "On Android: open the browser menu (⋮), choose Install app or Add to Home screen. On desktop, use your browser's Install app menu.";
}
if(button&&help&&helpText&&close){
  button.addEventListener("click",async()=>{
    if(deferredPrompt){
      const prompt=deferredPrompt;
      deferredPrompt=null;
      try{
        await prompt.prompt();
        await prompt.userChoice;
      }catch{
        helpText.textContent=instructions();help.hidden=false;
      }
    }else{
      helpText.textContent=instructions();help.hidden=false;
    }
  });
  close.addEventListener("click",()=>{help.hidden=true;button.focus();});
  help.addEventListener("keydown",event=>{
    if(event.key==="Escape"){help.hidden=true;button.focus();}
  });
}
reflect();
