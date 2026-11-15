# M2c — Owner MFA Session Foundation (2026-11-15)

**Status:** Implemented **synthetic-only** authentication foundation, not production-ready financial-data access. Owner inputs, authenticator setup, cloud deployment and real tax files are NOT required for development and were NOT requested or used. Repository intentionally PUBLIC (code/docs/synthetic fixtures only) by owner decision.

## Engineering outcomes

1. **Optional owner-only MFA session mode**, controlled by `OWNER_AUTH_MODE=totp_session`. Default legacy `local_basic` remains for loopback synthetic development only. Both modes reject non-local request clients; `totp_session` additionally requires HTTPS. `APP_DATA_MODE=real` still fails startup.
2. **Scrypt hashed owner password** and RFC6238 six-digit TOTP (30-second period, ±1 window); no plaintext password or TOTP seed committed. Login requires both factors. A persistent `owner_auth_state` record tracks last accepted TOTP counter to reject replay; database row lock is requested under PostgreSQL. Races across initial provisioning/multiple instances still need production hardening.
3. **Server-side owner sessions**, storing only SHA-256 of random 32-byte cookie token (not the cookie itself), creation/expiry/revocation and CSRF token hash in PostgreSQL/SQLite; 8-hour expiry. Cookies use `__Host-` prefix, `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/`, no Domain. Authenticated `GET /api/auth/session` retrieves a session-specific CSRF token; all mutating authenticated routes require the token. Cross-origin mutation attempts with an Origin header are rejected. Logout revokes the stored token.
4. **Browser login page** at `/login` in MFA mode; the existing local demo dashboard requests its session/CSRF on load and attaches CSRF headers to mutations. No login secrets are transmitted to GitHub or external providers.
5. **Alembic revision `0002_owner_mfa`** creates `owner_auth_state` and `owner_sessions`; existing `0001_initial` migration remains intact. For PostgreSQL runtime, app requires explicit migration to exactly revision 0002; no auto-DDL. Offline fail-closed destructive downgrade retained.

## Synthetic-only local test setup

To test without any owner secret, create **throwaway** credentials locally (do not paste them into chat/GitHub):

```bash
cd backend
python -m pip install -e '.[dev]'
python - <<'PY'
from app.auth_mfa import password_hash
import base64,secrets
print('OWNER_PASSWORD_SCRYPT='+password_hash('USE_A_UNIQUE_16_PLUS_CHARACTER_SYNTHETIC_PASSWORD'))
print('OWNER_TOTP_SECRET='+base64.b32encode(secrets.token_bytes(20)).decode())
PY
```

Set `OWNER_AUTH_MODE=totp_session` and those values in **local environment only**; configure the synthetic TOTP secret in a local authenticator for a **throwaway demo**. Serve HTTPS on loopback using a trusted local TLS arrangement. Visit `/login` (rather than `/`) for MFA session login. **Do not deploy this as a financial production service.** The default `local_basic` mode needs only `OWNER_PASSWORD` but remains localhost synthetic-only.

### Verification

- `pytest -q` — all current synthetic M1/M2a/M2b/M2c tests.
- RFC6238 known six-digit test vector, strong hashed-password verification, wrong-password failure, session cookie attributes, CSRF and Origin rejection, TOTP reuse denial, token-hash storage, session expiry, HTTPS requirement and audited logout revocation.
- `python -m alembic ... upgrade head` and `... check` on new disposable SQLite + ephemeral PostgreSQL 18 CI; expected migration version `0002_owner_mfa`.

## Still required before real financial documents

- A reviewed deployment strategy (true TLS termination, secure identity recovery, first-login credential provisioning, MFA recovery, admin session-device revocation, robust distributed login rate limiting and cross-worker TOTP replay tests).
- Secure PostgreSQL roles, encrypted **all** sensitive transaction/party/statement fields, original PDF/CSV blob storage and key-rotation design, encryption backup key availability, off-site backups and disaster restore trials.
- Idempotent document parser pipelines with verified real Pakistani bank/FBR formats, signed uploads, restricted Office/PDF processing and full authenticated audit trail.
- Legal year-specific deterministic FBR tax rules and independent validation, correct 2023+ wealth reconciliation, borrower/lender and asset holdings records.
- Final security audit before the app can accept any actual personal bank statements or previously filed tax returns. This phase does **not** remove the current synthetic-only prohibition.

## Handoff

Proceed independently on private storage, encrypted structured ledger fields, synthetic document adapters and accounting event models; do not ask for owner returns or paid infrastructure merely to continue coding. Real-data onboarding awaits a separate security acceptance. Read `AGENT_START_HERE.md` and `docs/CURRENT_HANDOFF.md` for the authoritative next step.
