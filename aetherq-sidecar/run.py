#!/usr/bin/env python3
"""
AETHER-Q demo — bitta buyruq bilan to'liq zanjir:

  klient (HTTP) ─▶ sidecar connect ══ AETHER-Q tunel ══▶ sidecar serve ─▶ Aether_new (monolit)
  klient (HTTP) ─▶ aqctl gateway connect ══ standart PQ-TLS ══▶ aqctl gateway serve ─▶ Aether_new

Bajaradi:
  1. Identity va allowlist yaratadi (ML-DSA-65 kalitlar)
  2. Aether_new monolitini, sidecar'larni va gateway'ni ishga tushiradi
  3. HTTP CRUD sinovlari: to'g'ri va noto'g'ri so'rovlar, ikki rejim orqali
  4. Resumption (ticket) ishlashini sidecar log'idan tasdiqlaydi
  5. Latency o'lchaydi (to'g'ridan-to'g'ri vs tunel) va /metrics ni o'qiydi
  6. Hammasini to'xtatadi

Ishga tushirish (Windows, Python 3.8+ — faqat stdlib):
    python run.py
    python run.py --latency-n 100   # latency o'lchovini kengaytirish
"""

import argparse
import http.client
import json
import pathlib
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent

PORT = {
    "monolit": 8080,        # Aether_new (to'g'ridan-to'g'ri)
    "aq_serve": 9443,       # AETHER-Q sidecar (server tomoni)
    "aq_connect": 7000,     # AETHER-Q sidecar (klient tomoni — HTTP shu portga)
    "gw_serve": 9444,       # standart PQ-TLS gateway (server)
    "gw_connect": 7001,     # standart PQ-TLS gateway (klient — HTTP shu portga)
    "metrics": 9100,        # gateway /metrics
}


def find_bin(name):
    for p in (HERE / "dist" / name, HERE / "target" / "release" / name, HERE / "bin" / name):
        if p.exists():
            return str(p)
    sys.exit(f"XATO: {name} topilmadi (dist/ papkasini tekshiring)")


class Demo:
    def __init__(self, work):
        self.work = work
        self.logs = work / "logs"
        self.procs = []
        self.results = []

    def check(self, name, ok, detail=""):
        self.results.append((name, bool(ok), detail))
        print(("  PASS " if ok else "  FAIL ") + name + (f"  ({detail})" if detail else ""))
        return ok

    def start(self, label, args):
        log = open(self.logs / f"{label}.log", "w", encoding="utf-8")
        p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, cwd=str(self.work))
        self.procs.append((label, p, log))
        return p

    def stop_all(self):
        for label, p, log in reversed(self.procs):
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:  # noqa: BLE001
                try:
                    p.kill()
                except Exception:  # noqa: BLE001
                    pass
            log.close()
        self.procs = []

    def log_text(self, label):
        return (self.logs / f"{label}.log").read_text(encoding="utf-8", errors="replace")


def request(port, method, path, body=None, timeout=10):
    """Har so'rov uchun yangi TCP ulanish (Connection: close) — har biri yangi tunel handshake'i."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    headers = {"Connection": "close"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    t0 = time.perf_counter()
    conn.request(method, path, body=data, headers=headers)
    resp = conn.getresponse()
    raw = resp.read()
    dt = (time.perf_counter() - t0) * 1000.0
    conn.close()
    try:
        payload = json.loads(raw) if raw else None
    except ValueError:
        payload = raw.decode("utf-8", errors="replace")
    return resp.status, payload, dt


def wait_http(port, path="/healthz", tries=60):
    for _ in range(tries):
        try:
            status, _, _ = request(port, "GET", path, timeout=3)
            if status == 200:
                return True
        except OSError:
            pass
        time.sleep(0.25)
    return False


def crud_suite(demo, label, port):
    """Bir yo'l (to'g'ridan-to'g'ri yoki tunel) uchun CRUD va xato holatlari."""
    print(f"\n[{label}] HTTP sinovlari (port {port})")
    st, body, _ = request(port, "GET", "/healthz")
    demo.check(f"{label}: GET /healthz", st == 200 and body.get("status") == "ok", f"HTTP {st}")
    st, rec, _ = request(port, "POST", "/api/v1/records", {"title": f"{label} yozuvi", "body": "AETHER-Q demo"})
    demo.check(f"{label}: POST yozuv yaratish", st == 201 and isinstance(rec, dict), f"HTTP {st}")
    rid = rec.get("id") if isinstance(rec, dict) else None
    st, lst, _ = request(port, "GET", "/api/v1/records")
    demo.check(f"{label}: GET ro'yxat", st == 200 and isinstance(lst, list) and any(r.get("id") == rid for r in lst),
               f"{len(lst) if isinstance(lst, list) else '?'} ta")
    st, one, _ = request(port, "GET", f"/api/v1/records/{rid}")
    demo.check(f"{label}: GET bitta yozuv", st == 200 and one.get("title") == f"{label} yozuvi", f"HTTP {st}")
    st, _, _ = request(port, "POST", "/api/v1/records", {"title": ""})
    demo.check(f"{label}: bo'sh title rad etiladi", st == 422, f"HTTP {st}")
    st, _, _ = request(port, "GET", "/api/v1/records/999999")
    demo.check(f"{label}: mavjud bo'lmagan ID → 404", st == 404, f"HTTP {st}")
    st, _, _ = request(port, "DELETE", f"/api/v1/records/{rid}")
    demo.check(f"{label}: DELETE", st == 204, f"HTTP {st}")
    st, _, _ = request(port, "GET", f"/api/v1/records/{rid}")
    demo.check(f"{label}: o'chirilgandan keyin 404", st == 404, f"HTTP {st}")


def latency(port, n):
    samples = []
    for i in range(n):
        st, _, dt = request(port, "GET", "/healthz")
        if st == 200:
            samples.append(dt)
    return samples


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--latency-n", type=int, default=30, help="har yo'l uchun latency so'rovlari soni")
    args = ap.parse_args()

    work = HERE / "run-demo"
    if work.exists():
        shutil.rmtree(work)
    (work / "logs").mkdir(parents=True)
    demo = Demo(work)

    sidecar = find_bin("aq-sidecar.exe")
    aqctl = find_bin("aqctl.exe")
    monolit = find_bin("aether_new.exe")
    print("AETHER-Q demo — ishchi papka:", work)
    print("ikkilik fayllar:", sidecar, "|", aqctl, "|", monolit)

    try:
        print("\n[1] Identity va allowlist")
        # Barcha identity'lar aqctl bilan (NAME.key + NAME.key.pub + NAME.meta.json — muddat/rotatsiya uchun).
        # Format Rust aq-sidecar bilan bir xil ("aq-identity v1"), shuning uchun sidecar ularni o'qiydi.
        for name in ("server", "client", "std-server"):
            subprocess.run([aqctl, "identity", "new", "--out", str(work / name)], check=True, capture_output=True)
        subprocess.run([aqctl, "allowlist", "build", "--out", str(work / "allow.txt"),
                        str(work / "client.key.pub")], check=True, capture_output=True)
        server_pub = (work / "server.key.pub").read_text().strip()
        std_pub = str(work / "std-server.key.pub")
        demo.check("AETHER-Q server + klient identity yaratildi", (work / "server.key").exists()
                   and (work / "client.key").exists())
        demo.check("standart server identity + allowlist", (work / "std-server.key").exists()
                   and (work / "allow.txt").exists())

        print("\n[2] Servislarni ishga tushirish")
        demo.start("monolit", [monolit, "-listen", f"127.0.0.1:{PORT['monolit']}",
                               "-data", str(work / "data.json")])
        demo.check("monolit (Aether_new) javob beradi", wait_http(PORT["monolit"]))
        demo.start("aq_serve", [sidecar, "serve", "--listen", f"127.0.0.1:{PORT['aq_serve']}",
                                "--upstream", f"127.0.0.1:{PORT['monolit']}",
                                "--identity", str(work / "server.key"),
                                "--require-client-auth", "--allow", str(work / "allow.txt"),
                                "--pow", "8"])
        demo.start("aq_connect", [sidecar, "connect", "--listen", f"127.0.0.1:{PORT['aq_connect']}",
                                  "--peer", f"127.0.0.1:{PORT['aq_serve']}",
                                  "--server-pub", str(work / "server.key.pub"),
                                  "--identity", str(work / "client.key"), "--resume"])
        demo.start("gw_serve", [aqctl, "gateway", "serve", "--listen", f"127.0.0.1:{PORT['gw_serve']}",
                                "--upstream", f"127.0.0.1:{PORT['monolit']}",
                                "--identity", str(work / "std-server.key"),
                                "--metrics", f"127.0.0.1:{PORT['metrics']}"])
        demo.start("gw_connect", [aqctl, "gateway", "connect", "--listen", f"127.0.0.1:{PORT['gw_connect']}",
                                  "--peer", f"127.0.0.1:{PORT['gw_serve']}", "--server-pub", std_pub])
        time.sleep(1.5)

        print("\n[3] HTTP sinovlari")
        crud_suite(demo, "to'g'ridan-to'g'ri", PORT["monolit"])
        aq_ok = wait_http(PORT["aq_connect"], tries=40)
        demo.check("AETHER-Q tunel (sidecar connect) ishlaydi", aq_ok)
        if aq_ok:
            crud_suite(demo, "AETHER-Q tunel", PORT["aq_connect"])
        gw_ok = wait_http(PORT["gw_connect"], tries=40)
        demo.check("standart PQ-TLS gateway ishlaydi", gw_ok)
        if gw_ok:
            crud_suite(demo, "standart PQ-TLS", PORT["gw_connect"])

        print("\n[4] Resumption va PoW (sidecar log'lari)")
        time.sleep(0.5)
        connect_log = demo.log_text("aq_connect")
        resumed = connect_log.count("(resumption)")
        opened = connect_log.count("tunel ochildi")
        demo.check("ikkinchi va keyingi tunellar resumption bilan", resumed >= 1,
                   f"{opened} ta tunel, {resumed} ta resumption")
        demo.check("klient ulanishlari muvaffaqiyatli", opened >= 2 and "handshake muvaffaqiyatsiz" not in connect_log)

        print("\n[5] Latency (MEASURED, bu mashina)")
        base = latency(PORT["monolit"], args.latency_n)
        aq = latency(PORT["aq_connect"], args.latency_n) if aq_ok else []
        gw = latency(PORT["gw_connect"], args.latency_n) if gw_ok else []

        def summary(name, xs):
            if not xs:
                print(f"  {name:<28} —")
                return
            xs = sorted(xs)
            p50 = statistics.median(xs)
            p95 = xs[min(len(xs) - 1, int(len(xs) * 0.95))]
            print(f"  {name:<28} n={len(xs):<3} p50={p50:7.2f} ms  p95={p95:7.2f} ms")
        summary("to'g'ridan-to'g'ri (monolit)", base)
        summary("AETHER-Q tunel", aq)
        summary("standart PQ-TLS gateway", gw)
        if aq:
            demo.check("AETHER-Q latency tunel ishlashini tasdiqlaydi", statistics.median(aq) < 1000,
                       f"p50={statistics.median(aq):.1f} ms")

        print("\n[6] Metrika (gateway /metrics)")
        try:
            text = urllib.request.urlopen(f"http://127.0.0.1:{PORT['metrics']}/metrics", timeout=5).read().decode()
            lines = [l for l in text.splitlines() if l.startswith("aqgw_connections_total") or l.startswith("aqgw_bytes_total")]
            for l in lines:
                print("  " + l)
            demo.check("/metrics hisoblagichlari to'ldirilgan", "aqgw_connections_total" in text)
        except OSError as e:
            demo.check("/metrics ochiladi", False, str(e))

        print("\n[7] Control plane: aqctl schedule va status")
        out = subprocess.run([aqctl, "schedule", "--dir", str(work)], capture_output=True, text=True)
        try:
            sched = json.loads(out.stdout)
            demo.check("aqctl schedule (rotatsiya jadvali)", len(sched) >= 3, f"{len(sched)} ta identity")
        except ValueError:
            demo.check("aqctl schedule (rotatsiya jadvali)", False, out.stderr[:120])
        st = subprocess.run([aqctl, "status", "--dir", str(work), "--allow", str(work / "allow.txt")],
                            capture_output=True, text=True)
        print("  " + st.stdout.replace("\n", "\n  ").rstrip())

    finally:
        demo.stop_all()

    failed = [r for r in demo.results if not r[1]]
    print("\n" + "=" * 60)
    print(f"NATIJA: {len(demo.results) - len(failed)}/{len(demo.results)} tekshiruv o'tdi")
    print("ish papkasi (kalitlar, ma'lumot, loglar):", work)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
