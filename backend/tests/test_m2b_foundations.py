"""Regression/security tests; fake/synthetic records only."""
from __future__ import annotations
import base64
import csv
from io import StringIO
from pathlib import Path
import sqlite3
import subprocess
import sys
import os
import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import inspect, create_engine, text
from app.db import Base
from app import models  # noqa
from app.bank_profiles import PROFILES
from app.synthetic_backup import create_backup, restore_backup, BackupError

@pytest.fixture
def backup_key(monkeypatch):
    key = base64.urlsafe_b64encode(bytes(range(32))).decode()
    monkeypatch.setenv('BACKUP_KEY',key)
    monkeypatch.setenv('APP_DATA_MODE','synthetic')
    return key

def test_alembic_baseline_fresh_sqlite(tmp_path):
    db=tmp_path/'migrated.db'
    env={**os.environ}
    env.pop('DATABASE_URL',None)
    result=subprocess.run([sys.executable,'-m','alembic','-x',f'db_url=sqlite:///{db}','upgrade','head'],cwd=Path(__file__).parents[1],env=env,capture_output=True,text=True,check=True)
    engine=create_engine(f'sqlite:///{db}')
    found=set(inspect(engine).get_table_names())
    expected=set(Base.metadata.tables)|{'alembic_version'}
    assert expected == found
    with engine.connect() as session:
        assert session.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0024_review_comments'
    second=subprocess.run([sys.executable,'-m','alembic','-x',f'db_url=sqlite:///{db}','upgrade','head'],cwd=Path(__file__).parents[1],env=env,capture_output=True,text=True,check=True)
    assert second.returncode == 0

def test_production_mode_refuses_to_start(tmp_path,monkeypatch):
    from app.main import create_app
    monkeypatch.setenv('APP_DATA_MODE','real')
    with pytest.raises(RuntimeError,match='Real-data mode'):
        create_app(f'sqlite:///{tmp_path / "no-real.db"}')

def test_synthetic_bank_split_and_direction_import(client, account):
    split=('Post Date,Narration,Withdrawals,Deposits,Running Balance,Transaction Ref\n'
           '01/02/2024,Salary (synthetic),,5000.00,5000.00,SAL-A\n'
           '02/02/2024,Donation (synthetic),100.00,,4900.00,DON-A\n')
    result=client.post('/api/statements',data={'account_id':account,'profile':'synthetic_split','opening_balance':'0.00'}, files={'file':('test.csv',split.encode('utf-8'),'text/csv')})
    assert result.status_code == 201,result.text
    assert result.json()['accepted']==2 and result.json()['reconciliation']=='opening_and_running_verified'
    dup=client.post('/api/statements',data={'account_id':account,'profile':'synthetic_split','opening_balance':'0.00'},files={'file':('test.csv',split.encode('utf-8'),'text/csv')})
    assert dup.json()['accepted']==0
    direction=('Transaction Date,Details,Amount,Type,Closing Balance,Trace\n'
               '05/03/2024,Investment payout (synthetic),300.00,CR,5200.00,INV-B\n'
               '06/03/2024,Loan given (synthetic),100.00,DR,5100.00,LOAN-B\n')
    res=client.post('/api/statements',data={'account_id':account,'profile':'synthetic_direction','opening_balance':'4900.00'},files={'file':('sample2.csv',direction.encode(),'text/csv')})
    assert res.status_code == 201, res.text

def test_synthetic_bank_direction_balances(client, account):
    direction=('Transaction Date,Details,Amount,Type,Closing Balance,Trace\n'
               '05/03/2024,Investment payout (synthetic),300.00,CR,5200.00,INV-B\n'
               '06/03/2024,Loan given (synthetic),100.00,DR,5100.00,LOAN-B\n')
    res=client.post('/api/statements',data={'account_id':account,'profile':'synthetic_direction','opening_balance':'4900.00'}, files={'file':('test.csv',direction.encode(),'text/csv')})
    assert res.status_code==201,res.text
    assert res.json()['reconciliation']=='opening_and_running_verified'
    assert res.json()['accepted']==2

def test_synthetic_bank_rejects_uncertified_and_invalid(client, account):
    bad=('Transaction Date,Details,Amount,Type,Closing Balance,Trace\n'
         '05/03/2024,Bad row,300.00,DEBIT,300.00,BAD\n')
    for profile, data in [('actual_hbl',bad),('synthetic_direction',bad),('synthetic_split',bad)]:
        res=client.post('/api/statements',data={'account_id':account,'profile':profile},files={'file':('bad.csv',data.encode(),'text/csv')})
        assert res.status_code==422, res.text
    assert client.get('/api/transactions?tax_year=2024').json()['rows']==[]

def test_encrypted_structured_fields_never_plaintext(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DOCUMENT_VAULT_KEY", base64.urlsafe_b64encode(bytes(range(32))).decode())
    monkeypatch.setenv("DOCUMENT_VAULT_DIR", str(tmp_path / "evidence"))
    from app.field_crypto import protect_fields,reveal_fields
    from app.evidence_vault import EncryptedEvidenceVault
    vault=EncryptedEvidenceVault.from_environment()
    fid='a5e7c8d2-793a-40df-a341-d14168711999'
    obj={'opening_wealth_minor':1234567,'closing_wealth_minor':4321987}
    sealed=protect_fields(vault,fid,2024,'wealth_statement',obj)
    assert sealed.startswith('TFJF1:') and '4321987' not in sealed
    assert reveal_fields(vault,fid,2024,'wealth_statement',sealed)==obj
    with pytest.raises(InvalidTag):
        reveal_fields(vault,fid,2025,'wealth_statement',sealed)
    with pytest.raises(ValueError,match='Legacy plaintext'):
        reveal_fields(vault,fid,2024,'wealth_statement','{"opening_wealth_minor": 20}')
    pay={'synthetic_fixture':True,'tax_year':2024,'kind':'wealth_statement','filing_status':'filed_original','fields':obj}
    post=client.post('/api/historical/synthetic-filings',json=pay)
    assert post.status_code==201,post.text
    # Database has an encrypted envelope, not readable filing amounts.
    with sqlite3.connect(tmp_path / "test.db") as c:
        stored=c.execute("SELECT fields_json FROM historical_filings").fetchone()[0]
    assert stored.startswith("TFJF1:") and "4321987" not in stored
    # Verify HTTP results decrypt only with protected application key.
    assert client.get('/api/historical/filings?tax_year=2024').json()['filings'][0]['fields']==obj

def _seed_db(path:Path):
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE synthetic_only (amount INTEGER NOT NULL)')
        c.execute('INSERT INTO synthetic_only(amount) VALUES (123456)')
        c.commit()

def test_synthetic_encrypted_backup_roundtrip_with_evidence(tmp_path,backup_key):
    db=tmp_path/'finance.db'
    _seed_db(db)
    evidence=tmp_path/'evidence'
    evidence.mkdir()
    identifier='a5e7c8d2-793a-40df-a341-d14168711111'
    (evidence/f'{identifier}.evd').write_bytes(b'ciphertext-synthetic-only')
    output=tmp_path/'backup.tfbk'
    result=create_backup(db,evidence,output)
    assert result['file_count']==2 and output.stat().st_mode & 0o777 == 0o600
    assert b'123456' not in output.read_bytes()
    restore=restore_backup(output,tmp_path/'restored')
    assert restore['restored_files']==2 and restore['sqlite_integrity_check']=='ok'
    with sqlite3.connect(tmp_path/'restored'/'finance.db') as c:
        assert c.execute('SELECT amount FROM synthetic_only').fetchone()[0]==123456
    assert (tmp_path/'restored'/'evidence'/f'{identifier}.evd').read_bytes()==b'ciphertext-synthetic-only'
    with pytest.raises(FileExistsError):
        restore_backup(output,tmp_path/'restored')
    with pytest.raises(FileExistsError):
        create_backup(db,evidence,output)

def test_backup_rejects_wrong_key_and_tampering(tmp_path,backup_key,monkeypatch):
    db=tmp_path/'finance.db';_seed_db(db)
    backup=tmp_path/'backup.tfbk'
    create_backup(db,tmp_path/'none',backup)
    monkeypatch.setenv('BACKUP_KEY',base64.urlsafe_b64encode(bytes(range(32,64))).decode())
    with pytest.raises(InvalidTag):
        restore_backup(backup,tmp_path/'wrong-key-restore')
    monkeypatch.setenv('BACKUP_KEY',backup_key)
    tampered=tmp_path/'tampered.tfbk'
    b=bytearray(backup.read_bytes());b[-1]^=1;tampered.write_bytes(b)
    with pytest.raises(InvalidTag):
        restore_backup(tampered,tmp_path/'tampered-restore')
    assert not (tmp_path/'wrong-key-restore').exists()
    assert not (tmp_path/'tampered-restore').exists()

def test_backup_fails_closed_invalid_evidence_and_non_synthetic(tmp_path,backup_key,monkeypatch):
    db=tmp_path/'finance.db';_seed_db(db)
    evidence=tmp_path/'evidence';evidence.mkdir(); (evidence/'unknown.txt').write_text('not allowed')
    with pytest.raises(BackupError,match='unexpected entry'):
        create_backup(db,evidence,tmp_path/'fail.tfbk')
    monkeypatch.setenv('APP_DATA_MODE','real')
    with pytest.raises(BackupError,match='synthetic'):
        create_backup(db,evidence,tmp_path/'fail.tfbk')
