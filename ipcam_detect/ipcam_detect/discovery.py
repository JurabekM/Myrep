"""discovery.py — lokal tarmoqdagi IP kameralarni avtomatik topish.

Uch bosqichli yondashuv (tashqi kutubxonalarsiz, faqat standart kutubxona):

1. **ONVIF WS-Discovery** — 239.255.255.250:3702 ga UDP multicast Probe.
   ONVIF'ni qo'llab-quvvatlaydigan kameralar o'zi javob beradi va
   `XAddrs` (device service URL) hamda nomini yuboradi. Eng ishonchli usul.

2. **Port skanerlash** — ONVIF o'chirilgan yoki eski kameralar uchun
   /24 tarmoqni keng tarqalgan kamera portlari bo'yicha tekshirish
   (554/8554 RTSP, 80/8080/88 HTTP, 34567/37777 vendor protokollari).

3. **RTSP URL aniqlash** — foydalanuvchi login/parol kiritgach:
   a) ONVIF `GetStreamUri` orqali RASMIY URL olinadi (eng to'g'ri yo'l);
   b) bo'lmasa, vendor shablonlari `DESCRIBE` bilan birma-bir sinaladi.

Shu tariqa foydalanuvchiga faqat login/parol kiritish qoladi.
"""

from __future__ import annotations

import base64
import concurrent.futures as futures
import hashlib
import ipaddress
import logging
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- doimiylar
WSD_ADDR = "239.255.255.250"
WSD_PORT = 3702

#: Kamera/NVR larda eng ko'p uchraydigan portlar
CAMERA_PORTS: Tuple[int, ...] = (
    554,    # RTSP (standart)
    8554,   # RTSP (alternativ)
    80,     # HTTP / ONVIF
    8080,   # HTTP (alternativ)
    88,     # Hikvision HTTP
    8000,   # Hikvision SDK
    8899,   # ONVIF (ba'zi xitoy kameralari)
    2020,   # ONVIF (alternativ)
    34567,  # Dahua/XM DVR (Sofia)
    37777,  # Dahua SDK
)
RTSP_PORTS: Tuple[int, ...] = (554, 8554)

#: Vendor bo'yicha RTSP yo'l shablonlari. `{ch}` — kanal raqami.
#: Tartib muhim: eng keng tarqalganlari birinchi turadi.
RTSP_TEMPLATES: Tuple[Tuple[str, str], ...] = (
    ("Hikvision / HiWatch",  "/Streaming/Channels/{ch}01"),
    ("Hikvision (eski)",     "/h264/ch{ch}/main/av_stream"),
    ("Dahua / Amcrest",      "/cam/realmonitor?channel={ch}&subtype=0"),
    ("Reolink",              "/h264Preview_0{ch}_main"),
    ("TP-Link Tapo / VIGI",  "/stream1"),
    ("Axis",                 "/axis-media/media.amp"),
    ("Uniview",              "/media/video{ch}"),
    ("Foscam",               "/videoMain"),
    ("Hanwha / Samsung",     "/profile{ch}/media.smp"),
    ("Vivotek",              "/live.sdp"),
    ("Bosch",                "/rtsp_tunnel"),
    ("Umumiy (generic) 1",   "/live/ch0{ch}_0"),
    ("Umumiy (generic) 2",   "/11"),
    ("Umumiy (generic) 3",   "/1"),
    ("Umumiy (generic) 4",   "/live"),
    ("Umumiy (generic) 5",   "/video{ch}"),
    ("Umumiy (generic) 6",   "/onvif{ch}"),
    ("Umumiy (generic) 7",   "/media/video1"),
    ("Umumiy (generic) 8",   "/"),
)

_NS = {
    "s": "http://www.w3.org/2003/05/soap-envelope",
    "d": "http://schemas.xmlsoap.org/ws/2005/04/discovery",
    "a": "http://schemas.xmlsoap.org/ws/2004/08/addressing",
}


# ------------------------------------------------------------------ modellar
@dataclass
class Camera:
    """Topilgan qurilma haqidagi ma'lumot."""

    ip: str
    ports: List[int] = field(default_factory=list)
    onvif_url: str = ""          # http://ip/onvif/device_service
    name: str = ""               # scopes/name yoki model
    manufacturer: str = ""
    model: str = ""
    source: str = "scan"         # "onvif" | "scan"
    rtsp_url: str = ""           # tasdiqlangan URL (login/parol bilan)
    rtsp_template: str = ""      # qaysi shablon ishladi
    auth_ok: Optional[bool] = None
    note: str = ""

    @property
    def rtsp_port(self) -> int:
        for p in RTSP_PORTS:
            if p in self.ports:
                return p
        return 554

    @property
    def title(self) -> str:
        parts = [x for x in (self.manufacturer, self.model) if x]
        return " ".join(parts) or self.name or "Noma'lum qurilma"

    def as_dict(self) -> dict:
        return {
            "ip": self.ip, "ports": self.ports, "onvif": self.onvif_url,
            "title": self.title, "source": self.source, "rtsp": self.rtsp_url,
        }


ProgressCb = Callable[[str, float], None]   # (matn, 0..1)


# ------------------------------------------------------------------ tarmoq
def local_ipv4_addresses() -> List[Tuple[str, str]]:
    """Lokal IPv4 manzillar ro'yxati: [(ip, netmask), …].

    `psutil` bo'lsa barcha interfeyslar, aks holda faqat asosiy marshrut.
    """
    out: List[Tuple[str, str]] = []
    try:
        import psutil

        for _name, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                if a.family == socket.AF_INET and a.address and a.netmask:
                    if not a.address.startswith("127."):
                        out.append((a.address, a.netmask))
    except Exception:  # psutil yo'q yoki xato
        pass

    if not out:
        # Zaxira: tashqi manzilga "ulanish" orqali asosiy IP ni aniqlash
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            out.append((s.getsockname()[0], "255.255.255.0"))
        except OSError:
            pass
        finally:
            s.close()
    return out


def local_subnets(max_hosts: int = 1024) -> List[str]:
    """Skanerlash mumkin bo'lgan tarmoqlar (CIDR) ro'yxati."""
    nets: List[str] = []
    for ip, mask in local_ipv4_addresses():
        try:
            net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
        except ValueError:
            continue
        # /16 kabi katta tarmoqni to'liq skanerlash mantiqsiz -> /24 ga qisqartiramiz
        if net.num_addresses > max_hosts:
            net = ipaddress.IPv4Network(f"{ip}/24", strict=False)
        cidr = str(net)
        if cidr not in nets:
            nets.append(cidr)
    return nets


# ------------------------------------------------------- 1) WS-Discovery
def _probe_message() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"'
        ' xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"'
        ' xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"'
        ' xmlns:dn="http://www.onvif.org/ver10/network/wsdl">'
        "<e:Header>"
        f"<w:MessageID>uuid:{uuid.uuid4()}</w:MessageID>"
        '<w:To e:mustUnderstand="true">'
        "urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>"
        '<w:Action e:mustUnderstand="true">'
        "http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>"
        "</e:Header><e:Body><d:Probe>"
        "<d:Types>dn:NetworkVideoTransmitter</d:Types>"
        "</d:Probe></e:Body></e:Envelope>"
    ).encode()


def _parse_probe_match(data: bytes, ip: str) -> Optional[Camera]:
    """WS-Discovery javobidan `Camera` yasaydi."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None

    xaddrs = ""
    scopes = ""
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "XAddrs" and el.text:
            xaddrs = el.text.strip()
        elif tag == "Scopes" and el.text:
            scopes = el.text.strip()
    if not xaddrs:
        return None

    url = xaddrs.split()[0]
    host = re.sub(r"^\w+://", "", url).split("/")[0].split(":")[0]
    cam = Camera(ip=host or ip, onvif_url=url, source="onvif")

    # Scopes ichida: onvif://www.onvif.org/name/CAM1 , …/hardware/DS-2CD2043
    for key, attr in (("name", "name"), ("hardware", "model"),
                      ("manufacturer", "manufacturer")):
        m = re.search(rf"onvif://www\.onvif\.org/{key}/([^\s]+)", scopes)
        if m:
            value = urllib.parse.unquote(m.group(1)).replace("_", " ")
            setattr(cam, attr, value)
    return cam


def ws_discover(timeout: float = 4.0, retries: int = 2) -> List[Camera]:
    """ONVIF qurilmalarini multicast Probe orqali topadi.

    Har bir lokal interfeysdan alohida yuboriladi — ko'p tarmoqli
    kompyuterlarda (Wi-Fi + Ethernet + VirtualBox) bu muhim.
    """
    found: Dict[str, Camera] = {}
    ifaces = [ip for ip, _ in local_ipv4_addresses()] or ["0.0.0.0"]

    for local_ip in ifaces:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            # Multicast'ni AYNAN shu interfeysdan yuborish
            if local_ip != "0.0.0.0":
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                                socket.inet_aton(local_ip))
                sock.bind((local_ip, 0))
            sock.settimeout(0.4)

            msg = _probe_message()
            for _ in range(max(1, retries)):
                try:
                    sock.sendto(msg, (WSD_ADDR, WSD_PORT))
                except OSError as exc:
                    logger.debug("WS-Discovery yuborilmadi (%s): %s", local_ip, exc)
                    break
                time.sleep(0.15)

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    data, addr = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    break
                cam = _parse_probe_match(data, addr[0])
                if cam and cam.ip not in found:
                    found[cam.ip] = cam
                    logger.info("ONVIF qurilma topildi: %s (%s)", cam.ip, cam.title)
        finally:
            sock.close()
    return list(found.values())


# --------------------------------------------------------- 2) port skaner
def _port_open(ip: str, port: int, timeout: float) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((ip, port)) == 0


def scan_subnet(
    cidr: str,
    ports: Sequence[int] = CAMERA_PORTS,
    timeout: float = 0.35,
    workers: int = 256,
    progress: Optional[ProgressCb] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> List[Camera]:
    """Tarmoqni kamera portlari bo'yicha skanerlaydi.

    Thread pool ishlatiladi: skanerlash butunlay I/O-kutishdan iborat,
    shuning uchun GIL to'sqinlik qilmaydi va 256 thread bemalol ishlaydi.
    """
    net = ipaddress.IPv4Network(cidr, strict=False)
    hosts = [str(h) for h in net.hosts()]
    total = len(hosts) or 1
    result: Dict[str, Camera] = {}
    done = 0

    def probe(ip: str) -> Tuple[str, List[int]]:
        open_ports = []
        for p in ports:
            if stop_flag and stop_flag():
                break
            if _port_open(ip, p, timeout):
                open_ports.append(p)
        return ip, open_ports

    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        tasks = {pool.submit(probe, ip): ip for ip in hosts}
        for fut in futures.as_completed(tasks):
            done += 1
            if progress and done % 8 == 0:
                progress(f"Skanerlanmoqda… {done}/{total}", done / total)
            if stop_flag and stop_flag():
                break
            try:
                ip, open_ports = fut.result()
            except Exception:
                continue
            if not open_ports:
                continue
            # RTSP yoki ONVIF-ga o'xshash port bo'lmasa — kamera emas
            if not any(p in open_ports for p in RTSP_PORTS + (80, 8080, 88, 8899, 2020)):
                continue
            cam = Camera(ip=ip, ports=open_ports, source="scan")
            cam.onvif_url = _guess_onvif_url(ip, open_ports)
            result[ip] = cam
            logger.info("Qurilma topildi: %s portlar=%s", ip, open_ports)

    if progress:
        progress(f"Skanerlash tugadi: {len(result)} qurilma", 1.0)
    return list(result.values())


def _guess_onvif_url(ip: str, ports: Sequence[int]) -> str:
    for p in (80, 8080, 8899, 2020, 88):
        if p in ports:
            host = ip if p == 80 else f"{ip}:{p}"
            return f"http://{host}/onvif/device_service"
    return ""


# ------------------------------------------------------------- ONVIF SOAP
def _ws_security(user: str, password: str) -> str:
    """WS-UsernameToken (PasswordDigest) — ONVIF'ning standart autentifikatsiyasi."""
    nonce = uuid.uuid4().bytes
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    digest = base64.b64encode(
        hashlib.sha1(nonce + created.encode() + password.encode()).digest()
    ).decode()
    return (
        '<s:Header><Security s:mustUnderstand="1" xmlns='
        '"http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">'
        f"<UsernameToken><Username>{user}</Username>"
        '<Password Type="http://docs.oasis-open.org/wss/2004/01/'
        f'oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</Password>'
        '<Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/'
        'oasis-200401-wss-soap-message-security-1.0#Base64Binary">'
        f"{base64.b64encode(nonce).decode()}</Nonce>"
        '<Created xmlns="http://docs.oasis-open.org/wss/2004/01/'
        f'oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created>'
        "</UsernameToken></Security></s:Header>"
    )


def _soap(url: str, body: str, user: str = "", password: str = "",
          timeout: float = 5.0) -> Optional[ET.Element]:
    """ONVIF SOAP so'rovi. Xatoda `None` qaytaradi (istisno tashlamaydi)."""
    header = _ws_security(user, password) if user else ""
    envelope = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">'
        f"{header}<s:Body>{body}</s:Body></s:Envelope>"
    ).encode()

    req = urllib.request.Request(
        url, data=envelope,
        headers={"Content-Type": "application/soap+xml; charset=utf-8"},
    )
    opener = urllib.request.build_opener()
    if user:
        # Ba'zi kameralar WS-Security o'rniga HTTP Digest talab qiladi
        mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        mgr.add_password(None, url, user, password)
        opener.add_handler(urllib.request.HTTPDigestAuthHandler(mgr))
        opener.add_handler(urllib.request.HTTPBasicAuthHandler(mgr))
    try:
        with opener.open(req, timeout=timeout) as resp:
            return ET.fromstring(resp.read())
    except (urllib.error.URLError, OSError, ET.ParseError) as exc:
        logger.debug("ONVIF so'rov xatosi (%s): %s", url, exc)
        return None


def _find_text(root: ET.Element, tag: str) -> str:
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] == tag and el.text:
            return el.text.strip()
    return ""


def onvif_device_info(url: str, user: str, password: str) -> Dict[str, str]:
    """`GetDeviceInformation` — ishlab chiqaruvchi, model, proshivka."""
    root = _soap(url, '<GetDeviceInformation xmlns='
                      '"http://www.onvif.org/ver10/device/wsdl"/>', user, password)
    if root is None:
        return {}
    return {
        "manufacturer": _find_text(root, "Manufacturer"),
        "model": _find_text(root, "Model"),
        "firmware": _find_text(root, "FirmwareVersion"),
        "serial": _find_text(root, "SerialNumber"),
    }


def onvif_media_url(device_url: str, user: str, password: str) -> str:
    """Media servisining manzilini aniqlaydi (GetCapabilities)."""
    root = _soap(device_url,
                 '<GetCapabilities xmlns="http://www.onvif.org/ver10/device/wsdl">'
                 "<Category>Media</Category></GetCapabilities>", user, password)
    if root is not None:
        for el in root.iter():
            if el.tag.rsplit("}", 1)[-1] == "XAddr" and el.text:
                return el.text.strip()
    return device_url  # ba'zi kameralarda media ham shu manzilda


def onvif_stream_uri(device_url: str, user: str, password: str) -> str:
    """ONVIF orqali RASMIY RTSP URL ni oladi (eng ishonchli usul)."""
    media = onvif_media_url(device_url, user, password)
    root = _soap(media, '<GetProfiles xmlns='
                        '"http://www.onvif.org/ver10/media/wsdl"/>', user, password)
    if root is None:
        return ""

    tokens = [el.get("token") for el in root.iter()
              if el.tag.rsplit("}", 1)[-1] == "Profiles" and el.get("token")]
    for token in tokens:
        body = (
            '<GetStreamUri xmlns="http://www.onvif.org/ver10/media/wsdl">'
            "<StreamSetup>"
            '<Stream xmlns="http://www.onvif.org/ver10/schema">RTP-Unicast</Stream>'
            '<Transport xmlns="http://www.onvif.org/ver10/schema">'
            "<Protocol>RTSP</Protocol></Transport>"
            "</StreamSetup>"
            f"<ProfileToken>{token}</ProfileToken></GetStreamUri>"
        )
        res = _soap(media, body, user, password)
        if res is None:
            continue
        uri = _find_text(res, "Uri")
        if uri.startswith("rtsp://"):
            return uri
    return ""


# ------------------------------------------------------------- RTSP tekshiruv
def _digest_header(method: str, uri: str, user: str, password: str,
                   challenge: str) -> str:
    """RFC 2069 Digest javobi (RTSP kameralar shu variantni ishlatadi)."""
    parts = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
    realm, nonce = parts.get("realm", ""), parts.get("nonce", "")
    ha1 = hashlib.md5(f"{user}:{realm}:{password}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    resp = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
    return (f'Digest username="{user}", realm="{realm}", nonce="{nonce}", '
            f'uri="{uri}", response="{resp}"')


def rtsp_describe(url: str, user: str = "", password: str = "",
                  timeout: float = 3.0) -> Tuple[int, str]:
    """RTSP DESCRIBE yuboradi va (status_code, xabar) qaytaradi.

    Dekodlash umuman qilinmaydi — bu eng arzon va tez tekshiruv usuli.
    401/403 -> login/parol xato; 200 -> URL to'g'ri; 404/455 -> yo'l xato.
    """
    m = re.match(r"rtsp://(?:[^@/]*@)?([^/:]+)(?::(\d+))?(/.*)?$", url)
    if not m:
        return 0, "URL formati noto'g'ri"
    host, port, path = m.group(1), int(m.group(2) or 554), m.group(3) or "/"
    clean = f"rtsp://{host}:{port}{path}"

    def request(auth: str, cseq: int) -> str:
        req = (f"DESCRIBE {clean} RTSP/1.0\r\nCSeq: {cseq}\r\n"
               "Accept: application/sdp\r\nUser-Agent: ipcam_detect\r\n")
        if auth:
            req += f"Authorization: {auth}\r\n"
        return req + "\r\n"

    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(request("", 1).encode())
            data = s.recv(4096).decode("utf-8", "replace")
            status = int(re.search(r"RTSP/1\.0 (\d+)", data).group(1)) \
                if re.search(r"RTSP/1\.0 (\d+)", data) else 0

            if status == 401 and user:
                challenge = ""
                for line in data.splitlines():
                    if line.lower().startswith("www-authenticate:"):
                        challenge = line.split(":", 1)[1].strip()
                        break
                if challenge.lower().startswith("digest"):
                    auth = _digest_header("DESCRIBE", clean, user, password, challenge)
                else:  # Basic
                    token = base64.b64encode(f"{user}:{password}".encode()).decode()
                    auth = f"Basic {token}"
                s.sendall(request(auth, 2).encode())
                data = s.recv(4096).decode("utf-8", "replace")
                m2 = re.search(r"RTSP/1\.0 (\d+)", data)
                status = int(m2.group(1)) if m2 else 0

            first = data.splitlines()[0] if data else "javob yo'q"
            return status, first
    except (OSError, socket.timeout) as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def build_rtsp_url(ip: str, port: int, path: str, user: str, password: str) -> str:
    """Login/parolni URL ga xavfsiz joylashtiradi (maxsus belgilar bilan)."""
    if not user:
        return f"rtsp://{ip}:{port}{path}"
    u = urllib.parse.quote(user, safe="")
    p = urllib.parse.quote(password, safe="")
    return f"rtsp://{u}:{p}@{ip}:{port}{path}"


def find_stream_url(
    cam: Camera,
    user: str,
    password: str,
    channel: int = 1,
    progress: Optional[ProgressCb] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> Camera:
    """Kamera uchun ishlaydigan RTSP URL ni topadi.

    Avval ONVIF (rasmiy yo'l), keyin vendor shablonlari sinaladi. Natija
    `cam.rtsp_url` ga yoziladi; `cam.auth_ok` login/parol to'g'riligini
    bildiradi (401 kelgan bo'lsa False).
    """
    port = cam.rtsp_port

    # --- 1) ONVIF: rasmiy URL ---
    if cam.onvif_url:
        if progress:
            progress("ONVIF orqali so'ralmoqda…", 0.1)
        info = onvif_device_info(cam.onvif_url, user, password)
        if info:
            cam.manufacturer = info.get("manufacturer") or cam.manufacturer
            cam.model = info.get("model") or cam.model
        uri = onvif_stream_uri(cam.onvif_url, user, password)
        if uri:
            # ONVIF URL da odatda login/parol bo'lmaydi — o'zimiz qo'shamiz
            path = re.sub(r"^rtsp://[^/]+", "", uri) or "/"
            m = re.match(r"rtsp://(?:[^@/]*@)?([^/:]+)(?::(\d+))?", uri)
            host = m.group(1) if m else cam.ip
            oport = int(m.group(2)) if m and m.group(2) else port
            full = build_rtsp_url(host, oport, path, user, password)
            status, msg = rtsp_describe(full, user, password)
            if status == 200:
                cam.rtsp_url, cam.rtsp_template = full, "ONVIF GetStreamUri"
                cam.auth_ok = True
                if progress:
                    progress("ONVIF orqali topildi", 1.0)
                return cam
            if status in (401, 403):
                cam.auth_ok = False
                cam.note = f"Login/parol rad etildi ({msg})"
                if progress:
                    progress(cam.note, 1.0)
                return cam

    # --- 2) Vendor shablonlari ---
    total = len(RTSP_TEMPLATES)
    unauthorized = False
    for i, (vendor, tpl) in enumerate(RTSP_TEMPLATES, 1):
        if stop_flag and stop_flag():
            break
        path = tpl.format(ch=channel)
        url = build_rtsp_url(cam.ip, port, path, user, password)
        if progress:
            progress(f"Sinalmoqda: {vendor} ({i}/{total})", i / total)
        status, msg = rtsp_describe(url, user, password, timeout=2.5)
        if status == 200:
            cam.rtsp_url, cam.rtsp_template = url, vendor
            cam.auth_ok = True
            if progress:
                progress(f"Topildi: {vendor}", 1.0)
            return cam
        if status in (401, 403):
            unauthorized = True   # yo'l to'g'ri, lekin parol xato

    cam.auth_ok = False if unauthorized else None
    cam.note = ("Login yoki parol xato" if unauthorized
                else "Ishlaydigan RTSP yo'li topilmadi — URL ni qo'lda kiriting")
    if progress:
        progress(cam.note, 1.0)
    return cam


# --------------------------------------------------------------- orkestrator
def discover(
    use_onvif: bool = True,
    subnets: Optional[Iterable[str]] = None,
    ports: Sequence[int] = CAMERA_PORTS,
    onvif_timeout: float = 4.0,
    progress: Optional[ProgressCb] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> List[Camera]:
    """ONVIF + port skanerlash natijalarini birlashtiradi (IP bo'yicha)."""
    found: Dict[str, Camera] = {}

    if use_onvif:
        if progress:
            progress("ONVIF qurilmalari qidirilmoqda…", 0.05)
        for cam in ws_discover(onvif_timeout):
            found[cam.ip] = cam

    if subnets is None:
        subnets = local_subnets()
    for cidr in subnets:
        if stop_flag and stop_flag():
            break
        for cam in scan_subnet(cidr, ports, progress=progress, stop_flag=stop_flag):
            if cam.ip in found:
                # ONVIF topgan qurilmaga port ma'lumotini qo'shamiz
                found[cam.ip].ports = sorted(set(found[cam.ip].ports) | set(cam.ports))
            else:
                found[cam.ip] = cam

    cams = sorted(found.values(), key=lambda c: tuple(int(x) for x in c.ip.split(".")))
    logger.info("Jami topildi: %d qurilma", len(cams))
    return cams
