"""
Standart PQ-TLS rejimi: Go aqctl gateway (crypto/tls, X25519MLKEM768, ML-DSA-65 sertifikat)
↔ Python ssl (OpenSSL 3.5.7) klient. Uchinchi tomon TLS stekiga qarshi interop.

Tekshiriladi:
  1. TLS 1.3 bilan ulanish muvaffaqiyatli
  2. Server sertifikati ML-DSA-65 kaliti (pinned ochiq kalit bilan mos)
  3. Echo ma'lumot tunel orqali o'tadi
  4. Go server log'ida kalit almashinuv: X25519MLKEM768 (post-kvant gibrid)
  5. Noto'g'ri pinned kalit — rad etiladi

Ishga tushirish (avval `scripts\\build-aqctl.ps1` yoki go build):
    set PYTHONIOENCODING=utf-8
    python scripts/interop_std.py
"""

import os
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AQCTL = os.path.join(ROOT, "bin", "aqctl.exe")
ECHO_PORT = 19210
GW_PORT = 19211


def start_echo(stop):
    ls = socket.socket()
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", ECHO_PORT))
    ls.listen(8)
    ls.settimeout(0.5)

    def serve(c):
        try:
            while True:
                d = c.recv(65536)
                if not d:
                    break
                c.sendall(d)
        except OSError:
            pass
        finally:
            c.close()

    while not stop.is_set():
        try:
            c, _ = ls.accept()
        except socket.timeout:
            continue
        threading.Thread(target=serve, args=(c,), daemon=True).start()
    ls.close()


def wait_port(port, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except OSError:
            s.close()
            time.sleep(0.1)
    return False


def cert_pubkey_raw(der):
    """Sertifikatdan ML-DSA ochiq kalitini (raw bayt) oladi."""
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    cert = x509.load_der_x509_certificate(der)
    pk = cert.public_key()
    return pk.public_bytes(Encoding.Raw, PublicFormat.Raw)


def tls_connect(pin_hex):
    """TLS 1.3 klient; sertifikat ochiq kaliti pin_hex bilan solishtiriladi."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE          # ishonch CA orqali emas — pinning orqali
    sock = socket.create_connection(("127.0.0.1", GW_PORT), timeout=10)
    tls = ctx.wrap_socket(sock, server_hostname="aq-gateway")
    der = tls.getpeercert(binary_form=True)
    raw = cert_pubkey_raw(der)
    pinned = bytes.fromhex(pin_hex)
    return tls, tls.version(), raw == pinned


def main():
    if not os.path.exists(AQCTL):
        print("XATO: aqctl binary topilmadi:", AQCTL)
        return 2
    tmp = tempfile.mkdtemp(prefix="aq-std-")
    base = os.path.join(tmp, "server")
    r = subprocess.run([AQCTL, "identity", "new", "--out", base], capture_output=True, text=True)
    if r.returncode != 0:
        print("identity new xato:", r.stderr)
        return 1
    pin_hex = open(base + ".key.pub", encoding="utf-8").read().strip()
    key = base + ".key"

    stop = threading.Event()
    threading.Thread(target=start_echo, args=(stop,), daemon=True).start()
    assert wait_port(ECHO_PORT), "echo ishlamadi"

    gw = subprocess.Popen(
        [AQCTL, "gateway", "serve", "--listen", f"127.0.0.1:{GW_PORT}",
         "--upstream", f"127.0.0.1:{ECHO_PORT}", "--identity", key],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    results = {}
    try:
        assert wait_port(GW_PORT), "gateway ishlamadi"

        # 1-3: TLS 1.3, pinned ML-DSA kalit, echo
        tls, version, pin_ok = tls_connect(pin_hex)
        results["1 TLS 1.3 ulanish"] = version == "TLSv1.3"
        results["2 ML-DSA-65 sertifikat pinned kalit bilan mos"] = pin_ok
        msg = b"Python ssl -> Go aqctl gateway -> echo"
        tls.sendall(msg)
        got = b""
        while len(got) < len(msg):
            chunk = tls.recv(4096)
            if not chunk:
                break
            got += chunk
        results["3 echo tunel orqali"] = got == msg
        tls.close()

        # 5: noto'g'ri pinned kalit (boshqa identity) — mos kelmasligi kerak
        other = os.path.join(tmp, "other")
        subprocess.run([AQCTL, "identity", "new", "--out", other], capture_output=True, text=True)
        other_pin = open(other + ".key.pub", encoding="utf-8").read().strip()
        tls2, _, pin_ok2 = tls_connect(other_pin)
        tls2.close()
        results["5 noto'g'ri pin — mos emas (rad)"] = pin_ok2 is False
    finally:
        stop.set()
        gw.terminate()
        try:
            _, err = gw.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            gw.kill()
            _, err = gw.communicate()

    log = err.decode("utf-8", errors="replace")
    results["4 server log: X25519MLKEM768 kalit almashinuv"] = "X25519MLKEM768" in log
    print("--- gateway log (oxiri):")
    for line in log.strip().splitlines()[-4:]:
        print("   ", line)
    ok = True
    for name, passed in results.items():
        print(("PASS" if passed else "FAIL"), name)
        ok = ok and bool(passed)
    print("\nNATIJA:", "barchasi o'tdi" if ok else "ba'zi tekshiruvlar muvaffaqiyatsiz")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
