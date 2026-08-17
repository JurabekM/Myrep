#!/usr/bin/env python3
"""
GCOM (LuCI) 4G/5G modem status logger.

Ma'lumot manbasi: http://<router-ip>/cgi-bin/luci/admin/network/gcom?iface=<iface>
Sahifadagi barcha ko'rsatkichlarni (RSSI, RSRP, RSRQ, SINR, IMEI, IMSI va h.k.)
o'qib, CSV yoki JSON-Lines log fayliga vaqt tamg'asi bilan yozadi.

Ishlatish:
    python logger.py --once                     # bir marta o'qib logga yozadi
    python logger.py                             # config.ini dagi interval bilan doimiy ishlaydi
    python logger.py --interval 60 --format jsonl

Konfiguratsiya config.ini fayl orqali (config.example.ini dan nusxa oling) yoki
--url / --username / --password / --iface CLI argumentlari orqali beriladi.
Muhit o'zgaruvchilari ham qo'llab-quvvatlanadi: GCOM_URL, GCOM_USERNAME, GCOM_PASSWORD, GCOM_IFACE.
"""

import argparse
import configparser
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_CONFIG = SCRIPT_DIR / "config.ini"

# LuCI sahifasidagi rus tilidagi yorliqlarni barqaror ustun nomlariga moslash.
# Kalitlar pastki registrga, ":" siz, ortiqcha bo'shliqsiz solishtiriladi.
LABEL_MAP = {
    "состояние": "state",
    "тип сети": "network_type",
    "исх. трафик / вх. трафик": "traffic_tx_rx_mb",
    "rssi": "rssi",
    "внешний ip-адрес": "external_ip",
    "ip-адрес": "ip_address",
    "время подключения": "connection_uptime",
    "imsi": "imsi",
    "imei": "imei",
    "iccid": "iccid",
    "режим": "duplex_mode",
    "mcc": "mcc",
    "mnc": "mnc",
    "cid": "cid",
    "pcid": "pcid",
    "диапазон": "band",
    "исх. пропускная способность": "bandwidth_ul",
    "входящая пропускная способность": "bandwidth_dl",
    "rsrp": "rsrp",
    "rsrq": "rsrq",
    "sinr": "sinr",
    "pcc": "pcc",
    "scc": "scc",
}

# Carrier aggregation yoqilganda PCC/SCC qatorlari sahifada bir necha marta
# takrorlanishi mumkin (masalan 2CA/3CA rejimida bir nechta SCC). Shu maydonlar
# uchun barcha qiymatlarni ro'yxatga yig'amiz, keyin belgilangan sondagi ustunlarga
# (pcc_1..pcc_2, scc_1..scc_4) taqsimlaymiz - agar shu sondan ortiq chiqsa, ortig'i
# oxirgi ustunga "; " bilan qo'shib yoziladi, hech qanday ma'lumot yo'qolmasin.
MULTI_VALUE_SLOTS = {"pcc": 2, "scc": 4}

# CSV ustunlari shu tartibda yoziladi.
FIELD_ORDER = [
    "timestamp",
    "state",
    "network_type",
    "traffic_tx_rx_mb",
    "rssi",
    "external_ip",
    "ip_address",
    "connection_uptime",
    "imsi",
    "imei",
    "iccid",
    "duplex_mode",
    "mcc",
    "mnc",
    "cid",
    "pcid",
    "band",
    "bandwidth_ul",
    "bandwidth_dl",
    "rsrp",
    "rsrq",
    "sinr",
    "pcc_1",
    "pcc_2",
    "scc_1",
    "scc_2",
    "scc_3",
    "scc_4",
    "scc_count",
]


def normalize_label(text: str) -> str:
    text = text.strip().rstrip(":").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def load_config(path: Path) -> dict:
    cfg = {
        "url": "http://192.168.8.144",
        "username": "admin",
        "password": "admin123",
        "iface": "4g",
        "interval": 60,
        "logfile": str(SCRIPT_DIR / "gcom_signal_log.csv"),
        "format": "csv",
    }
    if path.exists():
        parser = configparser.ConfigParser()
        parser.read(path, encoding="utf-8")
        if "gcom" in parser:
            section = parser["gcom"]
            cfg["url"] = section.get("url", cfg["url"])
            cfg["username"] = section.get("username", cfg["username"])
            cfg["password"] = section.get("password", cfg["password"])
            cfg["iface"] = section.get("iface", cfg["iface"])
            cfg["interval"] = section.getint("interval", cfg["interval"])
            cfg["logfile"] = section.get("logfile", cfg["logfile"])
            cfg["format"] = section.get("format", cfg["format"])

    # Muhit o'zgaruvchilari config.ini dan ustun turadi.
    cfg["url"] = os.environ.get("GCOM_URL", cfg["url"])
    cfg["username"] = os.environ.get("GCOM_USERNAME", cfg["username"])
    cfg["password"] = os.environ.get("GCOM_PASSWORD", cfg["password"])
    cfg["iface"] = os.environ.get("GCOM_IFACE", cfg["iface"])
    return cfg


def login(session: requests.Session, base_url: str, username: str, password: str) -> bool:
    """Bu LuCI (Cudy firmware) parolni ochiq matnda yubormaydi: login sahifasidan
    "salt" va "_csrf" olinadi, /admin/get_token dan bir martalik "token" so'raladi,
    so'ng parol ikki bosqichli SHA-256 bilan xeshlanadi (sysauth.js dagi mantiqqa mos):
        h1 = sha256(password + salt)
        luci_password = sha256(h1 + token)
    """
    base = base_url.rstrip("/")
    login_url = f"{base}/cgi-bin/luci/"

    # Eslatma: bu router (Cudy firmware) login sahifasini ba'zan 403 status bilan
    # qaytaradi, lekin tanasida to'liq login formasi keladi - shuning uchun status
    # kodini emas, javob tanasidagi maydonlarni tekshiramiz.
    page = session.get(login_url, timeout=15)

    def extract(name: str) -> str:
        m = re.search(rf'name="{name}"[^>]*value="([^"]*)"', page.text)
        return m.group(1) if m else ""

    csrf = extract("_csrf")
    salt = extract("salt")

    token_resp = session.post(f"{base}/cgi-bin/luci/admin/get_token", timeout=15)
    token_resp.raise_for_status()
    token = token_resp.text.strip()

    if salt:
        h1 = hashlib.sha256((password + salt).encode()).hexdigest()
        luci_password = hashlib.sha256((h1 + token).encode()).hexdigest() if token else h1
    else:
        luci_password = password

    resp = session.post(
        login_url,
        data={
            "_csrf": csrf,
            "token": token,
            "salt": salt,
            "zonename": "UTC",
            "timeclock": str(int(time.time())),
            "luci_language": "ru",
            "luci_username": username,
            "luci_password": luci_password,
        },
        timeout=15,
        allow_redirects=True,
    )
    resp.raise_for_status()
    # Muvaffaqiyatli kirishda LuCI "sysauth" (yoki "sysauth_http") cookie beradi.
    return any(name.startswith("sysauth") for name in session.cookies.keys())


def fetch_status_html(session: requests.Session, base_url: str, iface: str) -> str:
    """Status jadvali sahifada emas, JS orqali yuklanadigan AJAX bo'lagida keladi
    (LuCI cbi_xhr_load -> POST /admin/network/gcom/status, body: detail=1&iface=<iface>)."""
    status_url = f"{base_url.rstrip('/')}/cgi-bin/luci/admin/network/gcom/status"
    resp = session.post(
        status_url,
        data=f"detail=1&iface={iface}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.text


def cell_text(cell) -> str:
    """LuCI GCOM jadvalida har bir katak matni ikki marta takrorlanadi
    (masalan <p class="hidden-xs"> va <p class="visible-xs"> bir xil matn bilan) -
    faqat birinchi <p> ni olamiz, aks holda "RSSI RSSI" kabi qo'shilib ketadi."""
    p = cell.find("p")
    text = p.get_text(" ", strip=True) if p is not None else cell.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _collect_pairs(soup: BeautifulSoup) -> list:
    """(normallashtirilgan_label, qiymat) juftliklari ro'yxatini, sahifadagi
    tartibda, takrorlanishlarni yo'qotmasdan qaytaradi."""
    pairs = []
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) == 3:
            # Haqiqiy GCOM status jadvali: [bo'sh katak, yorliq, qiymat]
            label_cell, value_cell = cells[1], cells[2]
        elif len(cells) == 2:
            label_cell, value_cell = cells[0], cells[1]
        else:
            continue
        label = normalize_label(cell_text(label_cell))
        value = cell_text(value_cell)
        if label and value:
            pairs.append((label, value))

    # Ba'zi LuCI temalarida jadval o'rniga <div class="cbi-value">yorliq</div><div>qiymat</div>
    # ko'rinishida bo'lishi mumkin - shuni ham qamrab olamiz.
    if len(pairs) < 5:
        for value_div in soup.find_all(class_=re.compile("cbi-value")):
            label_el = value_div.find(class_=re.compile("cbi-value-title"))
            data_el = value_div.find(class_=re.compile("cbi-value-field"))
            if label_el and data_el:
                label = normalize_label(label_el.get_text(" ", strip=True))
                value = data_el.get_text(" ", strip=True)
                if label and value:
                    pairs.append((label, value))

    return pairs


def parse_status(html: str) -> dict:
    """Carrier aggregation yoqilganda PCC bir marta, SCC esa bir necha marta
    (2CA/3CA/4CA rejimida) takrorlanishi mumkin - masalan foydalanuvchi diapazon
    o'zgartirganda 2 ta SCC qatori paydo bo'lishi kuzatilgan. Shu sabab bir xil
    yorliqning barcha uchrashuvlarini ro'yxatga yig'amiz, keyin pcc_1/pcc_2,
    scc_1..scc_4 ustunlariga taqsimlaymiz; slotlardan ortsa, ortig'i oxirgi
    ustunga "; " bilan qo'shib yoziladi - hech qanday qiymat yo'qolmaydi."""
    soup = BeautifulSoup(html, "html.parser")
    multi_values = {key: [] for key in MULTI_VALUE_SLOTS}
    result = {}

    for label, value in _collect_pairs(soup):
        key = LABEL_MAP.get(label)
        if not key:
            continue
        if key in multi_values:
            multi_values[key].append(value)
        else:
            result[key] = value

    for key, slots in MULTI_VALUE_SLOTS.items():
        values = multi_values[key]
        if key == "scc":
            result["scc_count"] = str(len(values))
        for i in range(slots):
            column = f"{key}_{i + 1}"
            if i < slots - 1:
                result[column] = values[i] if i < len(values) else ""
            else:
                # Oxirgi ustun: kutilganidan ortiq qiymat bo'lsa, hammasini qo'shib yozamiz.
                overflow = values[i:]
                result[column] = "; ".join(overflow) if overflow else ""

    return result


def append_log(logfile: Path, fmt: str, record: dict):
    logfile.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "jsonl":
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    else:
        write_header = not logfile.exists() or logfile.stat().st_size == 0
        with open(logfile, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELD_ORDER)
            if write_header:
                writer.writeheader()
            writer.writerow({k: record.get(k, "") for k in FIELD_ORDER})


def collect_once(cfg: dict, session: requests.Session) -> dict:
    html = fetch_status_html(session, cfg["url"], cfg["iface"])
    data = parse_status(html)
    if len(data) < 5:
        # Sessiya eskirgan bo'lishi mumkin - qayta login qilib bir marta urinib ko'ramiz.
        if login(session, cfg["url"], cfg["username"], cfg["password"]):
            html = fetch_status_html(session, cfg["url"], cfg["iface"])
            data = parse_status(html)
    data["timestamp"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    return data


def main():
    parser = argparse.ArgumentParser(description="GCOM 4G/5G modem status logger")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="config.ini fayl yo'li")
    parser.add_argument("--url", help="Router bazaviy manzili, masalan http://192.168.8.144")
    parser.add_argument("--username", help="LuCI login")
    parser.add_argument("--password", help="LuCI parol")
    parser.add_argument("--iface", help="Interfeys nomi (masalan: 4g)")
    parser.add_argument("--interval", type=int, help="So'rovlar orasidagi interval (sekund)")
    parser.add_argument("--logfile", help="Log fayl yo'li")
    parser.add_argument("--format", choices=["csv", "jsonl"], help="Log fayl formati")
    parser.add_argument("--once", action="store_true", help="Faqat bir marta o'qib, natijani chiqarish")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    for key in ("url", "username", "password", "iface", "interval", "logfile", "format"):
        cli_value = getattr(args, key)
        if cli_value is not None:
            cfg[key] = cli_value

    logfile = Path(cfg["logfile"])
    session = requests.Session()

    print(f"[{datetime.now().isoformat(timespec='seconds')}] {cfg['url']} manziliga kirilmoqda...")
    if not login(session, cfg["url"], cfg["username"], cfg["password"]):
        print("XATO: LuCI ga login qilib bo'lmadi. Login/parolni tekshiring.", file=sys.stderr)
        sys.exit(1)
    print("Login muvaffaqiyatli. Modem holati o'qilmoqda...")

    if args.once:
        record = collect_once(cfg, session)
        append_log(logfile, cfg["format"], record)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        print(f"Yozildi: {logfile}")
        return

    print(f"Har {cfg['interval']} sekundda kuzatiladi. To'xtatish uchun Ctrl+C. Log: {logfile}")
    try:
        while True:
            try:
                record = collect_once(cfg, session)
                append_log(logfile, cfg["format"], record)
                summary = (
                    f"[{record.get('timestamp')}] RSSI={record.get('rssi')} "
                    f"RSRP={record.get('rsrp')} RSRQ={record.get('rsrq')} SINR={record.get('sinr')} "
                    f"Band={record.get('band')} Type={record.get('network_type')}"
                )
                print(summary)
            except requests.RequestException as e:
                print(f"So'rov xatosi: {e}", file=sys.stderr)
            time.sleep(cfg["interval"])
    except KeyboardInterrupt:
        print("\nTo'xtatildi.")


if __name__ == "__main__":
    main()
