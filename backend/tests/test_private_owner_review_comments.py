"""P5B encrypted owner review notes: fake owner and source IDs only."""
import base64
from uuid import UUID
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa: F401
from app.private_owner_review_comments import (
    append_owner_review_comment as add,
    list_owner_review_comments as listing,
    PrivateOwnerReviewBlocked,
)

OWNER="SYNTHETIC_OWNER_REVIEW_2026"
SOURCE="a"*64
OTHER="b"*64
T=1_800_140_001


def b64(x):
    return base64.urlsafe_b64encode(x*32).decode("ascii")


@pytest.fixture
def fake(tmp_path,monkeypatch):
    for name,value in {
      "APP_DATA_MODE":"synthetic",
      "P1N_PRIVATE_OWNER_AUTH_ONLY":"1",
      "P1N_G2_OWNER_IDENTITY_REVIEWED":"1",
      "P1N_SQLITE_FAKE_TEST_ONLY":"1",
      "P1N_OWNER_ENCRYPTION_KEY":b64(b"E"),
      "P1N_OWNER_IDENTITY_HMAC_KEY":b64(b"H"),
      "P1N_OWNER_SESSION_HMAC_KEY":b64(b"S"),
      "P5B_OWNER_REVIEW_COMMENTS_ENABLED":"1",
      "P5B_G2_PRIVATE_REVIEW_ENCRYPTION_ACCEPTED":"1",
      "P5B_G3_FINANCIAL_REVIEW_SCHEMA_ACCEPTED":"1",
    }.items():monkeypatch.setenv(name,value)
    engine=create_engine("sqlite:///"+str(tmp_path/"fake-owner-notes.db"))
    Base.metadata.create_all(engine)
    yield engine,monkeypatch
    engine.dispose()


def submit(engine, comment="This might be a transfer to another account I own.",
           owner=OWNER,subject=SOURCE,kind="document",when=T):
    with Session(engine) as db:
        return add(db,owner_ref=owner,subject_hmac=subject,
                   subject_kind=kind,comment=comment,now_epoch=when)


def read(engine,subject=SOURCE,kind="document",owner=OWNER):
    with Session(engine) as db:
        return listing(db,owner_ref=owner,subject_hmac=subject,
                       subject_kind=kind)


def test_append_not_resolve_and_authenticated_plaintext_only(fake):
    db,_=fake
    comment="This transfer is between my own accounts; please verify counterpart."
    result=submit(db,comment)
    assert UUID(result["id"])
    assert result["saved_encrypted"] is True
    assert result["review_state"]=="PENDING_EVIDENCE_RECONCILIATION"
    assert result["original_transaction_changed"] is False
    assert result["automatically_resolved"] is False
    assert result["analysis_pending"] is True
    all_notes=read(db)
    assert all_notes["comment_count"]==1
    assert all_notes["comments"][0]["comment"]==comment
    assert all_notes["financial_values_changed"] is False
    assert all_notes["automatic_resolution_performed"] is False
    with db.connect() as c:
        raw=str(c.execute(text("SELECT * FROM owner_financial_review_comments")).all())
    for secret in (comment,OWNER,"transfer is between",SOURCE[:20]):
        assert secret not in raw
    assert "P5B1:" in raw


def test_appended_history_not_overwritten_with_new_comment(fake):
    db,_=fake
    first=submit(db,"Please check this source.")
    second=submit(db,"Maybe it is a refund",when=T+1)
    assert second["revision"]==2
    assert first["id"]!=second["id"]
    payload=read(db)
    assert [x["revision"] for x in payload["comments"]]==[1,2]
    assert payload["comments"][0]["comment"]=="Please check this source."
    assert payload["comments"][1]["comment"]=="Maybe it is a refund"


def test_document_and_transaction_references_never_cross(fake):
    db,_=fake
    submit(db,"Owner said document category ambiguous.")
    submit(db,"Owner said transaction may be an own transfer.",kind="transaction")
    submit(db,"Unrelated source.",subject=OTHER)
    assert read(db)["comment_count"]==1
    assert read(db,kind="transaction")["comment_count"]==1
    assert read(db,subject=OTHER)["comments"][0]["comment"]=="Unrelated source."
    assert read(db,owner="SYNTHETIC_OTHER_OWNER_2026")["comment_count"]==0


@pytest.mark.parametrize("value",[
  "", " "*5,"\x00","x"*2001,"\x01bad","a\n"*1300,123,None,
])
def test_bad_comments_rejected(fake,value):
    db,_=fake
    with pytest.raises(PrivateOwnerReviewBlocked):
        submit(db,value)


@pytest.mark.parametrize("kind,subject",[
 ("invalid","a"*64),("document","a"*63),("transaction","not hmac"),
 ("document","A"*64),(None,"a"*64),
])
def test_bad_targets_rejected(fake,kind,subject):
    db,_=fake
    with pytest.raises(PrivateOwnerReviewBlocked):
        submit(db,kind=kind,subject=subject)


def test_key_rotation_without_version_rejected_instead_of_plaintext(fake):
    db,monkeypatch=fake
    submit(db)
    monkeypatch.setenv("P1N_OWNER_ENCRYPTION_KEY",b64(b"R"))
    with pytest.raises(PrivateOwnerReviewBlocked):
        read(db)


def test_ciphertext_and_row_mac_tamper_fail_closed(fake):
    db,_=fake
    submit(db)
    with db.begin() as c:
        c.execute(text("UPDATE owner_financial_review_comments "
                       "SET ciphertext='P5B1:invalid'"))
    with pytest.raises(PrivateOwnerReviewBlocked):
        read(db)


@pytest.mark.parametrize("flag",[
 "P1N_PRIVATE_OWNER_AUTH_ONLY",
 "P5B_OWNER_REVIEW_COMMENTS_ENABLED",
 "P5B_G2_PRIVATE_REVIEW_ENCRYPTION_ACCEPTED",
 "P5B_G3_FINANCIAL_REVIEW_SCHEMA_ACCEPTED",
])
def test_all_release_gates_default_off(fake,flag):
    db,monkeypatch=fake
    monkeypatch.setenv(flag,"0")
    with pytest.raises(PrivateOwnerReviewBlocked):
        submit(db)


def test_no_finance_graph_mutation(fake):
    db,_=fake
    submit(db)
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM transactions")).scalar_one()==0
        assert c.execute(text("SELECT COUNT(*) FROM private_financial_events")).scalar_one()==0
        assert c.execute(text("SELECT COUNT(*) FROM canonical_journal_entries")).scalar_one()==0
