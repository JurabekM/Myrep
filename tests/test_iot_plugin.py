"""`iot` plagini: haqiqiy yadro; MQTT — haqiqiy TCP (kichik broker), Modbus — pymodbus simulyatori,
serial — pyserial'ning `loop://` porti. Haqiqiy temir va Mosquitto ishtirok etmaydi."""

import asyncio
import json
import sqlite3
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx
import pytest

from conftest import free_port, serve_app
from iot_helpers import MiniBroker, ModbusSimulator, install_iot, topic_matches
from srv1_core.paths import DataPaths

API = "/api/v1/plugins/iot/api"


async def _eventually[T](
    probe: Callable[[], Awaitable[T]], accept: Callable[[T], bool], what: str, timeout_s: float = 10
) -> T:
    value = await probe()
    try:
        async with asyncio.timeout(timeout_s):
            while not accept(value):
                await asyncio.sleep(0.05)
                value = await probe()
    except TimeoutError:
        pytest.fail(f"{what}: kutilgan holat yuz bermadi, oxirgi qiymat: {value!r}")
    return value


class Iot:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get(self, path: str, **params: str | float) -> Any:  # noqa: ANN401
        response = await self.client.get(f"{API}{path}", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    async def post(self, operation: str, /, **body: object) -> httpx.Response:
        return await self.client.post(f"{API}{operation}", json=body)

    async def latest(self, source: str = "") -> dict[tuple[str, str], float]:
        rows = await self.get("/telemetry/latest", source=source)
        return {(row["source"], row["key"]): row["value"] for row in rows}

    async def wait_latest(self, key: tuple[str, str], value: float) -> None:
        await _eventually(self.latest, lambda found: found.get(key) == value, f"{key} = {value}")

    async def status_is(self, field: str, value: object) -> dict[str, Any]:
        async def probe() -> dict[str, Any]:
            return await self.get("/status")

        return await _eventually(probe, lambda s: s[field] == value, f"{field} = {value}")


@pytest.fixture
async def broker() -> AsyncGenerator[MiniBroker]:
    mini = MiniBroker()
    await mini.start()
    yield mini
    await mini.stop()


def _mqtt(broker: MiniBroker, **extra: object) -> dict[str, object]:
    return {"manage_broker": False, "host": "127.0.0.1", "port": broker.port, **extra}


def _audit(paths: DataPaths) -> list[tuple[str, str, int]]:
    with closing(sqlite3.connect(paths.db_file)) as conn:
        return conn.execute(
            "SELECT action, target, ok FROM audit_log WHERE actor = 'plugin:iot' ORDER BY id"
        ).fetchall()


# --- MQTT ----------------------------------------------------------------------------
async def test_mqtt_subscribe_publish_and_telemetry(
    paths: DataPaths, plugin_root: Path, broker: MiniBroker
) -> None:
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt=_mqtt(broker))
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        status = await iot.status_is("mqtt_state", "connected")
        assert (status["broker"], status["mqtt_messages"]) == ("external", 0)
        await _eventually(
            lambda: asyncio.sleep(0, broker.subscriptions()),
            lambda topics: topics == {"srv1/#"},
            "standart obuna",
        )
        events = served.core.bus.subscribe("plugin.iot.mqtt")

        # tashqi qurilma nashr qiladi: oddiy son, JSON va matn
        broker.inject("srv1/xona/harorat", b"21.5")
        broker.inject("srv1/issiqxona", b'{"temp": 24.25, "hum": 61, "ok": true, "nom": "A1"}')
        broker.inject("srv1/holat", b"ishlayapti")
        broker.inject("boshqa/mavzu", b"99")
        await iot.wait_latest(("mqtt:srv1/issiqxona", "hum"), 61.0)
        latest = await iot.latest()
        assert latest == {
            ("mqtt:srv1/xona/harorat", "value"): 21.5,
            ("mqtt:srv1/issiqxona", "temp"): 24.25,
            ("mqtt:srv1/issiqxona", "hum"): 61.0,
            ("mqtt:srv1/issiqxona", "ok"): 1.0,
        }
        assert await iot.latest("mqtt:srv1/xona") == {("mqtt:srv1/xona/harorat", "value"): 21.5}
        messages = await iot.get("/mqtt/messages")
        assert [(m["topic"], m["payload"]) for m in messages] == [
            ("srv1/xona/harorat", "21.5"),
            ("srv1/issiqxona", '{"temp": 24.25, "hum": 61, "ok": true, "nom": "A1"}'),
            ("srv1/holat", "ishlayapti"),
        ]
        assert (await iot.get("/mqtt/log"))[-1].endswith("srv1/holat  ishlayapti")
        event = await asyncio.wait_for(anext(events), 5)
        assert event.data == {"topic": "srv1/xona/harorat", "payload": "21.5"}

        # plagin nashr qiladi -> broker oladi -> o'zimizga ham qaytadi
        published = await iot.post("/mqtt/publish", topic="srv1/buyruq/rele", payload="1")
        assert published.json() == {"published": "srv1/buyruq/rele", "bytes": 1}
        await _eventually(
            lambda: asyncio.sleep(0, broker.received),
            lambda got: ("srv1/buyruq/rele", b"1") in got,
            "broker nashrni olishi",
        )
        await iot.wait_latest(("mqtt:srv1/buyruq/rele", "value"), 1.0)
        qos1 = await iot.post(
            "/mqtt/publish", topic="srv1/q", payload="oʻzbekcha", qos=1, retain=True
        )
        assert qos1.json()["bytes"] == len("oʻzbekcha".encode())
        for bad in ("srv1/#", "srv1/+/x", " "):
            assert (await iot.post("/mqtt/publish", topic=bad, payload="x")).status_code == 400

        # obuna qo'shish va bekor qilish (saqlanadi)
        added = (await iot.post("/mqtt/subscribe", topic="boshqa/+")).json()
        assert added == [{"topic": "srv1/#"}, {"topic": "boshqa/+"}]
        await _eventually(
            lambda: asyncio.sleep(0, broker.subscriptions()),
            lambda topics: "boshqa/+" in topics,
            "yangi obuna",
        )
        broker.inject("boshqa/mavzu", b"7")
        await iot.wait_latest(("mqtt:boshqa/mavzu", "value"), 7.0)
        assert (await iot.post("/mqtt/unsubscribe", topic="boshqa/+")).json() == [
            {"topic": "srv1/#"}
        ]
        assert (await iot.post("/mqtt/unsubscribe", topic="yoq/mavzu")).status_code == 404
        # 3 ta tashqi + rele + srv1/q + boshqa/mavzu = 6 xabar; ulardan 6 ta sonli qiymat
        # (JSON'dan 3 ta, matnli ikkita xabardan 0 ta).
        status = await iot.status_is("mqtt_messages", 6)
        assert status["samples"] == 6

    saved = json.loads((paths.plugin_data_dir("iot") / "iot.json").read_text(encoding="utf-8"))
    assert saved["mqtt"]["subscriptions"] == ["srv1/#"]


async def test_mqtt_reconnects_and_resubscribes(paths: DataPaths, plugin_root: Path) -> None:
    broker = MiniBroker()
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt=_mqtt(broker))
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        # broker hali yo'q: plagin ishlaydi, holat "disconnected", nashr 503
        assert (await iot.get("/status"))["mqtt_state"] == "disconnected"
        assert (await iot.post("/mqtt/publish", topic="srv1/x", payload="1")).status_code == 503
        assert (await client.get("/api/v1/health")).status_code == 200

        await broker.start()
        try:
            await iot.status_is("mqtt_state", "connected")
            await broker.stop()
            await iot.status_is("mqtt_state", "disconnected")
            await broker.start()
            await iot.status_is("mqtt_state", "connected")
            await _eventually(
                lambda: asyncio.sleep(0, broker.subscriptions()),
                lambda topics: topics == {"srv1/#"},
                "qayta ulangandan keyin obuna tiklanishi",
            )
            broker.inject("srv1/qaytdi", b"5")
            await iot.wait_latest(("mqtt:srv1/qaytdi", "value"), 5.0)
            assert broker.connects >= 2
        finally:
            await broker.stop()


async def test_mqtt_credentials_are_sent_but_never_exposed(
    paths: DataPaths, plugin_root: Path, broker: MiniBroker
) -> None:
    secret = "juda-maxfiy-parol"  # noqa: S105 — test qiymati
    mqtt = _mqtt(broker, username="srv1", password=secret)
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt=mqtt)
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        await iot.status_is("mqtt_state", "connected")
        assert broker.credentials == [("srv1", secret)]
        pages = [await client.get(f"{API}/status"), await client.get("/api/v1/plugins/iot")]
        assert all(secret not in page.text for page in pages)
    assert secret not in (paths.logs_dir / "srv1.log").read_text(encoding="utf-8")


async def test_mqtt_disabled_and_missing_mosquitto(
    paths: DataPaths, plugin_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt={"enabled": False})
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        status = await iot.get("/status")
        assert (status["mqtt_state"], status["broker"]) == ("disabled", "disabled")
        assert (await iot.post("/mqtt/publish", topic="a", payload="1")).status_code == 409
        assert (await iot.post("/mqtt/subscribe", topic="a")).status_code == 409
        assert await iot.get("/mqtt/subscriptions") == []

    # Mosquitto yo'q: plagin ishlayveradi va sababini aytadi
    monkeypatch.setenv("SRV1_MOSQUITTO_EXE", str(tmp_path / "yoq" / "mosquitto.exe"))
    settings = paths.plugin_data_dir("iot") / "iot.json"
    settings.write_text(json.dumps({"mqtt": {"port": free_port()}}), encoding="utf-8")
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        status = await iot.get("/status")
        assert (status["broker"], status["mqtt_state"]) == ("missing", "disconnected")
        assert "mosquitto.exe topilmadi" in status["broker_error"]
        assert (await client.get("/api/v1/plugins/iot")).json()["status"] == "running"


@pytest.mark.parametrize(
    "mqtt",
    [
        {"listen_host": "0.0.0.0"},  # noqa: S104
        {"listen_host": "0.0.0.0", "allow_non_loopback": True},  # noqa: S104
        {
            "listen_host": "0.0.0.0",  # noqa: S104
            "allow_non_loopback": True,
            "username": "u",
            "password": "qisqa",
        },
    ],
)
async def test_network_broker_needs_flag_and_password(
    paths: DataPaths, plugin_root: Path, mqtt: dict[str, object]
) -> None:
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt=mqtt)
    async with serve_app(paths) as served, served.client() as client:
        info = (await client.get("/api/v1/plugins/iot")).json()
        assert info["status"] == "error"
        assert "loopback emas" in info["error"] or "password" in info["error"]
        assert (await client.get("/api/v1/health")).status_code == 200


# --- Modbus ---------------------------------------------------------------------------
def _device(port: int, **extra: object) -> dict[str, object]:
    return {
        "name": "plc",
        "host": "127.0.0.1",
        "port": port,
        "interval_s": 0.2,
        "timeout_s": 1,
        "registers": [
            {"key": "harorat", "address": 0, "type": "int16", "scale": 0.1},
            {"key": "bosim", "address": 1, "kind": "input"},
            {"key": "hisob", "address": 2, "type": "uint32"},
            {"key": "oqim", "address": 4, "type": "float32"},
            {"key": "nasos", "address": 3, "kind": "coil", "type": "bool"},
        ],
        **extra,
    }


async def test_modbus_polling_writing_and_failure(paths: DataPaths, plugin_root: Path) -> None:
    simulator = ModbusSimulator([65286, 1013, 1, 34464, 0x4129, 0x999A])  # -250, 1013, 100000, 10.6
    await simulator.start()
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt={"enabled": False})
    try:
        async with serve_app(paths) as served, served.client() as client:
            iot = Iot(client)
            created = await client.post(f"{API}/modbus", json=_device(simulator.port))
            assert created.status_code == 201, created.text
            assert created.json()["address"] == f"127.0.0.1:{simulator.port}"

            await iot.wait_latest(("modbus:plc", "bosim"), 1013.0)
            latest = await iot.latest("modbus:plc")
            assert latest[("modbus:plc", "harorat")] == pytest.approx(-25.0)
            assert latest[("modbus:plc", "hisob")] == 100000.0
            assert latest[("modbus:plc", "oqim")] == pytest.approx(10.6, abs=1e-5)
            assert latest[("modbus:plc", "nasos")] == 0.0

            # qurilmadagi qiymat o'zgarsa, keyingi so'rovda ko'rinadi
            await simulator.set_input(1, [990])
            await iot.wait_latest(("modbus:plc", "bosim"), 990.0)
            series = await iot.get("/telemetry/series", source="modbus:plc", key="bosim")
            assert {point["value"] for point in series} == {1013.0, 990.0}
            assert [point["ts"] for point in series] == sorted(point["ts"] for point in series)

            # yozish: scale teskari qo'llanadi; coil; auditga tushadi
            written = await iot.post("/modbus/write", name="plc", key="harorat", value=31.5)
            assert written.json() == {"device": "plc", "key": "harorat", "value": 31.5}
            assert await simulator.holding(0) == [315]
            await iot.post("/modbus/write", name="plc", key="oqim", value=2.5)
            assert await simulator.holding(4, 2) == [0x4020, 0x0000]
            await iot.post("/modbus/write", name="plc", key="nasos", value=1)
            assert await simulator.coil(3) is True
            await iot.wait_latest(("modbus:plc", "nasos"), 1.0)
            read_only = await iot.post("/modbus/write", name="plc", key="bosim", value=1)
            assert (read_only.status_code, "faqat o'qiladi" in read_only.text) == (502, True)
            assert (
                await iot.post("/modbus/write", name="plc", key="yoq", value=1)
            ).status_code == 502
            assert (
                await iot.post("/modbus/write", name="yoq", key="a", value=1)
            ).status_code == 404

            devices = await iot.get("/modbus")
            assert (devices[0]["ok"], devices[0]["error"], devices[0]["registers"]) == (
                True,
                None,
                5,
            )
            assert devices[0]["polls"] >= 2
            assert (await iot.get("/status"))["modbus_ok"] == 1

            # qurilma o'chsa: xato holati, yadro ishlaydi; qaytsa — o'zi tiklanadi
            await simulator.stop()
            failed = await _eventually(
                lambda: iot.get("/modbus"), lambda rows: rows[0]["ok"] is False, "aloqa uzilishi"
            )
            assert failed[0]["error"]
            assert (await client.get("/api/v1/health")).status_code == 200
            simulator = ModbusSimulator([7] * 6)
            await simulator.start()
            await client.post(f"{API}/modbus/remove", json={"name": "plc"})
            await client.post(f"{API}/modbus", json=_device(simulator.port))
            await iot.wait_latest(("modbus:plc", "bosim"), 7.0)

            duplicate = await client.post(f"{API}/modbus", json=_device(simulator.port))
            assert duplicate.status_code == 409
    finally:
        await simulator.stop()

    audit = _audit(paths)
    assert ("modbus.write", "plc/harorat", 1) in audit
    assert ("modbus.write", "plc/bosim", 0) in audit
    saved = json.loads((paths.plugin_data_dir("iot") / "iot.json").read_text(encoding="utf-8"))
    assert [device["name"] for device in saved["modbus"]] == ["plc"]


async def test_modbus_validation_and_bad_addresses(paths: DataPaths, plugin_root: Path) -> None:
    simulator = ModbusSimulator([1, 2, 3])
    await simulator.start()
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt={"enabled": False})
    try:
        async with serve_app(paths) as served, served.client() as client:
            iot = Iot(client)
            bad_devices: list[dict[str, object]] = [
                _device(1, name="Bad Name"),
                _device(1, registers=[]),
                _device(1, registers=[{"key": "a", "address": 0, "kind": "coil"}]),
                _device(1, registers=[{"key": "a", "address": 0, "type": "bool"}]),
                _device(1, registers=[{"key": "a", "address": 0}, {"key": "a", "address": 1}]),
                _device(1, transport="rtu"),
                _device(1, interval_s=0),
            ]
            for device in bad_devices:
                assert (await client.post(f"{API}/modbus", json=device)).status_code == 422, device
            # RTU: manifestda ruxsat etilmagan port
            rtu = _device(1, transport="rtu", serial_port="COM9")
            assert (await client.post(f"{API}/modbus", json=rtu)).status_code == 403
            assert await iot.get("/modbus") == []

            # yo'q manzil: qurilma xato qaytaradi -> holatda ko'rinadi, boshqa hech narsa buzilmaydi
            wrong = _device(simulator.port, registers=[{"key": "yoq", "address": 5000}])
            await client.post(f"{API}/modbus", json=wrong)
            row = await _eventually(
                lambda: iot.get("/modbus"),
                lambda rows: rows[0]["error"] is not None,
                "manzil xatosi",
            )
            assert (row[0]["ok"], "yoq" in row[0]["error"]) == (False, True)
            assert await iot.latest("modbus:") == {}
    finally:
        await simulator.stop()


# --- serial ------------------------------------------------------------------------------
async def test_serial_loopback_monitor_and_permissions(paths: DataPaths, plugin_root: Path) -> None:
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt={"enabled": False})
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        events = served.core.bus.subscribe("plugin.iot.serial")

        # ruxsat etilmagan va noto'g'ri portlar
        assert (await iot.post("/serial/open", port="COM9")).status_code == 403
        for bad in ("socket://10.0.0.1:23", "rfc2217://host:1", "/dev/ttyUSB0", "..\\x"):
            assert (await iot.post("/serial/open", port=bad)).status_code == 400, bad
        assert (await client.get(f"{API}/serial/lines", params={"port": "COM9"})).status_code == 404
        assert (await iot.post("/serial/write", port="loop://", text="x")).status_code == 404

        opened = await iot.post("/serial/open", port="loop://", baudrate=115200)
        assert opened.json() == {"port": "loop://", "baudrate": 115200, "open": True}
        assert (await iot.post("/serial/open", port="loop://")).status_code == 409

        # halqa port: yozilgan satr o'qishga qaytadi
        await iot.post("/serial/write", port="loop://", text="temp=21.5,hum=40")
        await iot.post("/serial/write", port="loop://", text="salom, qurilma")
        await iot.post("/serial/write", port="loop://", text='{"volt": 3.31}')
        await iot.post("/serial/write", port="loop://", text="yarim ", newline=False)
        await iot.post("/serial/write", port="loop://", text="satr")
        lines = await _eventually(
            lambda: iot.get("/serial/lines", port="loop://"), lambda got: len(got) == 4, "satrlar"
        )
        assert lines == ["temp=21.5,hum=40", "salom, qurilma", '{"volt": 3.31}', "yarim satr"]
        assert await iot.latest("serial:") == {
            ("serial:loop://", "temp"): 21.5,
            ("serial:loop://", "hum"): 40.0,
            ("serial:loop://", "volt"): 3.31,
        }
        event = await asyncio.wait_for(anext(events), 5)
        assert event.data == {"port": "loop://", "line": "temp=21.5,hum=40"}

        ports = {row["port"]: row for row in await iot.get("/serial/ports")}
        assert (ports["loop://"]["open"], ports["loop://"]["allowed"]) == (True, True)
        assert ports["loop://"]["baudrate"] == 115200
        assert (await iot.get("/status"))["serial_open"] == 1

        assert (await iot.post("/serial/close", port="loop://")).json()["open"] is False
        assert (await iot.post("/serial/close", port="loop://")).status_code == 404
        assert (await iot.get("/status"))["serial_open"] == 0


# --- telemetriya --------------------------------------------------------------------------
async def test_telemetry_record_series_retention_and_restart(
    paths: DataPaths, plugin_root: Path
) -> None:
    data_dir = paths.plugin_data_dir("iot")
    install_iot(plugin_root, data_dir, mqtt={"enabled": False}, retention_days=1)
    now = time.time()
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        events = served.core.bus.subscribe("plugin.iot.telemetry")
        recorded = await iot.post(
            "/telemetry/record", source="datchik", values={"t": 20.5, "h": 55}
        )
        assert recorded.json() == {"source": "manual:datchik", "recorded": 2}
        flat = await iot.post("/telemetry/record", source="datchik", key="t", value=21)
        assert flat.status_code == 201
        for minutes_ago, value in ((30, 18.0), (90, 15.0), (60 * 30, 5.0)):
            stamp = now - minutes_ago * 60
            await iot.post("/telemetry/record", source="datchik", values={"t": value}, ts=stamp)

        # oxirgi qiymat — vaqt bo'yicha eng yangisi (yozilish tartibi bo'yicha emas)
        assert await iot.latest("manual:") == {
            ("manual:datchik", "t"): 21.0,
            ("manual:datchik", "h"): 55.0,
        }
        hour = await iot.get("/telemetry/series", source="manual:datchik", key="t", minutes=60)
        assert [point["value"] for point in hour] == [18.0, 20.5, 21.0]
        two_hours = await iot.get(
            "/telemetry/series", source="manual:datchik", key="t", minutes=120
        )
        assert [point["value"] for point in two_hours] == [15.0, 18.0, 20.5, 21.0]
        limited = await iot.get(
            "/telemetry/series", source="manual:datchik", key="t", minutes=9999, limit=2
        )
        assert [point["value"] for point in limited] == [20.5, 21.0], "oxirgi nuqtalar qoladi"
        event = await asyncio.wait_for(anext(events), 5)
        assert (event.data["source"], event.data["t"], event.data["h"]) == (
            "manual:datchik",
            20.5,
            55,
        )

        # saqlash muddati (1 kun): 30 soat oldingi yozuv o'chadi
        assert (await iot.get("/status"))["samples"] == 6
        purged = (await iot.post("/telemetry/purge")).json()
        assert purged == {"removed": 1, "retention_days": 1.0}
        everything = await iot.get(
            "/telemetry/series", source="manual:datchik", key="t", minutes=9999
        )
        assert len(everything) == 4

        bad_bodies: list[dict[str, object]] = [
            {"source": "datchik"},
            {"source": "Bad Source", "values": {"t": 1}},
            {"source": "datchik", "values": {"bad key": 1}},
            {"source": "datchik", "values": {"t": "matn"}},
            {"source": "datchik", "key": "t"},
        ]
        for body in bad_bodies:
            assert (await client.post(f"{API}/telemetry/record", json=body)).status_code == 422, (
                body
            )
        missing_key = await client.get(f"{API}/telemetry/series", params={"source": "manual:x"})
        assert missing_key.status_code == 422

    # qayta ishga tushgandan keyin ma'lumot joyida
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        assert (await iot.latest("manual:"))[("manual:datchik", "t")] == 21.0
    with closing(sqlite3.connect(data_dir / "telemetry.db")) as conn:
        assert conn.execute("SELECT COUNT(*) FROM telemetry").fetchone() == (5,)


def test_topic_matching_helper() -> None:
    assert topic_matches("srv1/#", "srv1/a/b")
    assert topic_matches("a/+/c", "a/b/c")
    assert not topic_matches("a/+", "a/b/c")
    assert not topic_matches("a/b", "a")
