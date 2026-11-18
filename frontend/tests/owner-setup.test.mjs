import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {OWNER_SETUP_STEPS,OWNER_SETUP_STATUS,renderOwnerSetup} from "../owner-setup.mjs";

const source=name=>readFileSync(new URL("../"+name,import.meta.url),"utf8");

test("owner setup makes the sole-owner sequence clear without claiming activation",()=>{
  assert.equal(OWNER_SETUP_STEPS.length,4);
  assert.equal(OWNER_SETUP_STATUS.role,"One owner");
  assert.equal(OWNER_SETUP_STATUS.accountProvisioned,false);
  assert.equal(OWNER_SETUP_STATUS.secureEnrollmentActive,false);
  assert.equal(OWNER_SETUP_STATUS.recoveryValidated,false);
  assert.equal(OWNER_SETUP_STATUS.googleConnected,false);
  const html=renderOwnerSetup();
  assert.match(html,/One account\. Yours\./);
  assert.match(html,/Secure enrollment is not live yet/);
  assert.match(html,/Save your recovery kit/);
  assert.match(html,/Connect your Google Drive folder/);
  assert.match(html,/What you will see after connection/);
  assert.match(html,/data-go="documents"/);
  assert.match(html,/role="status"/);
  assert.doesNotMatch(html,/input\b|form\b|type="password"|autocomplete="one-time-code"/);
  assert.doesNotMatch(html,/data-action="connect"|\/api\/drive\/oauth\/start/);
});

test("preview cannot pretend OAuth/MFA has been activated by injecting a status object",()=>{
  assert.throws(()=>renderOwnerSetup({...OWNER_SETUP_STATUS,googleConnected:true}),TypeError);
  assert.throws(()=>renderOwnerSetup({...OWNER_SETUP_STATUS,developerPreviewOnly:false}),TypeError);
  assert.throws(()=>renderOwnerSetup(null),TypeError);
});

test("owner setup visible in desktop and mobile PWA without public secret fields",()=>{
  const html=source("index.html");
  const ui=source("ui.mjs");
  const docker=source("Dockerfile");
  assert.equal((html.match(/data-view="setup"/g)||[]).length,2);
  assert.match(ui,/renderOwnerSetup/);
  assert.match(ui,/setup:renderOwnerSetup/);
  assert.match(docker,/owner-setup\.mjs \/usr\/share\/nginx\/html\//);
  assert.match(source("pwa.css"),/grid-template-columns:repeat\(6,minmax\(0,1fr\)\)/);
  assert.match(html,/Development preview, not your financial account/);
  assert.match(source("nginx.railway.conf"),/location\s*=\s*\/api\/owner\/login/);
  assert.match(source("nginx.railway.conf"),/if \(\$p1ak_owner_ingress != "1"\) \{ return 404; \}/);
  assert.match(source("nginx.railway.conf"),/location\s*=\s*\/api\/drive\/oauth\/callback/);
  assert.match(source("nginx.railway.conf"),/if \(\$p1ao_google_ingress != "1"\) \{ return 404; \}/);
});
