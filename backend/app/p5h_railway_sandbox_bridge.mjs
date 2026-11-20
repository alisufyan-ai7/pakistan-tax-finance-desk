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
export async function runIsolatedSandbox(envelope, Sandbox, {probeOnly = false} = {}) {
  if (!Sandbox || typeof Sandbox.create !== "function" ||
      typeof Sandbox.list !== "function") {
    throw new Error("P5H_NO_SANDBOX_PROVIDER");
  }
  const payload = probeOnly ? null : requireOwnerPayload(envelope);
  let sandbox = null;
  let output = null;
  try {
    sandbox = await Sandbox.create({
      networkIsolation: "ISOLATED",
      idleTimeoutMinutes: 5,
      env: {},
    });
    if (!sandbox || sandbox.networkIsolation !== "ISOLATED" ||
        !sandbox.id || typeof sandbox.destroy !== "function") {
      throw new Error("P5H_NOT_ISOLATED");
    }
    requireResult(await sandbox.exec(SETUP, {
      timeoutSec: 150, ephemeral: true, maxOutputBytes: 512,
    }), 512);
    for (const [source, destination] of FILES) {
      await sandbox.files.write(
        destination, readFileSync(join(HERE, source)),
        {mode: 0o444},
      );
    }
    await sandbox.files.write("/srv/backend/app/__init__.py", "", {mode: 0o444});
    const probeText = requireResult(await sandbox.exec(
      "bash /srv/backend/p5h_vm_launcher.sh probe",
      {timeoutSec: 16, ephemeral: true, maxOutputBytes: 1200},
    ), 1200);
    const probe = JSON.parse(probeText);
    if (typeof probe !== "object" || probe === null ||
        Array.isArray(probe) || Object.keys(probe).sort().join(",") !==
        [...PROBE_KEYS].sort().join(",") ||
        PROBE_KEYS.some(key => probe[key] !== true)) {
      throw new Error("P5H_OS_PYTHON_ISOLATION_FAILED");
    }
    if (probeOnly) {
      output = JSON.stringify({contract: CONTRACT,
        sandbox_synthetic_smoke_passed: true,
        python_pdf_worker_verified: true,
        owner_document_read: false, bank_runtime_activated: false});
    } else {
      // Railway's Oct-2026 SDK supports stdin + ephemeral execs, so untrusted
      // PDF/password are never written to host files or recorded as command.
      const handle = sandbox.exec(
        "bash /srv/backend/p5h_vm_launcher.sh parse",
        {stdin: true, ephemeral: true, timeoutSec: 16, maxOutputBytes: 5500},
      );
      const data = Buffer.from(payload, "utf8");
      for (let index = 0; index < data.length; index += 16 * 1024) {
        await handle.stdin.write(data.subarray(index, index + 16 * 1024));
      }
      await handle.stdin.end();
      const result = await handle;
      output = requireResult(result, 5500);
      JSON.parse(output); // Strict financial contract is validated by parent.
    }
  } finally {
    if (sandbox) {
      await sandbox.destroy();
      const active = await Sandbox.list();
      if (!Array.isArray(active) ||
          active.some(item => item.id === sandbox.id &&
            item.status !== "DESTROYED")) {
        throw new Error("P5H_SANDBOX_DESTROY_UNVERIFIED");
      }
    }
  }
  if (output === null) throw new Error("P5H_NO_RESULT");
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
  if (process.env.P5H_REMOTE_VM_WORKER_ACTIVE !== "1" ||
      process.env.P5H_REMOTE_VM_G3_REVIEWED !== "1" ||
      !process.env.RAILWAY_API_TOKEN ||
      !process.env.RAILWAY_ENVIRONMENT_ID) {
    throw new Error("P5H_RUNTIME_DISABLED");
  }
  const probeOnly = process.argv.length === 3 && process.argv[2] === "--synthetic-probe";
  if (!probeOnly && process.argv.length !== 2) {
    throw new Error("P5H_INVALID_COMMAND");
  }
  const envelope = probeOnly ? null : JSON.parse(await readStdinLimited());
  const { Sandbox } = await import("railway");
  const result = await runIsolatedSandbox(envelope, Sandbox, {probeOnly});
  process.stdout.write(result);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch(() => {
    // Never print SDK exceptions, host paths, guest stderr, owner data or keys.
    process.stderr.write("P5H_REMOTE_SANDBOX_UNAVAILABLE\n");
    process.exitCode = 1;
  });
}
