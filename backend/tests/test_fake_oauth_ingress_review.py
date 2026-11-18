"""P1L: hostile OAuth ingress path/method/authority and log minimization."""
from dataclasses import replace
from pathlib import Path
import pytest
from app.fake_oauth_ingress_review import (
    FakeIngressRequest, FakeOAuthIngressBlocked,
    plan_fake_exact_oauth_ingress, audit_current_public_nginx,
)
from app.drive_cloud_owner_gateway import HOST,ORIGIN


@pytest.fixture(autouse=True)
def flags(monkeypatch):
    monkeypatch.setenv("APP_DATA_MODE","synthetic")
    monkeypatch.setenv("P1L_FAKE_OAUTH_INGRESS_REVIEW_ONLY","1")


def req(**kwargs):
    valid=dict(method="GET",path="/api/drive/oauth/callback",
               scheme="https",host=HOST,origin=None,
               query="state="+"A"*48+"&code=SYNTHETIC_GOOGLE_CODE_"+"B"*20,
               owner_session_present=True,csrf_verified=False,
               forwarded_headers_present=False)
    valid.update(kwargs)
    return FakeIngressRequest(**valid)


def test_google_top_level_get_simulation_redacts_code_and_cookie():
    r=req()
    plan=plan_fake_exact_oauth_ingress(r)
    assert plan["candidate_private_path"]=="/internal/drive/oauth/callback"
    assert plan["candidate_public_path"]=="/api/drive/oauth/callback"
    assert plan["request_target_log_allowed"] is False
    assert plan["cookie_or_code_logged"] is False
    assert plan["real_google_redirect_routed"] is False
    assert plan["provider_code_exchanged"] is False
    assert plan["session_and_state_binding_independently_tested"] is False
    assert r.query not in str(plan) and "B"*20 not in str(plan)
    assert plan["proxy_must_strip_client_forwarded_headers"]


@pytest.mark.parametrize("change",[
    {"method":"POST"},{"path":"/api/"},{"path":"/api/drive/oauth/callback/"},
    {"path":"/api/owner/login"},{"path":"/internal/drive/oauth/callback"},
    {"scheme":"http"},{"host":"evil.example"},{"host":HOST+":443"},
    {"origin":ORIGIN},{"forwarded_headers_present":True},
    {"owner_session_present":False},
    {"query":"state="+"A"*48},
    {"query":"code=SYNTHETIC_GOOGLE_CODE_"+"B"*20},
    {"query":"state="+"A"*48+"&code=SYNTHETIC_GOOGLE_CODE_"+"B"*20+"&code=dup"},
    {"query":"state="+"A"*48+"&code=real-google-oauth-code"},
    {"query":"state=bad&code=SYNTHETIC_GOOGLE_CODE_"+"B"*20},
    {"query":"state="+"A"*48+"&code=SYNTHETIC_GOOGLE_CODE_"+"B"*20+"&secret=x"},
    {"query":"state="+"A"*48+"&code=SYNTHETIC_GOOGLE_CODE_"+"B"*20+"&"},
])
def test_bad_callback_host_origin_method_query_or_code_is_denied(change):
    with pytest.raises(FakeOAuthIngressBlocked):
        plan_fake_exact_oauth_ingress(req(**change))


@pytest.mark.parametrize("method,path",[
    ("POST","/api/drive/oauth/start"),
    ("POST","/api/drive/oauth/disconnect"),
    ("GET","/api/drive/oauth/status"),
])
def test_exact_private_mutations_and_status_only(method,path):
    request=req(method=method,path=path,query="",origin=ORIGIN,
                csrf_verified=(method=="POST"))
    result=plan_fake_exact_oauth_ingress(request)
    assert result["candidate_private_path"].startswith("/internal/drive/oauth/")
    assert result["real_google_redirect_routed"] is False
    if method=="POST":
        with pytest.raises(FakeOAuthIngressBlocked):
            plan_fake_exact_oauth_ingress(replace(request,csrf_verified=False))
        with pytest.raises(FakeOAuthIngressBlocked):
            plan_fake_exact_oauth_ingress(replace(request,origin="https://attacker.invalid"))
    with pytest.raises(FakeOAuthIngressBlocked):
        plan_fake_exact_oauth_ingress(replace(request,query="state=bad"))


def test_exact_deployed_nginx_still_has_no_google_callback():
    nginx=(Path(__file__).parents[2]/"frontend/nginx.railway.conf").read_text()
    result=audit_current_public_nginx(nginx_source=nginx)
    assert result["current_preview_route_only"] is False
    assert result["owner_login_routes_default_off_in_source"] is True
    assert result["actual_owner_login_activation_independently_verified"] is False
    assert result["public_google_oauth_route_active"] is False
    assert result["g2_exact_proxy_release_accepted"] is False
    for variant in ("location /api/ {","location = /api/drive/oauth/callback {",
                    "location = /api/owner/login {"):
        with pytest.raises(FakeOAuthIngressBlocked):
            audit_current_public_nginx(nginx_source=nginx+"\n"+variant)


@pytest.mark.parametrize("variable,value",[
    ("APP_DATA_MODE","real"),
    ("P1L_FAKE_OAUTH_INGRESS_REVIEW_ONLY","0"),
])
def test_fake_rehearsal_cannot_authorize_real_google(monkeypatch,variable,value):
    monkeypatch.setenv(variable,value)
    with pytest.raises(FakeOAuthIngressBlocked):
        plan_fake_exact_oauth_ingress(req())


def test_no_real_proxy_mounted_by_fake_ingress_review():
    from app.preview_api import create_preview_app
    paths={r.path for r in create_preview_app().routes}
    assert "/api/drive/oauth/start" not in paths
    assert "/api/drive/oauth/callback" not in paths
    assert "/api/owner/login" not in paths
