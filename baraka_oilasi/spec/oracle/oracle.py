#!/usr/bin/env python3
"""Baraka oilasi — mustaqil ma'lumotnoma implementatsiya (oracle).

Faqat standart kutubxona. Pul algoritmlari `docs/BARAKA_OILASI.md` 5-bo'limi,
jurnal algoritmi 6-bo'limi bo'yicha. Rust yadrosi shu natijalar bilan solishtiriladi.

Ishlatish:
    python3 -I spec/oracle/oracle.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from fractions import Fraction

EXPONENT = {"UZS": 2, "USD": 2, "EUR": 2, "RUB": 2, "KZT": 2, "TRY": 2, "GBP": 2, "KRW": 0}
NBSP = " "
UNIT = {"uz": "soʻm", "uz-Cyrl": "сўм", "ru": "сум"}
GENESIS = "0" * 64


class OracleError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# --- 5.3 yaxlitlash: yarimni noldan uzoqqa -------------------------------------------
def round_half_up(x: Fraction) -> int:
    sign = -1 if x < 0 else 1
    return sign * math.floor(abs(x) + Fraction(1, 2))


# --- 5.4 largest remainder --------------------------------------------------------------
def allocate(total: int, ratios: list[int]) -> list[int]:
    if not ratios or any(r < 0 for r in ratios) or sum(ratios) <= 0:
        raise OracleError("INVALID_RATIOS")
    if total < 0:
        return [-p for p in allocate(-total, ratios)]
    s = sum(ratios)
    exact = [Fraction(total * r, s) for r in ratios]
    parts = [math.floor(e) for e in exact]
    rest = total - sum(parts)
    order = sorted(range(len(ratios)), key=lambda i: (-(exact[i] - parts[i]), i))
    for i in order[:rest]:
        parts[i] += 1
    return parts


def percent_of(amount: int, bp: int) -> int:
    if not 0 <= bp <= 10000:
        raise OracleError("INVALID_BP")
    return allocate(amount, [bp, 10000 - bp])[0]


# --- 5.6 FX ---------------------------------------------------------------------------
def convert(minor: int, cur_from: str, cur_to: str, rate_num: int, rate_den: int) -> int:
    if rate_den <= 0 or rate_num <= 0:
        raise OracleError("INVALID_RATE")
    num = minor * rate_num * 10 ** EXPONENT[cur_to]
    den = rate_den * 10 ** EXPONENT[cur_from]
    return round_half_up(Fraction(num, den))


def add(a: tuple[int, str], b: tuple[int, str]) -> tuple[int, str]:
    if a[1] != b[1]:
        raise OracleError("CURRENCY_MISMATCH")
    return (a[0] + b[0], a[1])


# --- 5.7 formatlash ---------------------------------------------------------------------
def _group(n: int) -> str:
    s = str(n)
    out = []
    while len(s) > 3:
        out.insert(0, s[-3:])
        s = s[:-3]
    out.insert(0, s)
    return NBSP.join(out)


def money_format(minor: int, currency: str, locale: str) -> str:
    exp = EXPONENT[currency]
    sign = "-" if minor < 0 else ""
    major, frac = divmod(abs(minor), 10 ** exp) if exp else (abs(minor), 0)
    body = _group(major)
    if exp and frac:
        body += "," + str(frac).rjust(exp, "0")
    unit = UNIT[locale] if currency == "UZS" else currency
    return f"{sign}{body}{NBSP}{unit}"


# --- 5.8 amortizatsiya ------------------------------------------------------------------
def amortize(principal: int, annual_bp: int, months: int, extra: int):
    r = Fraction(annual_bp, 10000 * 12)
    payment = round_half_up(principal * r * (1 + r) ** months / ((1 + r) ** months - 1))
    balance, month, total_interest, schedule = principal, 0, 0, []
    while balance > 0:
        month += 1
        interest = round_half_up(balance * r)
        princ = payment - interest
        if princ >= balance or month == months:
            princ = balance
        balance -= princ
        ex = min(extra, balance)
        balance -= ex
        total_interest += interest
        schedule.append({"month": month, "interest": interest, "principal": princ, "extra": ex, "balance": balance})
    return payment, month, total_interest, schedule


# --- 5.9 izohsiz summa ------------------------------------------------------------------
def unexplained_gap(income, obligations, expenses, vault_net, balance_delta=0) -> int:
    return income - obligations - expenses - vault_net - balance_delta


# --- boshqa Uy suite'lari ---------------------------------------------------------------
def emergency_target(months: list[int], n: int) -> int:
    return round_half_up(Fraction(sum(months) * n, len(months)))


def price_change_bp(old: int, new: int) -> int:
    return round_half_up(Fraction((new - old) * 10000, old))


def profit_spike(plan, history, actual) -> bool:
    a = plan is not None and plan > 0 and actual * 10000 >= plan * 15000
    b = history is not None and len(history) == 3 and sum(history) > 0 and actual * 3 * 10000 >= sum(history) * 20000
    return actual > 0 and (a or b)


# --- 6. jurnal --------------------------------------------------------------------------
WHITELIST = ("id", "agreementId", "kind", "partyId", "amount", "date", "note", "correctsEntryId", "refs")


def _jcs(value) -> str:
    """RFC 8785 ning jurnal uchun yetarli qismi: faqat string, obyekt va massiv."""
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(_jcs(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + _jcs(value[k]) for k in keys) + "}"
    raise OracleError("JOURNAL_NON_STRING_VALUE")  # null, son, bool taqiqlangan


def canonical(entry: dict) -> str:
    return _jcs({k: entry[k] for k in WHITELIST if k in entry})


def chain(entries: list[dict]) -> list[str]:
    prev, out = GENESIS, []
    for e in entries:
        prev = hashlib.sha256((prev + "\n" + canonical(e)).encode("utf-8")).hexdigest()
        out.append(prev)
    return out


def verify_chain(entries: list[dict], hashes: list[str]):
    for i, h in enumerate(chain(entries)):
        if h != hashes[i]:
            return i + 1  # birinchi buzilgan yozuvning tartib raqami (1 dan)
    return None


def short_code(head: str) -> str:
    h = head[:16].upper()
    return "-".join(h[i:i + 4] for i in range(0, 16, 4))


# --- selftest ---------------------------------------------------------------------------
AGR = "0192a000-0000-7000-8000-0000000000a1"
CHAIN_ENTRIES = [
    {"id": "0192a000-0000-7000-8000-000000000001", "agreementId": AGR, "kind": "CONTRIBUTION", "partyId": "P1",
     "amount": {"minor": "300000000", "currency": "UZS"}, "date": "2026-10-01", "note": "Anvar hissasi"},
    {"id": "0192a000-0000-7000-8000-000000000002", "agreementId": AGR, "kind": "CONTRIBUTION", "partyId": "P2",
     "amount": {"minor": "300000000", "currency": "UZS"}, "date": "2026-10-01", "note": "Dilshod hissasi"},
    {"id": "0192a000-0000-7000-8000-000000000003", "agreementId": AGR, "kind": "PROFIT_DISTRIBUTION", "partyId": "P1",
     "amount": {"minor": "140000000", "currency": "UZS"}, "date": "2026-10-31", "note": "1-oy foyda ulushi"},
]
CHAIN_HASHES = [
    "e6ae98e545c7438c7de424286aa8f624493748c85a7f8cd79f2c576eb4f25b9e",
    "fa5d38ce32acd7beb4128a85231bbba0f2d7fc8081bc27024c1f1c4904257b53",
    "ba06ad59d6c270a58182a304bd376535d814dd210520f8359a4969f870b26903",
]


def _expect_error(code, fn, *args):
    try:
        fn(*args)
    except OracleError as e:
        assert e.code == code, (e.code, code)
        return
    raise AssertionError(f"{code} kutilgan edi")


def selftest() -> None:
    # allocate / percent_of (DESKTOP_PROMPT 5.3 + BARAKA_OILASI 12.3)
    assert allocate(100, [1, 1, 1]) == [34, 33, 33]
    assert allocate(800000000, [70, 20, 10]) == [560000000, 160000000, 80000000]
    assert allocate(12345, [1000, 9000]) == [1235, 11110]
    assert allocate(100, [1] * 7) == [15, 15, 14, 14, 14, 14, 14]
    assert allocate(0, [1, 2]) == [0, 0]
    assert allocate(-100, [1, 1, 1]) == [-34, -33, -33]
    assert allocate(-200000000, [1, 0]) == [-200000000, 0]
    _expect_error("INVALID_RATIOS", allocate, 100, [0, 0])
    assert percent_of(800000000, 1000) == 80000000
    assert percent_of(12345, 1000) == 1235
    # round
    assert [round_half_up(Fraction(*x)) for x in ((5, 2), (-5, 2), (-12, 5), (7, 2))] == [3, -3, -2, 4]
    # fx
    assert convert(10000, "USD", "UZS", 12650, 1) == 126500000
    assert convert(1000000, "KRW", "UZS", 91, 10) == 910000000
    _expect_error("CURRENCY_MISMATCH", add, (100, "USD"), (100, "UZS"))
    # format
    assert money_format(800000000, "UZS", "uz") == "8 000 000 soʻm"
    assert money_format(12345, "UZS", "uz") == "123,45 soʻm"
    assert money_format(-800000000, "UZS", "uz") == "-8 000 000 soʻm"
    assert money_format(800000000, "UZS", "ru") == "8 000 000 сум"
    assert money_format(800000000, "UZS", "uz-Cyrl") == "8 000 000 сўм"
    assert money_format(1000000, "KRW", "uz") == "1 000 000 KRW"
    # amortization
    expected = {0: (322147684, 14, 610067573), 160000000: (322147684, 9, 397018667), 240000000: (322147684, 8, 341756885)}
    for extra, (pay, months, interest) in expected.items():
        p, m, ti, sched = amortize(3900000000, 2400, 14, extra)
        assert (p, m, ti) == (pay, months, interest), (extra, p, m, ti)
        assert sched[-1]["balance"] == 0
    _, _, _, s2 = amortize(3900000000, 2400, 14, 160000000)
    assert s2[8] == {"month": 9, "interest": 8624259, "principal": 313523425, "extra": 117689511, "balance": 0}
    # profit distribution
    assert allocate(300000000, [5000, 5000]) == [150000000, 150000000]
    assert allocate(-300000000, [600000000, 200000000]) == [-225000000, -75000000]
    # boshqa Uy suite'lari
    assert emergency_target([520000000, 500000000, 530000000], 6) == 3100000000
    meat, bread = price_change_bp(8000000, 13000000), price_change_bp(200000, 300000)
    assert (meat, bread) == (6250, 5000)
    assert round_half_up(Fraction(meat * 5000 + bread * 5000, 10000)) == 5625
    assert unexplained_gap(800000000, 535000000, 165000000, 0) == 100000000
    assert unexplained_gap(800000000, 535000000, 165000000, 0, 60000000) == 40000000
    hist = [100000000, 120000000, 110000000]
    assert [profit_spike(100000000, None, 150000000), profit_spike(100000000, None, 149999999),
            profit_spike(None, hist, 220000000), profit_spike(None, hist, 219999999),
            profit_spike(100000000, None, -50000000)] == [True, False, True, False, False]
    # jurnal
    assert chain(CHAIN_ENTRIES) == CHAIN_HASHES
    tampered = json.loads(json.dumps(CHAIN_ENTRIES))
    tampered[1]["amount"]["minor"] = "300000001"
    assert verify_chain(tampered, CHAIN_HASHES) == 2
    extra_field = [dict(e, householdId="h", createdAt="2026-10-01T00:00:00Z") for e in CHAIN_ENTRIES]
    assert chain(extra_field) == CHAIN_HASHES  # whitelist'dan tashqari maydonlar xeshlanmaydi
    _expect_error("JOURNAL_NON_STRING_VALUE", canonical, dict(CHAIN_ENTRIES[0], note=None))
    assert short_code(CHAIN_HASHES[0]) == "E6AE-98E5-45C7-438C"
    print("oracle selftest: OK")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="hujjatdagi barcha qiymatlarni tekshirish")
    # Y2 vazifasida: --check spec/test-vectors (JSON vektor fayllarini oracle bilan solishtirish)
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
