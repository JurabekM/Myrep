"""NetMonitor testlari. Ushlash drayveri kerak emas: paketlar scapy bilan yasaladi."""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from scapy.layers.dns import DNS, DNSQR
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import Ether
from scapy.packet import Raw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import netmonitor as nm  # noqa: E402

ESC = "\x1b"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def printed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    lines: list[str] = []
    monkeypatch.setattr(nm.console, "write", lambda text="": lines.append(text))
    return lines


@pytest.fixture
def clock() -> Clock:
    return Clock()


def make_processor(
    tmp_path: Path, clock: Clock, config: dict[str, Any] | None = None, geo: Any = None
) -> nm.PacketProcessor:
    settings = copy.deepcopy(nm.DEFAULT_CONFIG)
    settings["console"]["max_lines_per_sec"] = 0
    for key, value in (config or {}).items():
        if isinstance(value, dict):
            settings[key].update(value)
        else:
            settings[key] = value
    state = nm.MonitorState(tmp_path / "state.json")
    packet_log = nm.PacketLog(tmp_path, "packets.json", 1000, 5)
    return nm.PacketProcessor(settings, state, packet_log, geo, clock)


def read_log(processor: nm.PacketProcessor) -> list[dict[str, Any]]:
    processor.packet_log.flush()
    return [json.loads(line) for line in processor.packet_log.path.read_text(encoding="utf-8").splitlines()]


def tcp(src: str, dst: str, dport: int, flags: str | int = "PA", payload: bytes = b"", sport: int = 40000) -> Any:
    packet = Ether() / IP(src=src, dst=dst) / TCP(sport=sport, dport=dport, flags=flags)
    return Ether(bytes(packet / Raw(payload) if payload else packet))


# --- Paket matnini tozalash -------------------------------------------------


def test_sanitize_escapes_control_bytes_and_backslash() -> None:
    assert nm.sanitize_bytes(b"a\x1b[31m\x07\x00\t\r\n~") == "a\\x1b[31m\\x07\\x00\\t\\r\\n~"
    # Matndagi `\x41` yozuvi haqiqiy 0x41 baytidan farqlanadi.
    assert nm.sanitize_bytes(b"\\x41") == "\\\\x41"
    assert nm.sanitize_bytes(b"A") == "A"


def test_sanitize_keeps_readable_utf8_but_not_format_characters() -> None:
    text = "Salom, дунё".encode()
    assert nm.is_utf8_text(text)
    assert nm.sanitize_text(text, True) == "Salom, дунё"
    # Yo'nalishni o'zgartiruvchi belgi (U+202E) va C1 boshqaruv belgisi ko'rinmas holda o'tmaydi.
    hidden = "a‮b\u0085".encode()
    assert nm.sanitize_text(hidden, True) == "a\\xe2\\x80\\xaeb\\xc2\\x85"
    assert not nm.is_utf8_text(b"\xff\xfe\x00binary")
    assert not nm.is_utf8_text(b"plain ascii")


def test_sanitize_text_handles_cut_multibyte_character() -> None:
    cut = "ж".encode()[:1]
    assert nm.sanitize_text(b"a" + cut, True) == "a\\xd0"


# --- Maxfiy maydonlarni topish ------------------------------------------------


@pytest.fixture
def scanner() -> nm.PayloadScanner:
    return nm.PayloadScanner(nm.DEFAULT_SENSITIVE_KEYWORDS, ["cmd.exe"])


@pytest.mark.parametrize(
    "payload",
    [
        b"GET / HTTP/1.1\r\nUser-Agent: Mozilla\r\nConnection: keep-alive\r\n\r\n",
        b"keyboard layout, monkey business, bypass the queue",
        b"Cache-Control: private\r\nContent-Type: text/html\r\n",
        b"compass=north&passenger=2",
    ],
)
def test_ordinary_words_are_not_flagged(scanner: nm.PayloadScanner, payload: bytes) -> None:
    assert scanner.scan(payload).names == ()


@pytest.mark.parametrize(
    ("payload", "names"),
    [
        (b"username=ali&password=sir", ("username", "password")),
        (b"PassWord = 'sir'", ("password",)),
        (b'{"token": "abc", "id": 1}', ("token",)),
        (b"Authorization: Basic YWxpOnNpcg==\r\n", ("authorization",)),
        (b"Set-Cookie: sid=1\r\n", ("cookie",)),
        (b"220 ready\r\nUSER ali\r\nPASS sir\r\n", ("user", "pass")),
        (b"api_key=XYZ", ("key",)),
    ],
)
def test_assignments_are_flagged(scanner: nm.PayloadScanner, payload: bytes, names: tuple[str, ...]) -> None:
    assert scanner.scan(payload).names == names


def test_tls_records_are_not_scanned(scanner: nm.PayloadScanner) -> None:
    assert scanner.scan(b"\x17\x03\x03\x00\x20password=sir").names == ()


def test_signature_from_config_is_reported(scanner: nm.PayloadScanner) -> None:
    assert scanner.scan(b"GET /a?x=CMD.EXE /c dir").signature == "cmd.exe"


def test_render_masks_values_and_highlights_names(scanner: nm.PayloadScanner) -> None:
    raw = b"user=ali&PassWord=Sir123&x=1\r\nAuthorization: Bearer abc.def\r\n"
    findings = scanner.scan(raw)
    masked = nm.render_payload(raw, findings, 500, color=False, mask=True)
    assert masked == "user=********&PassWord=********&x=1\\r\\nAuthorization: ********\\r\\n"
    shown = nm.render_payload(raw, findings, 500, color=False, mask=False)
    assert "Sir123" in shown and "Bearer abc.def" in shown
    colored = nm.render_payload(raw, findings, 500, color=True, mask=True)
    assert "Sir123" not in colored and "PassWord" in colored


def test_render_truncates_and_never_emits_raw_control_bytes(scanner: nm.PayloadScanner) -> None:
    raw = b"\x1b[2J" + b"A" * 300 + b" password=sir"
    findings = scanner.scan(raw)
    text = nm.render_payload(raw, findings, 150, color=False, mask=True)
    assert text.startswith("\\x1b[2J") and text.endswith("...")
    assert ESC not in text
    # Kesilgan qismdan keyingi maxfiy maydon baribir topiladi (signal uchun).
    assert findings.names == ("password",)


# --- Pauza va chiqarilgan manzillar -------------------------------------------


def test_exclude_accepts_ipv4_ipv6_and_networks(tmp_path: Path) -> None:
    state = nm.MonitorState(tmp_path / "state.json")
    assert state.exclude("192.168.1.5") == "added"
    assert state.exclude(" 192.168.1.5 ") == "exists"
    assert state.exclude("10.0.0.0/8") == "added"
    assert state.exclude("fe80::1") == "added"
    assert state.exclude("01.1.1.1") == "invalid"  # boshida nol: paketdagi yozuvga hech qachon mos kelmaydi
    assert state.exclude("999.1.1.1") == "invalid"
    assert state.exclude("salom") == "invalid"
    assert state.is_excluded("192.168.1.5")
    assert state.is_excluded("10.20.30.40")
    assert state.is_excluded("fe80:0:0:0:0:0:0:1")
    assert not state.is_excluded("192.168.1.6")
    assert not state.is_excluded("fe80::2")
    assert state.unexclude("10.0.0.0/8") == "removed"
    assert state.unexclude("10.0.0.0/8") == "missing"
    assert not state.is_excluded("10.20.30.40")


def test_excluded_list_survives_restart(tmp_path: Path) -> None:
    first = nm.MonitorState(tmp_path / "state.json")
    first.exclude("192.168.1.5")
    first.exclude("172.16.0.0/12")
    assert first.save()
    second = nm.MonitorState(tmp_path / "state.json")
    assert second.load() == 2
    assert second.excluded() == ["172.16.0.0/12", "192.168.1.5"]
    assert second.is_excluded("172.20.1.1")


def test_broken_state_file_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "state.json").write_text("{not json", encoding="utf-8")
    assert nm.MonitorState(tmp_path / "state.json").load() == 0


# --- Geolokatsiya ---------------------------------------------------------------


def test_only_public_addresses_are_looked_up() -> None:
    assert nm.is_public("8.8.8.8")
    assert nm.is_public("172.32.0.1")  # 172.16.0.0/12 dan tashqarida: ommaviy
    for address in ("172.16.5.1", "192.168.1.1", "10.1.1.1", "127.0.0.1", "169.254.1.1", "224.0.0.251",
                    "255.255.255.255", "0.0.0.0", "fe80::1", "ff02::fb", "yaroqsiz"):
        assert not nm.is_public(address), address
    assert nm.is_private("172.16.5.1") and not nm.is_private("172.32.0.1")


def test_lookup_never_blocks_and_caches_failures(clock: Clock) -> None:
    calls: list[str] = []
    answers: dict[str, nm.GeoInfo | None] = {"8.8.8.8": {"country": "US", "city": "", "isp": "Google"}, "1.2.3.4": None}

    def fetch(ip: str) -> nm.GeoInfo | None:
        calls.append(ip)
        return answers[ip]

    geo = nm.GeoResolver(fetch=fetch, clock=clock)
    assert geo.lookup("8.8.8.8") is None  # hali so'ralmagan: kutmaydi
    assert geo.lookup("8.8.8.8") is None
    assert geo.lookup("1.2.3.4") is None
    assert calls == []
    assert geo.lookup("192.168.1.1") == nm.GEO_PRIVATE
    assert geo.lookup("224.0.0.251") is None
    assert geo.resolve_one() == nm.GEO_MIN_INTERVAL_S
    assert geo.resolve_one() == nm.GEO_MIN_INTERVAL_S
    assert geo.resolve_one() is None
    assert calls == ["8.8.8.8", "1.2.3.4"]  # takroriy so'rov navbatga ikki marta tushmadi
    assert geo.lookup("8.8.8.8") == answers["8.8.8.8"]
    # Muvaffaqiyatsiz natija ham keshlanadi: har paketda qayta so'ralmaydi.
    assert geo.lookup("1.2.3.4") is None
    assert geo.resolve_one() is None
    clock.now += nm.GEO_FAIL_TTL_S + 1
    assert geo.lookup("1.2.3.4") is None
    assert geo.resolve_one() is not None
    assert calls == ["8.8.8.8", "1.2.3.4", "1.2.3.4"]


def test_rate_limit_pauses_requests(clock: Clock) -> None:
    def fetch(ip: str) -> nm.GeoInfo | None:
        raise nm.GeoRateLimited

    geo = nm.GeoResolver(fetch=fetch, clock=clock)
    geo.lookup("8.8.4.4")
    assert geo.resolve_one() == nm.GEO_RATE_LIMIT_PAUSE_S
    assert geo.rate_limited == 1


def test_geo_cache_is_bounded(clock: Clock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nm, "GEO_CACHE_SIZE", 3)
    geo = nm.GeoResolver(fetch=lambda ip: None, clock=clock)
    for last in range(1, 8):
        geo.lookup(f"8.8.8.{last}")
        geo.resolve_one()
    assert len(geo._cache) == 3


# --- Xavf tekshiruvlari -------------------------------------------------------


def make_detector(clock: Clock, **overrides: Any) -> nm.Detector:
    settings = dict(nm.DEFAULT_CONFIG["security_monitoring"])
    settings.update(overrides)
    return nm.Detector(settings, clock)


def kinds(alerts: list[nm.Alert]) -> list[str]:
    return [alert.kind for alert in alerts]


def test_port_scan_counts_only_new_connection_attempts(clock: Clock) -> None:
    detector = make_detector(clock)
    # Serverdan qaytgan javoblar: har xil o'tkinchi portlarga, lekin SYN emas — skanerlash emas.
    for port in range(100):
        assert detector.check("TCP", "93.184.216.34", "192.168.1.10", 50000 + port, "SA", nm.NO_FINDINGS) == []
        assert detector.check("TCP", "93.184.216.34", "192.168.1.10", 50000 + port, "PA", nm.NO_FINDINGS) == []
        assert detector.check("UDP", "8.8.8.8", "192.168.1.10", 50000 + port, "", nm.NO_FINDINGS) == []
    found: list[str] = []
    for port in range(16):
        found += kinds(detector.check("TCP", "10.7.7.7", "192.168.1.10", 1000 + port, "S", nm.NO_FINDINGS))
    assert found == ["port_scan"]


def test_port_scan_window_is_fixed_and_per_destination(clock: Clock) -> None:
    detector = make_detector(clock)
    # Sekin skan: har porti orasida 1 s — oyna (10 s) boshidan sanaladi, cheksiz cho'zilmaydi.
    for port in range(40):
        assert detector.check("TCP", "10.7.7.7", "192.168.1.10", 1000 + port, "S", nm.NO_FINDINGS) == []
        clock.now += 1.0
    # Har xil manzillarga bittadan port — skanerlash emas.
    for host in range(40):
        assert detector.check("TCP", "10.7.7.7", f"192.168.2.{host}", 80, "S", nm.NO_FINDINGS) == []


def test_scan_tables_are_bounded(clock: Clock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nm, "MAX_TRACKED", 50)
    detector = make_detector(clock, alert_quiet_sec=0)
    for index in range(500):
        detector.check("TCP", f"10.0.{index // 250}.{index % 250}", "192.168.1.10", 23, "S", nm.NO_FINDINGS)
    assert len(detector._scans) <= 50
    assert len(detector._last) <= 50


def test_flag_scans_and_repeat_suppression(clock: Clock) -> None:
    detector = make_detector(clock)
    assert kinds(detector.check("TCP", "10.9.9.9", "192.168.1.10", 22, "", nm.NO_FINDINGS)) == ["null_scan"]
    assert kinds(detector.check("TCP", "10.9.9.9", "192.168.1.10", 22, "F", nm.NO_FINDINGS)) == ["fin_scan"]
    assert kinds(detector.check("TCP", "10.9.9.9", "192.168.1.10", 22, "FPU", nm.NO_FINDINGS)) == ["xmas_scan"]
    assert detector.check("TCP", "10.9.9.9", "192.168.1.10", 22, "", nm.NO_FINDINGS) == []
    assert detector.suppressed == 1
    clock.now += 61
    assert kinds(detector.check("TCP", "10.9.9.9", "192.168.1.10", 22, "", nm.NO_FINDINGS)) == ["null_scan"]


def test_suspicious_port_accepts_strings_from_config(clock: Clock) -> None:
    detector = make_detector(clock, suspicious_ports=["4444", 23, "noto'g'ri", None])
    assert kinds(detector.check("TCP", "10.1.1.1", "192.168.1.10", 4444, "S", nm.NO_FINDINGS)) == ["port"]
    assert kinds(detector.check("UDP", "10.1.1.2", "192.168.1.10", 23, "", nm.NO_FINDINGS)) == ["port"]
    # Mavjud ulanish ichidagi paket va manba porti hisobga olinmaydi.
    assert detector.check("TCP", "10.1.1.3", "192.168.1.10", 4444, "PA", nm.NO_FINDINGS) == []


def test_disabled_checks_stay_silent(clock: Clock) -> None:
    detector = nm.Detector({}, clock)
    findings = nm.Findings(names=("password",), signature="cmd.exe")
    assert detector.check("TCP", "10.1.1.1", "192.168.1.10", 23, "", findings) == []


# --- Paketlar jurnali ---------------------------------------------------------


def test_rotation_twice_in_one_second_keeps_every_line(tmp_path: Path) -> None:
    log = nm.PacketLog(tmp_path, "packets.json", 3, 10)
    for index in range(10):
        log.write({"n": index})
    log.close()
    archives = sorted(tmp_path.glob("packets_*.json"))
    assert len(archives) == 3
    lines = [line for path in [*archives, log.path] for line in path.read_text(encoding="utf-8").splitlines()]
    assert sorted(json.loads(line)["n"] for line in lines) == list(range(10))


def test_old_archives_are_pruned(tmp_path: Path) -> None:
    log = nm.PacketLog(tmp_path, "packets.json", 1, 2)
    for index in range(8):
        log.write({"n": index})
    log.close()
    assert len(list(tmp_path.glob("packets_*.json"))) == 2


def test_existing_file_line_count_is_continued(tmp_path: Path) -> None:
    (tmp_path / "packets.json").write_text('{"n": 0}\n{"n": 1}\n', encoding="utf-8")
    log = nm.PacketLog(tmp_path, "packets.json", 3, 5)
    assert log.line_count == 2
    log.write({"n": 2})
    log.write({"n": 3})
    log.close()
    assert len(list(tmp_path.glob("packets_*.json"))) == 1


def test_failed_rotation_does_not_retry_on_every_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    log = nm.PacketLog(tmp_path, "packets.json", 2, 5)
    attempts: list[int] = []

    def refuse(source: Any, target: Any) -> None:
        attempts.append(1)
        raise PermissionError("band")

    monkeypatch.setattr(os, "rename", refuse)
    with caplog.at_level(logging.ERROR):
        for index in range(60):
            log.write({"n": index})
    log.close()
    assert len(attempts) == 1  # keyingi urinish 100 satrdan keyin
    assert len(log.path.read_text(encoding="utf-8").splitlines()) == 60
    assert sum("Rotatsiya xatosi" in record.getMessage() for record in caplog.records) == 1


# --- Paketlarni qayta ishlash -------------------------------------------------


def test_broken_packet_does_not_stop_capture(
    tmp_path: Path, clock: Clock, printed: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    processor = make_processor(tmp_path, clock)
    with caplog.at_level(logging.ERROR):
        for _ in range(5):
            processor.process_packet(object())  # istisno tashqariga chiqmaydi
    processor.process_packet(tcp("192.168.1.10", "192.168.1.1", 80))
    assert processor.stats.errors == 5
    assert processor.stats.processed == 1
    # Xato har paketda emas, oraliq bilan yoziladi.
    assert sum("Paketni qayta ishlashda xato" in record.getMessage() for record in caplog.records) == 1


def test_dns_name_is_sanitized(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    processor = make_processor(tmp_path, clock)
    packet = Ether() / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=40000, dport=53)
    packet /= DNS(rd=1, qd=DNSQR(qname="evil\x1b[31m.example.com"))
    processor.process_packet(Ether(bytes(packet)))
    output = "\n".join(printed)
    assert "DNS: evil\\x1b[31m.example.com." in output
    assert "evil\x1b" not in output
    assert read_log(processor)[0]["application"]["query"] == "evil\\x1b[31m.example.com."


def test_summary_has_no_double_separator(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    processor = make_processor(tmp_path, clock)
    processor.process_packet(tcp("192.168.1.10", "192.168.1.1", 80, "S"))
    assert "| |" not in printed[0]
    assert "192.168.1.10:40000" in printed[0] and "192.168.1.1:80" in printed[0]
    assert " | MAC: " in printed[0]


def test_excluded_address_is_dropped_before_geolocation(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    asked: list[str] = []

    class Geo:
        service_ips = frozenset({"208.95.112.1"})

        def lookup(self, ip: str) -> None:
            asked.append(ip)

    processor = make_processor(tmp_path, clock, geo=Geo())
    processor.state.exclude("8.8.8.8")
    processor.process_packet(tcp("192.168.1.10", "8.8.8.8", 443))
    processor.process_packet(tcp("8.8.8.8", "192.168.1.10", 50000, sport=443))
    assert asked == [] and printed == []
    assert processor.stats.excluded == 2
    # Geolokatsiya xizmatiga ketgan o'z so'rovlarimiz kuzatuvga tushmaydi.
    processor.process_packet(tcp("192.168.1.10", "208.95.112.1", 80))
    assert asked == [] and processor.stats.geo_self == 1
    processor.process_packet(tcp("192.168.1.10", "1.1.1.1", 443))
    assert asked == ["192.168.1.10", "1.1.1.1"]


def test_pause_and_quiet(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    processor = make_processor(tmp_path, clock)
    processor.state.pause()
    processor.process_packet(tcp("192.168.1.10", "192.168.1.1", 80))
    assert processor.stats.paused == 1 and printed == []
    processor.state.resume()
    processor.state.show_packets = False
    processor.process_packet(tcp("192.168.1.10", "192.168.1.1", 80))
    assert printed == []
    assert len(read_log(processor)) == 1  # konsol jim, fayl jurnali davom etadi


def test_ipv6_packets_are_processed(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    processor = make_processor(tmp_path, clock)
    packet = Ether() / IPv6(src="2001:db8::1", dst="2001:db8::2") / TCP(sport=40000, dport=443, flags="S")
    processor.process_packet(Ether(bytes(packet)))
    record = read_log(processor)[0]
    assert record["ip"]["version"] == 6
    assert "[2001:db8::1]:40000" in printed[0]
    processor.state.exclude("2001:db8::/32")
    processor.process_packet(Ether(bytes(packet)))
    assert processor.stats.excluded == 1


def test_payload_is_masked_in_console_and_log(
    tmp_path: Path, clock: Clock, printed: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    processor = make_processor(tmp_path, clock)
    body = b"POST /login HTTP/1.1\r\nUser-Agent: x\r\n\r\nusername=ali&password=Sir12345"
    with caplog.at_level(logging.WARNING):
        processor.process_packet(tcp("192.168.1.10", "93.184.216.34", 80, payload=body))
    record = read_log(processor)[0]
    assert "Sir12345" not in json.dumps(record) and "Sir12345" not in "\n".join(printed)
    assert record["payload"]["sensitive"] == ["username", "password"]
    assert record["payload"]["size"] == len(body)
    assert "XAVFLI PAYLOAD" in printed[0]
    messages = [item.getMessage() for item in caplog.records]
    assert any("Ochiq matnda maxfiy maydon (username, password)" in message for message in messages)
    assert not any("Sir12345" in message for message in messages)


def test_masking_can_be_turned_off(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    processor = make_processor(tmp_path, clock, {"payload": {"mask_sensitive_values": False}})
    processor.process_packet(tcp("192.168.1.10", "93.184.216.34", 80, payload=b"password=Sir12345"))
    assert "Sir12345" in read_log(processor)[0]["payload"]["raw"]


def test_payload_text_can_be_kept_out_of_the_log(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    processor = make_processor(tmp_path, clock, {"payload": {"log_max_bytes": 0}})
    processor.process_packet(tcp("192.168.1.10", "93.184.216.34", 80, payload=b"salom dunyo"))
    assert read_log(processor)[0]["payload"] == {"raw": "", "size": 11}


def test_console_rate_limit_keeps_important_lines(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    processor = make_processor(tmp_path, clock, {"console": {"max_lines_per_sec": 3}})
    for _ in range(10):
        processor.process_packet(tcp("192.168.1.10", "192.168.1.1", 80))
    assert len(printed) == 3 and processor.stats.console_skipped == 7
    processor.process_packet(tcp("192.168.1.10", "192.168.1.1", 80, payload=b"password=sir"))
    assert len(printed) == 4  # maxfiy maydonli paket chegaradan qat'i nazar chiqadi
    clock.now += 1.0
    processor.process_packet(tcp("192.168.1.10", "192.168.1.1", 80))
    assert len(printed) == 5
    assert len(read_log(processor)) == 12  # faylga hammasi yoziladi


def test_non_ip_frames_are_counted(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    processor = make_processor(tmp_path, clock)
    processor.process_packet(Ether(bytes(Ether(type=0x0806) / Raw(b"\x00" * 28))))
    assert processor.stats.non_ip == 1 and processor.stats.errors == 0


# --- Buyruqlar ----------------------------------------------------------------


def test_commands(tmp_path: Path, clock: Clock, printed: list[str]) -> None:
    processor = make_processor(tmp_path, clock)
    handler = nm.CommandHandler(processor.state, processor)
    assert handler.handle("PAUSE")
    assert not processor.state.active
    assert handler.handle("resume")
    assert processor.state.active
    assert handler.handle("exclude 192.168.1.5, 10.0.0.0/8 , 01.1.1.1")
    assert processor.state.excluded() == ["10.0.0.0/8", "192.168.1.5"]
    assert any("Noto'g'ri manzil: '01.1.1.1'" in line for line in printed)
    assert json.loads((tmp_path / "state.json").read_text(encoding="utf-8")) == {
        "excluded": ["10.0.0.0/8", "192.168.1.5"]
    }
    assert handler.handle("unexclude 192.168.1.5")
    assert processor.state.excluded() == ["10.0.0.0/8"]
    assert handler.handle("quiet") and not processor.state.show_packets
    assert handler.handle("verbose") and processor.state.show_packets
    for command in ("list", "status", "help", "", "   "):
        assert handler.handle(command)
    assert handler.handle("bogus\x1b[2J")
    assert ESC + "[2J" not in "\n".join(printed)
    assert not handler.handle("exit")
    assert not handler.handle("quit")


# --- Sozlamalar ---------------------------------------------------------------


def test_config_is_merged_over_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        '﻿{"log_folder": "x", "security_monitoring": {"port_scan_threshold_ports": 30}}', encoding="utf-8"
    )
    config = nm.load_config(path)
    assert config["log_folder"] == "x"
    assert config["security_monitoring"]["port_scan_threshold_ports"] == 30
    assert config["security_monitoring"]["suspicious_ports_enabled"] is True
    assert config["payload"]["mask_sensitive_values"] is True
    assert nm.load_config(tmp_path / "yoq.json") == nm.DEFAULT_CONFIG


@pytest.mark.parametrize("content", ["{broken", "[1, 2]"])
def test_bad_config_is_reported(tmp_path: Path, content: str) -> None:
    path = tmp_path / "config.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(nm.ConfigError):
        nm.load_config(path)


def test_wrong_types_in_config_fall_back_to_defaults(tmp_path: Path, clock: Clock) -> None:
    processor = make_processor(
        tmp_path, clock, {"console": {"max_lines_per_sec": "ko'p", "payload_preview_bytes": -5}}
    )
    assert processor.max_lines_per_sec == 50
    assert processor.preview_bytes == 150
    detector = make_detector(clock, port_scan_threshold_ports="x", port_scan_time_window_sec=True)
    assert detector.scan_threshold == 15 and detector.scan_window_s == 10.0


def test_example_config_matches_defaults() -> None:
    example = json.loads((Path(nm.__file__).parent / "config.example.json").read_text(encoding="utf-8"))
    assert example == nm.DEFAULT_CONFIG


# --- Butun zanjir -------------------------------------------------------------


def test_self_test_passes(capsys: pytest.CaptureFixture[str]) -> None:
    assert nm.self_test() == nm.EXIT_OK
    assert "muvaffaqiyatli" in capsys.readouterr().out


def test_interfaces_are_listed_without_loopback() -> None:
    interfaces = nm.list_interfaces()
    assert all(item.address != "127.0.0.1" for item in interfaces)
    assert nm.choose_interface(interfaces, "lo") == "lo"
    if interfaces:
        assert nm.choose_interface(interfaces, "0") == interfaces[0].capture_name
        assert nm.choose_interface(interfaces, interfaces[0].address) == interfaces[0].capture_name
