"""Synthetic owner frontend: static assets share the existing backend auth gate.

This does not certify production host/TLS/MFA or permit real financial records.
"""


def test_owner_dashboard_and_scripts_are_local_authenticated_demo_assets(client):
    page=client.get("/")
    assert page.status_code==200
    assert "Personal CFO | Financial workspace preview" in page.text
    assert "Do not enter personal financial information" in page.text
    assert 'type="file"' not in page.text
    assert page.headers["cache-control"]=="no-store"
    assert page.headers["x-content-type-options"]=="nosniff"
    for path, content in (
        ("/ui.css", "text/css"),
        ("/ui.mjs", "text/javascript"),
        ("/demo-data.mjs", "text/javascript"),
    ):
        response=client.get(path)
        assert response.status_code==200
        assert content in response.headers["content-type"]
        assert response.headers["cache-control"]=="no-store"
        assert response.headers["x-content-type-options"]=="nosniff"
    assert "hypotheticalBuffer" in client.get("/demo-data.mjs").text
    assert "No genuine" not in client.get("/ui.css").text


def test_dashboard_asset_requests_cannot_skip_basic_owner_authentication(client):
    authorized=client.auth
    client.auth=None
    try:
        for path in ("/","/ui.css","/ui.mjs","/demo-data.mjs"):
            response=client.get(path)
            assert response.status_code==401
    finally:
        client.auth=authorized
