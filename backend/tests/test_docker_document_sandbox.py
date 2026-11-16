"""G3 container policy tests do not execute Docker or use real documents."""
import base64
from io import BytesIO, StringIO
import json
from types import SimpleNamespace

import pytest

from app import docker_document_sandbox, document_worker_entry
from app.docker_document_sandbox import DocumentSandboxBlocked, inspect_in_docker, docker_args


IMAGE = "local/personal-cfo-document-worker@sha256:" + "a"*64
RAW = b"%PDF-" + b"synthetic-fixture-no-personal-data" * 8


def run(**kwargs):
    return inspect_in_docker(RAW, image=IMAGE, adapter_key="synthetic_bank_pdf_v1",
        kind="bank_statement", synthetic_fixture=True, **kwargs)


def fake_output():
    return {"synthetic_only": True, "adapter": "synthetic_bank_pdf_v1",
            "adapter_revision":1, "document_kind":"bank_statement",
            "format":".pdf", "import_performed":False,
            "owner_source_data_ingested":False, "real_source_certified":False,
            "fbr_ready":False, "tax_due_minor":None,
            "preview_rows": 1, "balance_validated":True,
            "needs_opening_balance":False, "source_marker_verified":True}


def test_pinned_container_has_no_network_writable_root_or_privilege(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    calls=[]
    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0,
            stdout=json.dumps(fake_output()).encode("utf-8"))
    monkeypatch.setattr(docker_document_sandbox.subprocess, "run", fake_run)
    out=run()
    assert out["container_network_disabled"] and out["real_document_acceptance"] is False
    args,kw=calls[0]
    for must in ("--network=none","--read-only","--cap-drop=ALL",
                 "--security-opt=no-new-privileges","--pids-limit=48",
                 "--pull=never","--user=65532:65532","--ipc=none"):
        assert must in args
    assert args[-1] == IMAGE
    assert "synthetic-fixture" not in str(args)
    assert kw["input"] and RAW not in args
    assert kw["stderr"] == docker_document_sandbox.subprocess.DEVNULL
    assert kw["timeout"] == 9


@pytest.mark.parametrize("image", [
    "python:latest", "local/worker@sha256:invalid",
    "local/worker@sha256:"+"a"*63, "https://example.com/a@sha256:"+"a"*64
])
def test_unpinned_or_remote_container_images_denied(image, monkeypatch):
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    with pytest.raises(DocumentSandboxBlocked):
        docker_args(image)


def test_remote_docker_host_context_denied(monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "tcp://remote.example:2375")
    with pytest.raises(DocumentSandboxBlocked):
        docker_args(IMAGE)
    monkeypatch.delenv("DOCKER_HOST")
    monkeypatch.setenv("DOCKER_CONTEXT", "other-project")
    with pytest.raises(DocumentSandboxBlocked):
        docker_args(IMAGE)


@pytest.mark.parametrize("opts", [
    {"synthetic_fixture":False}, {"adapter_key":"real_bank_pdf"},
    {"kind":"iris_income_return"}, {"tax_year":2022},
])
def test_unverified_document_refused_without_launch(monkeypatch, opts):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    kwargs={"image":IMAGE, "adapter_key":"synthetic_bank_pdf_v1",
            "kind":"bank_statement","synthetic_fixture":True}
    kwargs.update(opts)
    monkeypatch.setattr(docker_document_sandbox.subprocess, "run",
                        lambda *a,**k: (_ for _ in ()).throw(AssertionError("must not launch")))
    with pytest.raises(DocumentSandboxBlocked):
        inspect_in_docker(RAW,**kwargs)


def test_runtime_or_worker_failure_is_sanitized(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    monkeypatch.setattr(docker_document_sandbox.subprocess, "run",
        lambda *a,**k: (_ for _ in ()).throw(RuntimeError("PRIVATE-SOURCE-LEAK")))
    with pytest.raises(DocumentSandboxBlocked) as exc:
        run()
    assert "PRIVATE-SOURCE-LEAK" not in str(exc.value)
    monkeypatch.setattr(docker_document_sandbox.subprocess, "run",
        lambda *a,**k: SimpleNamespace(returncode=0,
            stdout=json.dumps({**fake_output(),"owner_tax_identifier":"NEVER"}).encode()))
    with pytest.raises(DocumentSandboxBlocked):
        run()


def test_real_mode_denied_even_with_known_image(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "real")
    with pytest.raises(DocumentSandboxBlocked):
        run()


def test_isolated_entry_read_only_synthetic_fixture_contract(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE", "synthetic")
    body={"synthetic_fixture":True,"adapter_key":"synthetic_bank_pdf_v1",
          "kind":"bank_statement","tax_year":2025,
          "raw_b64":base64.b64encode(RAW).decode("ascii")}
    monkeypatch.setattr(document_worker_entry.sys, "stdin",
                        SimpleNamespace(buffer=BytesIO(json.dumps(body).encode())))
    output=StringIO()
    monkeypatch.setattr(document_worker_entry.sys, "stdout", output)
    def fake_inspect(raw, **kwargs):
        assert raw == RAW and kwargs["synthetic_fixture"] is True
        return fake_output()
    monkeypatch.setattr(document_worker_entry, "inspect_synthetic_source", fake_inspect)
    document_worker_entry.main()
    assert json.loads(output.getvalue())["real_source_certified"] is False
