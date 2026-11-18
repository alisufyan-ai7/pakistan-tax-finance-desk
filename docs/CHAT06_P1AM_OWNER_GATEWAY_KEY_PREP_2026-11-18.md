# P1AM — One-command existing Railway owner gateway proof preparation (18 Nov 2026)

**Why:** The existing private backend P1AJ and default-off public frontend P1AK require a **distinct shared trusted server-to-server gateway token**. It must exist in both existing Personal CFO Railway `development` services, with no secret typed/pasted into ChatGPT or GitHub. Generating an opaque key twice would break login; reusing the preview token would collapse privilege domains.

## Code and exact contract

`backend/app/private_owner_gateway_prepare_cli.py` is a **Mac-only, attached-TTY**, default-off operator command. It generates a new cryptographically secure random URL-safe token of at least 64 characters **locally in memory**, and writes it via Railway CLI `--stdin` + `--skip-deploys` to exactly these already approved services in project `personal-cfo-dev-sandbox` / `development`:

- `personal-cfo-api-preview` — variable NAME `P1Q_PRIVATE_GATEWAY_SHARED_TOKEN`
- `personal-cfo-frontend-preview` — same variable NAME and identical private value

The command never displays or logs the value or saves it to a local file. It never sets `P1AK_OWNER_INGRESS_ENABLED`, `P1AJ_OWNER_LOGIN_RUNTIME`, a G2 review flag, `APP_DATA_MODE=real`, `P1C_GOOGLE_CLIENT_SECRET` or a Google folder ID. No redeploy, staged-secret acceptance, Google consent, owner login, original-byte import or financial table modification occurs. A failed/partial write leaves public login disabled and advises rerunning the same command; its sanitized result never confirms a successful gateway public release.

Once **code security acceptance is independently completed**, the only eventual owner terminal action for this key is:

```sh
# From their existing trusted Personal CFO backend directory and venv:
python -m app.private_owner_gateway_prepare_cli
```

It privately asks them to type the displayed full approval phrase. Owner confirms **only sanitized JSON booleans**; no secret/token output. Do not request the passphrase, token or raw Railway variable values. Running the command is *not required to merge source tests*. It is a once-only operational prerequisite **only when ready to activate secure owner login**. Do not ask for backups or repeat private restore exercises to develop this source-only component.

Source-only synthetic tests prove same random token passed exactly twice over stdin, no shell args/log output, distinct fixed services, --skip-deploys, rejection on non-Mac/non-TTY/no CLI/denied approval, and safe failure when second service write fails.

Remaining operational release gates: actual active strict private owner SQL role and MFA, authenticated TLS Nginx + exact method/path rate controls, Railway edge/upstream logs not containing URL/query/authorization material, browser session/CSRF and optional G2 independent recovery acceptance. **Google secret remains staged/unapplied** until the complete reviewed callback exists and the owner authorizes browser consent.
