"""HTTP-level tests for the Supabase transport.

A minimal PostgREST stand-in runs on localhost so the request shape (headers,
filters, ordering, paging) is verified without needing a real account.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from app.sync.transports.base import Change, TransportError
from app.sync.transports.supabase import SupabaseTransport

API_KEY = "test-anon-key"


class _FakePostgrest(BaseHTTPRequestHandler):
    """Implements just enough of PostgREST for the transport."""

    rows: list[dict] = []
    seen_headers: dict[str, str] = {}

    def log_message(self, *_args) -> None:  # silence the test output
        pass

    def _authorised(self) -> bool:
        type(self).seen_headers = dict(self.headers)
        return self.headers.get("apikey") == API_KEY

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self._authorised():
            self._send(401, {"message": "invalid key"})
            return
        parsed = urlparse(self.path)
        if not parsed.path.endswith("/bc_changes"):
            self._send(404, {"message": "no table"})
            return
        query = parse_qs(parsed.query)
        tenant = query.get("tenant", ["eq.default"])[0].removeprefix("eq.")
        after = int(query.get("seq", ["gt.0"])[0].removeprefix("gt."))
        limit = int(query.get("limit", ["500"])[0])
        rows = [r for r in type(self).rows if r["tenant"] == tenant and r["seq"] > after]
        rows.sort(key=lambda r: r["seq"])
        if query.get("order", [""])[0].endswith("desc"):
            rows.reverse()
        self._send(200, rows[:limit], extra={"content-range": f"0-{len(rows)}/{len(rows)}"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self._authorised():
            self._send(401, {"message": "invalid key"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        for row in body:
            row["seq"] = len(type(self).rows) + 1
            type(self).rows.append(row)
        self._send(201, [])

    def _send(self, code: int, payload, extra: dict | None = None) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def server():
    """Run the PostgREST stand-in on an ephemeral port."""
    _FakePostgrest.rows = []
    httpd = HTTPServer(("127.0.0.1", 0), _FakePostgrest)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()


def _change(uid: str, name: str) -> Change:
    return Change(entity="Project", uid=uid, op="upsert", payload={"name": name}, device="dev-1")


def test_check_push_and_pull_roundtrip(server) -> None:
    transport = SupabaseTransport(server, API_KEY, tenant="firma")
    assert "OK" in transport.check()

    assert transport.push([_change("u1", "Birinchi"), _change("u2", "Ikkinchi")]) == 2

    changes = transport.pull("", limit=100)
    assert [c.uid for c in changes] == ["u1", "u2"]
    assert [c.cursor for c in changes] == ["1", "2"]
    assert changes[0].payload == {"name": "Birinchi"}
    assert changes[0].device == "dev-1"

    # The cursor only returns newer rows.
    assert [c.uid for c in transport.pull("1")] == ["u2"]
    assert transport.pull("2") == []


def test_tenant_isolation(server) -> None:
    SupabaseTransport(server, API_KEY, tenant="firma-a").push([_change("a", "A")])
    SupabaseTransport(server, API_KEY, tenant="firma-b").push([_change("b", "B")])
    assert [c.uid for c in SupabaseTransport(server, API_KEY, "firma-a").pull("")] == ["a"]
    assert [c.uid for c in SupabaseTransport(server, API_KEY, "firma-b").pull("")] == ["b"]


def test_paging_respects_limit(server) -> None:
    transport = SupabaseTransport(server, API_KEY, tenant="firma")
    transport.push([_change(f"u{i}", f"N{i}") for i in range(10)])
    first = transport.pull("", limit=4)
    assert len(first) == 4
    second = transport.pull(first[-1].cursor, limit=4)
    assert [c.uid for c in second] == ["u4", "u5", "u6", "u7"]


def test_bad_key_is_reported_clearly(server) -> None:
    transport = SupabaseTransport(server, "wrong-key", tenant="firma")
    with pytest.raises(TransportError) as excinfo:
        transport.check()
    assert "401" in str(excinfo.value)


def test_unreachable_server_is_reported() -> None:
    transport = SupabaseTransport("http://127.0.0.1:9", API_KEY)
    with pytest.raises(TransportError) as excinfo:
        transport.check()
    assert "ulanib bo'lmadi" in str(excinfo.value)


def test_missing_configuration_rejected() -> None:
    with pytest.raises(TransportError):
        SupabaseTransport("", "")


def test_auth_headers_are_sent(server) -> None:
    SupabaseTransport(server, API_KEY, tenant="firma").check()
    headers = _FakePostgrest.seen_headers
    assert headers.get("apikey") == API_KEY
    assert headers.get("Authorization") == f"Bearer {API_KEY}"


def test_two_devices_replicate_over_http(server, tmp_path) -> None:
    """The full engine round-trip against the HTTP backend, not just the wire."""
    from app.database import session as db_session
    from app.models.enums import RoleCode
    from app.services import auth_service, project_service
    from app.sync.tracker import install as install_tracker
    from tests.test_sync import Device

    install_tracker()

    def factory():
        return SupabaseTransport(server, API_KEY, tenant="firma")

    a = Device("A", tmp_path / "http_a.db", transport_factory=factory)
    b = Device("B", tmp_path / "http_b.db", transport_factory=factory)
    try:
        with a.active():
            actor = auth_service.create_user(
                username="admin",
                password="secret123",
                full_name="Admin",
                role_code=RoleCode.ADMIN.value,
            )
            project_service.save_project(
                {"name": "HTTP orqali", "planned_budget": 7_000_000}, actor
            )
        assert a.sync().ok

        report = b.sync()
        assert report.ok, report.errors
        with b.active():
            projects = project_service.list_projects()
            assert [p.name for p in projects] == ["HTTP orqali"]
            assert projects[0].planned_budget == 7_000_000
    finally:
        db_session.reset_engine()
