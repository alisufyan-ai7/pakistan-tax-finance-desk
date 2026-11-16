"""Pure fictional archive metadata adversarial tests; no actual bank files."""
import io
import stat
import zipfile

import pytest
from app.synthetic_archive_gate import inspect_synthetic_zip, SyntheticArchiveBlocked


def archive(items):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,mode="w",compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in items:
            z.writestr(name,data)
    return buf.getvalue()


def test_small_synthetic_zip_preflight_reports_counts_only():
    data=archive([("fictional/statement.csv",b"day,amount\n01,2\n"),
                  ("fictional/sample.pdf",b"%PDF-fake")])
    result=inspect_synthetic_zip(data,fabricated_fixture=True)
    assert result["source_count"]==2
    assert result["extension_counts"]=={".csv":1,".pdf":1}
    assert result["extraction_performed"] is False
    assert result["import_performed"] is False
    assert result["real_data_authorized"] is False
    assert "statement.csv" not in str(result)
    assert "amount" not in str(result)


@pytest.mark.parametrize("filename",[
    "../secret.csv","safe/../../other.pdf","/absolute.csv","bad\\windows.pdf",
    "nested/a/b/c/too.deep.csv","unsupported.sh","nested/archive.zip",
    "x\x0aanother.pdf"," source.csv", "foo/.."
])
def test_dangerous_or_unsupported_paths_fail(filename):
    with pytest.raises(SyntheticArchiveBlocked):
        inspect_synthetic_zip(archive([(filename,b"fiction")]),fabricated_fixture=True)


def test_duplicate_member_case_fails_closed():
    value=archive([("FILE.csv",b"one"),("file.CSV",b"two")])
    with pytest.raises(SyntheticArchiveBlocked,match="duplicate"):
        inspect_synthetic_zip(value,fabricated_fixture=True)


def test_compressed_bomb_ratio_rejected_without_decompression():
    payload=b"z"*(1024*1024)
    with pytest.raises(SyntheticArchiveBlocked,match="ratio"):
        inspect_synthetic_zip(archive([("fictional.csv",payload)]),fabricated_fixture=True)


def test_zip_symlink_rejected():
    buf=io.BytesIO()
    member=zipfile.ZipInfo("shortcut.csv")
    member.create_system=3
    member.external_attr=(stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(buf,"w") as z:
        z.writestr(member,b"fiction")
    with pytest.raises(SyntheticArchiveBlocked,match="symlink"):
        inspect_synthetic_zip(buf.getvalue(),fabricated_fixture=True)


def test_real_mode_and_unmarked_source_refused(monkeypatch):
    value=archive([("fictional.csv",b"fake")])
    with pytest.raises(SyntheticArchiveBlocked):
        inspect_synthetic_zip(value,fabricated_fixture=False)
    monkeypatch.setenv("APP_DATA_MODE","real")
    with pytest.raises(SyntheticArchiveBlocked,match="Genuine"):
        inspect_synthetic_zip(value,fabricated_fixture=True)


def test_invalid_or_empty_container_fails_closed():
    with pytest.raises(SyntheticArchiveBlocked):
        inspect_synthetic_zip(b"not a ZIP",fabricated_fixture=True)
    with pytest.raises(SyntheticArchiveBlocked):
        inspect_synthetic_zip(archive([]),fabricated_fixture=True)
