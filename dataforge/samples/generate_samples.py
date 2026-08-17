"""Demo ma'lumotlar generatori.

Ishga tushirish::

    python samples/generate_samples.py

Yaratiladigan fayllar (barchasi ``samples/`` ichida):

* ``web_access.log``   — Apache combined access log (bot hujumi epizodi bilan)
* ``app.log``          — Python logging formatidagi ilova logi (xato portlashi bilan)
* ``syslog.log``       — RFC3164 syslog
* ``iot_sensors.csv``  — datchik telemetriyasi (nosozlik belgisi bilan) → ML uchun
* ``network_flows.jsonl`` — tarmoq oqimlari (JSON Lines)
* ``sales.xlsx``       — biznes jadvali (regressiya uchun)
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
SEED = 42


# ---------------------------------------------------------------- web log ---
def gen_web_access(n: int = 12_000) -> Path:
    rnd = random.Random(SEED)
    paths = ["/", "/index.html", "/api/v1/users", "/api/v1/orders", "/login",
             "/static/app.js", "/static/style.css", "/products", "/cart",
             "/checkout", "/admin", "/api/v1/search", "/health"]
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/17.0",
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0",
        "curl/8.4.0", "python-requests/2.31.0",
        "Mozilla/5.0 (compatible; Googlebot/2.1)",
    ]
    methods = ["GET"] * 12 + ["POST"] * 4 + ["PUT", "DELETE", "HEAD"]
    t = datetime(2024, 5, 1, 0, 0, 0)
    lines: list[str] = []

    for i in range(n):
        t += timedelta(seconds=rnd.expovariate(1 / 6.0))
        hour = t.hour
        # tunda kamroq trafik
        if hour < 6 and rnd.random() < 0.6:
            continue
        ip = f"{rnd.choice([10, 172, 192, 85, 203])}.{rnd.randint(0, 255)}." \
             f"{rnd.randint(0, 255)}.{rnd.randint(1, 254)}"
        path = rnd.choice(paths)
        method = rnd.choice(methods)
        status = rnd.choices([200, 201, 204, 301, 304, 400, 401, 403, 404, 500, 502],
                             weights=[62, 4, 3, 4, 8, 3, 3, 2, 7, 3, 1])[0]
        size = 0 if status in (204, 304) else rnd.randint(180, 48_000)
        agent = rnd.choice(agents)
        ref = rnd.choice(["-", "https://google.com/", "https://example.uz/",
                          "https://t.me/", "-"])
        lines.append(
            f'{ip} - - [{t.strftime("%d/%b/%Y:%H:%M:%S +0500")}] '
            f'"{method} {path} HTTP/1.1" {status} {size} "{ref}" "{agent}"'
        )

        # 3-kuni: bot skanerlash epizodi (anomaliya)
        if t.day == 3 and t.hour == 4 and rnd.random() < 0.08:
            attacker = "45.155.205.233"
            for probe in ["/wp-admin", "/.env", "/phpmyadmin", "/admin/config.php",
                          "/.git/config", "/backup.sql"]:
                t += timedelta(milliseconds=rnd.randint(20, 200))
                lines.append(
                    f'{attacker} - - [{t.strftime("%d/%b/%Y:%H:%M:%S +0500")}] '
                    f'"GET {probe} HTTP/1.1" 404 162 "-" "python-requests/2.31.0"'
                )

    p = OUT / "web_access.log"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


# ---------------------------------------------------------------- app log ---
def gen_app_log(n: int = 8_000) -> Path:
    rnd = random.Random(SEED + 1)
    loggers = ["api.auth", "api.orders", "db.pool", "cache.redis", "worker.email",
               "scheduler", "payments.gateway"]
    templates = [
        ("INFO", "Foydalanuvchi {uid} tizimga kirdi, sessiya {sid}"),
        ("INFO", "So'rov bajarildi: {method} {path} — {ms}ms"),
        ("DEBUG", "Cache hit key=user:{uid} ttl={ms}s"),
        ("INFO", "Buyurtma yaratildi id={oid} summa={amt}"),
        ("WARN", "Sekin so'rov: {path} {ms}ms chegaradan oshdi"),
        ("WARN", "Ulanishlar hovuzi {ms}% to'lgan"),
        ("ERROR", "DB ulanishi uzildi: timeout after {ms}ms host=db-{uid}"),
        ("ERROR", "To'lov rad etildi order={oid} kod=INSUFFICIENT_FUNDS"),
        ("CRITICAL", "Xizmat javob bermayapti: worker-{uid} qayta ishga tushirilmoqda"),
    ]
    weights = [22, 30, 14, 12, 7, 5, 5, 3, 2]
    t = datetime(2024, 5, 1, 0, 0, 0)
    lines: list[str] = []

    for i in range(n):
        t += timedelta(seconds=rnd.expovariate(1 / 9.0))
        # 12:00–12:20 oralig'ida xato portlashi
        burst = t.hour == 12 and t.minute < 20 and t.day == 2
        if burst:
            level, tmpl = rnd.choice(templates[6:])
        else:
            level, tmpl = rnd.choices(templates, weights=weights)[0]
        msg = tmpl.format(uid=rnd.randint(1, 900), sid=f"{rnd.getrandbits(48):012x}",
                          method=rnd.choice(["GET", "POST"]),
                          path=rnd.choice(["/api/v1/users", "/api/v1/orders", "/login"]),
                          ms=rnd.randint(3, 4200), oid=rnd.randint(10_000, 99_999),
                          amt=round(rnd.uniform(10_000, 4_000_000), 2))
        lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} - "
                     f"{rnd.choice(loggers)} - {level} - {msg}")

    p = OUT / "app.log"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


# ----------------------------------------------------------------- syslog ---
def gen_syslog(n: int = 3_000) -> Path:
    rnd = random.Random(SEED + 2)
    procs = ["sshd", "kernel", "systemd", "cron", "nginx", "docker", "ufw"]
    msgs = [
        "Accepted password for {user} from {ip} port {port} ssh2",
        "Failed password for invalid user {user} from {ip} port {port} ssh2",
        "Started Session {n} of user {user}.",
        "[UFW BLOCK] IN=eth0 OUT= SRC={ip} DST=10.0.0.5 PROTO=TCP SPT={port} DPT=22",
        "usb {n}-1: new high-speed USB device number {n}",
        "container {cid} started image=nginx:latest",
        "CRON[{n}]: (root) CMD (/usr/bin/backup.sh)",
    ]
    t = datetime(2024, 5, 1, 0, 0, 0)
    lines = []
    for _ in range(n):
        t += timedelta(seconds=rnd.randint(1, 90))
        m = rnd.choice(msgs).format(
            user=rnd.choice(["root", "admin", "deploy", "postgres", "test"]),
            ip=f"{rnd.randint(1, 223)}.{rnd.randint(0, 255)}.{rnd.randint(0, 255)}.{rnd.randint(1, 254)}",
            port=rnd.randint(1024, 65535), n=rnd.randint(1, 9999),
            cid=f"{rnd.getrandbits(48):012x}")
        lines.append(f"{t.strftime('%b %e %H:%M:%S')} srv-01 "
                     f"{rnd.choice(procs)}[{rnd.randint(100, 30000)}]: {m}")
    p = OUT / "syslog.log"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


# --------------------------------------------------------------- IoT CSV ----
def gen_iot(n: int = 20_000) -> Path:
    """Datchik telemetriyasi — ML klassifikatsiya uchun 'nosozlik' nishoni bilan."""
    rng = np.random.default_rng(SEED)
    t0 = datetime(2024, 5, 1)
    ts = [t0 + timedelta(minutes=3 * i) for i in range(n)]
    devices = np.array([f"SN-{i:03d}" for i in range(1, 13)])
    dev = rng.choice(devices, n)
    zones = {d: z for d, z in zip(devices, rng.choice(["ombor", "sex-1", "sex-2", "ofis"],
                                                      len(devices)))}

    hours = np.array([t.hour for t in ts])
    day = np.array([t.timetuple().tm_yday for t in ts])
    base_t = 22 + 6 * np.sin(2 * np.pi * hours / 24) + 2 * np.sin(2 * np.pi * day / 30)
    temp = base_t + rng.normal(0, 1.1, n)
    hum = 55 - 0.9 * (temp - 22) + rng.normal(0, 4, n)
    press = 1013 + rng.normal(0, 2.5, n) - 0.05 * (temp - 22)
    volt = 3.7 - 0.00002 * np.arange(n) + rng.normal(0, 0.02, n)
    vib = np.abs(rng.gamma(2.0, 0.35, n))
    rssi = -55 - 12 * rng.random(n) + rng.normal(0, 3, n)

    # Nosozlik: yuqori harorat + kuchli tebranish + past kuchlanish
    risk = (0.06 * (temp - 28) + 0.55 * (vib - 1.4) + 3.2 * (3.55 - volt)
            + rng.normal(0, 0.35, n))
    fault = (risk > 0.9).astype(int)
    # nosozlik paytida ko'rsatkichlar buziladi
    temp = temp + fault * rng.normal(4.5, 1.2, n)
    vib = vib + fault * rng.normal(1.6, 0.5, n)

    # ba'zi bo'sh qiymatlar va anomaliyalar
    hum[rng.choice(n, size=n // 90, replace=False)] = np.nan
    spike = rng.choice(n, size=45, replace=False)
    temp[spike] = temp[spike] + rng.normal(28, 6, len(spike))

    df = pd.DataFrame({
        "timestamp": ts,
        "device_id": dev,
        "zona": [zones[d] for d in dev],
        "harorat_c": temp.round(2),
        "namlik_pct": np.round(hum, 2),
        "bosim_hpa": press.round(2),
        "kuchlanish_v": volt.round(3),
        "tebranish_g": vib.round(3),
        "rssi_dbm": rssi.round(1),
        "nosozlik": fault,
    })
    df["holat"] = np.where(df["nosozlik"] == 1, "xato",
                           np.where(df["harorat_c"] > 30, "ogohlantirish", "normal"))
    p = OUT / "iot_sensors.csv"
    df.to_csv(p, index=False, encoding="utf-8")
    return p


# ----------------------------------------------------------- network flows --
def gen_flows(n: int = 9_000) -> Path:
    rng = np.random.default_rng(SEED + 3)
    rnd = random.Random(SEED + 3)
    t0 = datetime(2024, 5, 1)
    protos = ["TCP", "UDP", "ICMP"]
    apps = ["https", "dns", "http", "ssh", "smtp", "quic", "rdp", "smb"]
    lines = []
    for i in range(n):
        t = t0 + timedelta(seconds=float(rng.exponential(4)) * i / 12)
        proto = rnd.choices(protos, weights=[70, 26, 4])[0]
        app = rnd.choices(apps, weights=[45, 18, 10, 6, 4, 9, 4, 4])[0]
        dur = float(abs(rng.gamma(1.8, 1.6)))
        pkts = int(abs(rng.gamma(2.2, 14)) + 1)
        bytes_ = int(pkts * abs(rng.normal(640, 320)) + 40)
        suspicious = int(app in ("rdp", "smb") and pkts > 60 and rnd.random() < 0.35)
        rec = {
            "ts": t.isoformat(timespec="milliseconds"),
            "src_ip": f"10.0.{rnd.randint(0, 4)}.{rnd.randint(2, 254)}",
            "dst_ip": f"{rnd.randint(1, 223)}.{rnd.randint(0, 255)}."
                      f"{rnd.randint(0, 255)}.{rnd.randint(1, 254)}",
            "src_port": rnd.randint(1024, 65535),
            "dst_port": {"https": 443, "dns": 53, "http": 80, "ssh": 22,
                         "smtp": 25, "quic": 443, "rdp": 3389, "smb": 445}[app],
            "proto": proto,
            "app": app,
            "duration_s": round(dur, 3),
            "packets": pkts,
            "bytes": bytes_,
            "flags": rnd.choice(["SYN,ACK", "ACK", "FIN,ACK", "RST", "SYN"]),
            "suspicious": suspicious,
        }
        lines.append(json.dumps(rec, ensure_ascii=False))
    p = OUT / "network_flows.jsonl"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


# ------------------------------------------------------------------ sales ---
def gen_sales(n: int = 4_000) -> Path:
    rng = np.random.default_rng(SEED + 4)
    rnd = random.Random(SEED + 4)
    regions = ["Toshkent", "Samarqand", "Buxoro", "Farg'ona", "Namangan", "Xorazm"]
    cats = ["Elektronika", "Oziq-ovqat", "Kiyim", "Qurilish", "Maishiy texnika"]
    channels = ["do'kon", "onlayn", "ulgurji"]
    t0 = datetime(2023, 1, 1)
    rows = []
    for i in range(n):
        d = t0 + timedelta(days=int(rng.integers(0, 730)))
        region = rnd.choice(regions)
        cat = rnd.choice(cats)
        ch = rnd.choices(channels, weights=[50, 35, 15])[0]
        qty = int(abs(rng.gamma(2.0, 3)) + 1)
        unit = float(abs(rng.normal({"Elektronika": 3_500_000, "Oziq-ovqat": 45_000,
                                     "Kiyim": 260_000, "Qurilish": 180_000,
                                     "Maishiy texnika": 2_100_000}[cat], 60_000)))
        disc = round(rnd.choice([0, 0, 0, 5, 10, 15]) / 100, 2)
        season = 1 + 0.18 * np.sin(2 * np.pi * d.timetuple().tm_yday / 365)
        revenue = qty * unit * (1 - disc) * season
        rows.append({
            "sana": d, "hudud": region, "kategoriya": cat, "kanal": ch,
            "miqdor": qty, "birlik_narx": round(unit, 2), "chegirma": disc,
            "mijoz_yoshi": int(np.clip(rng.normal(37, 12), 18, 78)),
            "takroriy_mijoz": int(rng.random() < 0.42),
            "tushum": round(revenue, 2),
        })
    df = pd.DataFrame(rows).sort_values("sana").reset_index(drop=True)
    p = OUT / "sales.xlsx"
    try:
        df.to_excel(p, index=False)
    except Exception:
        p = OUT / "sales.csv"
        df.to_csv(p, index=False, encoding="utf-8")
    return p


def generate_all(verbose: bool = True) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    made = [gen_web_access(), gen_app_log(), gen_syslog(), gen_iot(),
            gen_flows(), gen_sales()]
    if verbose:
        for p in made:
            print(f"  ✓ {p.name:22s} {p.stat().st_size / 1024:8.1f} KB")
    return made


if __name__ == "__main__":
    print("Demo ma'lumotlar yaratilmoqda…")
    generate_all()
    print(f"\nTayyor → {OUT}")
