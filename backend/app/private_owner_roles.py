"""P1W: one human owner, explicit capability grants; no fake multi-user admin.

The *only* human application role for Personal CFO's initial deployment is
'owner'. Technical PostgreSQL roles (migration vs restricted credential
service) are not human users. No invited users, operator backdoors or
role elevation endpoint exist. Future team roles require a reviewed migration.
"""
from __future__ import annotations

import os

from sqlalchemy.orm import Session

from .private_owner_identity import (
    PrivateOwnerIdentityBlocked, verify_private_owner_session,
)


OWNER_CAPABILITIES = frozenset({
    "owner:session",
    "owner:recovery",
    "drive:metadata",
    "documents:review",
})


class PrivateOwnerRoleBlocked(ValueError):
    """A capability was not approved for the single authenticated owner."""


def require_single_owner_capability(
    db: Session, *, owner_ref: str, token: str,
    capability: str, csrf: str | None = None,
    mutation: bool = False, now_epoch: int | None = None,
) -> dict:
    """Require valid one-owner MFA, with CSRF for any mutating action.

    This policy does not grant actual Drive token exchange or financial-data
    authority; every underlying operation retains its own release gate.
    """
    if (os.getenv("P1W_OWNER_ROLE_POLICY_ONLY") != "1"
        or os.getenv("APP_DATA_MODE") != "synthetic"
        or type(capability) is not str
        or capability not in OWNER_CAPABILITIES):
        raise PrivateOwnerRoleBlocked("Owner capability denied")
    try:
        verify_private_owner_session(
            db, owner_ref=owner_ref, token=token,
            csrf=csrf, mutation=mutation, now_epoch=now_epoch)
    except PrivateOwnerIdentityBlocked:
        raise PrivateOwnerRoleBlocked("Owner MFA session required") from None
    return {
        "principal_type": "single_owner",
        "role": "owner",
        "capability": capability,
        "human_user_limit": 1,
        "additional_app_users_enabled": False,
        "finance_authority_from_role_alone": False,
        "google_provider_grant_from_role_alone": False,
    }
