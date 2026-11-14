#!/usr/bin/env python3
"""M-Pay Shield — sintetik hodisalar generatori (tranzaksiyalar + provisioning).

Faqat **xom hodisalar** yaratiladi; belgilarni Rust feature store hisoblaydi
(`shield-replay featurize`) — o'qitish va ishlab chiqarish belgilari bir xil bo'lishi uchun.

Stsenariylar (label = 1):
  account_takeover  — hujumchi qurilmasi qurbon kartasini tokenlashtiradi, keyin odatdan katta
                      summalar, ko'pincha tunda va P2P/onlayn;
  card_testing      — o'g'irlangan kartalar bir nechta qurilmada, onlayn merchantlarda tez-tez kichik summalar;
  mule_network      — qurilma–karta halqalari (har karta 2–3 qurilmada), muntazam P2P yechib olish;
  device_farm       — bitta qurilmada 10–25 karta qisqa vaqtda tokenlashtiriladi;
  p2p_wave          — buzilgan ilova orqali ko'p kartadan 10 daqiqa ichida P2P yechib olish to'lqini.

Qiyin legit holatlar (label = 0): telefon almashtirish (yangi qurilma), sayohat (xorijiy terminal),
yirik xaridlar, oylik kuni P2P'lar.

Foydalanish:
    uv run python generate.py --seed 1 --out data/events_train.csv
    uv run python generate.py --seed 2 --out data/events_test.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

START = 1_800_000_000  # 2027-01-15 (UTC), ixtiyoriy boshlanish
DAY = 86_400
UZS = 100  # 1 so'm = 100 tiyin


@dataclass
class Person:
    pid: int
    cards: list[str]
    devices: list[str]
    median_uzs: float
    rate: float
    peak_hour: float
    favorites: list[str]
    traveler: bool
    phone_change_day: int | None


@dataclass
class Gen:
    rng: np.random.Generator
    days: int
    rows: list[tuple] = field(default_factory=list)
    shops: list[str] = field(default_factory=list)
    shop_p: np.ndarray | None = None
    web: list[str] = field(default_factory=list)
    p2p: list[str] = field(default_factory=list)

    def emit(self, ts, kind, device, card, merchant="", country=860, amount=0, cdcvm=0, att=2, label=0, scenario="legit"):
        self.rows.append((int(ts), kind, device, card, merchant, int(country), int(amount), int(cdcvm), int(att), int(label), scenario))

    def txn(self, ts, device, card, merchant, amount_minor, country=860, label=0, scenario="legit"):
        cdcvm = 1 if amount_minor > 1_000_000 * UZS else int(self.rng.random() < 0.3)
        self.emit(ts, "txn", device, card, merchant, country, max(int(amount_minor), 100), cdcvm, 2, label, scenario)

    def hour_ts(self, day: int, hour: float) -> int:
        h = hour % 24
        return START + day * DAY + int(h * 3600) + int(self.rng.integers(0, 3600))


def build_merchants(g: Gen) -> None:
    g.shops = [f"SHOP{i:04d}" for i in range(400)]
    w = 1.0 / np.arange(1, 401) ** 0.9
    g.shop_p = w / w.sum()
    g.web = [f"WEB{i:04d}" for i in range(30)]
    g.p2p = [f"P2P{i:04d}" for i in range(15)]


def legit_population(g: Gen, n_people: int) -> list[Person]:
    rng = g.rng
    people = []
    for pid in range(n_people):
        n_cards = 1 if rng.random() < 0.85 else 2
        n_dev = 1 if rng.random() < 0.95 else 2
        favorites = list(rng.choice(g.shops, size=int(rng.integers(5, 16)), replace=False, p=g.shop_p))
        people.append(
            Person(
                pid=pid,
                cards=[f"card-l{pid}-{c}" for c in range(n_cards)],
                devices=[f"dev-l{pid}-{d}" for d in range(n_dev)],
                median_uzs=float(np.exp(rng.uniform(math.log(30_000), math.log(500_000)))),
                rate=float(rng.uniform(0.5, 4.0)),
                peak_hour=float(np.clip(rng.normal(14, 3), 8, 21)),
                favorites=favorites,
                traveler=bool(rng.random() < 0.02),
                phone_change_day=int(rng.integers(1, g.days)) if rng.random() < 0.03 else None,
            )
        )
    return people


def legit_activity(g: Gen, people: list[Person]) -> None:
    rng = g.rng
    for p in people:
        # Boshlang'ich provisioning: tarix boshlanishidan oldin.
        for d in p.devices:
            for c in p.cards:
                g.emit(START - int(rng.integers(DAY, 30 * DAY)), "provision", d, c, att=2, scenario="legit")
        travel_day = int(rng.integers(0, g.days)) if p.traveler else None
        for day in range(g.days):
            device = p.devices[0]
            scenario = "legit"
            if p.phone_change_day is not None and day >= p.phone_change_day:
                device = f"dev-l{p.pid}-new"
                scenario = "legit_new_device"
                if day == p.phone_change_day:
                    for c in p.cards:
                        g.emit(g.hour_ts(day, p.peak_hour - 3), "provision", device, c, att=2, scenario="legit_new_device")
            n = rng.poisson(p.rate)
            for _ in range(n):
                card = p.cards[int(rng.integers(0, len(p.cards)))]
                hour = rng.normal(p.peak_hour, 3.0)
                ts = g.hour_ts(day, hour)
                amount = rng.lognormal(math.log(p.median_uzs), 0.8) * UZS
                country = 860
                sc = scenario
                r = rng.random()
                if r < 0.05:
                    merchant = str(rng.choice(g.p2p))
                elif r < 0.15:
                    merchant = str(rng.choice(g.web))
                elif r < 0.85:
                    merchant = str(rng.choice(p.favorites))
                else:
                    merchant = str(rng.choice(g.shops, p=g.shop_p))
                if rng.random() < 0.01:
                    amount *= rng.uniform(5, 20)  # yirik xarid
                    sc = "legit_big_purchase"
                if travel_day is not None and day == travel_day:
                    country = int(rng.choice([398, 417, 762, 792, 643]))
                    sc = "legit_travel"
                g.txn(ts, device, card, merchant, amount, country, 0, sc)
        # Oylik kuni: P2P o'tkazmalar.
    salary_day = g.days // 2
    for p in people:
        if g.rng.random() < 0.25:
            ts = START + salary_day * DAY + 10 * 3600 + int(g.rng.integers(0, 4 * 3600))
            g.txn(ts, p.devices[0], p.cards[0], str(g.rng.choice(g.p2p)), p.median_uzs * UZS * g.rng.uniform(1, 3), 860, 0, "legit_salary_p2p")


def account_takeover(g: Gen, people: list[Person], n: int) -> None:
    rng = g.rng
    victims = rng.choice(len(people), size=n, replace=False)
    for k, vi in enumerate(victims):
        v = people[int(vi)]
        card = v.cards[0]
        dev = f"dev-ato-{k}"
        day = int(rng.integers(1, g.days))
        night = rng.random() < 0.5
        hour = float(rng.uniform(1, 5)) if night else float(rng.uniform(10, 22))
        t0 = g.hour_ts(day, hour)
        g.emit(t0, "provision", dev, card, att=int(rng.choice([1, 2], p=[0.3, 0.7])), label=1, scenario="account_takeover")
        for j in range(int(rng.integers(2, 6))):
            ts = t0 + int(rng.integers(300, 6 * 3600))
            merchant = str(rng.choice(g.p2p)) if rng.random() < 0.5 else str(rng.choice(g.web))
            amount = v.median_uzs * UZS * rng.uniform(5, 20)
            g.txn(ts, dev, card, merchant, amount, 860, 1, "account_takeover")


def card_testing(g: Gen, n_devices: int) -> None:
    rng = g.rng
    for k in range(n_devices):
        dev = f"dev-ct-{k}"
        day = int(rng.integers(0, g.days))
        t0 = g.hour_ts(day, float(rng.uniform(0, 24)))
        merchants = list(rng.choice(g.web, size=2, replace=False))
        for c in range(int(rng.integers(5, 13))):
            card = f"card-ct-{k}-{c}"
            tp = t0 + c * int(rng.integers(30, 180))
            g.emit(tp, "provision", dev, card, att=2, label=1, scenario="card_testing")
            for j in range(int(rng.integers(2, 6))):
                ts = tp + 60 + j * int(rng.integers(5, 60))
                g.txn(ts, dev, card, str(rng.choice(merchants)), rng.uniform(100, 1_000) * UZS, 860, 1, "card_testing")
            if rng.random() < 0.15:
                g.txn(tp + 1200, dev, card, str(rng.choice(g.web)), rng.uniform(200_000, 2_000_000) * UZS, 860, 1, "card_testing")


def mule_network(g: Gen, n_rings: int) -> None:
    rng = g.rng
    for r in range(n_rings):
        devices = [f"dev-mule-{r}-{d}" for d in range(int(rng.integers(3, 6)))]
        cards = [f"card-mule-{r}-{c}" for c in range(int(rng.integers(5, 10)))]
        t0 = START + int(rng.integers(0, 2 * DAY))
        for i, c in enumerate(cards):
            for d in rng.choice(devices, size=int(rng.integers(2, 4)), replace=False):
                g.emit(t0 + i * 600 + int(rng.integers(0, 600)), "provision", str(d), c, att=2, label=1, scenario="mule_network")
        for day in range(int((t0 - START) // DAY) + 1, g.days):
            for c in cards:
                for _ in range(int(rng.integers(1, 4))):
                    ts = g.hour_ts(day, float(rng.uniform(8, 23)))
                    g.txn(ts, str(rng.choice(devices)), c, str(rng.choice(g.p2p)), rng.uniform(300_000, 3_000_000) * UZS, 860, 1, "mule_network")


def device_farm(g: Gen, n_devices: int) -> None:
    rng = g.rng
    for k in range(n_devices):
        dev = f"dev-farm-{k}"
        t0 = g.hour_ts(int(rng.integers(0, g.days)), float(rng.uniform(0, 24)))
        for c in range(int(rng.integers(10, 26))):
            card = f"card-farm-{k}-{c}"
            tp = t0 + c * int(rng.integers(60, 400))
            g.emit(tp, "provision", dev, card, att=int(rng.choice([1, 2])), label=1, scenario="device_farm")
            if rng.random() < 0.5:
                g.txn(tp + int(rng.integers(600, 7200)), dev, card, str(rng.choice(g.web + g.p2p)), rng.uniform(50_000, 800_000) * UZS, 860, 1, "device_farm")


def p2p_wave(g: Gen, people: list[Person], n_waves: int) -> None:
    rng = g.rng
    for w in range(n_waves):
        t0 = g.hour_ts(int(rng.integers(1, g.days)), float(rng.uniform(0, 24)))
        victims = rng.choice(len(people), size=int(rng.integers(60, 120)), replace=False)
        for vi in victims:
            v = people[int(vi)]
            ts = t0 + int(rng.integers(0, 600))
            amount = v.median_uzs * UZS * rng.uniform(3, 15)
            g.txn(ts, v.devices[0], v.cards[0], str(rng.choice(g.p2p)), amount, 860, 1, "p2p_wave")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--people", type=int, default=2500)
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    g = Gen(rng=np.random.default_rng(a.seed), days=a.days)
    build_merchants(g)
    people = legit_population(g, a.people)
    legit_activity(g, people)
    account_takeover(g, people, 60)
    card_testing(g, 15)
    mule_network(g, 8)
    device_farm(g, 10)
    p2p_wave(g, people, 3)
    g.rows.sort(key=lambda r: (r[0], r[1] != "provision"))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ts", "kind", "device", "card", "merchant", "country", "amount_minor", "cdcvm", "attestation", "label", "scenario"])
        w.writerows(g.rows)
    from collections import Counter

    c = Counter((r[1], r[10]) for r in g.rows)
    print(f"{len(g.rows)} hodisa → {out}")
    for (kind, sc), n in sorted(c.items()):
        print(f"  {kind:9s} {sc:20s} {n}")


if __name__ == "__main__":
    main()
