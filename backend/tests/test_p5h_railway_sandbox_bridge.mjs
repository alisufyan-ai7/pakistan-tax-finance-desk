import test from "node:test";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {runIsolatedSandbox, inspectSandboxInventory, SandboxBridgeBlocked, safeFailureReport} from "../app/p5h_railway_sandbox_bridge.mjs";

const GOOD_PROBE = {
  network_denied: true,
  isolated_loopback_only: true,
  host_hidden: true,
  code_readonly: true,
  secret_env_hidden: true,
  python_pypdf_imported: true,
};
const ENVELOPE = {
  document_b64: Buffer.from("%PDF-1.7 SYNTHETIC FIXTURE ONLY").toString("base64"),
  document_password: "synthetic-only-password",
};
function fakeSdk({fail = "", mode = "ISOLATED"} = {}) {
  const state = {created: 0, destroyed: 0, commands: [], files: [],
    stdin: [], options: null, parsed: false, sourceReceivedBeforeProbe: false};
  const Sandbox = {
    async create(options) {
      state.created++;
      state.options = options;
      return {
        id: "synthetic-sandbox-id",
        networkIsolation: mode,
        files: {
          async write(path, data, config) {
            state.files.push({path, content: String(data), config});
          },
        },
        exec(command, options) {
          state.commands.push({command, options});
          if (command.startsWith("set -eu")) {
            return {exitCode: fail === "setup" ? 1 : 0,
              stdout: "", timedOut: false, truncated: false};
          }
          if (command.endsWith(" jail-boot")) {
            return {exitCode: fail === "jail" ? 1 : 0,
              stdout: "P5H_JAIL_BOOTED\n",
              timedOut: false, truncated: false};
          }
          if (command.endsWith(" python-import")) {
            return {exitCode: fail === "python" ? 1 : 0,
              stdout: "P5H_PYPDF_IMPORTED\n",
              timedOut: false, truncated: false};
          }
          if (command.endsWith(" probe")) {
            const data = {...GOOD_PROBE};
            if (fail === "probe") data.network_denied = false;
            return {exitCode: 0, stdout: JSON.stringify(data),
              timedOut: false, truncated: false};
          }
          if (!command.endsWith(" parse")) throw Error("unexpected fake command");
          state.parsed = true;
          const handle = Promise.resolve({
            exitCode: fail === "parse" ? 1 : 0,
            stdout: '{"status":"PASSWORD_REQUIRED","financial_values_verified":false}',
            timedOut: false, truncated: false,
          });
          handle.stdin = {
            async write(chunk) {
              state.stdin.push(Buffer.from(chunk));
            },
            async end() {},
          };
          return handle;
        },
        async destroy() { state.destroyed++; },
      };
    },
    async list() { return []; },
  };
  return {Sandbox, state};
}

test("synthetic guest Python check requires OS denial and guaranteed destruction", async () => {
  const {Sandbox, state} = fakeSdk();
  const result = JSON.parse(await runIsolatedSandbox(null, Sandbox, {probeOnly: true}));
  assert.equal(result.sandbox_synthetic_smoke_passed, true);
  assert.equal(result.python_pdf_worker_verified, true);
  assert.equal(result.owner_document_read, false);
  assert.equal(state.created, 1);
  assert.equal(state.destroyed, 1);
  assert.equal(state.options.networkIsolation, "ISOLATED");
  assert.deepEqual(state.options.env, {});
  assert.equal(state.options.idleTimeoutMinutes, 5);
  assert.equal(state.stdin.length, 0);
  assert.equal(state.files.length, 5);
  assert.ok(state.commands.every(c => !c.command.includes("document_password")));
});

test("sensitive PDF/passphrase go ONLY to ephemeral child stdin AFTER the probe", async () => {
  const {Sandbox, state} = fakeSdk();
  const result = JSON.parse(await runIsolatedSandbox(ENVELOPE, Sandbox));
  assert.equal(result.status, "PASSWORD_REQUIRED");
  assert.equal(state.created, 1);
  assert.equal(state.destroyed, 1);
  assert.equal(state.commands.filter(x => x.command.endsWith(" parse")).length, 1);
  const invocation = state.commands.at(-1);
  assert.equal(invocation.options.stdin, true);
  assert.equal(invocation.options.ephemeral, true);
  assert.ok(state.commands.every(x => !x.command.includes(ENVELOPE.document_password)));
  assert.ok(state.files.every(x => !x.content.includes(ENVELOPE.document_password)));
  assert.deepEqual(JSON.parse(Buffer.concat(state.stdin).toString("utf8")), ENVELOPE);
});

test("bad no-network proof means no payload ever enters the guest", async () => {
  const {Sandbox, state} = fakeSdk({fail: "probe"});
  await assert.rejects(runIsolatedSandbox(ENVELOPE, Sandbox));
  assert.equal(state.destroyed, 1);
  assert.equal(state.parsed, false);
  assert.equal(state.stdin.length, 0);
});

test("setup, source, parse, missing isolation, and bad owner request fail closed", async () => {
  for (const fail of ["setup", "parse"]) {
    const {Sandbox, state} = fakeSdk({fail});
    await assert.rejects(runIsolatedSandbox(ENVELOPE, Sandbox));
    assert.equal(state.created, 1);
    assert.equal(state.destroyed, 1);
  }
  const {Sandbox, state} = fakeSdk({mode: "PRIVATE"});
  await assert.rejects(runIsolatedSandbox(ENVELOPE, Sandbox));
  assert.equal(state.destroyed, 1);
  assert.equal(state.parsed, false);
  const invalid = {document_b64: "%%%/", document_password: "synthetic"};
  await assert.rejects(runIsolatedSandbox(invalid, Sandbox));
  assert.equal(state.created, 1); // prior rejected mode only
});


test("read-only inventory never creates VM and reports only safe counts", async () => {
  const {Sandbox, state} = fakeSdk();
  Sandbox.list = async () => [
    {id: "fake-one", status: "RUNNING"},
    {id: "fake-finished", status: "DESTROYED"},
  ];
  const result = await inspectSandboxInventory(Sandbox);
  assert.equal(result.active_sandbox_count, 1);
  assert.equal(result.new_sandbox_created, false);
  assert.equal(result.original_document_read, false);
  assert.equal(state.created, 0);
});

test("pre-existing live VM fails BEFORE another paid create", async () => {
  const {Sandbox, state} = fakeSdk();
  Sandbox.list = async () => [{id: "fake-existing", status: "RUNNING"}];
  await assert.rejects(
    runIsolatedSandbox(null, Sandbox, {probeOnly: true}),
    error => error instanceof SandboxBridgeBlocked &&
      error.stage === "API_PREFLIGHT" &&
      error.createAttempted === false,
  );
  assert.equal(state.created, 0);
});

test("safe stage and cleanup state on failed trusted setup", async () => {
  const {Sandbox, state} = fakeSdk({fail: "setup"});
  await assert.rejects(
    runIsolatedSandbox(null, Sandbox, {probeOnly: true}),
    error => error instanceof SandboxBridgeBlocked &&
      error.stage === "GUEST_SETUP" &&
      error.createAttempted === true &&
      error.createdConfirmed === true &&
      error.destroyedVerified === true &&
      !JSON.stringify(error).includes("synthetic-only-password"),
  );
  assert.equal(state.destroyed, 1);
});

test("create-time uncertain VM state is not falsely reported destroyed", async () => {
  const {Sandbox, state} = fakeSdk();
  Sandbox.create = async () => { throw new Error("fake secret runtime failure"); };
  await assert.rejects(
    runIsolatedSandbox(null, Sandbox, {probeOnly: true}),
    error => error instanceof SandboxBridgeBlocked &&
      error.stage === "SANDBOX_CREATE" &&
      error.createAttempted === true &&
      error.createdConfirmed === false &&
      error.destroyedVerified === false &&
      !error.message.includes("secret"),
  );
  assert.equal(state.created, 0);
});

test("cleanup uncertainty overrides successful synthetic proof", async () => {
  const {Sandbox, state} = fakeSdk();
  const create = Sandbox.create;
  Sandbox.create = async (...args) => {
    const guest = await create(...args);
    guest.destroy = async () => {throw new Error("synthetic sensitive guest failure");};
    return guest;
  };
  await assert.rejects(
    runIsolatedSandbox(null, Sandbox, {probeOnly: true}),
    error => error instanceof SandboxBridgeBlocked &&
      error.stage === "CLEANUP_UNVERIFIED" &&
      error.createdConfirmed === true &&
      error.destroyedVerified === false,
  );
  assert.equal(state.created, 1);
});


test("safe failure JSON does not leak upstream errors or misstate PDF read", () => {
  const createError = new SandboxBridgeBlocked("SANDBOX_CREATE", true, false, false);
  assert.deepEqual(safeFailureReport(createError), {
    contract: "personal_cfo_p5h_sandbox_safe_failure_v1",
    status: "BLOCKED",
    stage: "SANDBOX_CREATE",
    vm_create_attempted: true,
    vm_creation_confirmed: false,
    vm_destruction_verified: false,
    original_document_read: false,
    bank_runtime_activated: false,
  });
  const parseError = new SandboxBridgeBlocked("GUEST_PARSE", true, true, true);
  assert.equal(safeFailureReport(parseError).original_document_read, null);
  assert.equal(safeFailureReport(new Error("SYNTHETIC_SECRET")).stage, "PRE_REQUEST_UNKNOWN");
  assert.ok(!JSON.stringify(safeFailureReport(new Error("SYNTHETIC_SECRET"))).includes("SECRET"));
});


test("synthetic probe separates jailed shell from jailed Python failures", async () => {
  for (const [fail, expectedStage] of [
    ["jail", "GUEST_JAIL_BOOT"],
    ["python", "GUEST_PYTHON_IMPORT"],
  ]) {
    const {Sandbox, state} = fakeSdk({fail});
    await assert.rejects(
      runIsolatedSandbox(null, Sandbox, {probeOnly: true}),
      error => error instanceof SandboxBridgeBlocked &&
        error.stage === expectedStage &&
        error.createdConfirmed === true &&
        error.destroyedVerified === true,
    );
    assert.equal(state.created, 1);
    assert.equal(state.destroyed, 1);
    assert.equal(state.parsed, false);
    assert.equal(state.stdin.length, 0);
    if (fail === "jail") {
      assert.equal(state.commands.some(x => x.command.endsWith(" python-import")), false);
    }
  }
});

test("successful probe executes both synthetic preflights before actual parser", async () => {
  const {Sandbox, state} = fakeSdk();
  await runIsolatedSandbox(null, Sandbox, {probeOnly: true});
  const actions = state.commands.map(x => x.command);
  assert.ok(actions.indexOf(actions.find(x => x.endsWith(" jail-boot"))) <
            actions.indexOf(actions.find(x => x.endsWith(" python-import"))));
  assert.ok(actions.indexOf(actions.find(x => x.endsWith(" python-import"))) <
            actions.indexOf(actions.find(x => x.endsWith(" probe"))));
  assert.equal(state.destroyed, 1);
});


test("guest launcher Bash syntax and mandatory unchanged isolation contract", () => {
  const launcher = new URL("../app/p5h_vm_launcher.sh", import.meta.url);
  execFileSync("bash", ["-n", fileURLToPath(launcher)], {stdio: "ignore"});
  const script = readFileSync(launcher, "utf8");
  for (const invariant of [
    "--die-with-parent", "--unshare-all", "--cap-drop ALL",
    "--clearenv", "--tmpfs /", "--ro-bind /usr /usr",
    "--ro-bind /srv/backend/app /srv/backend/app",
  ]) {
    assert.ok(script.includes(invariant), "Missing guest boundary: " + invariant);
  }
  for (const mode of ["jail-boot", "python-import", "probe", "parse"]) {
    assert.ok(script.includes(mode + ") set --"));
  }
  assert.equal((script.match(/exec \/usr\/bin\/bwrap/g) || []).length, 1);
});
