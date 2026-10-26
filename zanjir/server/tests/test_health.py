from fastapi.testclient import TestClient

from zanjir_server.main import create_app


def test_healthz() -> None:
    client = TestClient(create_app())
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_docs_disabled() -> None:
    client = TestClient(create_app())
    assert client.get("/docs").status_code == 404
