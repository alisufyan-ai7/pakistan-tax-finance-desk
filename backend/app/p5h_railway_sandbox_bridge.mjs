/**
 * P5H default-off owner-only PDF bridge, via Railway's short-lived Sandbox SDK.
 *
 * No original/password in argv, env, logs or guest files. Trusted code only
 * is placed on the VM host BEFORE the owner payload reaches child stdin.
 * A guest's outward Internet access is NOT an adequate PDF sandbox; the
 * Python/pypdf process must pass the inner Bubblewrap network denial probe.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const CONTRACT = "personal_cfo_p5h_synthetic_guest_python_v1";
const FILES = [
  ["p5h_vm_guest_child.py", "/srv/backend/app/p5h_vm_guest_child.py"],
  ["p5h_vm_guest_probe.py", "/srv/backend/app/p5h_vm_guest_probe.py"],
  ["private_bahl_statement_reconciler.py", "/srv/backend/app/private_bahl_statement_reconciler.py"],
  ["p5h_vm_launcher.sh", "/srv/backend/p5h_vm_launcher.sh"],
];
const PROBE_KEYS = [
  "network_denied", "isolated_loopback_only", "host_hidden",
  "code_readonly", "secret_env_hidden", "python_pypdf_imported",
];
const SETUP = [
  "set -eu",
  "mkdir -p /srv/backend/app",
  "export DEBIAN_FRONTEND=noninteractive",
  "apt-get update -qq >/dev/null 2>&1",
  "apt-get install -qq -y --no-install-recommends bubblewrap python3 python3-venv ca-certificates >/dev/null 2>&1",
  "python3 -m venv /usr/local/p5h-venv >/dev/null 2>&1",
  "/usr/local/p5h-venv/bin/pip install --no-cache-dir --disable-pip-version-check -q 'pypdf==6.18.1' >/dev/null 2>&1",
  "test -x /usr/local/p5h-venv/bin/python && test -x /usr/bin/bwrap",
].join("; ");

function requireResult(result, maxBytes) {
  if (!result || result.exitCode !== 0 || result.timedOut === true ||
      result.truncated === true || typeof result.stdout !== "string" ||
      Buffer.byteLength(result.stdout, "utf8") > maxBytes) {
    throw new Error("P5H_GUEST_STEP_REJECTED");
  }
  return result.stdout;
}

function validateOwnerEnvelope(envelope) {
  if (typeof envelope !== "object" || envelope === null ||
      Array.isArray(envelope) ||
      Object.keys(envelope).sort().join(",") !== "document_b64,document_password" ||
      typeof envelope.document_b64 !== "string" ||
      !/^[A-Za-z0-9+/]+={0,2}$/.test(envelope.document_b64) ||
      envelope.document_b64.length > 5_600_000 ||
      typeof envelope.document_password !== "string" ||
      envelope.document_password.length > 128 ||
      (envelope.document_password.length > 0 &&
       !/^[!-~]+$/.test(envelope.document_password))) {
    throw new Error("P5H_BAD_PRIVATE_ENVELOPE");
  }
  return JSON.stringify(envelope);
}

/**
 * Injection is exclusively for synthetic CI; live call imports SDK directly.
 * The parent API separately revalidates exact parsed statement result fields.
 */
const ACTIVE_STATES = new Set(["CREATING", "RUNNING", "DESTROYING"]);

/** Fixed codes only. Never print exception messages, guest output or secrets. */
export class SandboxBridgeBlocked extends Error {
  constructor(stage, createAttempted, createdConfirmed, destroyedVerified) {
    super("P5H_SANDBOX_BLOCKED");
    this.stage = stage;
    this.createAttempted = createAttempted;
    this.createdConfirmed = createdConfirmed;
    this.destroyedVerified = destroyedVerified;
  }
}

function activeSandboxes(items) {
  if (!Array.isArray(items) ||
      items.some(item => typeof item !== "object" || item === null ||
        typeof item.id !== "string" || typeof item.status !== "string")) {
    throw new Error("Invalid sandbox inventory");
  }
  return items.filter(item => ACTIVE_STATES.has(item.status));
}

/** Read-only status command: zero VM creation and no owner document access. */
export async function inspectSandboxInventory(Sandbox) {
  if (!Sandbox || typeof Sandbox.list !== "function") {
    throw new SandboxBridgeBlocked("API_PREFLIGHT", false, false, false);
  }
  try {
    const active = activeSandboxes(await Sandbox.list());
    return {
      contract: "personal_cfo_p5h_sandbox_readonly_inventory_v1",
      active_sandbox_count: active.length,
      new_sandbox_created: false,
      original_document_read: false,
      bank_runtime_activated: false,
    };
  } catch {
    throw new SandboxBridgeBlocked("API_PREFLIGHT", false, false, false);
  }
}

/**
 * A failed SDK call must not consume another one-VM approval silently.
 * Preflight inventory before creation; report stage and cleanup facts,
 * without exposing SDK, VM, password, PDF, path or token error messages.
 */
export async function runIsolatedSandbox(envelope, Sandbox, {probeOnly = false} = {}) {
  if (!Sandbox || typeof Sandbox.create !== "function" ||
      typeof Sandbox.list !== "function") {
    throw new SandboxBridgeBlocked("API_PREFLIGHT", false, false, false);
  }
  let payload;
  try {
    payload = probeOnly ? null : requireOwnerPayload(envelope);
  } catch {
    throw new SandboxBridgeBlocked("INPUT_VALIDATION", false, false, false);
  }
  let sandbox = null;
  let output = null;
  let stage = "API_PREFLIGHT";
  let createAttempted = false;
  let createdConfirmed = false;
  let destroyedVerified = false;
  let failedStage = null;
  let cleanupFailed = false;
  try {
    // Stop if the environment already has a live/creating sandbox; this
    // avoids paying for a second one on the same owner instruction.
    const before = activeSandboxes(await Sandbox.list());
    if (before.length !== 0) throw new Error("Existing active sandbox");
    stage = "SANDBOX_CREATE";
    createAttempted = true;
    sandbox = await Sandbox.create({
      networkIsolation: "ISOLATED",
      idleTimeoutMinutes: 5,
      env: {},
    });
    createdConfirmed = Boolean(sandbox?.id);
    stage = "SANDBOX_POLICY";
    if (!sandbox || sandbox.networkIsolation !== "ISOLATED" ||
        typeof sandbox.id !== "string" ||
        typeof sandbox.destroy !== "function") {
      throw new Error("Missing sandbox identity/isolation");
    }
    stage = "GUEST_SETUP";
    requireResult(await sandbox.exec(SETUP, {
      timeoutSec: 150, ephemeral: true, maxOutputBytes: 512,
    }), 512);
    stage = "TRUSTED_CODE_UPLOAD";
    for (const [source, destination] of FILES) {
      await sandbox.files.write(
        destination, readFileSync(join(HERE, source)),
        {mode: 0o444},
      );
    }
    await sandbox.files.write("/srv/backend/app/__init__.py", "", {mode: 0o444});
    stage = "GUEST_PROBE";
    const probeText = requireResult(await sandbox.exec(
      "bash /srv/backend/p5h_vm_launcher.sh probe",
      {timeoutSec: 16, ephemeral: true, maxOutputBytes: 1200},
    ), 1200);
    stage = "GUEST_PROBE_CONTRACT";
    const probe = JSON.parse(probeText);
    if (typeof probe !== "object" || probe === null ||
        Array.isArray(probe) || Object.keys(probe).sort().join(",") !==
        [...PROBE_KEYS].sort().join(",") ||
        PROBE_KEYS.some(key => probe[key] !== true)) {
      throw new Error("Isolation proof rejected");
    }
    if (probeOnly) {
      output = JSON.stringify({contract: CONTRACT,
        sandbox_synthetic_smoke_passed: true,
        python_pdf_worker_verified: true,
        owner_document_read: false, bank_runtime_activated: false});
    } else {
      stage = "GUEST_PARSE";
      // Untrusted PDF and transient password enter only jailed child stdin.
      const handle = sandbox.exec(
        "bash /srv/backend/p5h_vm_launcher.sh parse",
        {stdin: true, ephemeral: true, timeoutSec: 16, maxOutputBytes: 5500},
      );
      const data = Buffer.from(payload, "utf8");
      for (let index = 0; index < data.length; index += 16 * 1024) {
        await handle.stdin.write(data.subarray(index, index + 16 * 1024));
      }
      await handle.stdin.end();
      output = requireResult(await handle, 5500);
      stage = "GUEST_JSON";
      JSON.parse(output); // Exact financial contract is checked by parent.
    }
  } catch {
    failedStage = stage;
  } finally {
    if (sandbox && typeof sandbox.destroy === "function") {
      try {
        await sandbox.destroy();
        const after = activeSandboxes(await Sandbox.list());
        if (after.some(item => item.id === sandbox.id)) {
          throw new Error("Sandbox still active");
        }
        destroyedVerified = true;
      } catch {
        cleanupFailed = true;
      }
    } else if (createdConfirmed) {
      cleanupFailed = true;
    }
  }
  if (cleanupFailed) {
    throw new SandboxBridgeBlocked(
      "CLEANUP_UNVERIFIED", createAttempted, createdConfirmed, false);
  }
  if (failedStage) {
    throw new SandboxBridgeBlocked(
      failedStage, createAttempted, createdConfirmed, destroyedVerified);
  }
  if (output === null || !destroyedVerified) {
    throw new SandboxBridgeBlocked(
      "CLEANUP_UNVERIFIED", createAttempted, createdConfirmed, destroyedVerified);
  }
  return output;
}

function requireOwnerPayload(envelope) {
  return validateOwnerEnvelope(envelope);
}

async function readStdinLimited(maxBytes = 5_700_000) {
  const chunks = [];
  let length = 0;
  for await (const chunk of process.stdin) {
    length += chunk.length;
    if (length > maxBytes) throw new Error("P5H_INPUT_TOO_LARGE");
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf8");
}

async function main() {
  const statusOnly = process.argv.length === 3 &&
    process.argv[2] === "--status-only";
  const probeOnly = process.argv.length === 3 &&
    process.argv[2] === "--synthetic-probe";
  if (process.argv.length > 3 ||
      (!statusOnly && !probeOnly && process.argv.length !== 2) ||
      !process.env.RAILWAY_TOKEN ||
      !process.env.RAILWAY_ENVIRONMENT_ID ||
      (!statusOnly && (
        process.env.P5H_REMOTE_VM_WORKER_ACTIVE !== "1" ||
        process.env.P5H_REMOTE_VM_G3_REVIEWED !== "1"
      ))) {
    throw new SandboxBridgeBlocked("API_PREFLIGHT", false, false, false);
  }
  let Sandbox;
  try {
    ({ Sandbox } = await import("railway"));
  } catch {
    throw new SandboxBridgeBlocked("SDK_IMPORT", false, false, false);
  }
  if (statusOnly) {
    process.stdout.write(JSON.stringify(await inspectSandboxInventory(Sandbox)) + "\n");
    return;
  }
  const envelope = probeOnly ? null : JSON.parse(await readStdinLimited());
  const result = await runIsolatedSandbox(envelope, Sandbox, {probeOnly});
  process.stdout.write(result + "\n");
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch(error => {
    // Emit only static phase/cleanup facts. Never print host/SDK error,
    // stderr, guest stdout, original bytes, password or token.
    const info = error instanceof SandboxBridgeBlocked ? error : null;
    process.stdout.write(JSON.stringify({
      contract: "personal_cfo_p5h_sandbox_safe_failure_v1",
      status: "BLOCKED",
      stage: info?.stage ?? "PRE_REQUEST_UNKNOWN",
      vm_create_attempted: info?.createAttempted ?? false,
      vm_creation_confirmed: info?.createdConfirmed ?? false,
      vm_destruction_verified: info?.destroyedVerified ?? false,
      original_document_read: false,
      bank_runtime_activated: false,
    }) + "\n");
    process.exitCode = 1;
  });
}
