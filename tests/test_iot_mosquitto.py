"""`iot` plagini HAQIQIY Mosquitto bilan: brokerni plagin o'zi ishga tushiradi.

`tools/mosquitto/mosquitto.exe` (yoki `SRV1_MOSQUITTO_EXE`, yoki standart o'rnatish joyi)
bo'lmasa testlar o'tkazib yuboriladi. Tashqi qurilma o'rnida — Mosquitto'ning o'z
`mosquitto_pub.exe` / `mosquitto_sub.exe` dasturlari (plagin kodidan mustaqil klient).
"""

import asyncio
import subprocess
from pathlib import Path

import psutil
import pytest

from conftest import free_port, serve_app
from iot_helpers import install_iot
from srv1_core.paths import DataPaths
from srv1_core.plugins.registry import BUILTIN_DIR
from test_iot_plugin import Iot

MOSQUITTO = BUILTIN_DIR.parent / "tools" / "mosquitto" / "mosquitto.exe"
PUB = MOSQUITTO.with_name("mosquitto_pub.exe")
SUB = MOSQUITTO.with_name("mosquitto_sub.exe")

pytestmark = pytest.mark.skipif(
    not (MOSQUITTO.is_file() and PUB.is_file() and SUB.is_file()),
    reason="tools/mosquitto yo'q (tools/README.md)",
)


@pytest.fixture(autouse=True)
def _real_mosquitto(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    # Testda plagin vaqtinchalik papkaga nusxalanadi, shuning uchun brokerni o'ziga
    # nisbatan (`../../tools`) topa olmaydi — aniq yo'l beriladi.
    monkeypatch.setenv("SRV1_MOSQUITTO_EXE", str(MOSQUITTO))


async def _tool(exe: Path, *arguments: str, timeout_s: float = 15) -> tuple[int, str]:
    """Mosquitto klient dasturini yuritadi: (chiqish kodi, stdout+stderr)."""

    def run() -> tuple[int, str]:
        done = subprocess.run(
            [str(exe), *arguments], capture_output=True, timeout=timeout_s, check=False
        )
        return done.returncode, (done.stdout + done.stderr).decode("utf-8", "replace").strip()

    return await asyncio.to_thread(run)


def _pub(port: int, topic: str, payload: str, *extra: str) -> tuple[str, ...]:
    return ("-h", "127.0.0.1", "-p", str(port), "-t", topic, "-m", payload, *extra)


async def test_managed_broker_full_cycle(paths: DataPaths, plugin_root: Path) -> None:
    port = free_port()
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt={"port": port})
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        status = await iot.status_is("mqtt_state", "connected")
        assert (status["broker"], status["broker_error"]) == ("running", None)
        broker_pid = status["broker_pid"]
        broker = psutil.Process(broker_pid)
        assert Path(broker.exe()) == MOSQUITTO
        # faqat loopback'da tinglaydi
        listening = {c.laddr.ip for c in broker.net_connections("tcp") if c.status == "LISTEN"}
        assert listening == {"127.0.0.1"}

        # tashqi qurilma (mosquitto_pub) -> broker -> plagin -> telemetriya
        assert (await _tool(PUB, *_pub(port, "srv1/xona/harorat", "23.5")))[0] == 0
        assert (await _tool(PUB, *_pub(port, "srv1/issiqxona", '{"temp": 24.25, "hum": 61}')))[
            0
        ] == 0
        await iot.wait_latest(("mqtt:srv1/issiqxona", "hum"), 61.0)
        latest = await iot.latest()
        assert latest[("mqtt:srv1/xona/harorat", "value")] == 23.5
        assert latest[("mqtt:srv1/issiqxona", "temp")] == 24.25
        assert (await _tool(PUB, *_pub(port, "boshqa/mavzu", "9")))[0] == 0  # obunada yo'q

        # plagin nashr qiladi (retain) -> keyin ulangan tashqi klient oladi
        sent = await iot.post(
            "/mqtt/publish", topic="srv1/buyruq/rele", payload="oʻn", qos=1, retain=True
        )
        assert sent.status_code == 200, sent.text
        await iot.status_is("mqtt_messages", 3)  # ikki tashqi + o'zimizga qaytgan nashr
        code, text = await _tool(
            SUB, "-h", "127.0.0.1", "-p", str(port), "-t", "srv1/buyruq/#", "-C", "1", "-W", "5"
        )
        assert (code, text) == (0, "oʻn")
        messages = await iot.get("/mqtt/messages")
        assert "boshqa/mavzu" not in {m["topic"] for m in messages}

    # yadro to'xtagach broker ham yo'q (yetim jarayon qolmaydi)
    assert not psutil.pid_exists(broker_pid) or psutil.Process(broker_pid).name() != "mosquitto.exe"


async def test_managed_broker_with_password(paths: DataPaths, plugin_root: Path) -> None:
    """Plagin yozgan `password_file` ni haqiqiy Mosquitto qabul qiladi; begona kirolmaydi."""
    port = free_port()
    secret = "juda-Maxfiy_parol 42"  # noqa: S105
    mqtt = {"port": port, "username": "srv1", "password": secret}
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt=mqtt)
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        status = await iot.status_is("mqtt_state", "connected")
        assert status["broker"] == "running"

        ok = await _tool(PUB, *_pub(port, "srv1/a", "1", "-u", "srv1", "-P", secret))
        assert ok[0] == 0, ok[1]
        await iot.wait_latest(("mqtt:srv1/a", "value"), 1.0)
        # parolsiz, noto'g'ri parol va noto'g'ri foydalanuvchi rad etiladi
        for extra in ((), ("-u", "srv1", "-P", "notogri"), ("-u", "begona", "-P", secret)):
            code, text = await _tool(PUB, *_pub(port, "srv1/a", "2", *extra))
            assert code != 0, (extra, text)
            assert "not authori" in text.lower() or "bad user" in text.lower(), text
        await asyncio.sleep(0.5)
        assert (await iot.latest())[("mqtt:srv1/a", "value")] == 1.0
    stored = (paths.plugin_data_dir("iot") / "mosquitto.passwd").read_text(encoding="utf-8")
    assert stored.startswith("srv1:$7$") and secret not in stored
    assert secret not in (paths.logs_dir / "srv1.log").read_text(encoding="utf-8")


async def test_broker_restart_reconnects(paths: DataPaths, plugin_root: Path) -> None:
    """Broker o'ldirilsa plagin holatni ko'rsatadi; yadro qayta ishga tushganda hammasi tiklanadi."""
    port = free_port()
    install_iot(plugin_root, paths.plugin_data_dir("iot"), mqtt={"port": port})
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        status = await iot.status_is("mqtt_state", "connected")
        psutil.Process(status["broker_pid"]).kill()
        status = await iot.status_is("mqtt_state", "disconnected")
        assert status["broker"] != "running"
        assert (await client.get("/api/v1/plugins/iot")).json()["status"] == "running"
    async with serve_app(paths) as served, served.client() as client:
        iot = Iot(client)
        status = await iot.status_is("mqtt_state", "connected")
        assert status["broker"] == "running"
        assert (await _tool(PUB, *_pub(port, "srv1/qayta", "5")))[0] == 0
        await iot.wait_latest(("mqtt:srv1/qayta", "value"), 5.0)
