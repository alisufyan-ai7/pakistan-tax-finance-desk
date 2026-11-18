"""P1AF synthetic-only encrypted owner credential snapshot tests."""
import json
import os
import stat
from types import SimpleNamespace

import pytest

from app import private_owner_credential_snapshot as b


def sample():
    owner="a"*64
    return {
        "contract":b._FMT,
        "schema_revision":"p1y_owner_auth_v1",
        "created_epoch":1_800_000_000,
        "tables":{
            "owner_private_identities":[{
                "singleton_id":1,"revision":1,"owner_hmac":owner,
                "password_scrypt":"SYNTHETIC_HASH_PRIVATE",
                "totp_cipher":"SYNTHETIC_CIPHERTEXT_PRIVATE",
            }],
            "owner_private_recovery_states":[{
                "owner_hmac":owner,"revision":1,"ciphertext":"SYNTHETIC_RECOVERY_PRIVATE",
            }],
            "owner_private_recovery_audit":[{
                "owner_hmac":owner,"revision":1,"action":"ISSUED",
                "row_hmac":"b"*64,
            }],
            "owner_private_sessions":[],
            "owner_google_metadata_grants":[],
            "owner_private_oauth_attempts":[],
        },
    }


@pytest.fixture(autouse=True)
def attended(monkeypatch):
    monkeypatch.setattr(b,"_tty",lambda:None)
    monkeypatch.setattr(b.getpass,"getpass",
                        lambda prompt="":"SYNTHETIC snapshot separate long passphrase 2026")


def test_wire_encryption_decryption_and_integrity_no_plaintext():
    private=b.X25519PrivateKey.generate()
    public=b._b64(private.public_key().public_bytes(b.Encoding.Raw,b.PublicFormat.Raw))
    envelope=b._seal_wire(sample(),public)
    content=json.dumps(envelope)
    assert "SYNTHETIC_HASH_PRIVATE" not in content
    assert "SYNTHETIC_RECOVERY_PRIVATE" not in content
    assert b._open_wire(envelope,private)==sample()
    envelope["ciphertext"]=envelope["ciphertext"][:-6]+"AAAAAA"
    with pytest.raises(b.PrivateCredentialSnapshotBlocked):
        b._open_wire(envelope,private)


def test_local_encrypted_snapshot_is_mode_0600_and_decrypts(tmp_path):
    p=tmp_path/"owner-credential.enc"
    status=b._write_local(sample(),str(p))
    assert status["encrypted_snapshot_created"]
    assert not status["restore_to_disposable_database_tested"]
    assert not status["independent_off_device_copy_verified"]
    assert stat.S_IMODE(p.stat().st_mode)==0o600
    assert "SYNTHETIC_HASH_PRIVATE" not in p.read_text()
    report=b.verify(str(p))
    assert report["authenticated_decryption"]
    assert report["single_owner_recovery_state_present"]
    with pytest.raises(b.PrivateCredentialSnapshotBlocked):
        b._write_local(sample(),str(p))


def test_wrong_snapshot_passphrase_and_tampering_fail_closed(tmp_path,monkeypatch):
    p=tmp_path/"encrypted.enc"
    b._write_local(sample(),str(p))
    monkeypatch.setattr(b.getpass,"getpass",lambda prompt="":"WRONG private long passphrase 2026")
    with pytest.raises(b.PrivateCredentialSnapshotBlocked):
        b.verify(str(p))
    monkeypatch.setattr(b.getpass,"getpass",
                        lambda prompt="":"SYNTHETIC snapshot separate long passphrase 2026")
    obj=json.loads(p.read_text())
    obj["ciphertext"]=obj["ciphertext"][:-8]+"AAAAAAAA"
    p.write_text(json.dumps(obj))
    with pytest.raises(b.PrivateCredentialSnapshotBlocked):
        b.verify(str(p))


def test_capture_ssh_uses_ephemeral_public_key_and_never_exposes_raw_rows(
    tmp_path,monkeypatch
):
    p=tmp_path/"credential-recovery.enc"
    seen=[]
    monkeypatch.setattr(b.shutil,"which",lambda cmd:"/usr/local/bin/railway")
    def fake_run(command,**kwargs):
        seen.append((command,kwargs))
        public=command[command.index("--recipient")+1]
        envelope=b._seal_wire(sample(),public)
        output=("Using SSH key: synthetic-public\n"
                +b._TAG+json.dumps(envelope,sort_keys=True)+"\n"
                +"Connection to Railway closed.\n")
        assert "SYNTHETIC_HASH_PRIVATE" not in output
        return SimpleNamespace(returncode=0,stdout=output,stderr="")
    monkeypatch.setattr(b.subprocess,"run",fake_run)
    result=b.capture(str(p))
    assert result["encrypted_snapshot_created"]
    assert not result["plaintext_database_rows_saved"]
    assert len(seen)==1
    args,kwargs=seen[0]
    assert args[0:2]==["railway","ssh"]
    assert args[args.index("--service")+1]=="personal-cfo-api-preview"
    assert "P1S_PRIVATE_CREDENTIAL_ROLE_AUDIT=1" in args
    assert "P1W_PRIVATE_CREDENTIAL_SNAPSHOT_EXPORT=1" in args
    assert "export" in args
    assert "--recipient" in args
    assert "SYNTHETIC_HASH_PRIVATE" not in str(args)
    assert kwargs["capture_output"] is True
    assert b.verify(str(p))["authenticated_decryption"]


def test_missing_or_duplicate_ciphertext_marker_refused_without_writing(
    tmp_path,monkeypatch
):
    monkeypatch.setattr(b.shutil,"which",lambda cmd:"/usr/bin/railway")
    monkeypatch.setattr(b.subprocess,"run",lambda *a,**k:
                        SimpleNamespace(returncode=0,stdout="untrusted data",stderr=""))
    path=tmp_path/"never.enc"
    with pytest.raises(b.PrivateCredentialSnapshotBlocked):
        b.capture(str(path))
    assert not path.exists()


def test_snapshot_rejects_noninitial_or_other_owner_rows():
    p=sample()
    p["tables"]["owner_google_metadata_grants"].append({"ciphertext":"token"})
    with pytest.raises(b.PrivateCredentialSnapshotBlocked):
        b._validate_snapshot(p)
    p=sample()
    p["tables"]["owner_private_recovery_states"][0]["owner_hmac"]="b"*64
    with pytest.raises(b.PrivateCredentialSnapshotBlocked):
        b._validate_snapshot(p)
    p=sample()
    p["tables"]["owner_private_identities"].append(p["tables"]["owner_private_identities"][0])
    with pytest.raises(b.PrivateCredentialSnapshotBlocked):
        b._validate_snapshot(p)


class Result:
    def __init__(self,rows):self.rows=rows
    def one(self):return self.rows
    def mappings(self):return self
    def all(self):return self.rows


class Conn:
    def __init__(self,payload):
        self.payload=payload
        self.sql=[]
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def execute(self,sql):
        query=str(sql)
        self.sql.append(query)
        if query=="SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY":
            return Result(None)
        if "current_database(), current_user" in query:
            return Result(("personal_cfo_owner_auth",
                           "personal_cfo_owner_credentials",True,"on"))
        for name in b._FIELDS:
            if query==f"SELECT * FROM public.{name} LIMIT 101":
                return Result(self.payload["tables"][name])
        pytest.fail("Unsafe SQL:"+query)


class Engine:
    def __init__(self,conn):self.conn=conn;self.disposed=False
    def connect(self):return self.conn
    def dispose(self):self.disposed=True


def test_remote_export_read_only_six_tables_and_least_privilege(monkeypatch):
    payload=sample()
    conn=Conn(payload)
    engine=Engine(conn)
    audits=[]
    monkeypatch.setenv("P1W_PRIVATE_CREDENTIAL_SNAPSHOT_EXPORT","1")
    monkeypatch.setattr(b,"_inventory",lambda:None)
    monkeypatch.setattr(b,"_operator_database_url",lambda:"fake-runtime-secret")
    monkeypatch.setattr(b,"create_engine",lambda *a,**k:engine)
    monkeypatch.setattr(b,"attest_private_credential_role",lambda c:audits.append(c))
    recipient=b.X25519PrivateKey.generate()
    public=b._b64(recipient.public_key().public_bytes(b.Encoding.Raw,b.PublicFormat.Raw))
    envelope=b._private_export(public)
    opened=b._open_wire(envelope,recipient)
    assert opened["tables"]==payload["tables"]
    assert audits==[conn]
    assert engine.disposed
    assert conn.sql[0]=="SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    assert sum(q.startswith("SELECT * FROM public.") for q in conn.sql)==6
    assert len(conn.sql)==8
    assert all(
        not any(word in query.upper() for word in
                ("INSERT INTO","DELETE FROM","DROP TABLE","CREATE TABLE",
                 "ALTER ROLE","UPDATE PUBLIC"))
        for query in conn.sql
    )


def test_export_requires_separate_one_shot_operator_authority(monkeypatch):
    monkeypatch.delenv("P1W_PRIVATE_CREDENTIAL_SNAPSHOT_EXPORT",raising=False)
    recipient=b.X25519PrivateKey.generate()
    public=b._b64(recipient.public_key().public_bytes(b.Encoding.Raw,b.PublicFormat.Raw))
    with pytest.raises(b.PrivateCredentialSnapshotBlocked):
        b._private_export(public)


def test_main_omits_any_raw_exception_details(monkeypatch,capsys):
    def fail(*args):
        raise RuntimeError("SYNTHETIC_SECRET_DSN hidden password")
    monkeypatch.setattr(b,"capture",fail)
    assert b.main(["capture","/tmp/not-a-real-file.enc"])==1
    output=capsys.readouterr()
    assert "SYNTHETIC_SECRET_DSN" not in output.out+output.err


def test_snapshot_export_uses_exact_reviewed_table_inventory():
    assert set(b._FIELDS)==b.PRIVATE_TABLES
