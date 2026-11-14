"""`monitor` plaginining tarmoq kuzatuvi (`netcap`): tahlil, xavf tekshiruvlari, xizmat."""

import asyncio
import os
import socket
import sqlite3
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from conftest import serve_app
from monitor_helpers import install_monitor
from netcap_helpers import netcap_module, write_fake_worker
from srv1_core.paths import DataPaths

API = "/api/v1/plugins/monitor/api/net"

text = netcap_module("text")
detect = netcap_module("detect")
engine_mod = netcap_module("engine")
geo = netcap_module("geo")
net_models = netcap_module("models")
net_store = netcap_module("store")
ifaces = netcap_module("ifaces")

NPCAP = ifaces.npcap_installed()


def _record(**fields: Any) -> Any:  # noqa: ANN401 — plagin moduli dinamik yuklanadi
    base: dict[str, Any] = {"ts": 100.0, "proto": "TCP", "src": "10.0.0.5", "dst": "10.0.0.9"}
    return detect.Record(**(base | fields))


def _syn(ts: float, dport: int, **fields: Any) -> Any:  # noqa: ANN401
    return _record(ts=ts, sport=40000, dport=dport, flags="S", **fields)


def _kinds(found: list[Any]) -> list[str]:
    return [alert.kind for alert in found]


# --- matn: ochiq uzatilgan sirlar -------------------------------------------------------
@pytest.mark.parametrize(
    ("payload", "mark"),
    [
        (b"POST /login HTTP/1.1\r\n\r\nuser=ali&password=hunter2", "password"),
        (b'{"login": "ali", "Password": "x"}', "password"),
        (b"pwd=1234", "pwd"),
        (b"GET /?api_key=abc123 HTTP/1.1", "api_key"),
        (b"GET / HTTP/1.1\r\nAuthorization: Basic YWxpOjEyMw==\r\n", "authorization"),
        (b"USER ali\r\nPASS hunter2\r\n", "pass_command"),
        (b"token: abcdef", "token"),
    ],
)
def test_find_secret_detects_cleartext_credentials(payload: bytes, mark: str) -> None:
    assert text.find_secret(payload) == mark


@pytest.mark.parametrize(
    "payload",
    [
        b"GET / HTTP/1.1\r\nUser-Agent: curl/8\r\nConnection: keep-alive\r\n",
        b"bypass=1&compass=north",
        b"passport: AA1234567",
        b"the password was long forgotten",  # so'z bor, lekin qiymat berilmagan
        b"Cookie-Policy: strict",
        b"",
        # TLS yozuvi: ichida tasodifan mos keladigan matn bo'lsa ham shifrlangan deb o'tiladi
        b"\x17\x03\x03\x00\x20password=hunter2",
    ],
)
def test_find_secret_ignores_ordinary_traffic(payload: bytes) -> None:
    assert text.find_secret(payload) == ""


def test_printable_escapes_control_bytes_and_truncates() -> None:
    assert text.printable(b"ab\t\r\n\x00\x1b\xff\\", 100) == "ab\\t\\r\\n\\x00\\x1b\\xff\\\\"
    assert text.printable(b"abcdef", 3) == "abc…"
    # natijada hech qachon boshqaruv belgisi bo'lmaydi
    assert all(ord(char) >= 32 for char in text.printable(bytes(range(256)), 256))


# --- xavf tekshiruvlari -----------------------------------------------------------------
def test_port_scan_counts_new_connections_per_pair() -> None:
    detector = detect.Detector(detect.Limits(scan_ports=5, scan_window_s=10))
    found: list[Any] = []
    for index in range(5):
        found += detector.check(_syn(100 + index, 1000 + index))
    assert _kinds(found) == ["port_scan"]
    assert (found[0].src, found[0].dst) == ("10.0.0.5", "10.0.0.9")
    assert found[0].note.startswith("5 port")


def test_dns_replies_and_established_traffic_are_not_a_port_scan() -> None:
    detector = detect.Detector(detect.Limits(scan_ports=5))
    found: list[Any] = []
    for index in range(50):
        # DNS server javoblari: har biri boshqa vaqtinchalik portga (asl dasturdagi yolg'on signal)
        found += detector.check(
            _record(ts=100 + index * 0.1, proto="UDP", src="8.8.8.8", sport=53, dport=50000 + index)
        )
        # o'rnatilgan ulanish paketlari (ACK bor) va SYN-ACK javoblari
        found += detector.check(_record(ts=100, sport=443, dport=50000 + index, flags="A"))
        found += detector.check(_record(ts=100, sport=443, dport=50000 + index, flags="SA"))
        # turli manzillarga bittadan ulanish — skan emas
        found += detector.check(_syn(100, 443, dst=f"10.0.1.{index}"))
    assert found == []


def test_port_scan_window_is_fixed_not_sliding() -> None:
    detector = detect.Detector(detect.Limits(scan_ports=5, scan_window_s=10))
    found: list[Any] = []
    # Har 4 soniyada bitta yangi port: 10 s lik oynaga hech qachon 5 tasi sig'maydi.
    for index in range(30):
        found += detector.check(_syn(100 + index * 4, 2000 + index))
    assert found == []


def test_flag_scans_and_suspicious_ports() -> None:
    detector = detect.Detector(detect.Limits(suspicious_ports=frozenset({23, 4444})))
    assert _kinds(detector.check(_record(sport=1, dport=80, flags=""))) == ["null_scan"]
    assert _kinds(detector.check(_record(sport=1, dport=80, flags="F", src="10.0.0.6"))) == [
        "fin_scan"
    ]
    assert _kinds(detector.check(_record(sport=1, dport=80, flags="FPU", src="10.0.0.7"))) == [
        "xmas_scan"
    ]
    # shubhali port: faqat manzil porti va faqat yangi murojaat
    assert _kinds(detector.check(_syn(100, 23, src="10.0.0.8"))) == ["port"]
    assert detector.check(_record(sport=23, dport=50000, flags="SA", src="10.0.0.9")) == []
    assert detector.check(_record(sport=50000, dport=23, flags="PA", src="10.0.0.10")) == []
    udp = _record(proto="UDP", sport=5000, dport=4444, src="10.0.0.11")
    assert _kinds(detector.check(udp)) == ["port"]


def test_repeated_alert_is_suppressed_for_quiet_period() -> None:
    detector = detect.Detector(detect.Limits(suspicious_ports=frozenset({23}), quiet_s=60))
    assert len(detector.check(_syn(100, 23))) == 1
    assert detector.check(_syn(130, 23)) == []
    assert detector.suppressed == 1
    assert len(detector.check(_syn(161, 23))) == 1
    # boshqa manba — alohida signal
    assert len(detector.check(_syn(162, 23, src="10.0.0.77"))) == 1


def test_secret_alert_names_the_kind_but_never_the_value() -> None:
    detector = detect.Detector(detect.Limits())
    record = _record(sport=50000, dport=80, flags="PA", payload=b"password=hunter2")
    found = detector.check(record)
    assert _kinds(found) == ["secret"] and record.mark == "password"
    assert found[0].note == "password → :80"
    assert "hunter2" not in repr(found)


# --- ishchi holati (engine) -------------------------------------------------------------
def _engine(**options: Any) -> Any:  # noqa: ANN401
    return engine_mod.Engine(engine_mod.Options.from_json({"interface": "x"} | options))


def test_engine_counts_ignores_paused_and_excluded() -> None:
    engine = _engine(excluded=["10.0.0.9", "yaroqsiz", "2001:DB8::1"])
    assert engine.excluded == {"10.0.0.9", "2001:db8::1"}
    engine.handle(_record(length=100))  # manzili chiqarilgan
    engine.handle(_record(dst="10.0.0.10", length=100))
    engine.handle(None)
    assert (engine.total, engine.ignored, engine.bytes) == (1, 1, 100)
    assert engine.command({"c": "pause"}) and engine.paused
    engine.handle(_record(dst="10.0.0.10"))
    assert (engine.total, engine.ignored) == (1, 2)
    assert engine.command({"c": "resume"}) and not engine.paused
    assert engine.command({"c": "exclude", "ips": ["10.0.0.10"]})
    engine.handle(_record(dst="10.0.0.10"))
    engine.handle(_record(dst="10.0.0.9", length=50))  # endi ro'yxatda yo'q
    assert (engine.total, engine.ignored) == (2, 3)
    assert engine.command({"c": "nomalum"}) is True
    assert engine.command({"c": "stop"}) is False


def test_engine_tick_drains_rows_and_reports_rate() -> None:
    engine = _engine(rows_per_tick=3)
    for index in range(10):
        engine.handle(_record(ts=100 + index, dst="10.0.0.10", flags="A", length=10))
    # chegaradan tashqari, lekin belgilangan paket jadvalga baribir tushadi
    engine.handle(_record(dst="10.0.0.10", dport=80, flags="PA", payload=b"pwd=1", length=10))
    tick = engine.tick(200.0, 2.0)
    assert (tick["total"], tick["skipped"], tick["pps"]) == (11, 7, 5.5)
    assert len(tick["packets"]) == 4 and tick["packets"][-1]["mark"] == "pwd"
    assert [a["kind"] for a in tick["alerts"]] == ["secret"]
    assert tick["hosts"][0] == {"ip": "10.0.0.5", "packets": 11, "bytes": 110, "where": ""}
    again = engine.tick(201.0, 1.0)
    assert (again["packets"], again["alerts"], again["pps"]) == ([], [], 0.0)


def test_payload_is_not_kept_unless_enabled() -> None:
    secret = _record(dst="10.0.0.10", dport=80, flags="PA", payload=b"password=hunter2\x00")
    off = _engine()
    off.handle(secret)
    row = off.tick(1.0, 1.0)["packets"][0]
    assert "payload" not in row and "hunter2" not in repr(row)
    on = _engine(store_payload=True, payload_chars=12)
    on.handle(_record(dst="10.0.0.10", dport=80, flags="PA", payload=b"password=hunter2\x00"))
    assert on.tick(1.0, 1.0)["packets"][0]["payload"] == "password=hun…"


def test_engine_survives_a_failing_packet_and_bounds_hosts() -> None:
    engine = _engine()
    engine.failed(ValueError("buzuq paket"))
    assert (engine.errors, engine.last_error) == (1, "ValueError: buzuq paket")
    for index in range(engine_mod.MAX_HOSTS + 500):
        engine.handle(_record(dst=f"10.{index // 65536}.{index // 256 % 256}.{index % 256}"))
    assert len(engine.tick(1.0, 1.0)["hosts"]) == engine_mod.TOP_HOSTS
    assert len(engine._hosts) <= engine_mod.MAX_HOSTS


# --- scapy paketlarini tahlil qilish ----------------------------------------------------
def test_parse_real_packets() -> None:
    from scapy.layers.dns import DNS, DNSQR
    from scapy.layers.inet import ICMP, IP, TCP, UDP
    from scapy.layers.inet6 import ICMPv6EchoRequest, IPv6
    from scapy.layers.l2 import ARP, Ether
    from scapy.packet import Raw

    parse = netcap_module("parse").parse

    def wire(packet: Any) -> Any:  # noqa: ANN401 — simdan o'qilgandek qayta tahlil qilinadi
        return Ether(bytes(packet))

    ip = IP(src="10.0.0.5", dst="10.0.0.9")
    tcp = parse(wire(Ether() / ip / TCP(sport=50000, dport=80, flags="PA") / Raw(b"pwd=1")))
    assert (tcp.proto, tcp.src, tcp.sport, tcp.dst, tcp.dport) == (
        "TCP",
        "10.0.0.5",
        50000,
        "10.0.0.9",
        80,
    )
    assert (tcp.flags, tcp.info, tcp.payload) == ("PA", "[PA]", b"pwd=1")
    assert tcp.length == len(bytes(Ether() / ip / TCP() / Raw(b"pwd=1")))
    assert parse(wire(Ether() / ip / TCP(flags=0))).flags == ""
    assert parse(wire(Ether() / ip / TCP(flags="FPU"))).flags == "FPU"

    query = Ether() / ip / UDP(sport=5000, dport=53) / DNS(rd=1, qd=DNSQR(qname="example.com"))
    dns = parse(wire(query))
    assert (dns.proto, dns.dport, dns.info) == ("UDP", 53, "DNS? example.com")

    ping = parse(wire(Ether() / ip / ICMP()))
    assert (ping.proto, ping.info, ping.sport) == ("ICMP", "echo-request", None)

    v6 = parse(wire(Ether() / IPv6(src="fe80::1", dst="ff02::1") / ICMPv6EchoRequest()))
    assert (v6.proto, v6.src, v6.dst) == ("ICMPv6", "fe80::1", "ff02::1")

    arp = parse(wire(Ether() / ARP(op=1, psrc="10.0.0.5", pdst="10.0.0.1")))
    assert (arp.proto, arp.src, arp.dst) == ("ARP", "10.0.0.5", "10.0.0.1")
    assert arp.info.startswith("who-has ")

    assert parse(Ether(src="00:11:22:33:44:55", dst="ff:ff:ff:ff:ff:ff", type=0x88CC)) is None


# --- geolokatsiya -----------------------------------------------------------------------
def test_geo_only_asks_about_public_addresses_and_caches() -> None:
    assert [geo.is_public(ip) for ip in ("8.8.8.8", "2001:4860:4860::8888")] == [True, True]
    private = ("192.168.1.5", "10.1.2.3", "172.20.0.1", "127.0.0.1", "169.254.1.1")
    other = ("224.0.0.251", "255.255.255.255", "fe80::1", "::1", "yaroqsiz")
    assert not any(geo.is_public(ip) for ip in (*private, *other))
    assert geo.is_public("172.32.0.1")  # asl dastur `172.` ning hammasini xususiy deb bilardi

    asked: list[str] = []
    clock = [0.0]

    def fetch(ip: str) -> str | None:
        asked.append(ip)
        return None if ip == "9.9.9.9" else f"joy {ip}"

    resolver = geo.GeoResolver(fetch=fetch, clock=lambda: clock[0])
    assert resolver.lookup("192.168.1.5") == "" and not resolver.resolve_one()
    assert resolver.lookup("8.8.8.8") == ""
    assert resolver.lookup("8.8.8.8") == ""  # navbatda turganda takror so'ralmaydi
    assert resolver.resolve_one() and not resolver.resolve_one()
    assert resolver.lookup("8.8.8.8") == "joy 8.8.8.8"
    # muvaffaqiyatsiz natija ham keshlanadi: har paketda qayta so'ralmaydi
    resolver.lookup("9.9.9.9")
    assert resolver.resolve_one()
    assert resolver.lookup("9.9.9.9") == "" and not resolver.resolve_one()
    assert asked == ["8.8.8.8", "9.9.9.9"]
    clock[0] = geo.FAIL_TTL_S + 1
    resolver.lookup("9.9.9.9")
    assert resolver.resolve_one() and asked[-1] == "9.9.9.9"


# --- sozlama va ombor -------------------------------------------------------------------
def test_config_validation(tmp_path: Path) -> None:
    config = net_models.NetConfig(excluded=["10.0.0.1", "10.0.0.1", "2001:DB8::1"])
    assert config.excluded == ("10.0.0.1", "2001:db8::1")
    assert (config.store_payload, config.geo) == (False, False)
    for bad in (
        {"excluded": ["yaroqsiz"]},
        {"bpf_filter": "tcp; rm -rf"},
        {"bpf_filter": 'port 80"'},
        {"suspicious_ports": [0]},
        {"scan_ports": 1},
        {"nomalum": 1},
    ):
        with pytest.raises(ValidationError):
            net_models.NetConfig(**bad)
    path = tmp_path / "netcap.json"
    net_models.save_config(path, config)
    assert net_models.load_config(path) == config
    assert net_models.load_config(tmp_path / "yoq.json") == net_models.NetConfig()
    options = config.worker_options("Ethernet")
    assert engine_mod.Options.from_json(options).excluded == {"10.0.0.1", "2001:db8::1"}


def test_store_keeps_newest_rows_and_filters(tmp_path: Path) -> None:
    store = net_store.NetStore(tmp_path / "netcap.db")
    packets = [
        {"ts": float(i), "proto": "TCP" if i % 2 else "UDP", "src": "10.0.0.5", "sport": 1000 + i,
         "dst": f"10.0.0.{i}", "dport": 80, "len": 60, "info": "[S]", "mark": ""}
        for i in range(10)
    ]  # fmt: skip
    alert = {"ts": 1.0, "kind": "port", "src": "10.0.0.5", "dst": "10.0.0.9", "note": "TCP :23"}
    store.add(packets, [alert] * 5, keep_packets=6, keep_alerts=3)
    assert store.counts() == (6, 3)
    rows = store.packets(100)
    assert [row["ts"] for row in rows] == [9.0, 8.0, 7.0, 6.0, 5.0, 4.0]
    assert rows[0]["src"] == "10.0.0.5:1009" and rows[0]["dst"] == "10.0.0.9:80"
    assert rows[0]["payload"] == ""
    assert [row["ts"] for row in store.packets(100, ip="10.0.0.8")] == [8.0]
    assert [row["ts"] for row in store.packets(100, proto="udp")] == [8.0, 6.0, 4.0]
    assert len(store.packets(2)) == 2
    v6 = {"ts": 20.0, "proto": "ICMPv6", "src": "fe80::1", "dst": "ff02::1", "len": 70}
    store.add([v6, {"ts": "buzuq", "sport": True}], [], 6, 3)  # buzuq qiymatlar yiqitmaydi
    assert store.packets(1, ip="fe80::1")[0]["src"] == "fe80::1"
    assert store.alerts(10)[0]["note"] == "TCP :23" and store.size() > 0
    assert store.clear() == (6, 3) and store.counts() == (0, 0)
    store.close()


# --- xizmat: soxta ishchi bilan to'liq sikl ---------------------------------------------
@pytest.fixture
def fake_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Npcap va tarmoqsiz: ishchi o'rniga oldindan ma'lum natija beradigan skript."""
    monkeypatch.setenv("SRV1_NETCAP_WORKER", str(write_fake_worker(tmp_path)))
    present = tmp_path / "wpcap.dll"
    present.write_bytes(b"")
    monkeypatch.setenv("SRV1_NPCAP_DLL", str(present))
    return present


async def _status(client: httpx.AsyncClient) -> dict[str, Any]:
    return (await client.get(f"{API}/status")).json()


async def _wait(client: httpx.AsyncClient, **expected: Any) -> dict[str, Any]:  # noqa: ANN401
    status: dict[str, Any] = {}
    for _ in range(200):
        status = await _status(client)
        if all(status.get(key) == value for key, value in expected.items()):
            return status
        await asyncio.sleep(0.05)
    pytest.fail(f"kutilgan holat kelmadi: {expected} != {status}")


async def _interface(client: httpx.AsyncClient, address: str = "") -> str:
    rows = (await client.get(f"{API}/interfaces")).json()
    assert rows, "bu mashinada yoqilgan tarmoq interfeysi yo'q"
    for row in rows:
        if row["address"] == address:
            return str(row["name"])
    return str(rows[0]["name"])


def _audit(paths: DataPaths) -> list[tuple[str, int]]:
    """`monitor` plagini yozgan audit yozuvlari: `(amal, ok)`."""
    db = sqlite3.connect(paths.db_file)
    try:
        rows = db.execute("SELECT actor, action, ok FROM audit_log ORDER BY id").fetchall()
    finally:
        db.close()
    return [(action, ok) for actor, action, ok in rows if actor == "plugin:monitor"]


@pytest.mark.parametrize("mode", ["inprocess", "subprocess"])
async def test_capture_full_cycle_with_fake_worker(
    paths: DataPaths, plugin_root: Path, fake_worker: Path, mode: str
) -> None:
    install_monitor(plugin_root, paths.plugin_data_dir("monitor"), mode)
    async with serve_app(paths) as served, served.client() as client:
        idle = await _status(client)
        assert (idle["state"], idle["npcap"], idle["worker_mb"]) == ("stopped", True, 0)
        assert (idle["store_payload"], idle["geo"]) == ("off", "off")
        summary = (await client.get(f"{API}/summary")).json()
        assert summary == [
            {
                "state": "stopped",
                "interface": "",
                "npcap": "ok",
                "store_payload": "off",
                "geo": "off",
                "error": "",
            }
        ]
        assert (await client.post(f"{API}/pause")).status_code == 409
        assert (
            await client.post(f"{API}/start", json={"name": "yo'q interfeys"})
        ).status_code == 404
        name = await _interface(client)

        started = await client.post(f"{API}/start", json={"name": name}, timeout=30)
        assert started.status_code == 200, started.text
        assert (started.json()["state"], started.json()["interface"]) == ("running", name)
        assert (await client.post(f"{API}/start", json={"name": name})).status_code == 409
        status = await _wait(client, total=2, stored_packets=2)
        assert status["worker_mb"] > 0 and status["stored_alerts"] == 1
        assert [r["capturing"] for r in (await client.get(f"{API}/interfaces")).json()].count(
            "●"
        ) == 1

        rows = (await client.get(f"{API}/packets")).json()
        assert {row["proto"] for row in rows} == {"TCP", "UDP"}
        marked = next(row for row in rows if row["mark"])
        assert (marked["src"], marked["dst"], marked["payload"]) == (
            "10.0.0.5:50000",
            "10.0.0.9:80",
            "",
        )
        assert len((await client.get(f"{API}/packets", params={"proto": "udp"})).json()) == 1
        assert len((await client.get(f"{API}/packets", params={"ip": "8.8.8.8"})).json()) == 1
        assert (await client.get(f"{API}/packets", params={"ip": "yaroqsiz"})).status_code == 422
        alerts = (await client.get(f"{API}/alerts")).json()
        assert [(a["kind"], a["src"]) for a in alerts] == [("secret", "10.0.0.5")]
        assert (await client.get(f"{API}/hosts")).json()[0]["ip"] == "10.0.0.5"

        # pauza / davom: buyruq ishchiga yetadi va holat tick orqali tasdiqlanadi
        assert (await client.post(f"{API}/pause")).json()["state"] == "paused"
        await asyncio.sleep(0.3)
        assert (await _status(client))["state"] == "paused"
        assert (await client.post(f"{API}/resume")).json()["state"] == "running"

        # chiqarilgan manzillar: saqlanadi va ishlab turgan ishchiga darhol yuboriladi
        added = await client.post(f"{API}/exclude", json={"ips": "10.0.0.9, 2001:DB8::1"})
        assert added.json() == [{"ip": "10.0.0.9"}, {"ip": "2001:db8::1"}]
        await _wait(client, ignored=2)  # soxta ishchi ro'yxat uzunligini qaytaradi
        assert (await client.post(f"{API}/exclude", json={"ips": "10.0.0.300"})).status_code == 422
        assert (await client.post(f"{API}/unexclude", json={"ip": "1.1.1.1"})).status_code == 404
        left = await client.post(f"{API}/unexclude", json={"ip": "2001:db8::1"})
        assert left.json() == [{"ip": "10.0.0.9"}]
        await _wait(client, ignored=1, excluded=1)

        # sozlama o'zgarsa, ushlash yangi sozlama bilan qayta boshlanadi
        changed = await client.post(
            f"{API}/settings",
            json={"store_payload": "on", "suspicious_ports": "23, 8080", "scan_ports": 20},
            timeout=30,
        )
        assert changed.status_code == 200, changed.text
        assert (changed.json()["store_payload"], changed.json()["suspicious_ports"]) == (
            True,
            "23, 8080",
        )
        await _wait(client, state="running", stored_packets=4, store_payload="on")
        payloads = {row["payload"] for row in (await client.get(f"{API}/packets")).json()}
        assert payloads == {"", "password=..."}
        for bad in ({"bpf_filter": "a;b"}, {"scan_ports": 1}, {"geo": "ha"}, {"nomalum": 1}):
            assert (await client.post(f"{API}/settings", json=bad)).status_code == 422

        stopped = await client.post(f"{API}/stop", timeout=30)
        assert (stopped.json()["state"], stopped.json()["worker_mb"]) == ("stopped", 0)
        assert (await client.post(f"{API}/stop")).json()["state"] == "stopped"  # takror — xatosiz
        cleared = await client.delete(f"{API}/data")
        assert cleared.json() == {"packets": 4, "alerts": 2}
        assert (await _status(client))["stored_packets"] == 0

        # sozlama diskda: qayta ishga tushganda ham shu
        saved = net_models.load_config(paths.plugin_data_dir("monitor") / "netcap.json")
        assert (saved.interface, saved.excluded, saved.store_payload) == (name, ("10.0.0.9",), True)
        actions = _audit(paths)
    assert actions.count(("process.spawn", 1)) == 2
    assert actions.count(("net.capture_start", 1)) == 2
    assert ("net.payload_store", 1) in actions
    assert ("net.capture_stop", 1) in actions and ("net.data_clear", 1) in actions


async def test_worker_failure_is_reported_not_hidden(
    paths: DataPaths, plugin_root: Path, fake_worker: Path
) -> None:
    install_monitor(plugin_root, paths.plugin_data_dir("monitor"))
    async with serve_app(paths) as served, served.client() as client:
        name = await _interface(client)
        # 1) ishchi boshlanmay turib xato bilan chiqdi: javobda sabab ko'rinadi
        assert (
            await client.post(f"{API}/settings", json={"bpf_filter": "crash"})
        ).status_code == 200
        failed = await client.post(f"{API}/start", json={"name": name}, timeout=30)
        assert failed.status_code == 502
        assert "soxta xato: interfeys ochilmadi" in failed.json()["detail"]
        status = await _status(client)
        assert (status["state"], status["worker_mb"]) == ("error", 0)
        assert "interfeys ochilmadi" in status["error"]
        # 2) ishchi ishlab turib o'ldi: holat `error`, keyin qayta boshlash mumkin
        await client.post(f"{API}/settings", json={"bpf_filter": "die"})
        assert (
            await client.post(f"{API}/start", json={"name": name}, timeout=30)
        ).status_code == 200
        status = await _wait(client, state="error")
        assert "kod 7" in status["error"]
        await client.post(f"{API}/settings", json={"bpf_filter": ""})
        again = await client.post(f"{API}/start", json={"name": name}, timeout=30)
        assert again.json()["state"] == "running"
        # 3) plagin o'chirilsa, ishchi ham to'xtaydi
        assert _audit(paths).count(("process.spawn", 1)) == 3
        disabled = await client.post("/api/v1/plugins/monitor/disable", timeout=30)
        assert disabled.json()["status"] == "stopped"
        actions = _audit(paths)
    assert ("net.capture_start", 0) in actions and ("net.capture_stop", 0) in actions
    assert actions[-1] == ("net.capture_stop", 1)


async def test_missing_npcap_is_explained(
    paths: DataPaths, plugin_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SRV1_NPCAP_DLL", str(tmp_path / "yoq" / "wpcap.dll"))
    install_monitor(plugin_root, paths.plugin_data_dir("monitor"))
    async with serve_app(paths) as served, served.client() as client:
        assert (await _status(client))["npcap"] is False
        reply = await client.post(f"{API}/start", json={"name": await _interface(client)})
        assert reply.status_code == 409 and "Npcap" in reply.json()["detail"]
        assert _audit(paths) == []  # hech narsa ishga tushirilmadi


# --- haqiqiy ushlash: Npcap bilan loopback ----------------------------------------------
@pytest.mark.skipif(not NPCAP, reason="Npcap o'rnatilmagan")
async def test_real_capture_on_loopback(paths: DataPaths, plugin_root: Path) -> None:
    """Haqiqiy ishchi, haqiqiy scapy va Npcap: 127.0.0.1 ga yuborilgan paketlar ushlanadi."""
    install_monitor(plugin_root, paths.plugin_data_dir("monitor"))
    async with serve_app(paths) as served, served.client() as client:
        name = await _interface(client, "127.0.0.1")
        addresses = {
            row["name"]: row["address"] for row in (await client.get(f"{API}/interfaces")).json()
        }
        if addresses[name] != "127.0.0.1":
            pytest.skip("loopback interfeysi topilmadi")
        await client.post(f"{API}/settings", json={"bpf_filter": "udp port 47999"})
        started = await client.post(f"{API}/start", json={"name": name}, timeout=40)
        assert started.status_code == 200, started.text
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            status: dict[str, Any] = {}
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                sender.sendto(b"login=ali&password=hunter2", ("127.0.0.1", 47999))
                status = await _status(client)
                if status["stored_packets"] >= 1 and status["stored_alerts"] >= 1:
                    break
                await asyncio.sleep(0.2)
            else:
                pytest.fail(f"loopback paketlari ushlanmadi: {status}")
        finally:
            sender.close()
        assert status["state"] == "running" and status["errors"] == 0
        assert 20 < status["worker_mb"] < 200
        rows = (await client.get(f"{API}/packets", params={"proto": "UDP"})).json()
        assert rows and all(row["dst"] == "127.0.0.1:47999" for row in rows)
        # standart holat: sir belgilanadi, lekin matni hech qayerga yozilmaydi
        assert {row["mark"] for row in rows} == {"password"}
        assert {row["payload"] for row in rows} == {""}
        alerts = (await client.get(f"{API}/alerts")).json()
        assert alerts[0]["kind"] == "secret" and "hunter2" not in str(alerts)
        assert (await client.post(f"{API}/stop", timeout=30)).json()["state"] == "stopped"
        database = (paths.plugin_data_dir("monitor") / "netcap.db").read_bytes()
        assert b"hunter2" not in database
    assert os.environ.get("SRV1_NETCAP_WORKER") is None
