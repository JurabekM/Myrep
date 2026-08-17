"""
GCOM Signal Monitor uchun tahlil qatlami: CSV qatorlarini tipланган
DataFrame'ga aylantirish, statistik xulosalar, band bo'yicha taqqoslash,
korrelyatsiya va hodisalarni (uzilish/handover/band almashinuvi/sifat
pasayishi) avtomatik aniqlash.
"""

import re
from datetime import datetime

import numpy as np
import pandas as pd

CONNECTED_TEXT = "Есть подключение"

_TRAFFIC_UNIT_MULT = {"КБ": 1 / 1024, "KB": 1 / 1024, "МБ": 1.0, "MB": 1.0, "ГБ": 1024.0, "GB": 1024.0}

# RSRP/RSRQ/SINR uchun sifat toifalari (yomondan yaxshiga) - hodisa aniqlashda
# toifa pasayishi/ko'tarilishini kuzatish uchun ishlatiladi.
QUALITY_BUCKETS = {
    "rsrp": [(-1e9, "Yomon"), (-105, "O'rta"), (-90, "Yaxshi")],
    "rsrq": [(-1e9, "Yomon"), (-15, "O'rta"), (-10, "Yaxshi")],
    "sinr": [(-1e9, "Yomon"), (0, "O'rta"), (13, "Yaxshi")],
}


def quality_bucket(metric: str, value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "?"
    bucket = "Yomon"
    for limit, name in QUALITY_BUCKETS.get(metric, []):
        if value >= limit:
            bucket = name
    return bucket


def parse_float(value):
    try:
        if value in (None, ""):
            return np.nan
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def parse_traffic_mb(value: str):
    if not value or "/" not in value:
        return np.nan, np.nan

    def to_mb(part: str):
        m = re.match(r"([\d.]+)\s*(КБ|МБ|ГБ|KB|MB|GB)", part.strip(), re.IGNORECASE)
        if not m:
            return np.nan
        return float(m.group(1)) * _TRAFFIC_UNIT_MULT.get(m.group(2).upper(), 1.0)

    tx_str, rx_str = value.split("/", 1)
    return to_mb(tx_str), to_mb(rx_str)


def parse_uptime_seconds(value: str):
    if not value:
        return np.nan
    parts = value.strip().split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return np.nan
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts[-3:]
    return h * 3600 + m * 60 + s


_CARRIER_RE = re.compile(r"BAND\s*(\d+)", re.IGNORECASE)
_BANDWIDTH_RE = re.compile(r"(\d+\s*MHz)", re.IGNORECASE)


def parse_carrier(value: str):
    """`'"LTE BAND 3" / 15MHz'` -> ("B3", "15MHz"). Bo'sh yoki tanib
    bo'lmaydigan qiymat uchun (None, None) qaytaradi."""
    if not value:
        return None, None
    band_m = _CARRIER_RE.search(value)
    band = f"B{band_m.group(1)}" if band_m else value.strip()
    bw_m = _BANDWIDTH_RE.search(value)
    bandwidth = bw_m.group(1).replace(" ", "") if bw_m else ""
    return band, bandwidth


def carrier_components(rec: dict) -> list:
    """Bitta qatordagi barcha faol component-carrier'larni (PCC + SCC lar)
    [(rol, band, bandwidth), ...] ro'yxati sifatida qaytaradi."""
    components = []
    pcc_band, pcc_bw = parse_carrier(rec.get("pcc_1", ""))
    if pcc_band:
        components.append(("PCC", pcc_band, pcc_bw))
    for i in range(1, 5):
        scc_band, scc_bw = parse_carrier(rec.get(f"scc_{i}", ""))
        if scc_band:
            components.append((f"SCC{i}", scc_band, scc_bw))
    return components


def ca_combo_signature(rec: dict) -> str:
    """CA konfiguratsiyasini taqqoslash uchun barqaror imzo hosil qiladi:
    band nomlari saralanib, "+" bilan qo'shiladi (masalan "B1+B3+B20").
    Faqat PCC bo'lsa (CA yo'q holat) bitta band nomi qaytadi."""
    bands = sorted({band for _, band, _ in carrier_components(rec)})
    return "+".join(bands) if bands else ""


def row_to_record(raw: dict) -> dict:
    """CSV qatoridagi xom (string) qiymatlarni tiplangan yozuvga aylantiradi."""
    try:
        ts = datetime.fromisoformat(raw.get("timestamp", ""))
    except ValueError:
        return None

    tx_mb, rx_mb = parse_traffic_mb(raw.get("traffic_tx_rx_mb", ""))
    scc_count_raw = raw.get("scc_count", "")
    try:
        scc_count = int(scc_count_raw) if scc_count_raw else 0
    except ValueError:
        scc_count = 0

    rec = {
        "ts": ts,
        "epoch": ts.timestamp(),
        "state": raw.get("state", ""),
        "connected": raw.get("state", "") == CONNECTED_TEXT,
        "network_type": raw.get("network_type", ""),
        "band": raw.get("band", ""),
        "duplex_mode": raw.get("duplex_mode", ""),
        "cid": raw.get("cid", ""),
        "pcid": raw.get("pcid", ""),
        "mcc": raw.get("mcc", ""),
        "mnc": raw.get("mnc", ""),
        "external_ip": raw.get("external_ip", ""),
        "uptime_s": parse_uptime_seconds(raw.get("connection_uptime", "")),
        "rssi": parse_float(raw.get("rssi")),
        "rsrp": parse_float(raw.get("rsrp")),
        "rsrq": parse_float(raw.get("rsrq")),
        "sinr": parse_float(raw.get("sinr")),
        "tx_mb": tx_mb,
        "rx_mb": rx_mb,
        "scc_count": scc_count,
        "pcc_1": raw.get("pcc_1", ""),
        "scc_1": raw.get("scc_1", ""),
        "scc_2": raw.get("scc_2", ""),
        "scc_3": raw.get("scc_3", ""),
        "scc_4": raw.get("scc_4", ""),
        "bandwidth_ul": raw.get("bandwidth_ul", ""),
        "bandwidth_dl": raw.get("bandwidth_dl", ""),
    }
    rec["ca_combo"] = ca_combo_signature(rec)
    return rec


def empty_dataframe() -> pd.DataFrame:
    return pd.DataFrame()


def filter_window(df: pd.DataFrame, minutes: int = None) -> pd.DataFrame:
    if df.empty or not minutes:
        return df
    cutoff = df["epoch"].max() - minutes * 60
    return df[df["epoch"] >= cutoff]


def compute_stats(df: pd.DataFrame, column: str) -> dict:
    series = df[column].dropna() if column in df else pd.Series(dtype=float)
    if series.empty:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "std": None, "p5": None, "p95": None}
    return {
        "count": int(series.count()),
        "min": float(series.min()),
        "max": float(series.max()),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "std": float(series.std()) if series.count() > 1 else 0.0,
        "p5": float(series.quantile(0.05)),
        "p95": float(series.quantile(0.95)),
    }


def band_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["band", "count", "pct", "rsrp", "rsrq", "sinr", "rssi"])
    total = len(df)
    grouped = (
        df[df["band"] != ""]
        .groupby("band")
        .agg(count=("band", "size"), rsrp=("rsrp", "mean"), rsrq=("rsrq", "mean"), sinr=("sinr", "mean"), rssi=("rssi", "mean"))
        .reset_index()
    )
    grouped["pct"] = grouped["count"] / total * 100.0
    return grouped.sort_values("count", ascending=False)


def ca_combo_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Har bir carrier-aggregation konfiguratsiyasi (masalan "B3+B20+B1")
    qancha marta uchraganini, umumiy vaqt ulushini va o'sha konfiguratsiyadagi
    o'rtacha signal sifatini hisoblaydi."""
    if df.empty or "ca_combo" not in df:
        return pd.DataFrame(columns=["combo", "count", "pct", "rsrp", "sinr"])
    connected = df[(df["connected"]) & (df["ca_combo"] != "")]
    if connected.empty:
        return pd.DataFrame(columns=["combo", "count", "pct", "rsrp", "sinr"])
    total = len(df)
    grouped = (
        connected.groupby("ca_combo")
        .agg(count=("ca_combo", "size"), rsrp=("rsrp", "mean"), sinr=("sinr", "mean"))
        .reset_index()
        .rename(columns={"ca_combo": "combo"})
    )
    grouped["pct"] = grouped["count"] / total * 100.0
    return grouped.sort_values("count", ascending=False)


def scc_count_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Bir vaqtning o'zida nechta component-carrier (0,1,2,3,4) faol
    bo'lganini - ya'ni CA qancha vaqt ishlatilganini - taqsimot sifatida
    qaytaradi."""
    if df.empty or "scc_count" not in df:
        return pd.DataFrame(columns=["scc_count", "count", "pct"])
    connected = df[df["connected"]]
    if connected.empty:
        return pd.DataFrame(columns=["scc_count", "count", "pct"])
    total = len(connected)
    grouped = connected.groupby("scc_count").size().reset_index(name="count")
    grouped["pct"] = grouped["count"] / total * 100.0
    return grouped.sort_values("scc_count")


def carrier_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """Har bir jismoniy diapazon (B1, B3, B20 va h.k.) component-carrier
    sifatida (PCC yoki SCC bo'lib) jami nechta qatorda ishtirok etganini
    hisoblaydi - qaysi bandlar tez-tez CA'ga jalb qilinishini ko'rsatadi."""
    if df.empty:
        return pd.DataFrame(columns=["band", "as_pcc", "as_scc", "total"])
    counts = {}
    for _, row in df[df["connected"]].iterrows():
        for role, band, _bw in carrier_components(row):
            entry = counts.setdefault(band, {"as_pcc": 0, "as_scc": 0})
            if role == "PCC":
                entry["as_pcc"] += 1
            else:
                entry["as_scc"] += 1
    records = [
        {"band": band, "as_pcc": v["as_pcc"], "as_scc": v["as_scc"], "total": v["as_pcc"] + v["as_scc"]}
        for band, v in counts.items()
    ]
    return pd.DataFrame(records, columns=["band", "as_pcc", "as_scc", "total"]).sort_values("total", ascending=False)


def correlation_matrix(df: pd.DataFrame, columns=("rssi", "rsrp", "rsrq", "sinr")) -> pd.DataFrame:
    cols = [c for c in columns if c in df]
    if df.empty or len(cols) < 2:
        return pd.DataFrame()
    return df[list(cols)].corr()


def hourly_profile(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    if df.empty or metric not in df:
        return pd.DataFrame(columns=["hour", metric])
    tmp = df.copy()
    tmp["hour"] = tmp["ts"].dt.hour
    return tmp.groupby("hour")[metric].mean().reindex(range(24)).reset_index()


def summarize_reliability(df: pd.DataFrame) -> dict:
    """Uzilishlar soni, o'rtacha sessiya davomiyligi (soniyada) va umumiy
    onlayn foizini hisoblaydi (`connected` ustunidagi False->True o'tishlar
    asosida)."""
    if df.empty:
        return {"disconnects": 0, "avg_session_s": None, "uptime_pct": None}
    connected = df["connected"].fillna(False)
    disconnects = int(((connected.shift(1) == True) & (connected == False)).sum())
    sessions = df.loc[connected, "uptime_s"].dropna()
    avg_session = float(sessions.mean()) if not sessions.empty else None
    uptime_pct = float(connected.mean() * 100.0)
    return {"disconnects": disconnects, "avg_session_s": avg_session, "uptime_pct": uptime_pct}


class EventDetector:
    """Yangi qator kelganda, oldingi qator bilan solishtirib hodisalar
    ro'yxatini (uzilish, handover, band/CA o'zgarishi, sifat pasayishi)
    hosil qiladi. Har chaqiriqda faqat YANGI hodisalarni qaytaradi."""

    def __init__(self):
        self.prev = None

    def push(self, rec: dict) -> list:
        events = []
        prev = self.prev
        self.prev = rec
        if prev is None:
            events.append(self._event(rec, "info", "Kuzatuv boshlandi", f"Band {rec['band'] or '?'}, holat: {rec['state'] or '?'}"))
            return events

        if prev["connected"] and not rec["connected"]:
            events.append(self._event(rec, "critical", "Ulanish uzildi", f"Oxirgi band: {prev['band']}"))
        elif not prev["connected"] and rec["connected"]:
            events.append(self._event(rec, "success", "Qayta ulandi", f"Band {rec['band']}"))

        if rec["band"] and prev["band"] and rec["band"] != prev["band"]:
            events.append(self._event(rec, "info", "Band almashdi", f"{prev['band']} → {rec['band']}"))
        elif rec["connected"] and prev["connected"] and rec["band"] == prev["band"] and (
            (rec["cid"] and prev["cid"] and rec["cid"] != prev["cid"])
            or (rec["pcid"] and prev["pcid"] and rec["pcid"] != prev["pcid"])
        ):
            events.append(self._event(rec, "info", "Handover (uyali minora almashdi)", f"CID {prev['cid']}→{rec['cid']}, PCID {prev['pcid']}→{rec['pcid']}"))

        if rec["connected"] and prev["connected"] and rec["scc_count"] != prev["scc_count"]:
            direction = "ko'paydi" if rec["scc_count"] > prev["scc_count"] else "kamaydi"
            events.append(
                self._event(rec, "info", f"Carrier aggregation {direction}", f"SCC soni: {prev['scc_count']} → {rec['scc_count']}")
            )

        for metric in ("rsrp", "sinr"):
            prev_b = quality_bucket(metric, prev.get(metric))
            cur_b = quality_bucket(metric, rec.get(metric))
            if prev_b != "?" and cur_b != "?" and prev_b != cur_b:
                order = ["Yomon", "O'rta", "Yaxshi"]
                if order.index(cur_b) < order.index(prev_b):
                    events.append(
                        self._event(rec, "warning", f"{metric.upper()} sifati pasaydi", f"{prev_b} → {cur_b} ({prev.get(metric):.0f} → {rec.get(metric):.0f})")
                    )
                else:
                    events.append(
                        self._event(rec, "success", f"{metric.upper()} sifati yaxshilandi", f"{prev_b} → {cur_b} ({prev.get(metric):.0f} → {rec.get(metric):.0f})")
                    )

        return events

    @staticmethod
    def _event(rec: dict, severity: str, title: str, detail: str) -> dict:
        return {"ts": rec["ts"], "severity": severity, "title": title, "detail": detail}
