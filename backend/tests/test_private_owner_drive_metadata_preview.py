"""P1AP: fake-Google authenticated single-folder metadata preview, no file bytes."""
import base64
import json
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import pytest

from app import models  # noqa
from app.db import Base
from app.drive_inbox_planner import _index
from app.drive_google_oauth import GOOGLE_METADATA_SCOPE, PERSONAL_CFO_RAILWAY_CALLBACK
from app.private_metadata_grant_custody import store_private_metadata_grant
from app.private_owner_drive_metadata_preview import (
    PrivateMetadataSnapshotBlocked, scan_one_owner_folder_metadata,
)

OWNER = "SYNTHETIC_PREVIEW_OWNER_P1AP_2026"
FOLDER = "SYNTHETIC_PRIVATE_P1AP_FOLDER_2026"
CLIENT = "000000000000-syntheticdev.apps.googleusercontent.com"
REFRESH = "SYNTHETIC_NOT_REAL_REFRESH_" + "T" * 48
ACCESS = "SYNTHETIC_NOT_REAL_ACCESS_" + "Z" * 50
FOO_ID = "SYNTHETIC_DRIVE_FILE_P1AP_ABCDEF1234"
BAR_ID = "SYNTHETIC_DRIVE_FILE_P1AP_ZYXW987654"
T = 1_800_270_000


def key(b):
    return base64.urlsafe_b64encode(bytes([b])*32).decode("ascii")


def file(name="bank_statement_2026.pdf", *, fid=FOO_ID, parent=FOLDER):
    return {
        "id": fid, "name": name,
        "mimeType": "application/pdf",
        "parents": [parent], "size": "12345",
        "modifiedTime": "2026-11-18T11:07:31.000Z",
        "md5Checksum": "d" * 32, "trashed": False,
    }


@pytest.fixture
def env(tmp_path, monkeypatch):
    values = {
        "APP_DATA_MODE": "synthetic",
        "P1W_OWNER_REF": OWNER,
        "P1B_PRIVATE_OAUTH_CONTRACT_ONLY": "1",
        "P1B_GOOGLE_CLIENT_ID": CLIENT,
        "P1B_GOOGLE_REDIRECT_URI": PERSONAL_CFO_RAILWAY_CALLBACK,
        "P1B_GOOGLE_FOLDER_ID": FOLDER,
        "P1D_RAILWAY_CALLBACK_CONTRACT_ONLY": "1",
        "DRIVE_INDEX_HMAC_KEY": key(11),
        "P1C_GOOGLE_NETWORK_ENABLED": "1",
        "P1C_PRIVATE_OWNER_MFA_ACCEPTED": "1",
        "P1C_GOOGLE_CLIENT_SECRET": "SYNTHETIC_WEB_CLIENT_NEVER_ACTUAL_" + "C"*20,
        "P1AL_CLOUD_METADATA_NETWORK_ONLY": "1",
        "P1AL_G2_EXACT_OAUTH_REVIEWED": "1",
        "P1AN_GOOGLE_METADATA_RUNTIME": "1",
        "P1R_PRIVATE_OAUTH_STATE_ONLY": "1",
        "P1R_G2_SESSION_OAUTH_REVIEWED": "1",
        "P1AP_OWNER_FOLDER_METADATA_REVIEW_ONLY": "1",
        "P1AP_G2_AUTHENTICATED_METADATA_UI_REVIEWED": "1",
        "P1M_PRIVATE_METADATA_CUSTODY_ONLY": "1",
        "P1M_G2_REAL_CREDENTIAL_RELEASE_REVIEWED": "1",
        "P1M_SQLITE_FAKE_TEST_ONLY": "1",
        "P1M_METADATA_ENCRYPTION_KEYS_JSON": json.dumps({
            "cfo-google-key-v1": key(12),
            "cfo-google-key-v2": key(13),
        }),
        "P1M_METADATA_ACTIVE_KEY_ID": "cfo-google-key-v1",
        "P1M_METADATA_ROW_HMAC_KEY": key(14),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("DRIVE_ALLOWED_FOLDER_HMAC", _index("folder", FOLDER))
    engine = create_engine("sqlite:///" + str(tmp_path / "fake-metadata.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        store_private_metadata_grant(
            db, owner_ref=OWNER, folder_id=FOLDER, client_id=CLIENT,
            refresh_token=REFRESH, now_epoch=T,
        )
    yield engine, monkeypatch
    engine.dispose()


def fake_google(seen, *, pages=None, owner=True):
    pages = pages if pages is not None else [
        {"files": [file()], "nextPageToken": "NEXT_P1AP"},
        {"files": [file("accountant_working_papers.xlsx", fid=BAR_ID,
                        ) | {"mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}]},
    ]
    def transport(method, url, form, bearer):
        seen.append((method, urlsplit(url).path, form is not None, bearer is not None))
        if method == "POST" and url == "https://oauth2.googleapis.com/token":
            assert form["grant_type"] == "refresh_token"
            assert form["refresh_token"] == REFRESH
            assert bearer is None
            return {
                "access_token": ACCESS, "token_type": "Bearer",
                "scope": GOOGLE_METADATA_SCOPE, "expires_in": 3599,
            }
        if method == "GET" and "/drive/v3/files/" in url:
            assert bearer == ACCESS
            return {
                "id": FOLDER,
                "mimeType": "application/vnd.google-apps.folder",
                "trashed": False, "shared": False, "owners": [{"me": owner}],
            }
        if method == "GET" and url.startswith("https://www.googleapis.com/drive/v3/files?"):
            assert bearer == ACCESS
            q = parse_qs(urlsplit(url).query)
            assert q["q"] == [f"'{FOLDER}' in parents and trashed = false"]
            assert q["fields"] == [
                "nextPageToken,incompleteSearch,files(id,name,mimeType,parents,size,modifiedTime,md5Checksum,trashed)"
            ]
            ix = 0 if "pageToken" not in q else 1
            return pages[ix]
        raise AssertionError("Unexpected Google transport call")
    return transport


def run(engine, transport):
    return scan_one_owner_folder_metadata(
        session_factory=lambda: Session(engine),
        owner_ref=OWNER, transport=transport, now_epoch=T,
    )


def test_full_two_page_one_folder_preview_with_no_raw_ids_or_media(env):
    engine, _ = env
    seen = []
    result = run(engine, fake_google(seen))
    assert result["total"] == 2
    assert result["snapshot_complete"] is True
    assert result["background_sync_active"] is False
    assert result["snapshot_persisted"] is False
    assert result["source_bytes_downloaded"] is False
    assert result["real_financial_data_enabled"] is False
    assert {x["virtual_collection"] for x in result["items"]} == {
        "bank_statements", "accountant_working",
    }
    assert all(not i["original_content_imported"] and
               not i["financial_claims_verified"] for i in result["items"])
    rendered = str(result)
    assert FOLDER not in rendered and CLIENT not in rendered
    assert FOO_ID not in rendered and BAR_ID not in rendered
    assert REFRESH not in rendered and ACCESS not in rendered
    assert [x[0] for x in seen] == ["POST", "GET", "GET", "GET"]
    assert not any("/export" in x[1] or "/alt=media" in x[1] for x in seen)
    with engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM owner_google_metadata_grants")).scalar_one() == 1
        assert db.execute(text("SELECT count(*) FROM drive_inbox_items")).scalar_one() == 0


@pytest.mark.parametrize("case", [
    "bad_parent", "duplicate_ids", "malformed_size", "incomplete",
    "cursor_loop", "bad_mime", "too_many_pages", "unowned_folder",
])
def test_adversarial_metadata_never_returns_partial_snapshot(env, case):
    engine, _ = env
    seen = []
    first = file()
    second = file("invoice.pdf", fid=BAR_ID)
    page1 = {"files": [first], "nextPageToken": "NEXT_P1AP"}
    page2 = {"files": [second]}
    if case == "bad_parent":
        page2["files"] = [file("out.pdf", fid=BAR_ID,
                               parent="SYNTHETIC_OUTSIDE_FOLDER_XYZ")]
    elif case == "duplicate_ids":
        page2["files"] = [file("duplicate.pdf", fid=FOO_ID)]
    elif case == "malformed_size":
        page2["files"] = [file("bad.pdf", fid=BAR_ID) | {"size": "-1"}]
    elif case == "incomplete":
        page2["incompleteSearch"] = True
    elif case == "cursor_loop":
        page2["nextPageToken"] = "NEXT_P1AP"
    elif case == "bad_mime":
        page2["files"] = [file("bad.pdf", fid=BAR_ID) | {"mimeType": ""}]
    elif case == "too_many_pages":
        page2["nextPageToken"] = "ANOTHER_PAGE_P1AP"
    with pytest.raises(PrivateMetadataSnapshotBlocked):
        run(engine, fake_google(seen,pages=[page1,page2],
                                owner=case!="unowned_folder"))
    with engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM drive_inbox_items")).scalar_one() == 0


@pytest.mark.parametrize("name,value", [
    ("P1AP_OWNER_FOLDER_METADATA_REVIEW_ONLY", "0"),
    ("P1AP_G2_AUTHENTICATED_METADATA_UI_REVIEWED", "0"),
    ("P1AN_GOOGLE_METADATA_RUNTIME", "0"),
    ("P1C_GOOGLE_NETWORK_ENABLED", "0"),
    ("APP_DATA_MODE", "real"),
    ("P1W_OWNER_REF", "SYNTHETIC_ANOTHER_OWNER_P1AP_2026"),
])
def test_wrong_release_scope_never_contacts_google(env, name, value):
    engine, monkeypatch = env
    monkeypatch.setenv(name,value)
    calls = []
    with pytest.raises(PrivateMetadataSnapshotBlocked):
        run(engine, lambda *args: calls.append(args))
    assert calls == []
