#!/usr/bin/env python3
"""Baraka oilasi — mustaqil ma'lumotnoma implementatsiya (oracle).

Faqat standart kutubxona. Pul algoritmlari `docs/BARAKA_OILASI.md` 5-bo'limi,
jurnal algoritmi 6-bo'limi bo'yicha. Rust yadrosi shu natijalar bilan solishtiriladi.

Ishlatish:
    python3 -I spec/oracle/oracle.py --selftest
    python3 -I spec/oracle/oracle.py --check spec/test-vectors
    python3 -I spec/oracle/oracle.py --generate spec/test-vectors   # faqat yangi case qo'shganda
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import date, timedelta
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


def amortize_rows(principal: int, annual_bp: int, months: int, differentiated: bool):
    """Qo'shimcha to'lovsiz jadval; differensialda asosiy qarz teng bo'laklarda (allocate)."""
    r = Fraction(annual_bp, 10000 * 12)
    if differentiated:
        parts = allocate(principal, [1] * months)
    elif annual_bp == 0:
        payment = round_half_up(Fraction(principal, months))
    else:
        payment = round_half_up(principal * r * (1 + r) ** months / ((1 + r) ** months - 1))
    balance, month, rows = principal, 0, []
    while balance > 0:
        month += 1
        interest = round_half_up(balance * r)
        princ = (parts[month - 1] if month <= months else balance) if differentiated else payment - interest
        if princ >= balance or month >= months:
            princ = balance
        princ = max(princ, 0)
        balance -= princ
        rows.append(interest + princ)
    return rows


# --- 4-qonun: qarz rejasi, haqiqiy narx, holat, oylik yuk (uy/SPEC 2C.7, 2D.3, 2D.5) -----
def add_months(d: date, k: int) -> date:
    """chrono `checked_add_months`: oy oxiridan oshsa — oyning oxirgi kuni."""
    y, m = divmod(d.month - 1 + k, 12)
    y, m = d.year + y, m + 1
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return date(y, m, min(d.day, (nxt - timedelta(days=1)).day))


def debt_plan(kind, principal, markup=0, annual_bp=0, months=0, first=None, lines=None):
    """To'lov rejasi qatorlari [(sana, summa)]. MANUAL'da `first` — qarz boshlangan sana."""
    if principal <= 0:
        raise OracleError("PRINCIPAL_NOT_POSITIVE")
    if markup < 0:
        raise OracleError("MARKUP_NEGATIVE")
    if kind == "MANUAL":
        if not lines:
            raise OracleError("SCHEDULE_REQUIRED")
        prev = first
        for d, a in lines:
            if a <= 0:
                raise OracleError("AMOUNT_NOT_POSITIVE")
            if d < prev:
                raise OracleError("SCHEDULE_DATES_ORDER")
            prev = d
        if sum(a for _, a in lines) != principal + markup:
            raise OracleError("SCHEDULE_SUM_MISMATCH")
        return list(lines)
    if not 1 <= months <= 600:
        raise OracleError("INVALID_TERM")
    if kind in ("ANNUITY", "DIFFERENTIATED"):
        if markup != 0:
            raise OracleError("MARKUP_NOT_ALLOWED")
        if not 0 <= annual_bp <= 100000:
            raise OracleError("INVALID_RATE")
        amounts = amortize_rows(principal, annual_bp, months, kind == "DIFFERENTIATED")
    elif kind == "FIXED_MARKUP":
        if markup == 0:
            raise OracleError("MARKUP_REQUIRED")
        amounts = allocate(principal + markup, [1] * months)
    else:
        raise OracleError("INVALID_PLAN_KIND")
    return [(add_months(first, k), a) for k, a in enumerate(amounts)]


def true_cost(plan_total, principal, original=None, paid_before=0, paid_since=0, goals=()):
    original = principal if original is None else original
    if original < principal:
        raise OracleError("ORIGINAL_BELOW_PRINCIPAL")
    if paid_before < 0 or paid_since < 0:
        raise OracleError("AMOUNT_NEGATIVE")
    if paid_since > plan_total:
        raise OracleError("PAYMENT_EXCEEDS_REMAINING")
    total = paid_before + plan_total
    overpay = total - original
    if overpay < 0:
        raise OracleError("COST_BELOW_PRINCIPAL")
    if any(g <= 0 for g in goals):
        raise OracleError("INVALID_GOAL")
    return {"originalPrincipal": original, "totalCost": total, "overpay": overpay,
            "overpayBp": round_half_up(Fraction(overpay * 10000, total)),
            "paidTotal": paid_before + paid_since, "remaining": plan_total - paid_since,
            "goalsBp": [round_half_up(Fraction(overpay * 10000, g)) for g in goals]}


DUE_SOON_DAYS = 3


def remaining_lines(lines, regular, prepaid=0):
    """Odatiy to'lovlar rejaning boshidan, muddatidan oldingi to'lovlar oxiridan yopiladi."""
    total = sum(a for _, a in lines)
    if regular < 0 or prepaid < 0 or regular + prepaid > total:
        raise OracleError("PAYMENT_EXCEEDS_REMAINING")
    out = [list(x) for x in lines]
    r = regular
    for x in out:
        take = min(r, x[1])
        x[1] -= take
        r -= take
    p = prepaid
    for x in reversed(out):
        take = min(p, x[1])
        x[1] -= take
        p -= take
    return [(d, a) for d, a in out if a > 0]


def plan_status(lines, paid, today, prepaid=0):
    rest = remaining_lines(lines, paid, prepaid)
    nxt = rest[0] if rest else None
    overdue = sum(a for d, a in rest if d < today)
    remaining = sum(a for _, a in rest)
    reminder = None
    if overdue > 0:
        reminder = "OVERDUE"
    elif nxt is not None and (nxt[0] - today).days <= DUE_SOON_DAYS:
        reminder = "DUE_SOON"
    return {"remaining": remaining, "nextDate": nxt[0] if nxt else None, "nextAmount": nxt[1] if nxt else None,
            "overdue": overdue, "payoffDate": rest[-1][0] if rest else None, "reminder": reminder}


# --- U9: qarzdan chiqish rejalovchisi (uy/SPEC 2D.2, 2D.9) ---------------------------------
# Holat to'lovlar tarixidan qayta hisoblanadi; prognoz kalendar oylari bo'yicha: har oyda avval
# shu oyga to'g'ri kelgan odatiy to'lovlar, keyin qo'shimcha to'lov (tartib bo'yicha birinchi
# ochiq qarzga). Bank qarzlarida qo'shimcha to'lov asosiy qarzni kamaytiradi («muddatni
# qisqartirish»), ustamali va foizsiz rejalarda reja oxiridan yopiladi (ustama tejalmaydi).
MAX_WINDOWS = 1200


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


class Amortizing:
    def __init__(self, kind, principal, bp, months, first, payments):
        if principal <= 0:
            raise OracleError("PRINCIPAL_NOT_POSITIVE")
        if not 1 <= months <= 600:
            raise OracleError("INVALID_TERM")
        if not 0 <= bp <= 100000:
            raise OracleError("INVALID_RATE")
        self.kind, self.bp, self.first, self.n = kind, bp, first, months
        self.parts = allocate(principal, [1] * months) if kind == "DIFFERENTIATED" else None
        if kind == "ANNUITY":
            r = Fraction(bp, 120000)
            self.A = round_half_up(Fraction(principal, months)) if bp == 0 else \
                round_half_up(principal * r * (1 + r) ** months / ((1 + r) ** months - 1))
        self.B, self.k, self.left = principal, 1, months
        if any(a <= 0 for _, a, _ in payments):
            raise OracleError("AMOUNT_NOT_POSITIVE")
        regular = sum(a for _, a, pre in payments if not pre)
        pre = sorted([(d, a) for d, a, p in payments if p], key=lambda x: x[0])
        j = 0
        while True:
            d = self.next_date()
            while j < len(pre) and pre[j][0] < d:
                self.B -= min(pre[j][1], self.B)
                j += 1
            if self.B == 0 or self.left == 0:
                break
            i_, p_ = self.inst()
            if regular >= i_ + p_:
                regular -= i_ + p_
                self.pay()
                continue
            break
        for _, a in pre[j:]:
            self.B -= min(a, self.B)
        self.B -= min(regular, self.B)  # qisman odatiy to'lov — asosiy qarzga

    def next_date(self):
        return add_months(self.first, self.k - 1)

    def inst(self):
        i_ = round_half_up(Fraction(self.B * self.bp, 120000))
        if self.kind == "ANNUITY":
            p_ = self.A - i_
        else:
            p_ = self.parts[self.k - 1] if self.k <= self.n else self.B
        if p_ >= self.B or self.left <= 1:
            p_ = self.B
        return i_, max(p_, 0)

    def pay(self):
        i_, p_ = self.inst()
        self.B -= p_
        self.k += 1
        self.left -= 1
        return i_, p_

    def regular(self, window_end):
        due = interest = 0
        last = None
        while self.B > 0 and self.next_date() < window_end:
            last = self.next_date()
            i_, p_ = self.pay()
            due += i_ + p_
            interest += i_
        return due, interest, last

    def balance(self):
        return self.B

    def extra(self, ex):
        self.B -= ex

    def state(self):
        return {"balance": self.B, "nextDate": self.next_date() if self.B > 0 else None}


class Scheduled:
    def __init__(self, lines, payments):
        if any(a <= 0 for _, a, _ in payments):
            raise OracleError("AMOUNT_NOT_POSITIVE")
        regular = sum(a for _, a, p in payments if not p)
        prepaid = sum(a for _, a, p in payments if p)
        self.lines = [list(x) for x in remaining_lines(lines, regular, prepaid)]

    def regular(self, window_end):
        due, last = 0, None
        while self.lines and self.lines[0][0] < window_end:
            d, a = self.lines.pop(0)
            due += a
            last = d
        return due, 0, last

    def balance(self):
        return sum(a for _, a in self.lines)

    def extra(self, ex):
        for x in reversed(self.lines):
            take = min(ex, x[1])
            x[1] -= take
            ex -= take
        self.lines = [x for x in self.lines if x[1] > 0]

    def state(self):
        return {"balance": self.balance(), "nextDate": self.lines[0][0] if self.lines else None}


def make_state(spec, payments):
    if spec["kind"] in ("ANNUITY", "DIFFERENTIATED"):
        return Amortizing(spec["kind"], spec["principal"], spec["annualBp"], spec["months"], spec["firstDate"], payments)
    return Scheduled(spec["lines"], payments)


def payoff_plan(debts, today, pool):
    """debts: tartiblangan [(id, holat, fee_bp)]. Har bir qarz va umumiy natija."""
    if pool < 0:
        raise OracleError("EXTRA_NEGATIVE")
    res = {i: {"rows": [], "payoffDate": None, "months": 0, "interest": 0, "fees": 0, "paid": 0} for i, _, _ in debts}
    ws0 = month_start(today)
    w = 0
    while any(s.balance() > 0 for _, s, _ in debts):
        if w >= MAX_WINDOWS:
            raise OracleError("NOT_CONVERGING")
        ws, we = add_months(ws0, w), add_months(ws0, w + 1)
        acts = {}
        for i, s, _ in debts:
            if s.balance() > 0:
                acts[i] = list(s.regular(we)) + [0, 0]
        rest = pool
        for i, s, fee_bp in debts:
            if i in acts and s.balance() > 0 and rest > 0:
                ex = min(rest, s.balance())
                s.extra(ex)
                rest -= ex
                acts[i][3], acts[i][4] = ex, percent_of(ex, fee_bp)
        for i, s, _ in debts:
            if i not in acts:
                continue
            due, interest, last, ex, fee = acts[i]
            if due == 0 and ex == 0:
                continue
            d = last if last is not None else max(ws, today)
            r = res[i]
            r["rows"].append({"date": d, "due": due, "interest": interest, "extra": ex, "fee": fee, "balance": s.balance()})
            r["interest"] += interest
            r["fees"] += fee
            r["paid"] += due + ex + fee
            if s.balance() == 0:
                r["payoffDate"], r["months"] = d, w + 1
        w += 1
    total = {"payoffDate": max((r["payoffDate"] for r in res.values() if r["payoffDate"]), default=None),
             "months": max((r["months"] for r in res.values()), default=0),
             "interest": sum(r["interest"] for r in res.values()), "fees": sum(r["fees"] for r in res.values()),
             "paid": sum(r["paid"] for r in res.values())}
    return res, total


def default_order(keys):
    """keys: [(id, ribo, cost_bp, payoff_date, priority)]. Qo'lda tartib bo'lsa — u birinchi; keyin
    foizli qarzlar (eng qimmati birinchi), keyin foizsizlar (muddati yaqini birinchi)."""
    far = date(9999, 12, 31)
    return [k[0] for k in sorted(keys, key=lambda k: (k[4] is None, k[4] or 0, not k[1], -k[2] if k[1] else 0,
                                                      k[3] or far, k[0]))]


def debt_load_bp(payments: int, income: int):
    return None if income <= 0 else round_half_up(Fraction(payments * 10000, income))


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


# --- 5-qonun: foyda/zarar taqsimoti -------------------------------------------------------
def distribute(kind, result, partners, fixed_return=None, negligence=None):
    if fixed_return is not None:
        raise OracleError("GUARANTEED_RETURN_FORBIDDEN")
    if len(partners) < 2:
        raise OracleError("MIN_TWO_PARTNERS")
    shares = [p["profitShareBp"] for p in partners]
    if any(s < 0 for s in shares) or sum(shares) != 10000:
        raise OracleError("PROFIT_SHARES_NOT_100")
    if result >= 0:
        return allocate(result, shares)
    if kind == "MUSHARAKA":
        return allocate(result, [max(0, p["capital"]) for p in partners])
    if negligence is not None:
        return allocate(result, [1 if p["id"] == negligence["partnerId"] else 0 for p in partners])
    return allocate(result, [max(0, p["capital"]) if p["role"] in ("CAPITAL_PROVIDER", "BOTH") else 0 for p in partners])


def recovery_split(income, household, extra, savings):
    if min(household, extra, savings) < 0 or household + extra + savings != 10000:
        raise OracleError("SPLIT_NOT_100")
    if savings < 100:
        raise OracleError("SAVINGS_SHARE_TOO_LOW")
    return allocate(income, [household, extra, savings])


# --- vektor fayllarini generatsiya qilish (faqat oracle egalik qiladigan suite'lar) ------
def _s(v):
    return str(v)


def _case(cid, inp, fn):
    try:
        return {"id": cid, "input": inp, "expected": fn()}
    except OracleError as e:
        return {"id": cid, "input": inp, "expected": {"error": e.code}}


def _suite(name, desc, cases):
    return {"suite": name, "version": 1, "description": desc, "generatedBy": "spec/oracle/oracle.py", "cases": cases}


def _entry_json(e):
    return {k: e[k] for k in e}


UTF8_ENTRIES = [
    {"id": "0192a000-0000-7000-8000-000000000011", "agreementId": "0192a000-0000-7000-8000-0000000000b1",
     "kind": "OPENING_BALANCE", "partyId": "P1", "amount": {"minor": "50000000", "currency": "UZS"},
     "date": "2026-09-01", "note": "Gʻayrat va Oʻgʻiloyning qarzi — boshlangʻich holat; маъно ʼ"},
    {"id": "0192a000-0000-7000-8000-000000000012", "agreementId": "0192a000-0000-7000-8000-0000000000b1",
     "kind": "DUTY_INCIDENT", "partyId": "P2", "date": "2026-09-15", "note": "Kasal boʻldi, \"bot\" toʻxtadi\n1 kun"},
    {"id": "0192a000-0000-7000-8000-000000000013", "agreementId": "0192a000-0000-7000-8000-0000000000b1",
     "kind": "CORRECTION", "partyId": "P1", "amount": {"minor": "-1000000", "currency": "UZS"},
     "date": "2026-09-20", "correctsEntryId": "0192a000-0000-7000-8000-000000000011",
     "refs": ["sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"]},
]


def build_suites():
    U = "UZS"
    suites = {}
    alloc_cases = [
        ("alloc-001", 100, [1, 1, 1]), ("alloc-002", 800000000, [70, 20, 10]), ("alloc-003", 12345, [1000, 9000]),
        ("alloc-004", 100, [1] * 7), ("alloc-005", 0, [1, 2]), ("alloc-neg-001", -100, [1, 1, 1]),
        ("alloc-neg-002", -200000000, [1, 0]), ("alloc-err-001", 100, [0, 0]),
    ]
    suites["allocate"] = _suite("allocate", "Largest remainder; teng kasrda kichik indeks; manfiy summa simmetrik", [
        _case(cid, {"total": _s(t), "currency": U, "ratios": r}, lambda t=t, r=r: {"parts": [_s(x) for x in allocate(t, r)]})
        for cid, t, r in alloc_cases])
    suites["percent_of"] = _suite("percent_of", "percent_of = allocate([bp, 10000 - bp])[0]", [
        _case(cid, {"amount": _s(a), "currency": U, "bp": bp}, lambda a=a, bp=bp: {"result": _s(percent_of(a, bp))})
        for cid, a, bp in (("pct-001", 800000000, 1000), ("pct-002", 12345, 1000))])
    suites["round"] = _suite("round", "round_half_up: yarimni noldan uzoqqa", [
        _case(f"round-00{i}", {"num": _s(n), "den": _s(d)}, lambda n=n, d=d: {"result": _s(round_half_up(Fraction(n, d)))})
        for i, (n, d) in enumerate(((5, 2), (-5, 2), (-12, 5), (7, 2)), 1)])

    def fx(amount, cur, rf, rt, num, den):
        if cur != rf:
            raise OracleError("CURRENCY_MISMATCH")
        return {"result": _s(convert(amount, rf, rt, num, den)), "currency": rt}
    fx_cases = [("fx-001", 10000, "USD", "USD", "UZS", 12650, 1), ("fx-002", 1000000, "KRW", "KRW", "UZS", 91, 10),
                ("fx-003", 910000, "UZS", "UZS", "KRW", 10, 91), ("fx-err-001", 10000, "USD", "EUR", "UZS", 14000, 1)]
    suites["fx_convert"] = _suite("fx_convert", "1 major from = rateNum/rateDen major to; exponent hisobga olinadi", [
        _case(cid, {"amount": _s(a), "currency": c, "rateFrom": rf, "rateTo": rt, "rateNum": _s(n), "rateDen": _s(d)},
              lambda a=a, c=c, rf=rf, rt=rt, n=n, d=d: fx(a, c, rf, rt, n, d))
        for cid, a, c, rf, rt, n, d in fx_cases])
    fmt_cases = [("fmt-001", 800000000, U, "uz"), ("fmt-002", 12345, U, "uz"), ("fmt-003", -800000000, U, "uz"),
                 ("fmt-004", 800000000, U, "ru"), ("fmt-005", 800000000, U, "uz-Cyrl"), ("fmt-006", 1000000, "KRW", "uz"),
                 ("fmt-007", 5, U, "uz"), ("fmt-008", 10000, "USD", "uz")]
    suites["money_format"] = _suite("money_format", "NBSP minglik ajratuvchi, vergul kasr, soʻm (U+02BB)", [
        _case(cid, {"amount": _s(a), "currency": c, "locale": loc},
              lambda a=a, c=c, loc=loc: {"text": money_format(a, c, loc), "utf8Hex": money_format(a, c, loc).encode().hex()})
        for cid, a, c, loc in fmt_cases])

    def amort(extra):
        pay, months, ti, sched = amortize(3900000000, 2400, 14, extra)
        return {"payment": _s(pay), "months": months, "totalInterest": _s(ti),
                "schedule": [{"month": r["month"], "interest": _s(r["interest"]), "principal": _s(r["principal"]),
                              "extra": _s(r["extra"]), "balance": _s(r["balance"])} for r in sched]}
    suites["amortization"] = _suite("amortization", "Annuitet, muddatni qisqartirish rejimi (Anvar avtokrediti, 24% illyustrativ)", [
        _case(cid, {"principal": "3900000000", "currency": U, "annualBp": 2400, "months": 14, "extraPerMonth": _s(ex)},
              lambda ex=ex: amort(ex))
        for cid, ex in (("amort-001", 0), ("amort-002", 160000000), ("amort-003", 240000000))])
    suites["emergency_target"] = _suite("emergency_target", "round_half_up(Σ(ZARUR+KERAK, k oy) × N / k)", [
        _case("emerg-001", {"currency": U, "monthlyEssentials": ["520000000", "500000000", "530000000"], "months": 6},
              lambda: {"target": _s(emergency_target([520000000, 500000000, 530000000], 6))})])

    def infl(items):
        ch = [price_change_bp(o, n) for _, w, o, n in items]
        idx = round_half_up(Fraction(sum(w * c for (_, w, _, _), c in zip(items, ch)), sum(w for _, w, _, _ in items)))
        return {"changesBp": ch, "indexBp": idx}
    basket = [("goʻsht", 5000, 8000000, 13000000), ("non", 5000, 200000, 300000)]
    suites["personal_inflation"] = _suite("personal_inflation", "Mahsulot o'zgarishi va og'irlikli indeks, bp", [
        _case("infl-001", {"currency": U, "items": [{"name": n, "weightBp": w, "oldPrice": _s(o), "newPrice": _s(nw)} for n, w, o, nw in basket]},
              lambda: infl(basket))])
    gap_cases = [("gap-001", 800000000, 535000000, 165000000, 0, 0), ("gap-002", 800000000, 535000000, 165000000, 0, 60000000)]
    suites["unexplained_gap"] = _suite("unexplained_gap", "income − obligations − expenses − vaultNet − Δ(naqd + karta)", [
        _case(cid, {"currency": U, "income": _s(i), "obligations": _s(o), "expenses": _s(e), "vaultNet": _s(v), "balanceDelta": _s(b)},
              lambda i=i, o=o, e=e, v=v, b=b: {"gap": _s(unexplained_gap(i, o, e, v, b))})
        for cid, i, o, e, v, b in gap_cases])
    hist = [100000000, 120000000, 110000000]
    spike_cases = [("ps-001", 100000000, None, 150000000), ("ps-002", 100000000, None, 149999999),
                   ("ps-003", None, hist, 220000000), ("ps-004", None, hist, 219999999), ("ps-005", 100000000, None, -50000000)]
    suites["profit_spike"] = _suite("profit_spike", "A: actual ≥ 150% reja; B: actual ≥ 200% oxirgi 3 davr o'rtachasi", [
        _case(cid, {"currency": U, "plan": None if p is None else _s(p), "lastThree": None if h is None else [_s(x) for x in h], "actual": _s(a)},
              lambda p=p, h=h, a=a: {"alert": profit_spike(p, h, a)})
        for cid, p, h, a in spike_cases])
    mud = [{"id": "P1", "role": "CAPITAL_PROVIDER", "profitShareBp": 5000, "capital": 800000000},
           {"id": "P2", "role": "WORKER", "profitShareBp": 5000, "capital": 0}]
    mush = [{"id": "P1", "role": "BOTH", "profitShareBp": 6000, "capital": 600000000},
            {"id": "P2", "role": "BOTH", "profitShareBp": 4000, "capital": 200000000}]
    dist_cases = [("dist-001", "MUDARABA", 300000000, mud, None, None), ("dist-002", "MUDARABA", -200000000, mud, None, None),
                  ("dist-003", "MUSHARAKA", -300000000, mush, None, None), ("dist-004", "MUDARABA", 300000000, mud, 50000000, None),
                  ("dist-005", "MUDARABA", -200000000, mud, None, {"partnerId": "P2", "note": "shart buzildi"})]

    def pj(ps):
        return [dict(p, capital=_s(p["capital"])) for p in ps]
    suites["profit_distribution"] = _suite("profit_distribution", "Mudoraba/musharaka foyda va zarar taqsimoti", [
        _case(cid, {"kind": k, "currency": U, "result": _s(r), "partners": pj(ps), "fixedReturn": None if f is None else _s(f), "negligence": ng},
              lambda k=k, r=r, ps=ps, f=f, ng=ng: {"parts": [_s(x) for x in distribute(k, r, ps, f, ng)]})
        for cid, k, r, ps, f, ng in dist_cases])
    drs_cases = [("drs-001", 800000000, 7000, 2000, 1000), ("drs-002", 800000000, 8000, 2000, 0),
                 ("drs-003", 800000000, 7900, 2000, 100), ("drs-004", 800000000, 7000, 2000, 900)]

    def drs(i, h, e, s):
        a, b, c = recovery_split(i, h, e, s)
        return {"household": _s(a), "extraDebt": _s(b), "savings": _s(c)}
    suites["debt_recovery_split"] = _suite("debt_recovery_split", "DEBT_RECOVERY 70/20/10; jamg'arma ulushi ≥ 1%", [
        _case(cid, {"currency": U, "income": _s(i), "householdBp": h, "extraDebtBp": e, "savingsBp": s},
              lambda i=i, h=h, e=e, s=s: drs(i, h, e, s))
        for cid, i, h, e, s in drs_cases])
    tampered = json.loads(json.dumps(CHAIN_ENTRIES))
    tampered[1]["amount"]["minor"] = "300000001"
    suites["journal_chain"] = _suite("journal_chain", "JCS + SHA-256 zanjiri; whitelist v1; genesis = 64 ta 0", [
        {"id": "chain-001-003", "input": {"entries": CHAIN_ENTRIES}, "expected": {"hashes": chain(CHAIN_ENTRIES)}},
        {"id": "chain-neg-001", "input": {"entries": tampered, "storedHashes": CHAIN_HASHES}, "expected": {"firstBroken": verify_chain(tampered, CHAIN_HASHES)}},
        {"id": "chain-utf8-opt-corr-001", "input": {"entries": UTF8_ENTRIES, "withShortCodes": True}, "expected": {"hashes": chain(UTF8_ENTRIES), "shortCodes": [short_code(h) for h in chain(UTF8_ENTRIES)]}},
    ])
    D = date.fromisoformat

    def plan_case(cid, inp):
        def run():
            lines = [(D(l["date"]), int(l["amount"])) for l in inp.get("lines", [])]
            plan = debt_plan(inp["kind"], int(inp["principal"]), int(inp.get("markup", "0")), inp.get("annualBp", 0),
                             inp.get("months", 0), D(inp["firstDate"]), lines)
            tot = sum(a for _, a in plan)
            tc = true_cost(tot, int(inp["principal"]),
                           int(inp["originalPrincipal"]) if "originalPrincipal" in inp else None,
                           int(inp.get("paidBefore", "0")), int(inp.get("paidSince", "0")),
                           [int(g) for g in inp.get("goals", [])])
            return {"lines": [{"date": d.isoformat(), "amount": _s(a)} for d, a in plan], "planTotal": _s(tot),
                    "trueCost": {k: (_s(v) if k != "goalsBp" and k != "overpayBp" else v) for k, v in tc.items()}}
        return _case(cid, inp, run)
    ml = lambda *xs: [{"date": d, "amount": a} for d, a in xs]  # noqa: E731
    suites["debt_plan"] = _suite("debt_plan", "To'lov rejasi (4 tur) va qarzning haqiqiy narxi: asosiy → jami → ortiqcha", [
        plan_case("plan-001-annuity", {"kind": "ANNUITY", "currency": U, "principal": "3900000000", "annualBp": 2400,
                                       "months": 14, "firstDate": "2026-11-05", "paidSince": "644295368",
                                       "goals": ["1200000000", "60000000000"]}),
        plan_case("plan-002-differentiated", {"kind": "DIFFERENTIATED", "currency": U, "principal": "1200000000",
                                              "annualBp": 2400, "months": 6, "firstDate": "2027-01-31"}),
        plan_case("plan-003-fixed-markup", {"kind": "FIXED_MARKUP", "currency": U, "principal": "600000000",
                                            "markup": "120000000", "months": 12, "firstDate": "2026-10-20",
                                            "goals": ["50000000"]}),
        plan_case("plan-004-manual-karim", {"kind": "MANUAL", "currency": U, "principal": "900000000",
                                            "originalPrincipal": "4000000000", "paidBefore": "5100000000",
                                            "firstDate": "2026-10-15",
                                            "lines": ml(("2026-11-15", "300000000"), ("2026-12-15", "300000000"),
                                                        ("2027-01-15", "300000000"))}),
        plan_case("plan-005-manual-hasana", {"kind": "MANUAL", "currency": U, "principal": "200000000",
                                             "firstDate": "2026-10-15", "paidSince": "150000000",
                                             "lines": ml(("2026-11-15", "120000000"), ("2026-12-15", "80000000"))}),
        plan_case("plan-006-annuity-zero-rate", {"kind": "ANNUITY", "currency": U, "principal": "100000", "annualBp": 0,
                                                 "months": 3, "firstDate": "2026-12-31"}),
        plan_case("plan-neg-001-sum", {"kind": "MANUAL", "currency": U, "principal": "200000000", "firstDate": "2026-10-15",
                                       "lines": ml(("2026-11-15", "100000000"))}),
        plan_case("plan-neg-002-order", {"kind": "MANUAL", "currency": U, "principal": "200000000", "firstDate": "2026-10-15",
                                         "lines": ml(("2026-12-15", "100000000"), ("2026-11-15", "100000000"))}),
        plan_case("plan-neg-003-before-start", {"kind": "MANUAL", "currency": U, "principal": "100000000",
                                                "firstDate": "2026-10-15", "lines": ml(("2026-10-14", "100000000"))}),
        plan_case("plan-neg-004-markup-required", {"kind": "FIXED_MARKUP", "currency": U, "principal": "600000000",
                                                   "months": 12, "firstDate": "2026-10-20"}),
        plan_case("plan-neg-005-term", {"kind": "ANNUITY", "currency": U, "principal": "600000000", "annualBp": 2400,
                                        "months": 0, "firstDate": "2026-10-20"}),
        plan_case("plan-neg-006-original", {"kind": "MANUAL", "currency": U, "principal": "200000000",
                                            "originalPrincipal": "100000000", "firstDate": "2026-10-15",
                                            "lines": ml(("2026-11-15", "200000000"))}),
        plan_case("plan-neg-007-empty", {"kind": "MANUAL", "currency": U, "principal": "200000000",
                                         "firstDate": "2026-10-15", "lines": []}),
        plan_case("plan-neg-008-overpaid", {"kind": "MANUAL", "currency": U, "principal": "200000000",
                                            "firstDate": "2026-10-15", "paidSince": "200000001",
                                            "lines": ml(("2026-11-15", "200000000"))}),
    ])

    def status_case(cid, lines, paid, today, prepaid=None):
        inp = {"currency": U, "lines": ml(*lines), "paid": paid, "today": today}
        if prepaid is not None:
            inp["prepaid"] = prepaid

        def run():
            st = plan_status([(D(d), int(a)) for d, a in lines], int(paid), D(today), int(prepaid or 0))
            return {k: (v.isoformat() if isinstance(v, date) else _s(v) if isinstance(v, int) else v)
                    for k, v in st.items()}
        return _case(cid, inp, run)
    three = (("2026-11-15", "300000000"), ("2026-12-15", "300000000"), ("2027-01-15", "300000000"))
    suites["debt_status"] = _suite("debt_status", "To'lovlar rejaga ketma-ket yoziladi: keyingi to'lov, kechikkan, qoldiq, eslatma (≤ 3 kun)", [
        status_case("status-001-fresh", three, "0", "2026-10-15"),
        status_case("status-002-due-soon", three, "0", "2026-11-12"),
        status_case("status-003-partial-overdue", three, "100000000", "2026-12-20"),
        status_case("status-004-ahead", three, "450000000", "2026-11-20"),
        status_case("status-005-closed", three, "900000000", "2027-03-01"),
        status_case("status-neg-001", three, "900000001", "2026-10-15"),
        status_case("status-006-prepaid-from-end", three, "300000000", "2026-11-20", "400000000"),
        status_case("status-neg-002-prepaid", three, "300000000", "2026-11-20", "600000001"),
    ])

    def spec_json(sp):
        out = {"kind": sp["kind"]}
        if sp["kind"] in ("ANNUITY", "DIFFERENTIATED"):
            out.update({"principal": sp["principal"], "annualBp": sp["annualBp"], "months": sp["months"],
                        "firstDate": sp["firstDate"]})
        else:
            out["lines"] = ml(*sp["lines"])
        return out

    def spec_py(sp):
        if sp["kind"] in ("ANNUITY", "DIFFERENTIATED"):
            return {"kind": sp["kind"], "principal": int(sp["principal"]), "annualBp": sp["annualBp"],
                    "months": sp["months"], "firstDate": D(sp["firstDate"])}
        return {"kind": sp["kind"], "lines": [(D(d), int(a)) for d, a in sp["lines"]]}

    def pays_json(ps):
        return [{"date": d, "amount": a, "prepayment": pre} for d, a, pre in ps]

    def pays_py(ps):
        return [(D(d), int(a), pre) for d, a, pre in ps]

    def rows_json(rows):
        return [{"date": r["date"].isoformat(), "due": _s(r["due"]), "interest": _s(r["interest"]),
                 "extra": _s(r["extra"]), "fee": _s(r["fee"]), "balance": _s(r["balance"])} for r in rows]

    def proj_case(cid, sp, pays, today, extra, fee_bp=0):
        inp = {"currency": U, "debt": spec_json(sp), "payments": pays_json(pays), "today": today,
               "extraPerMonth": extra, "prepaymentFeeBp": fee_bp}

        def run():
            st = make_state(spec_py(sp), pays_py(pays))
            state = st.state()
            res, _ = payoff_plan([("d", st, fee_bp)], D(today), int(extra))
            r = res["d"]
            return {"state": {"balance": _s(state["balance"]),
                              "nextDate": state["nextDate"].isoformat() if state["nextDate"] else None},
                    "rows": rows_json(r["rows"]), "months": r["months"],
                    "payoffDate": r["payoffDate"].isoformat() if r["payoffDate"] else None,
                    "totalInterest": _s(r["interest"]), "totalFees": _s(r["fees"]), "totalPaid": _s(r["paid"])}
        return _case(cid, inp, run)

    anvar = {"kind": "ANNUITY", "principal": "3900000000", "annualBp": 2400, "months": 14, "firstDate": "2026-11-05"}
    karim = {"kind": "MANUAL", "lines": three}
    shop = {"kind": "FIXED_MARKUP", "lines": tuple((add_months(D("2026-10-20"), k).isoformat(), "60000000") for k in range(12))}
    suites["payoff_projection"] = _suite("payoff_projection", "Holat to'lovlar tarixidan; kalendar oylari bo'yicha prognoz: avval odatiy to'lov, keyin qo'shimcha; bankda asosiy qarz kamayadi, ustamali/foizsiz rejada oxiridan yopiladi", [
        proj_case("payoff-001-anvar-base", anvar, [], "2026-11-01", "0"),
        proj_case("payoff-002-anvar-1.6m", anvar, [], "2026-11-01", "160000000"),
        proj_case("payoff-003-anvar-2.4m-fee", anvar, [], "2026-11-01", "240000000", 100),
        proj_case("payoff-004-anvar-replay", anvar,
                  [("2026-11-05", "322147684", False), ("2026-12-05", "322147684", False),
                   ("2026-12-20", "500000000", True)], "2027-01-10", "0"),
        proj_case("payoff-005-overdue", anvar, [], "2027-01-20", "0"),
        proj_case("payoff-006-differentiated", {"kind": "DIFFERENTIATED", "principal": "1200000000", "annualBp": 2400,
                                                "months": 6, "firstDate": "2027-01-31"}, [], "2027-01-01", "100000000"),
        proj_case("payoff-007-karim", karim, [("2026-11-15", "300000000", False), ("2026-11-18", "100000000", True)],
                  "2026-11-20", "100000000"),
        proj_case("payoff-008-shop-markup", shop, [], "2026-10-01", "60000000"),
        proj_case("payoff-009-zero-rate", {"kind": "ANNUITY", "principal": "100000", "annualBp": 0, "months": 3,
                                           "firstDate": "2026-12-31"}, [], "2026-12-01", "0"),
        proj_case("payoff-neg-001-overpaid", karim, [("2026-11-15", "900000001", False)], "2026-11-20", "0"),
        proj_case("payoff-neg-002-extra", karim, [], "2026-11-20", "-1"),
    ])

    def plan_case(cid, debts, today, pool):
        inp = {"currency": U, "today": today, "poolPerMonth": pool,
               "debts": [{"id": i, "debt": spec_json(sp), "payments": pays_json(ps), "prepaymentFeeBp": f,
                          "ribo": rb, "costBp": cb, "priority": pr} for i, sp, ps, f, rb, cb, pr in debts]}

        def run():
            keys = []
            states = {}
            for i, sp, ps, f, rb, cb, pr in debts:
                st = make_state(spec_py(sp), pays_py(ps))
                base, _ = payoff_plan([(i, make_state(spec_py(sp), pays_py(ps)), f)], D(today), 0)
                keys.append((i, rb, cb, base[i]["payoffDate"], pr))
                states[i] = (st, f)
            order = default_order(keys)
            fresh = lambda: [(i, make_state(spec_py(sp), pays_py(ps)), f) for i in order  # noqa: E731
                             for j, sp, ps, f, *_ in debts if j == i]
            _, base = payoff_plan(fresh(), D(today), 0)
            per, acc = payoff_plan(fresh(), D(today), int(pool))
            iso = lambda d: d.isoformat() if d else None  # noqa: E731
            return {"order": order,
                    "base": {"payoffDate": iso(base["payoffDate"]), "months": base["months"],
                             "totalInterest": _s(base["interest"]), "totalFees": _s(base["fees"])},
                    "accelerated": {"payoffDate": iso(acc["payoffDate"]), "months": acc["months"],
                                    "totalInterest": _s(acc["interest"]), "totalFees": _s(acc["fees"]),
                                    "debts": [{"id": i, "payoffDate": iso(per[i]["payoffDate"]), "months": per[i]["months"],
                                               "interest": _s(per[i]["interest"]), "fees": _s(per[i]["fees"])} for i in order]},
                    "monthsSaved": base["months"] - acc["months"],
                    "interestSaved": _s(base["interest"] - acc["interest"]),
                    "netSaved": _s(base["interest"] - acc["interest"] - acc["fees"])}
        return _case(cid, inp, run)

    trio = [("avto", anvar, [], 100, True, 2400, None), ("toy", karim, [], 0, False, 0, None),
            ("nasiya", shop, [], 0, True, 1667, None)]
    suites["payoff_plan"] = _suite("payoff_plan", "Bir nechta qarz: tartib (qo'lda → foizli eng qimmati → foizsiz muddati yaqini), qo'shimcha to'lov tartib bo'yicha birinchi ochiq qarzga; «Qarzsiz kun»", [
        plan_case("plan-all-001-default-order", trio, "2026-11-01", "240000000"),
        plan_case("plan-all-002-manual-order", [("avto", anvar, [], 100, True, 2400, 2), ("toy", karim, [], 0, False, 0, 1),
                                                ("nasiya", shop, [], 0, True, 1667, None)], "2026-11-01", "240000000"),
        plan_case("plan-all-003-no-extra", trio, "2026-11-01", "0"),
    ])
    suites["debt_load"] = _suite("debt_load", "Oylik qarz yuki = shu davrdagi reja to'lovlari / oylik daromad, bp (round_half_up)", [
        _case(cid, {"currency": U, "payments": _s(p), "income": _s(i)}, lambda p=p, i=i: {"loadBp": debt_load_bp(p, i)})
        for cid, p, i in (("load-001", 322147684, 1200000000), ("load-002", 0, 800000000),
                          ("load-003", 150000000, 0), ("load-004", 100000000, 300000000))])
    return suites


ORACLE_SUITES = ("allocate", "percent_of", "round", "fx_convert", "money_format", "amortization", "emergency_target",
                 "personal_inflation", "unexplained_gap", "profit_spike", "profit_distribution", "debt_recovery_split",
                 "journal_chain", "debt_plan", "debt_status", "debt_load", "payoff_projection", "payoff_plan")


def generate(directory: str) -> None:
    import os
    os.makedirs(directory, exist_ok=True)
    for name, suite in build_suites().items():
        with open(os.path.join(directory, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(suite, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(f"oracle: {len(ORACLE_SUITES)} ta suite yozildi -> {directory}")


def check(directory: str) -> int:
    import os
    bad = 0
    for name, suite in build_suites().items():
        path = os.path.join(directory, f"{name}.json")
        if not os.path.exists(path):
            print(f"YO'Q: {path}")
            bad += 1
            continue
        with open(path, encoding="utf-8") as f:
            on_disk = json.load(f)
        disk_cases = {c["id"]: c for c in on_disk.get("cases", [])}
        for case in suite["cases"]:
            got = disk_cases.get(case["id"])
            if got is None:
                print(f"{name}/{case['id']}: faylda yo'q")
                bad += 1
            elif got.get("input") != case["input"] or got.get("expected") != case["expected"]:
                print(f"{name}/{case['id']}: oracle bilan mos emas")
                bad += 1
    print("oracle check: OK" if bad == 0 else f"oracle check: {bad} ta muammo")
    return 1 if bad else 0


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
    # 4-qonun: qarz
    assert add_months(date(2027, 1, 31), 1) == date(2027, 2, 28) and add_months(date(2026, 11, 5), 13) == date(2027, 12, 5)
    anv = debt_plan("ANNUITY", 3900000000, annual_bp=2400, months=14, first=date(2026, 11, 5))
    assert sum(a for _, a in anv) == 3900000000 + 610067573 and anv[0] == (date(2026, 11, 5), 322147684)
    assert sum(debt_plan("DIFFERENTIATED", 1000, annual_bp=2400, months=3, first=date(2026, 1, 1))[i][1] for i in range(3)) == 1040
    karim = true_cost(900000000, 900000000, 4000000000, 5100000000)
    assert (karim["totalCost"], karim["overpay"], karim["overpayBp"]) == (6000000000, 2000000000, 3333)
    st = plan_status([(date(2026, 11, 15), 300), (date(2026, 12, 15), 300)], 100, date(2026, 12, 20))
    assert (st["nextAmount"], st["overdue"], st["reminder"]) == (200, 500, "OVERDUE")
    assert debt_load_bp(322147684, 1200000000) == 2685 and debt_load_bp(1, 0) is None
    # U9: yangi prognoz eski amortizatsiya vektorlari bilan bir xil (birinchi oy — to'lov oyi)
    for extra, (months, interest) in {0: (14, 610067573), 160000000: (9, 397018667), 240000000: (8, 341756885)}.items():
        st = Amortizing("ANNUITY", 3900000000, 2400, 14, date(2026, 11, 5), [])
        res, tot = payoff_plan([("a", st, 0)], date(2026, 11, 1), extra)
        assert (res["a"]["months"], res["a"]["interest"]) == (months, interest), (extra, res["a"]["months"])
        assert res["a"]["rows"][-1]["balance"] == 0
    assert remaining_lines([(1, 300), (2, 300), (3, 300)], 300, 400) == [(2, 200)]
    print("oracle selftest: OK")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="hujjatdagi barcha qiymatlarni tekshirish")
    ap.add_argument("--generate", metavar="DIR", help="oracle suite'larini DIR ga yozish")
    ap.add_argument("--check", metavar="DIR", help="DIR dagi vektorlar oracle bilan mosligini tekshirish")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return 0
    if args.generate:
        generate(args.generate)
        return 0
    if args.check:
        return check(args.check)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
