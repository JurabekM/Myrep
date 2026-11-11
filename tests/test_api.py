"""API va WebSocket testlari: haqiqiy uvicorn, test bilan bitta event loop'da."""

import json
import os
import sqlite3
from contextlib import closing

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from conftest import Served
from conftest import until as _until
from srv1_core import __version__
from srv1_core.api.ws import DROPPED_TOPIC, parse_topics
from srv1_core.app import create_app
from srv1_core.paths import DataPaths
from srv1_core.system import take_snapshot


async def test_health_needs_no_token(served: Served) -> None:
    async with served.client(authorized=False) as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["uptime_s"] >= 0


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer " + "x" * 43}])
async def test_system_rejects_bad_token(served: Served, headers: dict[str, str]) -> None:
    async with served.client(authorized=False) as client:
        response = await client.get("/api/v1/system", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_system_snapshot(served: Served) -> None:
    async with served.client() as client:
        response = await client.get("/api/v1/system")
    assert response.status_code == 200
    body = response.json()
    assert body["process"]["pid"] == os.getpid()
    assert body["process"]["rss"] > 1_000_000
    assert body["memory"]["total"] > body["memory"]["available"] > 0
    assert 0 <= body["cpu"]["percent"] <= 100
    assert body["cpu"]["logical"] >= 1
    assert any(disk["total"] > 0 for disk in body["disks"])


async def test_process_report_lists_core(served: Served) -> None:
    async with served.client() as client:
        report = (await client.get("/api/v1/system/processes")).json()
    assert report["budget_bytes"] == 350 * 1024 * 1024
    assert [(p["name"], p["kind"], p["pid"]) for p in report["processes"]] == [
        ("core", "core", os.getpid())
    ]
    assert report["total_rss"] == report["processes"][0]["rss"] > 1_000_000


async def test_logs_tail_and_live_stream(served: Served) -> None:
    async with served.client() as client:
        entries = (await client.get("/api/v1/logs")).json()
        assert "core_started" in [entry["event"] for entry in entries]
        assert all(entry["level"] != "debug" for entry in entries)
        last = (await client.get("/api/v1/logs", params={"tail": 1})).json()
        assert len(last) == 1
        assert (await client.get("/api/v1/logs", params={"tail": 0})).status_code == 422
        assert (await client.get("/api/v1/logs", params={"tail": 501})).status_code == 422
    async with served.client(authorized=False) as anonymous:
        assert (await anonymous.get("/api/v1/logs")).status_code == 401

    async with connect(served.ws_url("?topics=log"), additional_headers=served.headers) as ws:
        await _until(lambda: served.core.bus.has_subscribers("log"))
        await served.core.audit.record("test.action", "nishon")
        message = json.loads(await ws.recv())
    assert message["topic"] == "log"
    assert (message["data"]["event"], message["data"]["target"]) == ("audit", "nishon")


def test_snapshot_function_directly() -> None:
    snapshot = take_snapshot()
    assert snapshot.process.threads >= 1
    assert snapshot.process.private is not None


async def test_foreign_host_header_rejected(served: Served) -> None:
    async with served.client() as client:
        response = await client.get("/api/v1/health", headers={"Host": "evil.example"})
    assert response.status_code == 400


async def test_unknown_path_and_docs_closed(served: Served) -> None:
    async with served.client() as client:
        assert (await client.get("/api/v1/yoq")).status_code == 404
        assert (await client.get("/docs")).status_code == 404
        assert (await client.get("/openapi.json")).status_code == 404


async def test_first_start_creates_files_and_audit_row(paths: DataPaths) -> None:
    app = create_app(paths)
    async with app.router.lifespan_context(app):
        pass
    log_text = (paths.logs_dir / "srv1.log").read_text(encoding="utf-8")
    assert paths.config_file.is_file()
    with closing(sqlite3.connect(paths.db_file)) as conn:
        rows = conn.execute("SELECT action, ok FROM audit_log").fetchall()
    assert rows == [("auth.token_created", 1)]
    assert "core_started" in log_text
    assert paths.token_file.read_text(encoding="ascii").strip() not in log_text


async def test_token_survives_restart(paths: DataPaths) -> None:
    tokens: list[str] = []
    for _ in range(2):
        app = create_app(paths)
        async with app.router.lifespan_context(app):
            tokens.append(paths.token_file.read_text(encoding="ascii"))
    assert tokens[0] == tokens[1]
    with closing(sqlite3.connect(paths.db_file)) as conn:
        assert conn.execute("SELECT count(*) FROM audit_log").fetchone() == (1,)


async def test_ws_delivers_only_matching_topics(served: Served) -> None:
    bus = served.core.bus
    url = served.ws_url("?topics=test.*,audit")
    async with connect(url, additional_headers=served.headers) as ws:
        await _until(lambda: bus.subscriber_count == 1)
        bus.publish("other.topic", {"n": 0})
        bus.publish("test.one", {"n": 1})
        bus.publish("audit", {"n": 2})
        first = json.loads(await ws.recv())
        second = json.loads(await ws.recv())
    assert (first["topic"], first["data"]) == ("test.one", {"n": 1})
    assert (second["topic"], second["data"]) == ("audit", {"n": 2})
    assert second["seq"] > first["seq"]


async def test_ws_unsubscribes_on_disconnect(served: Served) -> None:
    bus = served.core.bus
    async with connect(served.ws_url(), additional_headers=served.headers):
        await _until(lambda: bus.subscriber_count == 1)
    await _until(lambda: bus.subscriber_count == 0)


async def test_ws_reports_dropped_events(served: Served) -> None:
    bus = served.core.bus
    queue_size = served.core.settings.events.queue_size
    # max_queue=None: aks holda klient o'qilmagan xabarlar ortidagi Close kadrini 10 s kutadi.
    url = served.ws_url("?topics=flood")
    async with connect(url, additional_headers=served.headers, max_queue=None) as ws:
        await _until(lambda: bus.subscriber_count == 1)
        for index in range(queue_size + 5):  # loop'ga navbat bermasdan — navbat toshadi
            bus.publish("flood", {"i": index})
        first = json.loads(await ws.recv())
        second = json.loads(await ws.recv())
    assert first == {"topic": DROPPED_TOPIC, "data": {"count": 5}}
    assert second["data"] == {"i": 5}


async def test_ws_closed_when_bus_closes(served: Served) -> None:
    bus = served.core.bus
    async with connect(served.ws_url(), additional_headers=served.headers) as ws:
        await _until(lambda: bus.subscriber_count == 1)
        bus.close()
        with pytest.raises(ConnectionClosed) as excinfo:
            await ws.recv()
    assert excinfo.value.rcvd is not None
    assert excinfo.value.rcvd.code == 1001


@pytest.mark.parametrize(
    ("query", "headers"),
    [
        ("", {}),
        ("", {"Authorization": "Bearer " + "x" * 43}),
        ("?token=whatever", {}),
    ],
)
async def test_ws_rejects_without_valid_header(
    served: Served, query: str, headers: dict[str, str]
) -> None:
    with pytest.raises(InvalidStatus) as excinfo:
        async with connect(served.ws_url(query), additional_headers=headers):
            pass
    assert excinfo.value.response.status_code == 403
    assert served.core.bus.subscriber_count == 0


async def test_ws_token_in_query_is_not_accepted(served: Served) -> None:
    with pytest.raises(InvalidStatus):
        async with connect(served.ws_url(f"?token={served.token}")):
            pass


async def test_ws_rejects_bad_topics(served: Served) -> None:
    url = served.ws_url("?topics=A%20B;drop")
    with pytest.raises(InvalidStatus) as excinfo:
        async with connect(url, additional_headers=served.headers):
            pass
    assert excinfo.value.response.status_code == 403


async def test_ws_rejects_foreign_host(served: Served) -> None:
    headers = served.headers | {"Host": "evil.example"}
    with pytest.raises(InvalidStatus) as excinfo:
        async with connect(served.ws_url(), additional_headers=headers):
            pass
    assert excinfo.value.response.status_code == 400


def test_parse_topics() -> None:
    assert parse_topics("*") == ("*",)
    assert parse_topics(" system.* , audit ") == ("system.*", "audit")
    assert parse_topics("") is None
    assert parse_topics("UPPER") is None
    assert parse_topics(",".join(["a"] * 17)) is None
