"""discovery_selftest.py — kamera qidirish moduli sinovi (haqiqiy kamerasiz).

Lokalda SOXTA RTSP va SOXTA ONVIF serverlari ko'tariladi, shundan keyin
`discovery` moduli xuddi haqiqiy kamera bilan ishlagandek sinaladi:
Digest autentifikatsiya, noto'g'ri parol, yo'l shablonlarini tanlash,
ONVIF `GetStreamUri`, port skanerlash va WS-Discovery javobini tahlil qilish.

    python tests/discovery_selftest.py
"""

from __future__ import annotations

import base64
import hashlib
import re
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ipcam_detect import discovery as D  # noqa: E402

USER, PASSWORD = "admin", "P@rol/123"
GOOD_PATH = "/Streaming/Channels/101"
RTSP_PORT = 8554
ONVIF_PORT = 8899

_results: List[tuple] = []


def check(name: str, cond: bool, info: str = "") -> None:
    _results.append((name, cond, info))
    text = f"{'[OK]  ' if cond else '[FAIL]'} {name}" + (f"  ({info})" if info else "")
    enc = sys.stdout.encoding or "ascii"
    print(text.encode(enc, "replace").decode(enc))


# ============================================================ soxta RTSP
class FakeRTSPServer(threading.Thread):
    """Digest auth talab qiladigan minimal RTSP server."""

    daemon = True

    def __init__(self, port: int = RTSP_PORT) -> None:
        super().__init__(name="FakeRTSP")
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", port))
        self.sock.listen(16)
        self._stop = threading.Event()
        self.requests: List[str] = []

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        with conn:
            conn.settimeout(3.0)
            while True:
                try:
                    data = conn.recv(4096).decode("utf-8", "replace")
                except (OSError, socket.timeout):
                    return
                if not data:
                    return
                self.requests.append(data.splitlines()[0] if data else "")
                conn.sendall(self._respond(data).encode())

    def _respond(self, req: str) -> str:
        cseq = "1"
        m = re.search(r"CSeq:\s*(\d+)", req)
        if m:
            cseq = m.group(1)
        url_m = re.match(r"DESCRIBE (\S+)", req)
        url = url_m.group(1) if url_m else ""
        path = re.sub(r"^rtsp://[^/]+", "", url) or "/"

        auth = ""
        for line in req.splitlines():
            if line.lower().startswith("authorization:"):
                auth = line.split(":", 1)[1].strip()

        if not auth:
            return (f"RTSP/1.0 401 Unauthorized\r\nCSeq: {cseq}\r\n"
                    'WWW-Authenticate: Digest realm="IP Camera", '
                    'nonce="0011223344556677"\r\n\r\n')

        if not self._auth_ok(auth, url):
            return f"RTSP/1.0 401 Unauthorized\r\nCSeq: {cseq}\r\n\r\n"

        # Parol to'g'ri: endi yo'lni tekshiramiz
        if path != GOOD_PATH:
            return f"RTSP/1.0 404 Not Found\r\nCSeq: {cseq}\r\n\r\n"

        sdp = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=Fake\r\nm=video 0 RTP/AVP 96\r\n"
        return (f"RTSP/1.0 200 OK\r\nCSeq: {cseq}\r\n"
                f"Content-Type: application/sdp\r\n"
                f"Content-Length: {len(sdp)}\r\n\r\n{sdp}")

    @staticmethod
    def _auth_ok(auth: str, url: str) -> bool:
        if auth.lower().startswith("basic"):
            try:
                raw = base64.b64decode(auth.split()[1]).decode()
            except Exception:
                return False
            return raw == f"{USER}:{PASSWORD}"
        parts = dict(re.findall(r'(\w+)="([^"]*)"', auth))
        if parts.get("username") != USER:
            return False
        ha1 = hashlib.md5(
            f"{USER}:{parts.get('realm', '')}:{PASSWORD}".encode()).hexdigest()
        ha2 = hashlib.md5(f"DESCRIBE:{parts.get('uri', url)}".encode()).hexdigest()
        want = hashlib.md5(
            f"{ha1}:{parts.get('nonce', '')}:{ha2}".encode()).hexdigest()
        return want == parts.get("response")

    def stop(self) -> None:
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass


# =========================================================== soxta ONVIF
DEVICE_INFO = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
 <s:Body><tds:GetDeviceInformationResponse
   xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
  <tds:Manufacturer>FakeVision</tds:Manufacturer>
  <tds:Model>FV-2043</tds:Model>
  <tds:FirmwareVersion>1.2.3</tds:FirmwareVersion>
  <tds:SerialNumber>SN0001</tds:SerialNumber>
 </tds:GetDeviceInformationResponse></s:Body></s:Envelope>"""

CAPABILITIES = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
 <s:Body><GetCapabilitiesResponse xmlns="http://www.onvif.org/ver10/device/wsdl">
  <Capabilities><Media><XAddr>http://127.0.0.1:{port}/onvif/media_service</XAddr>
  </Media></Capabilities></GetCapabilitiesResponse></s:Body></s:Envelope>"""

PROFILES = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
 <s:Body><GetProfilesResponse xmlns="http://www.onvif.org/ver10/media/wsdl">
  <Profiles token="Profile_1"><Name>mainstream</Name></Profiles>
 </GetProfilesResponse></s:Body></s:Envelope>"""

STREAM_URI = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
 <s:Body><GetStreamUriResponse xmlns="http://www.onvif.org/ver10/media/wsdl">
  <MediaUri><Uri>rtsp://127.0.0.1:{port}{path}</Uri></MediaUri>
 </GetStreamUriResponse></s:Body></s:Envelope>"""


class ONVIFHandler(BaseHTTPRequestHandler):
    def log_message(self, *_a) -> None:
        pass

    def do_POST(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", "replace")

        if "GetDeviceInformation" in body:
            payload = DEVICE_INFO
        elif "GetCapabilities" in body:
            payload = CAPABILITIES.format(port=ONVIF_PORT)
        elif "GetProfiles" in body:
            payload = PROFILES
        elif "GetStreamUri" in body:
            payload = STREAM_URI.format(port=RTSP_PORT, path=GOOD_PATH)
        else:
            self.send_error(400)
            return

        data = payload.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/soap+xml")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


# ================================================================ testlar
WSD_SAMPLE = b"""<?xml version="1.0"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
 xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery">
 <e:Body><d:ProbeMatches><d:ProbeMatch>
  <d:Scopes>onvif://www.onvif.org/name/Kirish_kamera
   onvif://www.onvif.org/hardware/DS-2CD2043G2
   onvif://www.onvif.org/manufacturer/Hikvision</d:Scopes>
  <d:XAddrs>http://192.168.1.64/onvif/device_service</d:XAddrs>
 </d:ProbeMatch></d:ProbeMatches></e:Body></e:Envelope>"""


def test_network_helpers() -> None:
    subs = D.local_subnets()
    check("lokal tarmoqlar aniqlandi", bool(subs), f"{len(subs)} ta: {subs[:2]}")
    check("CIDR formati to'g'ri", all("/" in s for s in subs))
    url = D.build_rtsp_url("192.168.1.10", 554, GOOD_PATH, USER, PASSWORD)
    check("URL da maxsus belgilar kodlandi",
          "P%40rol%2F123" in url and "@192.168.1.10:554" in url, url)


def test_wsd_parse() -> None:
    cam = D._parse_probe_match(WSD_SAMPLE, "192.168.1.64")
    ok = cam is not None
    check("WS-Discovery javobi tahlil qilindi", ok)
    if not ok:
        return
    check("ONVIF manzili olindi",
          cam.onvif_url == "http://192.168.1.64/onvif/device_service", cam.onvif_url)
    check("IP XAddrs dan ajratildi", cam.ip == "192.168.1.64", cam.ip)
    check("scopes'dan nom/model o'qildi",
          cam.manufacturer == "Hikvision" and "DS-2CD2043G2" in cam.model,
          f"{cam.manufacturer} / {cam.model} / {cam.name}")
    check("probe xabari to'g'ri yasaladi",
          b"NetworkVideoTransmitter" in D._probe_message()
          and b"Probe" in D._probe_message())


def test_rtsp_auth(rtsp: FakeRTSPServer) -> None:
    url = f"rtsp://127.0.0.1:{RTSP_PORT}{GOOD_PATH}"

    status, msg = D.rtsp_describe(url)
    check("parolsiz -> 401", status == 401, msg)

    status, msg = D.rtsp_describe(url, USER, "xato-parol")
    check("noto'g'ri parol -> 401", status == 401, msg)

    status, msg = D.rtsp_describe(url, USER, PASSWORD)
    check("to'g'ri parol -> 200", status == 200, msg)

    status, _ = D.rtsp_describe(f"rtsp://127.0.0.1:{RTSP_PORT}/yolq",
                                USER, PASSWORD)
    check("noto'g'ri yo'l -> 404", status == 404, str(status))

    status, msg = D.rtsp_describe(f"rtsp://127.0.0.1:{RTSP_PORT + 300}/x",
                                  USER, PASSWORD, timeout=1.0)
    check("yopiq port -> 0 (xato matni bilan)", status == 0, msg[:40])

    check("digest sarlavhasi to'g'ri hisoblandi",
          any("Authorization" not in r for r in rtsp.requests))


def test_template_search() -> None:
    cam = D.Camera(ip="127.0.0.1", ports=[RTSP_PORT])
    steps: List[Tuple[str, float]] = []
    out = D.find_stream_url(cam, USER, PASSWORD,
                            progress=lambda t, p: steps.append((t, p)))
    check("shablon orqali URL topildi", out.rtsp_url.endswith(GOOD_PATH),
          out.rtsp_url or out.note)
    check("vendor aniqlandi", "Hikvision" in out.rtsp_template, out.rtsp_template)
    check("auth_ok = True", out.auth_ok is True)
    # Hikvision shabloni ro'yxatda birinchi -> 1 urinish + yakuniy xabar
    check("progress callback chaqirildi va yakunlandi",
          len(steps) >= 2 and steps[-1][1] == 1.0,
          f"{len(steps)} qadam, oxirgisi: {steps[-1][0]}")

    bad = D.find_stream_url(D.Camera(ip="127.0.0.1", ports=[RTSP_PORT]),
                            USER, "xato-parol")
    check("xato parolda aniq xabar beriladi",
          bad.auth_ok is False and "parol" in bad.note.lower(), bad.note)


def test_onvif(server: HTTPServer) -> None:
    url = f"http://127.0.0.1:{ONVIF_PORT}/onvif/device_service"
    info = D.onvif_device_info(url, USER, PASSWORD)
    check("ONVIF GetDeviceInformation ishladi",
          info.get("manufacturer") == "FakeVision" and info.get("model") == "FV-2043",
          str(info))

    media = D.onvif_media_url(url, USER, PASSWORD)
    check("media servis manzili olindi", media.endswith("/media_service"), media)

    uri = D.onvif_stream_uri(url, USER, PASSWORD)
    check("ONVIF GetStreamUri RTSP qaytardi",
          uri.startswith("rtsp://") and uri.endswith(GOOD_PATH), uri)

    cam = D.Camera(ip="127.0.0.1", ports=[RTSP_PORT], onvif_url=url, source="onvif")
    out = D.find_stream_url(cam, USER, PASSWORD)
    check("ONVIF yo'li orqali to'liq URL yig'ildi",
          out.rtsp_template == "ONVIF GetStreamUri" and USER in out.rtsp_url,
          out.rtsp_url or out.note)
    check("ONVIF'dan model ma'lumoti ko'chirildi",
          out.manufacturer == "FakeVision", out.title)


def test_scan() -> None:
    cams = D.scan_subnet("127.0.0.1/30", ports=(RTSP_PORT, ONVIF_PORT),
                         timeout=0.3, workers=8)
    ips = [c.ip for c in cams]
    check("port skaner qurilmani topdi", "127.0.0.1" in ips, str(ips))
    if "127.0.0.1" in ips:
        cam = next(c for c in cams if c.ip == "127.0.0.1")
        check("ochiq portlar aniqlandi", RTSP_PORT in cam.ports, str(cam.ports))
        check("rtsp_port to'g'ri tanlandi", cam.rtsp_port == RTSP_PORT,
              str(cam.rtsp_port))


def main() -> int:
    import logging

    logging.basicConfig(level=logging.WARNING)
    print("=" * 68)
    print(" discovery — soxta RTSP/ONVIF serverlari bilan sinov")
    print("=" * 68)

    rtsp = FakeRTSPServer()
    rtsp.start()
    onvif = HTTPServer(("127.0.0.1", ONVIF_PORT), ONVIFHandler)
    threading.Thread(target=onvif.serve_forever, daemon=True).start()

    try:
        print("\n-- Tarmoq yordamchilari --")
        test_network_helpers()
        print("\n-- WS-Discovery tahlili --")
        test_wsd_parse()
        print("\n-- RTSP autentifikatsiya --")
        test_rtsp_auth(rtsp)
        print("\n-- Vendor shablonlari --")
        test_template_search()
        print("\n-- ONVIF SOAP --")
        test_onvif(onvif)
        print("\n-- Port skanerlash --")
        test_scan()
    finally:
        rtsp.stop()
        onvif.shutdown()

    ok = sum(1 for _, c, _ in _results if c)
    print("\n" + "=" * 68)
    print(f" NATIJA: {ok}/{len(_results)} test o'tdi")
    print("=" * 68)
    for name, cond, info in _results:
        if not cond:
            print(f"  [FAIL] {name} {info}")
    return 0 if ok == len(_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
