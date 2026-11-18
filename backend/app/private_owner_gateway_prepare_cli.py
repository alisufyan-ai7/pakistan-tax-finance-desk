"""P1AM: one attended Mac command to PREPARE (never activate) ingress secret.

Writes a fresh random independent gateway proof ONLY to two existing approved
Personal CFO Railway development services over railway CLI stdin. It never
prints/copies the generated token to ChatGPT, shell argv, environment, logs or
GitHub, and never sets public G2 flags, applies staged Google secret, deploys,
starts browser OAuth or exposes financial records.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys

PROJECT = "7021b227-f704-43d6-bcff-debdb7255b81"
ENVIRONMENT = "development"
SERVICES = ("personal-cfo-api-preview", "personal-cfo-frontend-preview")
VARIABLE = "P1Q_PRIVATE_GATEWAY_SHARED_TOKEN"
APPROVAL = "PREPARE PERSONAL CFO PRIVATE GATEWAY ONLY"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{48,256}$")


class PrivateGatewayPreparationBlocked(ValueError):
    """Private one-owner gateway credential was not fully configured."""


def prepare():
    if (sys.platform != "darwin"
        or not sys.stdin.isatty() or not sys.stdout.isatty()
        or shutil.which("railway") is None):
        raise PrivateGatewayPreparationBlocked(
            "Trusted attended Mac with authenticated Railway CLI required"
        )
    print("Personal CFO owner login gateway key preparation only.")
    print("No public login, OAuth consent, financial data or staged Google change.")
    print("Never screenshot or share any Railway variables or secrets.")
    if input("Type exact approval phrase: ").strip() != APPROVAL:
        raise PrivateGatewayPreparationBlocked("Owner did not approve gateway prep")
    token = secrets.token_urlsafe(64)
    if _TOKEN_RE.fullmatch(token) is None:
        raise PrivateGatewayPreparationBlocked("Random gateway token invalid")
    written = 0
    for service in SERVICES:
        command = [
            "railway", "variable", "set", VARIABLE, "--stdin",
            "--project", PROJECT, "--environment", ENVIRONMENT,
            "--service", service, "--skip-deploys",
        ]
        try:
            result = subprocess.run(
                command, input=token, text=True, capture_output=True,
                timeout=60, check=False,
            )
            if result.returncode != 0:
                raise ValueError()
        except Exception:
            # A partial write leaves all owner ingress flags OFF. Rerun the
            # command after resolving CLI authorization to replace both keys.
            raise PrivateGatewayPreparationBlocked(
                "Private gateway preparation incomplete; no release enabled"
            ) from None
        written += 1
    return {
        "existing_approved_services_configured": written,
        "gateway_key_strength_independent": True,
        "gateway_token_printed": False,
        "railway_deploys_triggered": False,
        "staged_google_oauth_secret_applied": False,
        "public_owner_login_activated": False,
        "real_financial_data_enabled": False,
    }


def main():
    try:
        print(json.dumps(prepare(), sort_keys=True))
        return 0
    except PrivateGatewayPreparationBlocked:
        print("Private owner gateway key preparation unavailable or denied",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
