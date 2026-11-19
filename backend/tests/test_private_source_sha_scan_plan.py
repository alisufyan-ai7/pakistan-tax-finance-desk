"""P5I synthetic complete original-SHA planning: zero real source or DB access."""
import base64
from datetime import datetime, timezone, timedelta

import pytest

from app.drive_inbox_planner import DriveFile, _index, _version
from app.private_source_sha_scan_plan import (
    PrivateSourceShaPlanBlocked as Blocked,
    plan_complete_synthetic_source_sha_scan as plan,
)

FOLDER = "SYNTHETIC_P5I_OWNER_FOLDER_2026"
OTHER = "SYNTHETIC_OTHER_OWNER_FOLDER_2026"
A = "SYNTHETIC_P5I_FILE_ABCDEFGHIJKLMNOP"
B = "SYNTHETIC_P5I_FILE_ZYXWVUTSRQPONMLK"
WHEN = datetime(2026, 11, 19, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def gated(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.setenv("P5I_SYNTHETIC_SHA_PLANNER_ONLY", "1")
    monkeypatch.setenv("DRIVE_INDEX_HMAC_KEY",
                       base64.urlsafe_b64encode(b"I"*32).decode("ascii"))
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))


def file(fid=A, name="synthetic.pdf", *, when=WHEN, parent=FOLDER):
    return DriveFile(id=fid, name=name, mime_type="application/pdf",
                     parent_ids=(parent,), modified_time=when,
                     size_bytes=152, md5_checksum="a"*32, trashed=False)


def receipt(f, content="v1"):
    return {
        "source_hmac": _index("file", f.id),
        "revision_hmac": _version(f),
        "source_content_hmac": _index("source-sha256", "f"*64 if content=="v1" else "e"*64),
        "byte_hash_verified": True,
    }


def run(files, proofs=None, *, prior=None, **options):
    files = tuple(files)
    return plan(
        folder_id=options.get("folder", FOLDER),
        files=files,
        proof_receipts=tuple(receipt(f) for f in files) if proofs is None else tuple(proofs),
        prior=prior, inventory_complete=options.get("inventory_complete", True),
        proofs_complete=options.get("proofs_complete", True),
        approved_synthetic_fixture=options.get("approved", True),
    )


def test_first_scan_replay_and_no_ledger_or_persistence_claims():
    files = (file(), file(B, "synthetic-second.pdf"))
    first = run(files)
    assert first["stage_counts"]["new"] == 2
    assert first["source_hashes_persisted"] is False
    assert first["background_sync_active"] is False
    assert first["financial_values_verified"] is False
    assert first["provider_network_used"] is False
    assert first["planner_computed_source_sha256"] is False
    assert len(first["next_manifest"]) == 2
    assert A not in str(first) and B not in str(first)
    assert FOLDER not in str(first) and "synthetic.pdf" not in str(first)
    identical = run(files[::-1], prior=first["next_manifest"])
    assert identical["idempotent_replay"] is True
    assert identical["stage_counts"]["unchanged"] == 2
    assert identical["next_manifest"] == first["next_manifest"]


def test_separates_renamed_revision_content_changed_missing_reappeared():
    initial = run([file(), file(B, "second.pdf")])["next_manifest"]
    rename = file(name="renamed.pdf")
    assert run([rename, file(B, "second.pdf")], prior=initial)["stage_counts"][
        "renamed_needs_review"] == 1
    revised = file(when=WHEN + timedelta(days=1))
    assert run([revised, file(B, "second.pdf")], prior=initial)["stage_counts"][
        "revision_changed_needs_review"] == 1
    changed = run([file(), file(B, "second.pdf")],
                  proofs=[receipt(file(), "v2"), receipt(file(B, "second.pdf"))],
                  prior=initial)
    assert changed["stage_counts"]["content_changed_needs_review"] == 1
    missing = run([file()], prior=initial)
    assert missing["stage_counts"]["missing_in_source"] == 1
    repeat = run([file()], prior=missing["next_manifest"])
    assert repeat["stage_counts"]["still_missing"] == 1
    assert repeat["idempotent_replay"] is True
    return_back = run([file(), file(B, "second.pdf")], prior=missing["next_manifest"])
    assert return_back["stage_counts"]["reappeared_needs_review"] == 1


@pytest.mark.parametrize("reason", [
    "real_mode", "feature_off", "wrong_folder", "incomplete_inventory",
    "incomplete_proofs", "not_approved", "partial_proofs", "duplicate_proofs",
    "duplicate_metadata", "wrong_revision", "unknown_file_proof",
    "unverified_proof", "wrong_parent", "invalid_prior", "bad_content_hmac",
])
def test_rejects_untrusted_or_partial_without_advancing_state(monkeypatch, reason):
    f = file()
    files = [f]
    proofs = [receipt(f)]
    kw = {}
    prior = None
    if reason == "real_mode":
        monkeypatch.setenv("APP_DATA_MODE", "real")
    elif reason == "feature_off":
        monkeypatch.delenv("P5I_SYNTHETIC_SHA_PLANNER_ONLY")
    elif reason == "wrong_folder":
        monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", "f"*64)
    elif reason == "incomplete_inventory":
        kw["inventory_complete"] = False
    elif reason == "incomplete_proofs":
        kw["proofs_complete"] = False
    elif reason == "not_approved":
        kw["approved"] = False
    elif reason == "partial_proofs":
        proofs = []
    elif reason == "duplicate_proofs":
        proofs = [receipt(f), receipt(f)]
    elif reason == "duplicate_metadata":
        files = [f, f]
        proofs = [receipt(f), receipt(f)]
    elif reason == "wrong_revision":
        proofs[0]["revision_hmac"] = "f"*64
    elif reason == "unknown_file_proof":
        proofs[0]["source_hmac"] = "d"*64
    elif reason == "unverified_proof":
        proofs[0]["byte_hash_verified"] = False
    elif reason == "wrong_parent":
        files = [file(parent=OTHER)]
    elif reason == "invalid_prior":
        prior = {_index("file", A): {"raw_name": "should-not-accept"}}
    elif reason == "bad_content_hmac":
        proofs[0]["source_content_hmac"] = "not-sha-hmac"
    with pytest.raises(Blocked):
        run(files, proofs=proofs, prior=prior, **kw)


def test_empty_only_allowed_as_explicit_completed_folder_inventory():
    assert run([])["visible_sources"] == 0
    before = run([file()])["next_manifest"]
    missing = run([], proofs=[], prior=before)
    assert missing["stage_counts"]["missing_in_source"] == 1
    with pytest.raises(Blocked):
        run([], proofs=[], prior=before, inventory_complete=False)
