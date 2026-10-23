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


# --- U10: marosim rejalovchisi (uy/SPEC 2D.8) -------------------------------------------
SOURCES = ("SAVINGS", "FAMILY", "EXPECTED_GIFTS", "DEBT")


def line_total(kind, amount, guests):
    if amount <= 0:
        raise OracleError("AMOUNT_NOT_POSITIVE")
    if kind == "ONE_OFF":
        return amount
    if kind == "PER_GUEST":
        return amount * guests
    raise OracleError("INVALID_LINE_KIND")


def scenario_totals(lines, guests):
    """lines: [(kind, amount, source)]. Manba bo'yicha yig'indilar."""
    if guests < 0:
        raise OracleError("INVALID_GUESTS")
    by = {k: 0 for k in SOURCES}
    for kind, amount, source in lines:
        if source not in SOURCES:
            raise OracleError("INVALID_SOURCE")
        by[source] += line_total(kind, amount, guests)
    return sum(by.values()), by


def informal_debt_payoff(debt, start, monthly):
    """Marosim qarzini oyiga `monthly` bilan uzish — U9 simulyatori bilan (muddatsiz foizsiz qarz:
    reja qatori juda uzoqda, faqat qo'shimcha to'lov yopadi). Qarz yo'q — (0, None);
    to'lov 0 — None (yopilmaydi)."""
    if debt == 0:
        return 0, None
    if monthly <= 0:
        return None
    st = Scheduled([(add_months(month_start(start), MAX_WINDOWS), debt)], [])
    res, _ = payoff_plan([("c", st, 0)], start, monthly)
    return res["c"]["months"], res["c"]["payoffDate"]


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


def review_protocol(entries, stored, seq, head):
    """Ko'rik bayonnomasi yaxlitligi (uy/SPEC 2F.5–2F.6): bayonnomada `seq` va o'sha paytdagi zanjir boshi
    qayd etilgan. TRUNCATED — yozuvlar kamaygan; CHAIN_BROKEN — saqlangan xesh qayta hisoblanganga mos
    emas (yozuv xeshsiz o'zgartirilgan); HEAD_MISMATCH — zanjir o'zicha butun, lekin bayonnomadagi boshga
    mos emas (yozuv o'zgartirilib, xeshlar qayta hisoblangan). Bayonnomadan keyingi yozuvlar sanaladi."""
    if seq < 0 or len(stored) != len(entries):
        raise OracleError("INVALID_PROTOCOL")
    if len(entries) < seq:
        return {"status": "TRUNCATED", "firstBroken": None, "entriesAfter": 0}
    broken = verify_chain(entries, stored)
    if broken is not None:
        return {"status": "CHAIN_BROKEN", "firstBroken": broken, "entriesAfter": len(entries) - seq}
    at = GENESIS if seq == 0 else chain(entries[:seq])[-1]
    status = "INTACT" if at == head else "HEAD_MISMATCH"
    return {"status": status, "firstBroken": None, "entriesAfter": len(entries) - seq}


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


ROLES = ("CAPITAL_PROVIDER", "WORKER", "BOTH")
LOSS_FOR = {"MUDARABA": "CAPITAL_PROVIDER_BEARS", "MUSHARAKA": "PROPORTIONAL_TO_CAPITAL"}


def partnership_rules(kind, partners, fixed_return, loss_rule, duration_months):
    """U11: sheriklik shartlari (uy/SPEC 2E.1). Barcha xatolar birdan qaytadi (usta uchun)."""
    if kind not in LOSS_FOR:
        raise OracleError("INVALID_KIND")
    errors, warnings, caps = set(), set(), []
    for p in partners:
        if p["role"] not in ROLES:
            raise OracleError("INVALID_ROLE")
        items = p["capitalItems"]
        if any(i["amount"] <= 0 for i in items):
            errors.add("CAPITAL_ITEM_NOT_POSITIVE")
        caps.append(sum(i["amount"] for i in items if i["amount"] > 0))
    if len(partners) < 2:
        errors.add("MIN_TWO_PARTNERS")
    shares = [p["profitShareBp"] for p in partners]
    if any(x < 0 for x in shares) or sum(shares) != 10000:
        errors.add("PROFIT_SHARES_NOT_100")
    if fixed_return is not None:
        errors.add("GUARANTEED_RETURN_FORBIDDEN")
    roles = [p["role"] for p in partners]
    if any(r != "WORKER" and c == 0 for r, c in zip(roles, caps)):
        errors.add("CAPITAL_PROVIDER_WITHOUT_CAPITAL")
    if kind == "MUDARABA":
        if not any(r == "CAPITAL_PROVIDER" and c > 0 for r, c in zip(roles, caps)):
            errors.add("MUDARABA_CAPITAL_PROVIDER_REQUIRED")
        if "WORKER" not in roles:
            errors.add("MUDARABA_WORKER_REQUIRED")
        if "BOTH" in roles:
            errors.add("MUDARABA_BOTH_ROLE")
        if any(r == "WORKER" and c > 0 for r, c in zip(roles, caps)):
            errors.add("MUDARABA_WORKER_CAPITAL")
    else:
        if sum(1 for c in caps if c > 0) < 2:
            errors.add("MUSHARAKA_TWO_CAPITALS_REQUIRED")
        total = sum(caps)
        # OQ-D2 (Hanafiy): ishlamaydigan sherik ulushi kapital ulushidan oshmasin — hozircha ogohlantirish.
        if total > 0 and any(r == "CAPITAL_PROVIDER" and x * total > c * 10000 for r, x, c in zip(roles, shares, caps)):
            warnings.add("SILENT_PARTNER_SHARE_ABOVE_CAPITAL")
    if loss_rule != LOSS_FOR[kind]:
        errors.add("LOSS_RULE_MISMATCH")
    if duration_months is None or not 1 <= duration_months <= 600:
        errors.add("TERM_REQUIRED")
    loss = None
    if not errors:
        loss = allocate(10000, [c if kind == "MUSHARAKA" or r == "CAPITAL_PROVIDER" else 0 for r, c in zip(roles, caps)])
    return {"errors": sorted(errors), "warnings": sorted(warnings), "capital": [_s(c) for c in caps], "lossShareBp": loss}


def buyout_schedule(stake, total_capital, buyer_capital, units, per_period, start, period_months,
                    expected_profit, buyer_share_bp):
    """Kamayib boruvchi musharaka: sotuvchining butun ulushi teng birliklarga bo'linadi, xaridor har davrda
    `per_period` birlik oladi. Narx — taxminiy (har birlik sotilgan kuni baholanadi, OQ-D6)."""
    if stake <= 0:
        raise OracleError("STAKE_NOT_POSITIVE")
    if buyer_capital < 0 or stake + buyer_capital > total_capital:
        raise OracleError("STAKE_EXCEEDS_CAPITAL")
    if not 1 <= units <= 600:
        raise OracleError("INVALID_UNITS")
    if not 1 <= per_period <= units:
        raise OracleError("INVALID_UNITS_PER_PERIOD")
    if not 1 <= period_months <= 12:
        raise OracleError("INVALID_PERIOD")
    if expected_profit is not None and expected_profit < 0:
        raise OracleError("INVALID_PROFIT")
    buyer_profit = None if expected_profit is None else percent_of(expected_profit, buyer_share_bp)
    prices = allocate(stake, [1] * units)
    rows, i, bought = [], 0, 0
    while i < units:
        n = min(per_period, units - i)
        pay = sum(prices[i:i + n])
        i += n
        bought += pay
        rows.append({
            "period": len(rows) + 1,
            "date": add_months(start, len(rows) * period_months).isoformat(),
            "units": n,
            "payment": _s(pay),
            "remainingStake": _s(stake - bought),
            "sellerBp": round_half_up(Fraction((stake - bought) * 10000, total_capital)),
            "buyerBp": round_half_up(Fraction((buyer_capital + bought) * 10000, total_capital)),
            "exceedsShare": buyer_profit is not None and pay > buyer_profit,
        })
    return {"periods": len(rows), "endDate": rows[-1]["date"],
            "buyerProfit": None if buyer_profit is None else _s(buyer_profit), "rows": rows}


def recovery_split(income, household, extra, savings):
    if min(household, extra, savings) < 0 or household + extra + savings != 10000:
        raise OracleError("SPLIT_NOT_100")
    if savings < 100:
        raise OracleError("SAVINGS_SHARE_TOO_LOW")
    return allocate(income, [household, extra, savings])


# --- U12: venture ledger, davr taqsimoti, «Hunardan ishga», taklif tekshiruvi -----------
ENTRY_SIGN = {"INCOME": 1, "EXPENSE": -1, "FORCE_MAJEURE": -1}
LOSS_POLICIES = ("CAPITAL_FIRST", "PER_PERIOD")


def venture_period(kind, partners, entries, policy, carried, negligence=None, buyout=None):
    """Davrni yopish (uy/SPEC 2E.3): natija = kirim − xarajat − fors-major ± tuzatishlar.
    Foyda: CAPITAL_FIRST siyosatida avval o'tgan zararlar (kapital) tiklanadi (OQ-D1, klassik qoida),
    qolgani foyda ulushlari bo'yicha. Zarar: kapitalga mutanosib (mudorabada kapital — faqat kapital
    egalarida; buyout bilan xaridor ham kapital egasi bo'ladi), beparvolikda — ishchining zimmasida
    (kapital kamaymaydi, ishchi qoplaydi). Buyout: xaridor foyda ulushidan muddati kelgan to'lovlar
    tartib bilan, faqat to'liq to'lanadi; to'lanmagani keyingi davrga qoladi."""
    if kind not in LOSS_FOR:
        raise OracleError("INVALID_KIND")
    if policy not in LOSS_POLICIES:
        raise OracleError("INVALID_POLICY")
    if len(partners) < 2:
        raise OracleError("MIN_TWO_PARTNERS")
    shares = [p["profitShareBp"] for p in partners]
    if any(x < 0 for x in shares) or sum(shares) != 10000:
        raise OracleError("PROFIT_SHARES_NOT_100")
    caps = [p["capital"] for p in partners]
    if any(c < 0 for c in caps):
        raise OracleError("CAPITAL_NEGATIVE")
    if len(carried) != len(partners) or any(c < 0 for c in carried) or (policy == "PER_PERIOD" and any(carried)):
        raise OracleError("INVALID_CARRIED")
    totals = {"INCOME": 0, "EXPENSE": 0, "FORCE_MAJEURE": 0, "CORRECTION": 0}
    for e in entries:
        k, a = e["kind"], e["amount"]
        if k not in totals:
            raise OracleError("INVALID_ENTRY_KIND")
        if (k == "CORRECTION" and a == 0) or (k != "CORRECTION" and a <= 0):
            raise OracleError("AMOUNT_NOT_POSITIVE")
        totals[k] += a
    result = totals["INCOME"] - totals["EXPENSE"] - totals["FORCE_MAJEURE"] + totals["CORRECTION"]
    ids = [p["id"] for p in partners]
    if negligence is not None:
        if kind != "MUDARABA":
            raise OracleError("NEGLIGENCE_NOT_APPLICABLE")
        if not negligence["note"].strip():
            raise OracleError("NEGLIGENCE_NOTE_REQUIRED")
        if not any(p["id"] == negligence["partnerId"] and p["role"] == "WORKER" for p in partners):
            raise OracleError("NEGLIGENCE_PARTY_NOT_WORKER")
        if result >= 0:
            raise OracleError("NEGLIGENCE_WITHOUT_LOSS")
    if buyout is not None:
        if buyout["sellerId"] == buyout["buyerId"]:
            raise OracleError("BUYOUT_SAME_PARTY")
        if buyout["sellerId"] not in ids or buyout["buyerId"] not in ids:
            raise OracleError("UNKNOWN_PARTY")
        if any(d["units"] <= 0 or d["capital"] < 0 or d["price"] < 0 for d in buyout["due"]):
            raise OracleError("INVALID_INSTALLMENT")
    n = len(partners)
    recovered, liability, after = [0] * n, [0] * n, list(carried)
    cap_after = list(caps)
    if result >= 0:
        rec_total = min(result, sum(carried)) if policy == "CAPITAL_FIRST" else 0
        if rec_total > 0:
            recovered = allocate(rec_total, carried)
        distributable = result - rec_total
        parts = allocate(distributable, shares)
        after = [c - r for c, r in zip(carried, recovered)]
        cap_after = [c + r for c, r in zip(caps, recovered)]
    else:
        distributable = 0
        if negligence is not None:
            parts = allocate(result, [1 if i == negligence["partnerId"] else 0 for i in ids])
            liability = [-x for x in parts]
        else:
            weights = [max(0, c) for c in caps]
            if sum(weights) == 0:
                raise OracleError("NO_CAPITAL")
            parts = allocate(result, weights)
            cap_after = [c + x for c, x in zip(caps, parts)]
            if policy == "CAPITAL_FIRST":
                after = [c - x for c, x in zip(carried, parts)]
    payouts = [max(0, x) for x in parts]
    bo = None
    if buyout is not None:
        si, bi = ids.index(buyout["sellerId"]), ids.index(buyout["buyerId"])
        available, amount, capital, paid = payouts[bi], 0, 0, []
        for d in buyout["due"]:
            if amount + d["price"] > available:
                break
            amount += d["price"]
            capital += d["capital"]
            paid.append(d["no"])
        capital = min(capital, max(0, cap_after[si]))
        payouts[bi] -= amount
        payouts[si] += amount
        cap_after[si] -= capital
        cap_after[bi] += capital
        bo = {"paid": paid, "amount": _s(amount), "capital": _s(capital),
              "unpaid": [d["no"] for d in buyout["due"] if d["no"] not in paid]}
    S = lambda xs: [_s(x) for x in xs]  # noqa: E731
    return {"income": _s(totals["INCOME"]), "expense": _s(totals["EXPENSE"]),
            "forceMajeure": _s(totals["FORCE_MAJEURE"]), "corrections": _s(totals["CORRECTION"]),
            "result": _s(result), "recovered": S(recovered), "distributable": _s(distributable),
            "shares": S(parts), "liability": S(liability), "carriedAfter": S(after),
            "buyout": bo, "payouts": S(payouts), "capitalAfter": S(cap_after)}


SCENARIOS = ("PESSIMISTIC", "BASE", "OPTIMISTIC")


def ceil_div(a: int, b: int) -> int:
    return -((-a) // b)


def venture_idea(capex_items, scenarios, worker_share_bp=None):
    """«Hunardan ishga» (2E.4): CAPEX, 3 stsenariy; payback = ⌈CAPEX / oylik sof foyda⌉ oy.
    Sheriklikda: ishchi ulushi foydadan (zararda 0), qolgani kapital egasiga va uning payback'i."""
    if any(a <= 0 for a in capex_items):
        raise OracleError("CAPEX_ITEM_NOT_POSITIVE")
    if sorted(s["name"] for s in scenarios) != sorted(SCENARIOS):
        raise OracleError("INVALID_SCENARIOS")
    if worker_share_bp is not None and not 0 <= worker_share_bp <= 10000:
        raise OracleError("INVALID_BP")
    capex = sum(capex_items)
    by = {s["name"]: s for s in scenarios}
    out, nets = [], []
    for name in SCENARIOS:
        s = by[name]
        if s["income"] < 0 or s["expense"] < 0:
            raise OracleError("AMOUNT_NEGATIVE")
        net = s["income"] - s["expense"]
        nets.append(net)
        pay = (0 if capex == 0 else ceil_div(capex, net)) if net > 0 else None
        row = {"name": name, "net": _s(net), "annualNet": _s(net * 12), "paybackMonths": pay}
        if worker_share_bp is not None:
            w = percent_of(net, worker_share_bp) if net > 0 else 0
            inv = net - w
            row.update({"workerMonthly": _s(w), "investorMonthly": _s(inv),
                        "investorPaybackMonths": (0 if capex == 0 else ceil_div(capex, inv)) if inv > 0 else None})
        out.append(row)
    warnings = [] if nets[0] <= nets[1] <= nets[2] else ["SCENARIOS_NOT_ORDERED"]
    return {"capex": _s(capex), "scenarios": out, "warnings": warnings}


# (savol, javob) → (bayroq, daraja); javobning qolgan qiymati xavfsiz.
OFFER_QUESTIONS = ("guaranteed", "lossShared", "realActivity", "recruitment", "urgency", "written",
                   "licensed", "inspection", "exitEasy")
OFFER_TABLE = {
    "guaranteed": {"YES": ("GUARANTEED_PROFIT", "RED"), "UNKNOWN": ("GUARANTEED_UNKNOWN", "YELLOW")},
    "lossShared": {"NO": ("LOSS_NOT_SHARED", "RED"), "UNKNOWN": ("LOSS_SHARING_UNKNOWN", "YELLOW")},
    "realActivity": {"NO": ("NO_REAL_ACTIVITY", "RED"), "UNKNOWN": ("REAL_ACTIVITY_UNKNOWN", "YELLOW")},
    "recruitment": {"YES": ("RECRUITMENT_REQUIRED", "RED"), "UNKNOWN": ("RECRUITMENT_UNKNOWN", "YELLOW")},
    "urgency": {"YES": ("URGENCY", "YELLOW"), "UNKNOWN": ("URGENCY_UNKNOWN", "YELLOW")},
    "written": {"NO": ("NO_WRITTEN_CONTRACT", "YELLOW"), "UNKNOWN": ("WRITTEN_UNKNOWN", "YELLOW")},
    # M5 («besh xavf belgisi», musofir/SPEC 6.8): davlat ruxsati, o'z ko'zi bilan tekshirish, pulni qaytarib olish.
    "licensed": {"NO": ("NO_LICENSE", "YELLOW"), "UNKNOWN": ("LICENSE_UNKNOWN", "YELLOW")},
    "inspection": {"NO": ("INSPECTION_REFUSED", "RED"), "UNKNOWN": ("INSPECTION_UNKNOWN", "YELLOW")},
    "exitEasy": {"NO": ("EXIT_HARD", "RED"), "UNKNOWN": ("EXIT_UNKNOWN", "YELLOW")},
}
# «Besh xavf belgisi»: 1 — kafolatlangan foyda, 2 — shoshirish, 3 — yangi odam olib kelish,
# 4 — ishning o'zi yo'q (mol, ruxsat, tekshirtirmaydi), 5 — kirish oson, chiqish qiyin. Bitta belgi — ehtiyot
# bo'lishga, ikkitasi — voz kechishga sabab: ikki va undan ortiq belgi — TWO_SIGNS (qizil).
OFFER_SIGNS = {"GUARANTEED_PROFIT": 1, "URGENCY": 2, "RECRUITMENT_REQUIRED": 3, "NO_REAL_ACTIVITY": 4,
               "NO_LICENSE": 4, "INSPECTION_REFUSED": 4, "EXIT_HARD": 5}


def offer_signs(flags):
    """Bayroqlar → topilgan belgilar soni va kerak bo'lsa TWO_SIGNS bayrog'i (ro'yxatga qo'shiladi)."""
    n = len({OFFER_SIGNS[f["code"]] for f in flags if f["code"] in OFFER_SIGNS})
    if n >= 2:
        flags.append({"code": "TWO_SIGNS", "level": "RED"})
    return n


def offer_check(answers):
    """«Kafolatlangan foyda» detektori (2E.5): biror qizil bayroq — QIZIL, aks holda sariq — SARIQ."""
    flags = []
    for q in OFFER_QUESTIONS:
        a = answers.get(q)
        if a is None:
            raise OracleError("MISSING_ANSWER")
        if a not in ("YES", "NO", "UNKNOWN"):
            raise OracleError("INVALID_ANSWER")
        hit = OFFER_TABLE[q].get(a)
        if hit:
            flags.append({"code": hit[0], "level": hit[1]})
    signs = offer_signs(flags)
    levels = {f["level"] for f in flags}
    verdict = "RED" if "RED" in levels else "YELLOW" if levels else "GREEN"
    return {"verdict": verdict, "flags": flags, "signs": signs}


# --- K1: Kasb-kor — ikki cho'ntak, egasi maoshi, hamyonlar (kasbkor/SPEC 2) ---------------
KK_WALLETS = ("CASH", "CARD")
KK_EFFECT = {"SALE": 1, "EXPENSE": -1, "OWNER_DRAW": -1, "OWNER_CONTRIBUTION": 1, "OWNER_SALARY": -1,
             "EQUIPMENT_PURCHASE": -1, "EQUIPMENT_SALE": 1, "CASH_SHORT": -1, "CASH_OVER": 1, "STOCK_PURCHASE": -1}


def kk_month_report(opening_cash, opening_card, salary, moves):
    """Oy hisoboti: tushum, chiqim, pul oqimi (tushum − chiqim; egasi oldi, kapital va maosh bu yerga
    kirmaydi), egasiga to'langan (maosh o'tkazmasi + «egasi oldi»), maosh qoldig'i yoki ortiqcha olingan
    (maosh belgilangan bo'lsa), hamyon qoldiqlari (oy boshidagi qoldiq + harakatlar). K2: uskuna xaridi va
    sotuvi hamyonga ta'sir qiladi, lekin pul oqimiga kirmaydi (aktiv; xarajat — eskirish orqali)."""
    if salary < 0:
        raise OracleError("AMOUNT_NOT_POSITIVE")
    bal = {"CASH": opening_cash, "CARD": opening_card}
    tot = {k: 0 for k in KK_EFFECT}
    for m in moves:
        amount = int(m["amount"])
        if amount <= 0:
            raise OracleError("AMOUNT_NOT_POSITIVE")
        if m["wallet"] not in KK_WALLETS:
            raise OracleError("INVALID_WALLET")
        if m["kind"] == "TRANSFER":
            to = m.get("toWallet")
            if to not in KK_WALLETS:
                raise OracleError("INVALID_WALLET")
            if to == m["wallet"]:
                raise OracleError("SAME_WALLET")
            bal[m["wallet"]] -= amount
            bal[to] += amount
            continue
        if m["kind"] not in KK_EFFECT:
            raise OracleError("INVALID_KIND")
        bal[m["wallet"]] += KK_EFFECT[m["kind"]] * amount
        tot[m["kind"]] += amount
    paid = tot["OWNER_SALARY"] + tot["OWNER_DRAW"]
    return {
        "revenue": _s(tot["SALE"]), "expenses": _s(tot["EXPENSE"]), "cashFlow": _s(tot["SALE"] - tot["EXPENSE"]),
        "ownerDraws": _s(tot["OWNER_DRAW"]), "ownerSalaryTransferred": _s(tot["OWNER_SALARY"]),
        "contributions": _s(tot["OWNER_CONTRIBUTION"]), "ownerPaid": _s(paid),
        "salaryRemaining": None if salary == 0 else _s(max(0, salary - paid)),
        "overdrawn": None if salary == 0 else _s(max(0, paid - salary)),
        "equipmentPurchases": _s(tot["EQUIPMENT_PURCHASE"]), "equipmentSales": _s(tot["EQUIPMENT_SALE"]),
        "cashDifference": _s(tot["CASH_OVER"] - tot["CASH_SHORT"]),
        "stockPurchases": _s(tot["STOCK_PURCHASE"]),
        "cash": _s(bal["CASH"]), "card": _s(bal["CARD"]),
        "negativeWallets": [w for w in KK_WALLETS if bal[w] < 0],
    }


KK_MAX_LIFE = 600


def kk_depreciation(cost, salvage, months, query, disposal=None):
    """Uskuna eskirishi (SPEC 3.1, 3.3). (narx − qoldiq qiymati) foydali muddat oylariga largest remainder
    bilan teng bo'linadi — qoldiq tiyinlar birinchi oylarga, yig'indi aniq. 0-oy — xarid oyi. `d`-oyda
    sotilsa yoki yaroqsiz bo'lsa: shu oydan oddiy eskirish yo'q, `d`-oyda bir martalik «chiqib ketish» =
    balans qiymati (narx − d gacha eskirish) − tushgan pul (manfiy — foyda); keyin balans 0."""
    if cost <= 0:
        raise OracleError("AMOUNT_NOT_POSITIVE")
    if salvage < 0 or salvage > cost:
        raise OracleError("INVALID_SALVAGE")
    if not 1 <= months <= KK_MAX_LIFE:
        raise OracleError("INVALID_USEFUL_LIFE")
    schedule = allocate(cost - salvage, [1] * months)
    d = None
    if disposal is not None:
        d, proceeds = disposal["month"], int(disposal["proceeds"])
        if d < 0:
            raise OracleError("INVALID_MONTH")
        if proceeds < 0:
            raise OracleError("AMOUNT_NEGATIVE")

    def book_before(m):
        return cost - sum(schedule[:min(m, months)])

    def at(m):
        if m < 0:
            raise OracleError("INVALID_MONTH")
        if d is not None and m >= d:
            return {"month": m, "depreciation": _s(0), "disposal": _s(book_before(d) - proceeds if m == d else 0), "bookValue": _s(0)}
        return {"month": m, "depreciation": _s(schedule[m] if m < months else 0), "disposal": _s(0), "bookValue": _s(book_before(m + 1))}

    return {"schedule": [_s(x) for x in schedule], "total": _s(sum(schedule)), "months": [at(m) for m in query]}


def kk_hours_value(hours100, rate):
    """Soat (yuzdan birlarda: 250 = 2,5 soat) × soat bahosi, yarimni noldan uzoqqa yaxlitlab."""
    if hours100 < 0:
        raise OracleError("INVALID_HOURS")
    if rate < 0:
        raise OracleError("AMOUNT_NEGATIVE")
    return round_half_up(Fraction(hours100 * rate, 100))


def kk_true_profit(revenue, cogs, opex, owner_labor, family, depreciation, disposal, stock_losses=0):
    """Haqiqiy foyda (SPEC 3.1): ko'rinadigan = tushum − sotilgan tovar tannarxi − tovar yo'qotishi
    (hisobdan chiqarish va inventarizatsiya farqi; manfiy — topilgan tovar) − operatsion xarajat;
    haqiqiy = ko'rinadigan − o'z mehnati − to'lanmagan oilaviy mehnat − eskirish − uskuna chiqib ketishi.
    To'langan oilaviy mehnat operatsion xarajatda bor — ikki marta hisoblanmaydi."""
    for v in (revenue, cogs, opex, owner_labor, depreciation):
        if v < 0:
            raise OracleError("AMOUNT_NEGATIVE")
    unpaid = paid = 0
    for f in family:
        v = kk_hours_value(int(f["hours100"]), int(f["hourlyRate"]))
        if f["paid"]:
            paid += v
        else:
            unpaid += v
    visible = revenue - cogs - stock_losses - opex
    return {"visibleProfit": _s(visible), "stockLosses": _s(stock_losses), "ownerLabor": _s(owner_labor), "familyLabor": _s(unpaid), "familyLaborPaid": _s(paid),
            "depreciation": _s(depreciation), "disposal": _s(disposal),
            "trueProfit": _s(visible - owner_labor - unpaid - depreciation - disposal)}


KK_CASH_REASONS = ("UNRECORDED_EXPENSE", "CHANGE_ERROR", "GIVEN_ON_CREDIT", "OWNER_TOOK", "UNKNOWN")
KK_SHORTAGE_REPEAT = 3


def kk_cash_close(opening, moves, counted, reason, recent):
    """Kunlik kassa yopish (SPEC 5.1). Kutilgan = ochilish + kunning naqd kassaga ta'siri (naqd tushum,
    naqd chiqim, naqd «egasi oldi», kartaga topshirilgan, kartadan olingan va boshqalar); karta
    harakatlari kassaga ta'sir qilmaydi. Farq = sanalgan − kutilgan; nol bo'lmasa sabab tanlanadi.
    `recent` — oxirgi 4 hafta (shu kunsiz) farqlari: shu bilan 3+ kamomad — «xato qidirish» taklifi."""
    if counted < 0 or opening < 0:
        raise OracleError("AMOUNT_NEGATIVE")
    br = {"cashSales": 0, "cashExpenses": 0, "ownerDraws": 0, "handedOver": 0, "otherIn": 0, "otherOut": 0}
    for m in moves:
        a = int(m["amount"])
        if a <= 0:
            raise OracleError("AMOUNT_NOT_POSITIVE")
        k, w = m["kind"], m["wallet"]
        if w not in KK_WALLETS:
            raise OracleError("INVALID_WALLET")
        if k == "TRANSFER":
            to = m.get("toWallet")
            if to not in KK_WALLETS:
                raise OracleError("INVALID_WALLET")
            if to == w:
                raise OracleError("SAME_WALLET")
            if w == "CASH":
                br["handedOver"] += a
            else:
                br["otherIn"] += a
            continue
        if k not in KK_EFFECT and k != "OPENING":
            raise OracleError("INVALID_KIND")
        if w != "CASH":
            continue
        sign = 1 if k == "OPENING" else KK_EFFECT[k]
        key = {"SALE": "cashSales", "EXPENSE": "cashExpenses", "OWNER_DRAW": "ownerDraws"}.get(k, "otherIn" if sign > 0 else "otherOut")
        br[key] += a
    expected = opening + br["cashSales"] - br["cashExpenses"] - br["ownerDraws"] - br["handedOver"] + br["otherIn"] - br["otherOut"]
    diff = counted - expected
    if diff != 0:
        if reason is None:
            raise OracleError("REASON_REQUIRED")
        if reason not in KK_CASH_REASONS:
            raise OracleError("INVALID_REASON")
    shortages = sum(1 for d in recent if int(d) < 0) + (1 if diff < 0 else 0)
    return {**{k: _s(v) for k, v in br.items()}, "expected": _s(expected), "difference": _s(diff),
            "status": "EXACT" if diff == 0 else ("SHORT" if diff < 0 else "OVER"),
            "reason": reason if diff != 0 else None, "suggestSearch": diff < 0 and shortages >= KK_SHORTAGE_REPEAT}


KK_SHIFT_IN = ("SALE", "CREDIT_PAYMENT")


def kk_shift_close(opening, ins, counted, handed_over, reason, recent):
    """Sotuvchi smenasi (kasbkor/SPEC 12, ADR-0003). Sotuvchi qurilmasi faqat o'z naqd tushumi va naqd
    nasiya to'lovlarini biladi: kutilgan = ochilish + ular (kunlik kassa yopish qoidasi, `kk_cash_close`).
    Sanalgandan egasiga topshirilgani ayriladi — qolgani keyingi smena ochilishi. Karta tushumlari
    kassaga ta'sir qilmaydi (ma'lumot uchun alohida)."""
    if handed_over < 0:
        raise OracleError("AMOUNT_NEGATIVE")
    moves, sales, payments, card = [], 0, 0, 0
    for m in ins:
        if m["kind"] not in KK_SHIFT_IN:
            raise OracleError("INVALID_KIND")
        a = int(m["amount"])
        if m["wallet"] == "CARD" and a > 0:
            card += a
        elif m["wallet"] == "CASH" and a > 0:
            if m["kind"] == "SALE":
                sales += a
            else:
                payments += a
        moves.append({"kind": "SALE", "wallet": m["wallet"], "amount": m["amount"]})
    r = kk_cash_close(opening, moves, counted, reason, recent)
    if handed_over > counted:
        raise OracleError("HANDOVER_ABOVE_COUNTED")
    return {"cashSales": _s(sales), "creditPayments": _s(payments), "cardIn": _s(card), "expected": r["expected"],
            "difference": r["difference"], "status": r["status"], "reason": r["reason"], "suggestSearch": r["suggestSearch"],
            "handedOver": _s(handed_over), "left": _s(counted - handed_over)}


KK_MAX_INSTALLMENTS = 120


def kk_credit_sale(credit_price, cash_price, n, first_due, events, today):
    """Nasiya (SPEC 5.2). Nasiya narxi qotiriladi: `n` ta oylik to'lovga largest remainder bilan bo'linadi
    (qoldiq tiyinlar birinchi to'lovlarga), birinchisi `first_due` da. Hodisalar sana tartibida:
    to'lov, kechirish (to'liq yoki qisman), muddatni uzaytirish (yopilmagan to'lovlar `m` oyga
    suriladi, summa o'zgarmaydi). Kechikish uchun ustama yo'q — qoldiq sanaga bog'liq emas.
    Kechikkan kunlar — eng birinchi yopilmagan va muddati o'tgan to'lov sanasidan; guruhlar 1–30,
    31–60, 61–90, 90+."""
    if credit_price <= 0:
        raise OracleError("AMOUNT_NOT_POSITIVE")
    if cash_price is not None and cash_price <= 0:
        raise OracleError("AMOUNT_NOT_POSITIVE")
    if not 1 <= n <= KK_MAX_INSTALLMENTS:
        raise OracleError("INVALID_INSTALLMENTS")
    amounts = allocate(credit_price, [1] * n)
    dues = [add_months(first_due, k) for k in range(n)]
    paid = forgiven = 0
    prev = None
    for e in events:
        d = date.fromisoformat(e["date"])
        if prev is not None and d < prev:
            raise OracleError("INVALID_DATE")
        prev = d
        outstanding = credit_price - paid - forgiven
        if e["kind"] in ("PAYMENT", "FORGIVE"):
            a = int(e["amount"])
            if a <= 0:
                raise OracleError("AMOUNT_NOT_POSITIVE")
            if a > outstanding:
                raise OracleError("EXCEEDS_OUTSTANDING")
            if e["kind"] == "PAYMENT":
                paid += a
            else:
                forgiven += a
        elif e["kind"] == "EXTEND":
            mths = e["months"]
            if not 1 <= mths <= 24:
                raise OracleError("INVALID_EXTENSION")
            if outstanding == 0:
                raise OracleError("ALREADY_SETTLED")
            covered, cum = paid + forgiven, 0
            for i in range(n):
                cum += amounts[i]
                if cum > covered:
                    dues[i] = add_months(dues[i], mths)
        else:
            raise OracleError("INVALID_KIND")
    covered, cum = paid + forgiven, 0
    rows, earliest, nxt = [], None, None
    for i in range(n):
        c = min(amounts[i], max(0, covered - cum))
        cum += amounts[i]
        if c == amounts[i]:
            state = "PAID"
        elif dues[i] < today:
            state = "OVERDUE"
            earliest = earliest or dues[i]
        else:
            state = "DUE"
        if c < amounts[i] and nxt is None:
            nxt = {"date": dues[i].isoformat(), "amount": _s(amounts[i] - c)}
        rows.append({"due": dues[i].isoformat(), "amount": _s(amounts[i]), "covered": _s(c), "state": state})
    outstanding = credit_price - paid - forgiven
    days = (today - earliest).days if earliest else 0
    if outstanding == 0:
        status, bucket = "SETTLED", None
    elif days == 0:
        status, bucket = "CURRENT", None
    else:
        status = "OVERDUE"
        bucket = "D1_30" if days <= 30 else "D31_60" if days <= 60 else "D61_90" if days <= 90 else "D90_PLUS"
    return {"schedule": rows, "paid": _s(paid), "forgiven": _s(forgiven), "outstanding": _s(outstanding),
            "status": status, "overdueDays": days, "bucket": bucket, "nextDue": nxt,
            "creditMarkup": None if cash_price is None else _s(credit_price - cash_price)}


KK_COST_METHODS = ("AVERAGE", "FIFO")


def kk_cogs(method, factor, moves):
    """Tovar qoldig'i va tannarx (SPEC 4.1–4.2). Miqdorlar butun sonda (asosiy birlik: g, ml, dona, mm).
    Driftsiz: o'rtachada tannarx = round_half_up(qoldiq qiymati × chiqim / qoldiq miqdor), qiymat shunga
    kamayadi — oxirgi birlik chiqqanda qiymat aniq 0. FIFO — eng eski partiyadan, qisman partiya shu
    formula bilan. Chiqimlar: sotuv, hisobdan chiqarish, inventarizatsiyada kamomad (manfiy tuzatish).
    Ortiqcha (musbat tuzatish) — `amount` qiymat bilan yangi partiya. `factor` — narx ko'rsatish birligi
    (1000: kg, l, m; 1: dona)."""
    if method not in KK_COST_METHODS:
        raise OracleError("INVALID_METHOD")
    if factor not in (1, 1000):
        raise OracleError("INVALID_UNIT")
    qty = value = 0
    layers = []
    out = []

    def take(q):
        nonlocal qty, value
        if q > qty:
            raise OracleError("INSUFFICIENT_STOCK")
        if method == "AVERAGE":
            c = round_half_up(Fraction(value * q, qty))
        else:
            c, left = 0, q
            while left:
                lq, lv = layers[0]
                t = min(left, lq)
                part = lv if t == lq else round_half_up(Fraction(lv * t, lq))
                layers[0] = [lq - t, lv - part]
                if layers[0][0] == 0:
                    layers.pop(0)
                c += part
                left -= t
        qty -= q
        value -= c
        return c

    for m in moves:
        k, q = m["kind"], int(m["qty"])
        if k == "PURCHASE":
            a = int(m["amount"])
            if q <= 0:
                raise OracleError("INVALID_QTY")
            if a <= 0:
                raise OracleError("AMOUNT_NOT_POSITIVE")
            qty, value = qty + q, value + a
            layers.append([q, a])
            out.append({"kind": k, "cost": _s(a)})
        elif k in ("SALE", "WRITE_OFF"):
            if q <= 0:
                raise OracleError("INVALID_QTY")
            out.append({"kind": k, "cost": _s(take(q))})
        elif k == "ADJUST":
            if q == 0:
                raise OracleError("INVALID_QTY")
            if q < 0:
                out.append({"kind": k, "cost": _s(take(-q))})
            else:
                a = int(m["amount"])
                if a < 0:
                    raise OracleError("AMOUNT_NEGATIVE")
                qty, value = qty + q, value + a
                layers.append([q, a])
                out.append({"kind": k, "cost": _s(-a)})
        else:
            raise OracleError("INVALID_KIND")
    return {"moves": out, "qty": qty, "value": _s(value),
            "unitCost": None if qty == 0 else _s(round_half_up(Fraction(value * factor, qty))),
            "layers": [{"qty": lq, "value": _s(lv)} for lq, lv in layers] if method == "FIFO" else None}


def kk_replacement(qty, book_value, price, factor, sale_price):
    """Qayta tiklash narxi (SPEC 4.3): qoldiqning bugungi xarid narxidagi qiymati
    = round_half_up(miqdor × narx / factor); farq — «inflyatsiya yegan kapital» (manfiy — narx tushgan).
    Sotuv narxi qayta tiklash narxidan past bo'lsa — ogohlantirish."""
    if qty < 0:
        raise OracleError("INVALID_QTY")
    if factor not in (1, 1000):
        raise OracleError("INVALID_UNIT")
    if price <= 0:
        raise OracleError("AMOUNT_NOT_POSITIVE")
    if book_value < 0 or (sale_price is not None and sale_price <= 0):
        raise OracleError("AMOUNT_NEGATIVE")
    rv = round_half_up(Fraction(qty * price, factor))
    return {"replacementValue": _s(rv), "inflationGap": _s(rv - book_value),
            "saleBelowReplacement": sale_price is not None and sale_price < price}


KK_TAX_BASES = ("NONE", "REVENUE", "PROFIT", "FIXED")


def kk_month_close(revenue, expenses, depreciation, salary, paid, tax, rule, carry_overdraw):
    """«Hisob kuni» (SPEC 4.5). Tartib: (1) soliq zaxirasi — egasi kiritgan qoida: tushumdan yoki
    foydadan (tushum − chiqim, manfiy bo'lsa 0) foiz, yoki qat'iy summa; (2) egasi maoshi — belgilangan
    maosh, lekin olingan undan ko'p bo'lsa — olingani; (3) qolgan = tushum − soliq − chiqim − maosh;
    manfiy bo'lmasa — taqsimot qoidasi (zaxira / aylanma / kengayish / sadaqa, bp, jami 10 000) bo'yicha
    largest remainder. Manfiy — taqsimot yo'q, izoh so'raladi. Zaxira eskirishdan kam bo'lsa — belgi.
    Maoshdan ortiq olingan summa tanlansa keyingi oy maoshidan ushlanadi."""
    for v in (revenue, expenses, depreciation, salary, paid):
        if v < 0:
            raise OracleError("AMOUNT_NEGATIVE")
    parts = [rule["reserveBp"], rule["workingBp"], rule["expansionBp"], rule["sadaqaBp"]]
    if any(p < 0 for p in parts) or sum(parts) != 10000:
        raise OracleError("INVALID_RULE")
    base = tax["base"]
    if base not in KK_TAX_BASES:
        raise OracleError("INVALID_TAX_BASE")
    if base == "FIXED":
        t = int(tax["amount"])
        if t < 0:
            raise OracleError("AMOUNT_NEGATIVE")
    elif base == "NONE":
        t = 0
    else:
        t = percent_of(revenue if base == "REVENUE" else max(0, revenue - expenses), tax["bp"])
    owner_pay = max(salary, paid)
    overdrawn = max(0, paid - salary) if salary > 0 else 0
    remaining = revenue - t - expenses - owner_pay
    alloc = None if remaining < 0 else allocate(remaining, parts)
    return {"tax": _s(t), "ownerPay": _s(owner_pay), "overdrawn": _s(overdrawn), "carryForward": _s(overdrawn if carry_overdraw else 0),
            "remaining": _s(remaining), "needsExplanation": remaining < 0,
            "allocation": None if alloc is None else {"reserve": _s(alloc[0]), "working": _s(alloc[1]), "expansion": _s(alloc[2]), "sadaqa": _s(alloc[3])},
            "reserveBelowDepreciation": alloc is not None and alloc[0] < depreciation}


def kk_order_quote(material, hours100, rate, travel, depreciation, reserve_bp, price=None, advance=None):
    """Buyurtma kalkulyatori (SPEC 3.2): tannarx = material + mehnat + yo'l + eskirish ulushi + zaxira
    (shu yig'indidan foiz). Narx berilsa: marja, o'z mehnatingizga qoladigan pul (narx − mehnatsiz
    tannarx) va uning soatbayi. Avans berilsa: materialga yetmagan va materialdan ortgan qism."""
    for v in (material, travel, depreciation):
        if v < 0:
            raise OracleError("AMOUNT_NEGATIVE")
    labor = kk_hours_value(hours100, rate)
    base = material + labor + travel + depreciation
    reserve = percent_of(base, reserve_bp)
    cost = base + reserve
    out = {"labor": _s(labor), "subtotal": _s(base), "reserve": _s(reserve), "cost": _s(cost),
           "margin": None, "laborPaid": None, "belowCost": None, "effectiveHourlyRate": None,
           "materialShortfall": None, "advanceAfterMaterial": None}
    if price is not None:
        if price < 0:
            raise OracleError("AMOUNT_NEGATIVE")
        left = price - (cost - labor)
        out.update(margin=_s(price - cost), laborPaid=_s(left), belowCost=price < cost,
                   effectiveHourlyRate=None if hours100 == 0 else _s(round_half_up(Fraction(left * 100, hours100))))
    if advance is not None:
        if advance < 0:
            raise OracleError("AMOUNT_NEGATIVE")
        out.update(materialShortfall=_s(max(0, material - advance)), advanceAfterMaterial=_s(max(0, advance - material)))
    return out


KK_MAX_ADVANCE_INSTALLMENTS = 24


def kk_payroll(months, advances, opening=0):
    """Xodim bilan oylik hisob (SPEC 7.2). `months` — xodim ishlagan oylar (0 dan), har birida oylik haq va
    shu oy to'langan summalar. Avans foizsiz va jarimasiz: summa `n` ta teng ulushga largest remainder bilan
    bo'linadi (qoldiq tiyinlar birinchi ulushlarga), `startMonth` dan boshlab har oy haqdan ushlanadi.
    Haq yetmasa (masalan, haqsiz ta'til) — ushlanmagan qism keyingi oyga o'tadi, ustama yo'q. Bir nechta avans —
    berilgan oy va tartib bo'yicha (eskisi birinchi). Qoldiq = oldingi qoldiq + (haq − ushlangan) − to'langan;
    manfiy — ortiq to'langan (keyingi oy haqidan qoplanadi)."""
    rows_in = []
    for m in months:
        salary = int(m["salary"])
        if salary < 0:
            raise OracleError("AMOUNT_NEGATIVE")
        paid = [int(x) for x in m.get("paid", [])]
        if any(x <= 0 for x in paid):
            raise OracleError("AMOUNT_NOT_POSITIVE")
        rows_in.append((salary, sum(paid)))
    plans = []
    for idx, a in enumerate(advances):
        amount, n, given, start = int(a["amount"]), a["installments"], a["month"], a["startMonth"]
        if amount <= 0:
            raise OracleError("AMOUNT_NOT_POSITIVE")
        if not 1 <= n <= KK_MAX_ADVANCE_INSTALLMENTS:
            raise OracleError("INVALID_INSTALLMENTS")
        if given < 0 or start < given:
            raise OracleError("INVALID_START")
        plans.append({"id": a["id"], "given": given, "idx": idx, "start": start, "amount": amount,
                      "parts": allocate(amount, [1] * n), "due": 0, "deducted": 0})
    order = sorted(plans, key=lambda p: (p["given"], p["idx"]))
    balance = opening
    rows = []
    for i, (salary, paid) in enumerate(rows_in):
        avail, scheduled, deducted = salary, 0, 0
        for p in order:
            k = i - p["start"]
            if 0 <= k < len(p["parts"]):
                p["due"] += p["parts"][k]
            if p["due"] > 0:
                scheduled += p["due"]
                d = min(p["due"], avail)
                p["due"] -= d
                p["deducted"] += d
                avail -= d
                deducted += d
        net = salary - deducted
        balance += net - paid
        rows.append({"salary": _s(salary), "scheduled": _s(scheduled), "deducted": _s(deducted), "net": _s(net),
                     "paid": _s(paid), "balance": _s(balance)})
    adv = [{"id": p["id"], "schedule": [{"month": p["start"] + k, "amount": _s(v)} for k, v in enumerate(p["parts"])],
            "deducted": _s(p["deducted"]), "outstanding": _s(p["amount"] - p["deducted"])} for p in plans]
    return {"months": rows, "advances": adv}


KK_MAX_SUPPLY_DAYS = 365
KK_DUE_SOON_DAYS = 7


def kk_supplier_balance(deliveries, payments, today):
    """Ta'minotchiga qarz (SPEC 7.1 `SUPPLY`). Har yetkazish — summa va to'lov muddati (kun, 0 — darhol).
    To'lovlar sana tartibida eng erta muddatli ochiq yetkazishdan yopiladi (muddat, yetkazilgan sana, tartib);
    to'lov shu kungacha yetkazilganlar qoldig'idan oshmaydi (oldindan to'lov — K6 da yo'q). Kechikish uchun
    jarima yoki ustama yo'q. `dueSoon` — 7 kun ichida muddati keladigan qoldiq."""
    dl = []
    for idx, d in enumerate(deliveries):
        amount, days = int(d["amount"]), d["dueDays"]
        if amount <= 0:
            raise OracleError("AMOUNT_NOT_POSITIVE")
        if not 0 <= days <= KK_MAX_SUPPLY_DAYS:
            raise OracleError("INVALID_DAYS")
        on = date.fromisoformat(d["on"])
        dl.append({"id": d["id"], "idx": idx, "on": on, "due": on + timedelta(days=days), "amount": amount, "left": amount})
    prev = None
    paid_total = 0
    for p in payments:
        on, a = date.fromisoformat(p["on"]), int(p["amount"])
        if prev is not None and on < prev:
            raise OracleError("INVALID_DATE")
        prev = on
        if a <= 0:
            raise OracleError("AMOUNT_NOT_POSITIVE")
        open_ = sorted((d for d in dl if d["on"] <= on and d["left"] > 0), key=lambda d: (d["due"], d["on"], d["idx"]))
        if a > sum(d["left"] for d in open_):
            raise OracleError("EXCEEDS_OUTSTANDING")
        paid_total += a
        for d in open_:
            x = min(a, d["left"])
            d["left"] -= x
            a -= x
    rows, overdue, soon, nxt = [], 0, 0, None
    for d in dl:
        if d["left"] == 0:
            state, days = "PAID", 0
        elif d["due"] < today:
            state, days = "OVERDUE", (today - d["due"]).days
            overdue += d["left"]
        else:
            state, days = "DUE", 0
            if (d["due"] - today).days <= KK_DUE_SOON_DAYS:
                soon += d["left"]
        rows.append({"id": d["id"], "due": d["due"].isoformat(), "amount": _s(d["amount"]), "paid": _s(d["amount"] - d["left"]),
                     "outstanding": _s(d["left"]), "state": state, "overdueDays": days})
    unpaid = sorted((d for d in dl if d["left"] > 0), key=lambda d: (d["due"], d["on"], d["idx"]))
    if unpaid:
        nxt = {"date": unpaid[0]["due"].isoformat(), "amount": _s(unpaid[0]["left"])}
    return {"deliveries": rows, "paid": _s(paid_total), "outstanding": _s(sum(d["left"] for d in dl)),
            "overdue": _s(overdue), "dueSoon": _s(soon), "nextDue": nxt}


KK_GATE_CONDITIONS = ("RESERVE", "PROFIT", "RECEIVABLES", "INTEREST_DEBT", "PLAN")


def kk_expansion_gate(reserve, opex_months, required_months, true_profits, receivables, receivables_90, max_bad_bp,
                      has_interest_debt, has_payoff_plan, has_plan):
    """Kengayish darvozasi (SPEC 6.1): beshala shart bajarilsa ochiq. (1) biznes zaxirasi ≥ `required_months` ×
    oxirgi to'liq oylar operatsion xarajati o'rtachasi (`round_half_up`; xarajat 0 bo'lsa — bajarilgan, tarix
    yo'q bo'lsa — bajarilmagan); (2) oxirgi 3 «Hisob kuni»da haqiqiy foyda > 0 (3 tadan kam — bajarilmagan);
    (3) 90+ kunlik nasiya ≤ `max_bad_bp` × jami nasiya; (4) foizli qarz yo'q yoki qarzdan chiqish rejasi bor;
    (5) kengayish rejasi yozilgan. Qamrov — yuzdan bir oyda, `round_half_up`."""
    if reserve < 0 or receivables < 0 or receivables_90 < 0 or any(x < 0 for x in opex_months):
        raise OracleError("AMOUNT_NEGATIVE")
    if not 1 <= required_months <= 24:
        raise OracleError("INVALID_MONTHS")
    if not 0 <= max_bad_bp <= 10000:
        raise OracleError("INVALID_BP")
    if receivables_90 > receivables:
        raise OracleError("INVALID_RECEIVABLES")
    avg = round_half_up(Fraction(sum(opex_months), len(opex_months))) if opex_months else None
    if avg is None:
        reserve_ok, coverage = False, None
    elif avg == 0:
        reserve_ok, coverage = True, None
    else:
        reserve_ok = reserve >= avg * required_months
        coverage = round_half_up(Fraction(reserve * 100, avg))
    profit_ok = len(true_profits) >= 3 and all(p > 0 for p in true_profits[-3:])
    bad_bp = round_half_up(Fraction(receivables_90 * 10000, receivables)) if receivables > 0 else 0
    receivables_ok = receivables_90 * 10000 <= max_bad_bp * receivables
    debt_ok = (not has_interest_debt) or has_payoff_plan
    ok = {"RESERVE": reserve_ok, "PROFIT": profit_ok, "RECEIVABLES": receivables_ok, "INTEREST_DEBT": debt_ok, "PLAN": has_plan}
    return {"open": all(ok.values()), "conditions": [{"code": c, "ok": ok[c]} for c in KK_GATE_CONDITIONS],
            "reasons": [c for c in KK_GATE_CONDITIONS if not ok[c]],
            "averageOpex": None if avg is None else _s(avg), "requiredReserve": None if avg is None else _s(avg * required_months),
            "coverageCentiMonths": coverage, "badDebtBp": bad_bp}


ZAKAT_BP = 250


def kk_zakat(stock, cash, receivables, debts, gold_price, nisab_grams, hawl_complete):
    """Savdo mollari zakoti hisobi (SPEC 8.3; ulamo tasdig'igacha shartli — OQ-D5, OQ-D7). Baza = tovar + naqd va
    hisobdagi pul + umidli nasiya − yaqin muddatli qarzlar; nisob = oltin narxi (1 g) × gramm. Zakot =
    percent_of(baza, 250 bp), agar baza ≥ nisob va hawl to'lgan bo'lsa; aks holda 0 va sababi."""
    if min(stock, cash, receivables, debts) < 0:
        raise OracleError("AMOUNT_NEGATIVE")
    if gold_price <= 0:
        raise OracleError("AMOUNT_NOT_POSITIVE")
    if not 1 <= nisab_grams <= 1000:
        raise OracleError("INVALID_NISAB")
    base = stock + cash + receivables - debts
    nisab = gold_price * nisab_grams
    if base <= 0:
        reason = "BASE_NOT_POSITIVE"
    elif base < nisab:
        reason = "BELOW_NISAB"
    elif not hawl_complete:
        reason = "HAWL_NOT_COMPLETE"
    else:
        reason = None
    zakat = percent_of(base, ZAKAT_BP) if reason is None else 0
    return {"base": _s(base), "nisab": _s(nisab), "due": reason is None, "zakat": _s(zakat), "reason": reason}


KK_FUNDS = ("TAX", "RESERVE", "WORKING", "EXPANSION", "SADAQA")


def kk_funds(events):
    """«Hisob kuni» konvertlari (SPEC 4.5, 8.2): har bayonnoma soliq zaxirasi va taqsimotni qo'shadi, foydalanish
    ayiradi (soliq zaxirasidan — to'langan soliq). Foydalanish qoldiqdan oshmaydi. Hodisalar sana tartibida."""
    bal = {f: 0 for f in KK_FUNDS}
    added = {f: 0 for f in KK_FUNDS}
    used = {f: 0 for f in KK_FUNDS}
    for e in events:
        if e["kind"] == "CLOSE":
            for f in KK_FUNDS:
                a = int(e.get(f.lower(), "0"))
                if a < 0:
                    raise OracleError("AMOUNT_NEGATIVE")
                bal[f] += a
                added[f] += a
        elif e["kind"] == "USE":
            f, a = e["fund"], int(e["amount"])
            if f not in KK_FUNDS:
                raise OracleError("INVALID_FUND")
            if a <= 0:
                raise OracleError("AMOUNT_NOT_POSITIVE")
            if a > bal[f]:
                raise OracleError("FUND_INSUFFICIENT")
            bal[f] -= a
            used[f] += a
        else:
            raise OracleError("INVALID_KIND")
    return {"funds": [{"fund": f, "added": _s(added[f]), "used": _s(used[f]), "balance": _s(bal[f])} for f in KK_FUNDS]}



# --- Musofir (musofir/SPEC 2–4) ------------------------------------------------------------
MF_KINDS = ("SALARY", "OTHER_INCOME", "EXPENSE", "SENT_HOME", "FUND_IN", "FUND_OUT", "OPENING", "FUND_OPENING",
            "RESERVE_IN", "RESERVE_OUT", "RESERVE_OPENING")


def bp_of(part: int, whole: int) -> int:
    """Ulush basis points'da: round_half_up(part × 10000 / whole), whole > 0."""
    return round_half_up(Fraction(part * 10000, whole))


def mf_month(opening, fund_opening, share_bp, moves, reserve_opening=0):
    """Musofir oy hisoboti (SPEC 2.1, 3, 6.4), ish valyutasida. Qo'ldagi pul = boshlang'ich + daromad − xarajat −
    uyga yuborilgan − komissiya − jamg'armaga sof − qorovul pulga sof. O'z ulushi = jamg'armaga sof + qorovul pulga
    qo'yilgan (qorovul puldan olish ulushni kamaytirmaydi — u shuning uchun bor); maqsad = percent_of(daromad,
    share_bp); yetmagani = max(0, maqsad − o'z ulushi). Jamg'arma va qorovul puldan olish qoldiqdan oshmaydi."""
    if not 0 <= share_bp <= 10000:
        raise OracleError("INVALID_BP")
    if fund_opening < 0 or reserve_opening < 0:
        raise OracleError("AMOUNT_NEGATIVE")
    t = {k: 0 for k in MF_KINDS}
    fees, fund, reserve = 0, fund_opening, reserve_opening
    for m in moves:
        k, a = m["kind"], int(m["amount"])
        if k not in MF_KINDS:
            raise OracleError("INVALID_KIND")
        if a <= 0:
            raise OracleError("AMOUNT_NOT_POSITIVE")
        if k == "SENT_HOME":
            f = int(m.get("fee") or "0")
            if f < 0:
                raise OracleError("FEE_NEGATIVE")
            fees += f
        if k in ("FUND_IN", "FUND_OPENING"):
            fund += a
        elif k == "FUND_OUT":
            if a > fund:
                raise OracleError("FUND_INSUFFICIENT")
            fund -= a
        elif k in ("RESERVE_IN", "RESERVE_OPENING"):
            reserve += a
        elif k == "RESERVE_OUT":
            if a > reserve:
                raise OracleError("RESERVE_INSUFFICIENT")
            reserve -= a
        t[k] += a
    income = t["SALARY"] + t["OTHER_INCOME"]
    fund_net = t["FUND_IN"] - t["FUND_OUT"]
    reserve_net = t["RESERVE_IN"] - t["RESERVE_OUT"]
    saved = fund_net + t["RESERVE_IN"]
    pocket = opening + t["OPENING"] + income - t["EXPENSE"] - t["SENT_HOME"] - fees - fund_net - reserve_net
    target = percent_of(income, share_bp)
    gap = max(0, target - saved)
    warnings = []
    if pocket < 0:
        warnings.append("POCKET_NEGATIVE")
    if target > 0 and saved <= 0:
        warnings.append("NO_SHARE")
    elif 0 < saved < target:
        warnings.append("SHARE_BELOW_TARGET")
    if t["FUND_OUT"] > 0:
        warnings.append("FUND_WITHDRAWN")
    bp = (lambda x: bp_of(x, income)) if income > 0 else (lambda x: None)
    return {"income": _s(income), "expenses": _s(t["EXPENSE"]), "sentHome": _s(t["SENT_HOME"]), "fees": _s(fees),
            "fundIn": _s(t["FUND_IN"]), "fundOut": _s(t["FUND_OUT"]), "fundNet": _s(fund_net), "fundBalance": _s(fund),
            "reserveIn": _s(t["RESERVE_IN"]), "reserveOut": _s(t["RESERVE_OUT"]), "reserveNet": _s(reserve_net),
            "reserveBalance": _s(reserve), "savedNet": _s(saved),
            "pocket": _s(pocket), "shareTarget": _s(target), "shareGap": _s(gap),
            "expensesBp": bp(t["EXPENSE"]), "sentBp": bp(t["SENT_HOME"] + fees), "fundBp": bp(fund_net),
            "reserveBp": bp(t["RESERVE_IN"]), "warnings": warnings}


def mf_reserve(balance, monthly, months, share):
    """Qorovul pul (SPEC 6.4, OQ-MF3), ish valyutasida. Maqsad = round_half_up(Σ oylik xarajat × N / oylar soni)
    (oxirgi to'liq oylar, yozuvi borlari); N — 1–3. Tarix yo'q — maqsad yo'q. O'z ulushi avval qorovul pulga:
    qorovulga = min(ulush, yetmagani), jamg'armaga = qolgani."""
    if not 1 <= months <= 3:
        raise OracleError("INVALID_MONTHS")
    if balance < 0 or (share is not None and share < 0) or any(x < 0 for x in monthly):
        raise OracleError("AMOUNT_NEGATIVE")
    out = {"avgMonthly": None, "target": None, "gap": None, "progressBp": None, "status": "NO_HISTORY",
           "toReserve": None if share is None else _s(0), "toFund": None if share is None else _s(share)}
    if not monthly:
        return out
    target = round_half_up(Fraction(sum(monthly) * months, len(monthly)))
    gap = max(0, target - balance)
    out.update({"avgMonthly": _s(round_half_up(Fraction(sum(monthly), len(monthly)))), "target": _s(target),
                "gap": _s(gap), "progressBp": min(10000, bp_of(balance, target)) if target > 0 else 10000,
                "status": "FULL" if gap == 0 else "EMPTY" if balance == 0 else "PARTIAL"})
    if share is not None:
        to_reserve = min(share, gap)
        out.update({"toReserve": _s(to_reserve), "toFund": _s(share - to_reserve)})
    return out


def mf_startup(target, startup):
    """Ish boshlash summasi (SPEC 6.6) — qaytish jamg'armasi maqsadining bir qismi, uy valyutasida:
    yashash uchun = maqsad − ish boshlash; maqsaddan oshmaydi. Maqsadsiz — faqat summa."""
    if startup <= 0:
        raise OracleError("AMOUNT_NOT_POSITIVE")
    if target is None:
        return {"startup": _s(startup), "living": None, "startupBp": None}
    if target <= 0:
        raise OracleError("INVALID_TARGET")
    if startup > target:
        raise OracleError("STARTUP_EXCEEDS_TARGET")
    return {"startup": _s(startup), "living": _s(target - startup), "startupBp": bp_of(startup, target)}


def months_between(start: date, end: date) -> int:
    """`start` dan `end` gacha to'liq oylar soni (o'tib ketgan bo'lsa 0)."""
    n = (end.year - start.year) * 12 + end.month - start.month - (1 if end.day < start.day else 0)
    return max(0, n)


def mf_return_fund(cur, home, balance, rate, target, monthly, today, return_on):
    """Qaytish jamg'armasi prognozi (SPEC 2.2). `rate` — (num, den): 1 ish valyutasi = num/den uy valyutasi; yo'q bo'lsa
    uy valyutasidagi ko'rsatkichlar yo'q (taxmin qilinmaydi). O'rtacha — berilgan oylar sof jamg'armasining o'rtachasi;
    maqsadgacha oylar — yuqoriga yaxlitlangan; qaytishdagi prognoz = qoldiq + o'rtacha × to'liq oylar (≥ 0)."""
    if balance < 0:
        raise OracleError("AMOUNT_NEGATIVE")
    if target is not None and target <= 0:
        raise OracleError("INVALID_TARGET")
    if rate is not None and (rate[0] <= 0 or rate[1] <= 0):
        raise OracleError("INVALID_RATE")
    avg = round_half_up(Fraction(sum(monthly), len(monthly))) if monthly else None
    left = months_between(today, return_on) if return_on else None
    out = {"avgMonthly": None if avg is None else _s(avg), "monthsUntilReturn": left, "balanceHome": None,
           "avgMonthlyHome": None, "remainingHome": None, "progressBp": None, "monthsToTarget": None,
           "projectedHome": None, "shortfallAtReturn": None}
    if rate is None:
        out["status"] = "NO_RATE"
        return out
    bh = convert(balance, cur, home, rate[0], rate[1])
    ah = None if avg is None else convert(avg, cur, home, rate[0], rate[1])
    projected = None if left is None else max(0, bh + (ah or 0) * left)
    out.update({"balanceHome": _s(bh), "avgMonthlyHome": None if ah is None else _s(ah),
                "projectedHome": None if projected is None else _s(projected)})
    if target is None:
        out["status"] = "NO_TARGET"
        return out
    remaining = max(0, target - bh)
    out["remainingHome"] = _s(remaining)
    out["progressBp"] = min(10000, bp_of(bh, target))
    if projected is not None:
        out["shortfallAtReturn"] = _s(max(0, target - projected))
    if remaining == 0:
        out["monthsToTarget"], out["status"] = 0, "REACHED"
    elif ah is None or ah <= 0:
        out["status"] = "NO_SAVING"
    else:
        out["monthsToTarget"] = ceil_div(remaining, ah)
        out["status"] = "BEHIND" if projected is not None and projected < target else "ON_TRACK"
    return out


MF_PURPOSES = ("HOUSEHOLD", "DEBT", "BUILD", "EDUCATION", "CEREMONY", "SAVINGS", "OTHER")


def mf_shares(shares):
    """«Ikki qirg'oq» ulushlari (SPEC 5): har biri 1–10000 bp, maqsad takrorlanmaydi, yig'indisi 100 %.
    Kanonik maqsadlar tartibida qaytadi (largest remainder shu tartibda)."""
    seen = set()
    for x in shares:
        if x["purpose"] not in MF_PURPOSES:
            raise OracleError("INVALID_PURPOSE")
        if x["purpose"] in seen:
            raise OracleError("DUPLICATE_PURPOSE")
        if not 1 <= x["bp"] <= 10000:
            raise OracleError("INVALID_BP")
        seen.add(x["purpose"])
    if sum(x["bp"] for x in shares) != 10000:
        raise OracleError("SHARES_NOT_FULL")
    return sorted(shares, key=lambda x: MF_PURPOSES.index(x["purpose"]))


def mf_remittance(remittances, spends):
    """Maqsadlar qoldig'i (SPEC 5): har qabul qilingan summa ulushlar bo'yicha bo'linadi (allocate);
    maqsad bo'yicha olingan − sarflangan = qoldiq. Qabul qilinmagani — «yo'lda» (`pending`)."""
    rec = {p: 0 for p in MF_PURPOSES}
    spent = {p: 0 for p in MF_PURPOSES}
    used, pending, allocations = set(), 0, []
    for r in remittances:
        ordered = mf_shares(r["shares"])
        used |= {x["purpose"] for x in ordered}
        if r.get("received") is None:
            pending += 1
            allocations.append(None)
            continue
        a = int(r["received"])
        if a <= 0:
            raise OracleError("AMOUNT_NOT_POSITIVE")
        parts = allocate(a, [x["bp"] for x in ordered])
        allocations.append([{"purpose": x["purpose"], "amount": _s(v)} for x, v in zip(ordered, parts)])
        for x, v in zip(ordered, parts):
            rec[x["purpose"]] += v
    for x in spends:
        if x["purpose"] not in MF_PURPOSES:
            raise OracleError("INVALID_PURPOSE")
        a = int(x["amount"])
        if a <= 0:
            raise OracleError("AMOUNT_NOT_POSITIVE")
        spent[x["purpose"]] += a
        used.add(x["purpose"])
    rows = []
    for p in MF_PURPOSES:
        if p in used:
            bal = rec[p] - spent[p]
            rows.append({"purpose": p, "received": _s(rec[p]), "spent": _s(spent[p]), "balance": _s(bal),
                         "status": "OVERSPENT" if bal < 0 else "OK"})
    tr, ts = sum(rec.values()), sum(spent.values())
    return {"purposes": rows, "received": _s(tr), "spent": _s(ts), "balance": _s(tr - ts), "pending": pending,
            "overspent": any(r["status"] == "OVERSPENT" for r in rows), "allocations": allocations}


def mf_travel_debt(outstanding, available, monthly, target_months, today):
    """Yo'l qarzi rejasi (SPEC 6.1), uy valyutasida: qolgan = qoldiq − «Qarz to'lovi» maqsadidagi pul (≥ 0);
    oylik o'rtacha — oxirgi oylarda shu maqsadga kelgan; necha oyda yopiladi (yuqoriga); maqsadli muddat
    uchun oyiga kerak = round_half_up(qolgan / muddat)."""
    if outstanding < 0:
        raise OracleError("AMOUNT_NEGATIVE")
    if not 1 <= target_months <= 60:
        raise OracleError("INVALID_MONTHS")
    remaining = max(0, outstanding - max(0, available))
    avg = round_half_up(Fraction(sum(monthly), len(monthly))) if monthly else None
    out = {"remaining": _s(remaining), "avgMonthly": None if avg is None else _s(avg), "monthsToClear": None,
           "clearOn": None, "requiredMonthly": _s(round_half_up(Fraction(remaining, target_months)))}
    if remaining == 0:
        out.update({"monthsToClear": 0, "clearOn": today.isoformat(), "status": "CLEARED"})
    elif avg is None or avg <= 0:
        out["status"] = "NO_PAYMENTS"
    else:
        n = ceil_div(remaining, avg)
        out.update({"monthsToClear": n, "clearOn": add_months(today, n).isoformat(),
                    "status": "ON_TRACK" if n <= target_months else "BEHIND"})
    return out


MF_DECISION_KINDS = ("LEND", "PARTNERSHIP", "INVEST", "PURCHASE", "OTHER")
MF_COOLING_DAYS = 90
MF_BIG_BP = 1000
MF_LARGE_BP = 3000
# Musofirga xos savollar (SPEC 6.3): javob → (bayroq, daraja); qolgan javoblar bayroqsiz.
MF_EXTRA = (
    ("approached", {"YES": ("FRESH_RETURN_APPROACH", "YELLOW")}),
    ("upfront", {"YES": ("UPFRONT_BEFORE_DOCUMENTS", "RED"), "UNKNOWN": ("UPFRONT_UNKNOWN", "YELLOW")}),
    ("abroadJobFee", {"YES": ("ABROAD_JOB_FEE", "RED")}),
    ("repaymentDate", {"NO": ("NO_REPAYMENT_DATE", "YELLOW"), "UNKNOWN": ("REPAYMENT_DATE_UNKNOWN", "YELLOW")}),
    ("familyDiscussed", {"NO": ("NOT_DISCUSSED", "YELLOW")}),
)


MF_WALL_MONTHS = 6


def mf_wall(monthly, months=MF_WALL_MONTHS):
    """«Qal'a devori» (SPEC 6.8): oilaning N oylik ro'zg'ori = round_half_up(Σ oylik Uy xarajati × N / oylar soni);
    tarix yo'q — devor yo'q."""
    if not 1 <= months <= 12:
        raise OracleError("INVALID_MONTHS")
    if any(x < 0 for x in monthly):
        raise OracleError("AMOUNT_NEGATIVE")
    if not monthly:
        return {"avgMonthly": None, "wall": None}
    return {"avgMonthly": _s(round_half_up(Fraction(sum(monthly), len(monthly)))),
            "wall": _s(round_half_up(Fraction(sum(monthly) * months, len(monthly))))}


def mf_cooling(today, returned_on, brought, kind, amount, answers, wall=None, promised_bp=None):
    """Sovutish davri va kengaytirilgan taklif detektori (SPEC 6.3). Sheriklik va sarmoyada — U12 ning 6 savoli;
    qarz berishda — qaytarish muddati; davr ichida summa olib kelinganning 10 %idan ko'p — sariq, 30 %idan ko'p —
    qizil. Qaror taqiqlanmaydi: «kutish sanasi» — davr oxiri."""
    if kind not in MF_DECISION_KINDS:
        raise OracleError("INVALID_KIND")
    if amount <= 0:
        raise OracleError("AMOUNT_NOT_POSITIVE")
    if (brought is not None and brought < 0) or (wall is not None and wall < 0):
        raise OracleError("AMOUNT_NEGATIVE")
    if promised_bp is not None and promised_bp <= 0:
        raise OracleError("INVALID_BP")
    questions = []
    if kind in ("PARTNERSHIP", "INVEST"):
        questions += [(q, OFFER_TABLE[q]) for q in OFFER_QUESTIONS]
    for q, table in MF_EXTRA:
        if q == "repaymentDate" and kind != "LEND":
            continue
        questions.append((q, table))
    flags = []
    for q, table in questions:
        a = answers.get(q)
        if a is None:
            raise OracleError("MISSING_ANSWER")
        if a not in ("YES", "NO", "UNKNOWN"):
            raise OracleError("INVALID_ANSWER")
        hit = table.get(a)
        if hit:
            flags.append({"code": hit[0], "level": hit[1]})
    signs = offer_signs(flags)
    # «Qal'a devori» — olib kelingandan oilaning 6 oylik ro'zg'ori ajratiladi; qaror unga tegsa — qizil (davrdan
    # tashqarida ham).
    free = max(0, brought - wall) if brought is not None and wall is not None else None
    if free is not None and amount > free:
        flags.append({"code": "FORTRESS_WALL", "level": "RED"})
    ends = returned_on + timedelta(days=MF_COOLING_DAYS) if returned_on else None
    in_cooling = ends is not None and returned_on <= today < ends
    share = bp_of(amount, brought) if brought else None
    if in_cooling:
        if share is None:
            flags.append({"code": "COOLING_PERIOD", "level": "YELLOW"})
        elif share > MF_LARGE_BP:
            flags.append({"code": "LARGE_SHARE", "level": "RED"})
        elif share > MF_BIG_BP:
            flags.append({"code": "COOLING_BIG_DECISION", "level": "YELLOW"})
    levels = {f["level"] for f in flags}
    verdict = "RED" if "RED" in levels else "YELLOW" if levels else "GREEN"
    # Va'da qilingan oylik foyda — oddiy hisobda bir yilda: yiliga = oyiga × 12, pul = (1 + yiliga) barobar (o'ndan birgacha).
    yearly = promised_bp * 12 if promised_bp is not None else None
    times = round_half_up(Fraction((10000 + yearly) * 10, 10000)) if yearly is not None else None
    return {"inCooling": in_cooling, "endsOn": ends.isoformat() if ends else None,
            "daysLeft": (ends - today).days if in_cooling else 0, "shareBp": share, "flags": flags,
            "verdict": verdict, "waitUntil": ends.isoformat() if in_cooling and verdict != "GREEN" else None,
            "signs": signs, "free": None if free is None else _s(free),
            "promisedYearlyBp": yearly, "promisedTimesTenths": times}

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
    def cer_case(cid, start, capacity, goals, scenarios):
        inp = {"currency": U, "start": start, "monthlyCapacity": capacity, "goals": goals,
               "scenarios": [{"name": n, "guests": g, "lines": [{"kind": k, "amount": a, "source": src} for k, a, src in ls]}
                             for n, g, ls in scenarios]}

        def run():
            tots = [scenario_totals([(k, int(a), src) for k, a, src in ls], g) for _, g, ls in scenarios]
            mx = max(t for t, _ in tots)
            out = []
            for (n, g, ls), (total, by) in zip(scenarios, tots):
                pay = informal_debt_payoff(by["DEBT"], D(start), int(capacity))
                saved = mx - total
                out.append({"name": n, "total": _s(total), "bySource": {k: _s(v) for k, v in by.items()},
                            "payoffMonths": None if pay is None else pay[0],
                            "payoffDate": None if pay is None or pay[1] is None else pay[1].isoformat(),
                            "savedVsMax": _s(saved),
                            "goalsBp": [round_half_up(Fraction(saved * 10000, int(t))) for t in goals]})
            return {"scenarios": out}
        return _case(cid, inp, run)

    toy3 = ("3 kunlik, 200 kishi", 200, [("PER_GUEST", "25000000", "SAVINGS"), ("ONE_OFF", "1500000000", "FAMILY"),
                                         ("ONE_OFF", "800000000", "EXPECTED_GIFTS"), ("ONE_OFF", "2000000000", "DEBT")])
    toy1 = ("1 kunlik, 100 kishi", 100, [("PER_GUEST", "25000000", "SAVINGS"), ("ONE_OFF", "600000000", "FAMILY"),
                                         ("ONE_OFF", "400000000", "EXPECTED_GIFTS")])
    toy2 = ("Oʻrtacha, 150 kishi", 150, [("PER_GUEST", "25000000", "SAVINGS"), ("ONE_OFF", "1000000000", "FAMILY"),
                                         ("ONE_OFF", "500000000", "DEBT")])
    suites["ceremony_scenarios"] = _suite("ceremony_scenarios", "Marosim stsenariylari: qator = summa yoki kishi boshiga × mehmonlar; manba bo'yicha yig'indi; qarzni oyiga X bilan uzish — U9 simulyatori; eng qimmatiga nisbatan tejam va maqsadlar", [
        cer_case("cer-001-karim", "2027-05-20", "240000000", ["1200000000"], [toy3, toy1, toy2]),
        cer_case("cer-002-no-capacity", "2027-05-20", "0", [], [toy3, toy1]),
        cer_case("cer-003-big-capacity", "2027-05-31", "3000000000", [], [toy2]),
        cer_case("cer-neg-001-guests", "2027-05-20", "240000000", [], [("x", -1, [("ONE_OFF", "100", "SAVINGS")])]),
        cer_case("cer-neg-002-amount", "2027-05-20", "240000000", [], [("x", 10, [("PER_GUEST", "0", "SAVINGS")])]),
        cer_case("cer-neg-003-source", "2027-05-20", "240000000", [], [("x", 10, [("ONE_OFF", "100", "BANK")])]),
    ])

    # U11: sheriklik shartlari va buyout jadvali.
    def partner(pid, role, bp, *items):
        return {"id": pid, "role": role, "profitShareBp": bp,
                "capitalItems": [{"kind": k, "description": d, "amount": a} for k, d, a in items]}

    def rules_case(cid, kind, partners, fixed=None, loss=None, months=12):
        loss = loss or LOSS_FOR.get(kind, "OTHER")
        inp = {"kind": kind, "currency": "UZS", "fixedReturn": None if fixed is None else _s(fixed), "lossRule": loss,
               "durationMonths": months,
               "partners": [dict(p, capitalItems=[dict(i, amount=_s(i["amount"])) for i in p["capitalItems"]])
                            for p in partners]}
        return _case(cid, inp, lambda: partnership_rules(kind, partners, fixed, loss, months))

    sobir = partner("P1", "CAPITAL_PROVIDER", 5000, ("EQUIPMENT", "Tikuv mashinasi (2 ta)", 2400000000),
                    ("MONEY", "Mato uchun", 600000000))
    nilufar = partner("P2", "WORKER", 5000)
    anvar = partner("P1", "BOTH", 5000, ("MONEY", "naqd", 3000000000))
    dilshod = partner("P2", "BOTH", 5000, ("MONEY", "naqd", 3000000000))
    silent = partner("P1", "CAPITAL_PROVIDER", 7000, ("MONEY", "naqd", 4000000000))
    working = partner("P2", "BOTH", 3000, ("MONEY", "naqd", 6000000000))
    suites["partnership_rules"] = _suite("partnership_rules", "Sheriklik shartlari: mudoraba/musharaka rollari, kapital, ulushlar 100%, kafolatli daromad taqiqi, zarar qoidasi, muddat; zarar ulushlari (bp)", [
        rules_case("rules-001-mudaraba-ok", "MUDARABA", [sobir, nilufar]),
        rules_case("rules-002-musharaka-ok", "MUSHARAKA", [anvar, dilshod]),
        rules_case("rules-003-guaranteed-return", "MUDARABA", [sobir, nilufar], fixed=50000000),
        rules_case("rules-004-shares-not-100", "MUDARABA", [dict(sobir, profitShareBp=6000), nilufar]),
        rules_case("rules-005-one-partner", "MUSHARAKA", [dict(anvar, profitShareBp=10000)]),
        rules_case("rules-006-mudaraba-no-worker", "MUDARABA", [sobir, dict(sobir, id="P2", capitalItems=[{"kind": "MONEY", "description": "naqd", "amount": 100}])]),
        rules_case("rules-007-mudaraba-both-and-worker-capital", "MUDARABA", [dict(sobir, role="BOTH"), dict(nilufar, capitalItems=[{"kind": "MONEY", "description": "naqd", "amount": 100}])]),
        rules_case("rules-008-provider-without-capital", "MUDARABA", [partner("P1", "CAPITAL_PROVIDER", 5000), nilufar]),
        rules_case("rules-009-musharaka-one-capital", "MUSHARAKA", [anvar, partner("P2", "WORKER", 5000)]),
        rules_case("rules-010-loss-mismatch", "MUSHARAKA", [anvar, dilshod], loss="CAPITAL_PROVIDER_BEARS"),
        rules_case("rules-011-no-term", "MUSHARAKA", [anvar, dilshod], months=0),
        rules_case("rules-012-item-not-positive", "MUSHARAKA", [anvar, partner("P2", "BOTH", 5000, ("MONEY", "naqd", 0))]),
        rules_case("rules-013-silent-partner-warning", "MUSHARAKA", [silent, working]),
        rules_case("rules-014-uneven-loss-bp", "MUSHARAKA", [partner("P1", "BOTH", 5000, ("MONEY", "a", 100000000)),
                                                            partner("P2", "BOTH", 2500, ("MONEY", "b", 100000000)),
                                                            partner("P3", "BOTH", 2500, ("MONEY", "c", 100000000))]),
        rules_case("rules-neg-001-kind", "IJARA", [anvar, dilshod]),
    ])

    def buy_case(cid, stake, total, buyer, units, per, start, months, profit, share):
        inp = {"currency": "UZS", "stake": _s(stake), "totalCapital": _s(total), "buyerCapital": _s(buyer), "units": units,
               "unitsPerPeriod": per, "start": start, "periodMonths": months,
               "expectedProfit": None if profit is None else _s(profit), "buyerShareBp": share}
        return _case(cid, inp, lambda: buyout_schedule(stake, total, buyer, units, per, date.fromisoformat(start), months,
                                                       profit, share))

    suites["buyout_schedule"] = _suite("buyout_schedule", "Kamayib boruvchi musharaka: ulush teng birliklarga bo'linadi (largest remainder), har davrda N birlik; sotuvchi va xaridor ulushi (bp, half-up); to'lov xaridor foyda ulushidan oshsa — belgi", [
        buy_case("buy-001-nilufar", 3000000000, 3000000000, 0, 10, 1, "2026-11-30", 1, 800000000, 5000),
        buy_case("buy-002-uneven-quarterly", 100000001, 300000001, 200000000, 3, 2, "2027-01-31", 3, 50000000, 6000),
        buy_case("buy-003-no-profit-estimate", 1200000000, 2000000000, 800000000, 4, 4, "2027-03-15", 1, None, 5000),
        buy_case("buy-neg-001-stake", 0, 100, 0, 1, 1, "2027-01-01", 1, None, 5000),
        buy_case("buy-neg-002-exceeds", 200, 300, 200, 2, 1, "2027-01-01", 1, None, 5000),
        buy_case("buy-neg-003-per-period", 100, 100, 0, 2, 3, "2027-01-01", 1, None, 5000),
        buy_case("buy-neg-004-period", 100, 100, 0, 2, 1, "2027-01-01", 13, None, 5000),
        buy_case("buy-neg-005-units", 100, 100, 0, 0, 1, "2027-01-01", 1, None, 5000),
    ])
    # U12 — davr taqsimoti
    mud3 = [{"id": "P1", "role": "CAPITAL_PROVIDER", "profitShareBp": 5000, "capital": 3000000000},
            {"id": "P2", "role": "WORKER", "profitShareBp": 5000, "capital": 0}]
    mud46 = [dict(mud3[0], profitShareBp=4000), dict(mud3[1], profitShareBp=6000)]
    mush2 = [{"id": "P1", "role": "BOTH", "profitShareBp": 6000, "capital": 600000000},
             {"id": "P2", "role": "BOTH", "profitShareBp": 4000, "capital": 200000000}]
    E = lambda k, a: {"kind": k, "amount": a}  # noqa: E731
    shop = [E("INCOME", 1200000000), E("INCOME", 300000000), E("EXPENSE", 500000000), E("EXPENSE", 200000000)]
    inst = lambda no, cap, price: {"no": no, "units": 1, "capital": cap, "price": price}  # noqa: E731
    bo = lambda due: {"sellerId": "P1", "buyerId": "P2", "due": due}  # noqa: E731
    neg = {"partnerId": "P2", "note": "mato boshqa ishga ishlatildi"}

    def withcap(ps, *cs):
        return [dict(p, capital=c) for p, c in zip(ps, cs)]
    vp_cases = [
        ("vp-001-mudaraba-profit", "MUDARABA", mud3, shop, "CAPITAL_FIRST", [0, 0], None, None),
        ("vp-002-mudaraba-loss", "MUDARABA", mud3, [E("INCOME", 300000000), E("EXPENSE", 400000000), E("FORCE_MAJEURE", 100000000)],
         "CAPITAL_FIRST", [0, 0], None, None),
        ("vp-003-loss-recovered-first", "MUDARABA", withcap(mud3, 2800000000, 0), [E("INCOME", 500000000), E("EXPENSE", 200000000)],
         "CAPITAL_FIRST", [200000000, 0], None, None),
        ("vp-004-per-period", "MUDARABA", withcap(mud3, 2800000000, 0), [E("INCOME", 500000000), E("EXPENSE", 200000000)],
         "PER_PERIOD", [0, 0], None, None),
        ("vp-005-musharaka-loss", "MUSHARAKA", mush2, [E("EXPENSE", 300000000)], "CAPITAL_FIRST", [0, 0], None, None),
        ("vp-006-buyout-from-profit", "MUDARABA", mud46, shop, "CAPITAL_FIRST", [0, 0], None,
         bo([inst(1, 150000000, 150000000), inst(2, 150000000, 150000000)])),
        ("vp-007-buyout-shortfall", "MUDARABA", mud3, [E("INCOME", 300000000)], "CAPITAL_FIRST", [0, 0], None,
         bo([inst(1, 150000000, 100000000), inst(2, 150000000, 100000000)])),
        ("vp-008-buyout-loss", "MUDARABA", withcap(mud3, 2850000000, 150000000), [E("EXPENSE", 100000000)], "CAPITAL_FIRST", [0, 0], None,
         bo([inst(2, 150000000, 150000000)])),
        ("vp-009-negligence", "MUDARABA", mud3, [E("INCOME", 100000000), E("EXPENSE", 300000000)], "CAPITAL_FIRST", [0, 0], neg, None),
        ("vp-010-correction", "MUDARABA", mud3, [E("INCOME", 500000000), E("EXPENSE", 100000000), E("CORRECTION", -50000000)],
         "CAPITAL_FIRST", [0, 0], None, None),
        ("vp-011-musharaka-recovery", "MUSHARAKA", withcap(mush2, 375000000, 125000000), [E("INCOME", 400000000)],
         "CAPITAL_FIRST", [225000000, 75000000], None, None),
        ("vp-012-partial-recovery", "MUDARABA", withcap(mud3, 2800000000, 0), [E("INCOME", 150000000)],
         "CAPITAL_FIRST", [200000000, 0], None, None),
        ("vp-neg-001-shares", "MUDARABA", [dict(mud3[0], profitShareBp=6000), mud3[1]], shop, "CAPITAL_FIRST", [0, 0], None, None),
        ("vp-neg-002-amount", "MUDARABA", mud3, [E("EXPENSE", 0)], "CAPITAL_FIRST", [0, 0], None, None),
        ("vp-neg-003-negligence-profit", "MUDARABA", mud3, shop, "CAPITAL_FIRST", [0, 0], neg, None),
        ("vp-neg-004-buyout-same", "MUDARABA", mud3, shop, "CAPITAL_FIRST", [0, 0], None,
         {"sellerId": "P1", "buyerId": "P1", "due": []}),
        ("vp-neg-005-carried-per-period", "MUDARABA", mud3, shop, "PER_PERIOD", [100, 0], None, None),
        ("vp-neg-006-negligence-musharaka", "MUSHARAKA", mush2, [E("EXPENSE", 100)], "CAPITAL_FIRST", [0, 0], neg, None),
    ]

    def vp_case(cid, kind, ps, es, pol, car, ng, b):
        inp = {"kind": kind, "currency": U, "partners": pj(ps), "entries": [dict(e, amount=_s(e["amount"])) for e in es],
               "lossPolicy": pol, "carriedLoss": [_s(c) for c in car], "negligence": ng,
               "buyout": None if b is None else dict(b, due=[dict(d, capital=_s(d["capital"]), price=_s(d["price"])) for d in b["due"]])}
        return _case(cid, inp, lambda: venture_period(kind, ps, es, pol, car, ng, b))
    suites["venture_period"] = _suite("venture_period", "Davrni yopish: natija, o'tgan zararni avval tiklash (OQ-D1), foyda/zarar taqsimoti, beparvolik, buyout to'lovini xaridor ulushidan ayirish, kapital qoldiqlari", [
        vp_case(*c) for c in vp_cases])

    def idea_case(cid, capex, sc, share):
        inp = {"currency": U, "capex": [_s(a) for a in capex],
               "scenarios": [{"name": n, "income": _s(i), "expense": _s(e)} for n, i, e in sc], "workerShareBp": share}
        return _case(cid, inp, lambda: venture_idea(capex, [{"name": n, "income": i, "expense": e} for n, i, e in sc], share))
    tikuv = [500000000, 150000000, 150000000]
    sc3 = [("PESSIMISTIC", 400000000, 300000000), ("BASE", 600000000, 350000000), ("OPTIMISTIC", 800000000, 400000000)]
    suites["venture_idea"] = _suite("venture_idea", "«Hunardan ishga»: CAPEX, 3 stsenariy, payback = ⌈CAPEX / sof foyda⌉, sheriklikda ishchi va kapital egasi ulushi", [
        idea_case("idea-001-tikuv-8mln", tikuv, sc3, None),
        idea_case("idea-002-partnership-50", tikuv, sc3, 5000),
        idea_case("idea-003-loss-scenario", [300000000], [("PESSIMISTIC", 100000000, 150000000), ("BASE", 200000000, 150000000),
                                                          ("OPTIMISTIC", 300000000, 150000000)], 6000),
        idea_case("idea-004-not-ordered", [100000000], [("PESSIMISTIC", 300000000, 100000000), ("BASE", 200000000, 100000000),
                                                         ("OPTIMISTIC", 400000000, 100000000)], None),
        idea_case("idea-005-no-capex", [], sc3, None),
        idea_case("idea-neg-001-capex", [0], sc3, None),
        idea_case("idea-neg-002-scenarios", tikuv, sc3[:2], None),
        idea_case("idea-neg-003-bp", tikuv, sc3, 10001),
    ])
    A = lambda g, l, r, rc, u, w, lc="YES", ins="YES", ex="YES": {"guaranteed": g, "lossShared": l, "realActivity": r, "recruitment": rc,  # noqa: E731
                                                              "urgency": u, "written": w, "licensed": lc, "inspection": ins, "exitEasy": ex}
    oc = [("offer-001-green", A("NO", "YES", "YES", "NO", "NO", "YES")),
          ("offer-002-guaranteed", A("YES", "YES", "YES", "NO", "NO", "YES")),
          ("offer-003-pyramid", A("YES", "NO", "NO", "YES", "YES", "NO")),
          ("offer-004-urgency", A("NO", "YES", "YES", "NO", "YES", "YES")),
          ("offer-005-unknowns", A("UNKNOWN", "UNKNOWN", "YES", "NO", "NO", "UNKNOWN")),
          ("offer-006-no-contract", A("NO", "YES", "YES", "NO", "NO", "NO")),
          ("offer-007-crypto-signals", A("YES", "NO", "UNKNOWN", "NO", "YES", "NO")),
          # M5: «Oltin foyda» — kafolat va shoshirish (ikki belgi), tekshirtirmaydi, chiqish qiyin.
          ("offer-008-guaranteed-scam", A("YES", "UNKNOWN", "UNKNOWN", "UNKNOWN", "YES", "YES", "UNKNOWN", "NO", "NO")),
          # Faqat shoshirish (bitta belgi) — sariq; bitta 4-belgi ichidagi uch bayroq — bitta belgi.
          ("offer-009-one-sign", A("NO", "YES", "YES", "NO", "YES", "YES")),
          ("offer-010-sign-four-once", A("NO", "YES", "NO", "NO", "NO", "YES", "NO", "NO")),
          # Ruxsat yo'q va shoshirish — ikki belgi, qizil.
          ("offer-011-two-yellow-signs", A("NO", "YES", "YES", "NO", "YES", "YES", "NO")),
          ("offer-neg-001-missing", {"guaranteed": "NO"}),
          ("offer-neg-002-invalid", A("MAYBE", "YES", "YES", "NO", "NO", "YES"))]
    suites["offer_check"] = _suite("offer_check", "«Kafolatlangan foyda» detektori: 9 savol → bayroqlar; «besh xavf belgisi»dan ikkitasi — TWO_SIGNS; qizil bo'lsa QIZIL, sariq bo'lsa SARIQ, aks holda YASHIL", [
        _case(cid, {"answers": a}, lambda a=a: offer_check(a)) for cid, a in oc])
    # U13 — ko'rik bayonnomasi yaxlitligi
    def tamper(i, minor):
        t = json.loads(json.dumps(CHAIN_ENTRIES))
        t[i]["amount"]["minor"] = minor
        return t
    h = chain(CHAIN_ENTRIES)
    rp = [("rp-001-intact", CHAIN_ENTRIES, h, 2, h[1]),
          ("rp-002-tampered-rehashed", tamper(0, "300000001"), chain(tamper(0, "300000001")), 2, h[1]),
          ("rp-003-tampered-not-rehashed", tamper(1, "1"), h, 2, h[1]),
          ("rp-004-truncated", CHAIN_ENTRIES[:1], h[:1], 2, h[1]),
          ("rp-005-genesis", CHAIN_ENTRIES, h, 0, GENESIS),
          ("rp-006-after-protocol", tamper(2, "1"), chain(tamper(2, "1")), 2, h[1])]
    suites["review_protocol"] = _suite("review_protocol", "Bayonnomadagi zanjir boshi: INTACT / CHAIN_BROKEN / HEAD_MISMATCH / TRUNCATED, bayonnomadan keyingi yozuvlar soni", [
        _case(cid, {"entries": es, "storedHashes": hs, "protocolSeq": n, "protocolHead": hd},
              lambda es=es, hs=hs, n=n, hd=hd: review_protocol(es, hs, n, hd))
        for cid, es, hs, n, hd in rp])

    # K1: Kasb-kor — egasi maoshi va hamyonlar. Summalar tiyinda (UZS exponent 2).
    def mv(kind, wallet, amount, to=None):
        m = {"kind": kind, "wallet": wallet, "amount": _s(amount * 100)}
        if to:
            m["toWallet"] = to
        return m
    kk = [
        # Nilufar (SPEC 2.2): maosh 5 mln; 1,2 mln «egasi oldi», 3,8 mln o'tkazildi — qoldiq 0.
        ("kk-001", 0, 3000000, 5000000, [mv("SALE", "CARD", 10000000), mv("SALE", "CASH", 8000000), mv("EXPENSE", "CARD", 8500000),
                                   mv("OWNER_DRAW", "CASH", 1200000), mv("OWNER_SALARY", "CARD", 3800000)]),
        # Ortiqcha olingan: maosh 4 mln, «egasi oldi» 3 + 1,5 mln.
        ("kk-002", 2000000, 0, 4000000, [mv("SALE", "CASH", 6000000), mv("OWNER_DRAW", "CASH", 3000000), mv("OWNER_DRAW", "CASH", 1500000)]),
        # Kapital kiritish tushum emas va maoshga ta'sir qilmaydi; maosh qisman o'tkazilgan.
        ("kk-003", 0, 0, 3000000, [mv("OWNER_CONTRIBUTION", "CARD", 5000000), mv("EXPENSE", "CARD", 4200000), mv("OWNER_SALARY", "CARD", 800000)]),
        # Bahodir aka (SPEC 5.1 bilan bir xil raqamlar): kassadan kartaga topshirildi.
        ("kk-004", 500000, 2000000, 0, [mv("SALE", "CASH", 3200000), mv("EXPENSE", "CASH", 400000), mv("OWNER_DRAW", "CASH", 300000),
                                        mv("TRANSFER", "CASH", 1500000, "CARD")]),
        # Maosh belgilanmagan; kassa minusga tushdi (yozilmagan tushum yoki xato) — belgi.
        ("kk-005", 100000, 0, 0, [mv("EXPENSE", "CASH", 250000), mv("SALE", "CARD", 50000)]),
        # Chiqim tushumdan ko'p — pul oqimi manfiy.
        ("kk-006", 0, 10000000, 2000000, [mv("SALE", "CARD", 3000000), mv("EXPENSE", "CARD", 4500000)]),
        # Bo'sh oy.
        ("kk-007", 750000, 0, 2500000, []),
        # K2: uskuna kartadan olindi, eskisi naqdga sotildi — hamyonlar o'zgaradi, pul oqimi o'zgarmaydi.
        ("kk-008", 1000000, 15000000, 0, [mv("SALE", "CARD", 4000000), mv("EXPENSE", "CARD", 1000000),
                                          mv("EQUIPMENT_PURCHASE", "CARD", 12000000), mv("EQUIPMENT_SALE", "CASH", 800000)]),
        # K4: kassa yopishdagi farq — naqd hamyonni tuzatadi, pul oqimiga kirmaydi.
        ("kk-009", 500000, 0, 0, [mv("SALE", "CASH", 3200000), mv("CASH_SHORT", "CASH", 50000), mv("CASH_OVER", "CASH", 20000)]),
        # K5: tovar xaridi zaxiraga kiradi — hamyondan chiqadi, pul oqimiga kirmaydi.
        ("kk-010", 2000000, 0, 0, [mv("STOCK_PURCHASE", "CASH", 1250000), mv("SALE", "CASH", 1120000)]),
        ("kk-neg-001", 0, 0, 1000000, [mv("SALE", "CASH", 0)]),
        ("kk-neg-002", 0, 0, 1000000, [{"kind": "TRANSFER", "wallet": "CASH", "toWallet": "CASH", "amount": "100"}]),
        ("kk-neg-003", 0, 0, 1000000, [{"kind": "SALE", "wallet": "SAFE", "amount": "100"}]),
        ("kk-neg-004", 0, 0, -1, []),
    ]
    suites["kk_owner_pay"] = _suite("kk_owner_pay", "Kasb-kor: tushum, chiqim, pul oqimi, egasiga to'langan, maosh qoldig'i, naqd va karta qoldiqlari (kasbkor/SPEC 2)", [
        _case(cid, {"currency": U, "openingCash": _s(oc * 100), "openingCard": _s(ob * 100), "ownerSalary": _s(sal * 100 if sal > 0 else sal), "moves": ms},
              lambda oc=oc, ob=ob, sal=sal, ms=ms: kk_month_report(oc * 100, ob * 100, sal * 100 if sal > 0 else sal, ms))
        for cid, oc, ob, sal, ms in kk])

    # K2: eskirish. Summalar so'mda yoziladi, vektorda tiyin.
    dep = [
        # SPEC 3.1: 2 ta tikuv mashinasi 12 mln, 60 oy → oyiga 200 000.
        ("dep-001", 12000000, 0, 60, [0, 59, 60], None),
        # SPEC 3.1 yaxlitlash misoli: 7 mln / 36 → 16 oy 194 444,45, 20 oy 194 444,44.
        ("dep-002", 7000000, 0, 36, [0, 15, 16, 35, 36], None),
        # Qoldiq qiymati bilan: 10 mln, 1 mln qoladi, 24 oy.
        ("dep-003", 10000000, 1000000, 24, [0, 23, 30], None),
        # Muddatdan oldin sotildi (10-oy, 4 mln): balans 10 mln → 6 mln bir martalik.
        ("dep-004", 12000000, 0, 60, [9, 10, 11], {"month": 10, "proceeds": 4000000}),
        # Balansdan qimmatga sotildi — foyda (manfiy chiqib ketish).
        ("dep-005", 3000000, 0, 12, [10, 11], {"month": 11, "proceeds": 500000}),
        # Muddat tugagandan keyin yaroqsiz bo'ldi: qoldiq qiymati hisobdan chiqadi.
        ("dep-006", 2400000, 400000, 10, [9, 14], {"month": 14, "proceeds": 0}),
        # Narx = qoldiq qiymati — eskirish yo'q.
        ("dep-007", 500000, 500000, 6, [0], None),
        ("dep-neg-001", 0, 0, 12, [0], None),
        ("dep-neg-002", 1000000, 1000001, 12, [0], None),
        ("dep-neg-003", 1000000, 0, 0, [0], None),
        ("dep-neg-004", 1000000, 0, 601, [0], None),
        ("dep-neg-005", 1000000, 0, 12, [-1], None),
        ("dep-neg-006", 1000000, 0, 12, [0], {"month": 3, "proceeds": -1}),
    ]
    def dep_input(c, sv, n, q, dsp):
        inp = {"currency": U, "cost": _s(c * 100), "salvage": _s(sv * 100), "usefulMonths": n, "queryMonths": q}
        if dsp is not None:
            inp["disposal"] = {"month": dsp["month"], "proceeds": _s(dsp["proceeds"] * 100)}
        return inp
    suites["kk_depreciation"] = _suite("kk_depreciation", "Kasb-kor: uskuna eskirishi — teng oylik ulush (largest remainder), qoldiq qiymati, muddatdan oldin chiqib ketish (kasbkor/SPEC 3.1, 3.3)", [
        _case(cid, dep_input(c, sv, n, q, dsp),
              lambda c=c, sv=sv, n=n, q=q, dsp=dsp: kk_depreciation(c * 100, sv * 100, n, q,
                                                                     None if dsp is None else {"month": dsp["month"], "proceeds": dsp["proceeds"] * 100}))
        for cid, c, sv, n, q, dsp in dep])

    # K2: haqiqiy foyda. `hours100` — soat × 100.
    def fl(hours100, rate, paid=False):
        return {"hours100": hours100, "hourlyRate": _s(rate * 100), "paid": paid}
    tp = [
        # SPEC 3.1 Nilufar: ko'rinadigan 9 500 000, haqiqiy 3 100 000.
        ("tp-001", 18000000, 6000000, 2500000, 5000000, [fl(8000, 15000)], 200000, 0),
        # Qizining yordami to'langan (500 000 operatsion xarajatda) — ikki marta hisoblanmaydi.
        ("tp-002", 18000000, 6000000, 3000000, 5000000, [fl(4000, 12500, True), fl(2000, 15000)], 200000, 0),
        # O'z mehnati va oilaviy mehnat hisobga olinsa — zarar.
        ("tp-003", 6000000, 2000000, 1500000, 4000000, [fl(6000, 10000)], 150000, 0),
        # Tovar xaridi xarajat emas: 5 mln tovar olindi, 2 mln lik qismi sotildi — tannarx faqat 2 mln.
        ("tp-004", 3500000, 2000000, 300000, 0, [], 0, 0),
        # Kasr soat (2,5 × 13 333,33) va uskunani balansdan qimmatga sotish (foyda).
        ("tp-005", 1000000, 0, 0, 0, [fl(250, Fraction(1333333, 100))], 0, -250000),
        ("tp-neg-001", -1, 0, 0, 0, [], 0, 0),
        ("tp-neg-002", 1000000, 0, 0, 0, [fl(-100, 10000)], 0, 0),
    ]
    tp = [row + (0,) for row in tp] + [
        # K5: hisobdan chiqarilgan tovar (buzilgan) — yo'qotish; inventarizatsiyada topilgan — manfiy yo'qotish.
        ("tp-006", 5000000, 3000000, 500000, 0, [], 0, 0, 120000),
        ("tp-007", 5000000, 3000000, 500000, 0, [], 0, 0, -30000),
    ]
    suites["kk_true_profit"] = _suite("kk_true_profit", "Kasb-kor: ko'rinadigan va haqiqiy foyda — o'z mehnati, to'lanmagan oilaviy mehnat, eskirish (kasbkor/SPEC 3.1)", [
        _case(cid, {"currency": U, "revenue": _s(r * 100), "cogs": _s(cg * 100), "operatingExpenses": _s(op * 100), "ownerLabor": _s(ol * 100),
                    "familyLabor": fs, "depreciation": _s(dp * 100), "disposal": _s(ds * 100), "stockLosses": _s(sl * 100)},
              lambda r=r, cg=cg, op=op, ol=ol, fs=fs, dp=dp, ds=ds, sl=sl: kk_true_profit(r * 100, cg * 100, op * 100, ol * 100, fs, dp * 100, ds * 100, sl * 100))
        for cid, r, cg, op, ol, fs, dp, ds, sl in tp])

    # K2: buyurtma kalkulyatori.
    oq = [
        # Jasur (SPEC 3.2): material 450 000, 6 soat × 40 000, yo'l 50 000, eskirish 20 000, zaxira 5 %;
        # narx 700 000 — tannarxdan past; avans 300 000 materialga yetmaydi.
        ("oq-001", 450000, 600, 40000, 50000, 20000, 500, 700000, 300000),
        # Narx tannarxdan yuqori, avans materialni yopadi.
        ("oq-002", 1200000, 1000, 50000, 100000, 30000, 300, 2500000, 1500000),
        # Narxsiz va avanssiz, 3,5 soat — faqat tannarx.
        ("oq-003", 80000, 350, 35000, 0, 0, 0, None, None),
        # Zaxira foizi yaxlitlanadi (tiyinlar bilan).
        ("oq-004", Fraction(12345, 100), 100, Fraction(6789, 100), 0, 0, 333, None, None),
        # Mehnat soati yo'q — soatbay hisoblanmaydi.
        ("oq-005", 300000, 0, 0, 0, 0, 1000, 330000, None),
        ("oq-neg-001", -1, 0, 0, 0, 0, 0, None, None),
        ("oq-neg-002", 100, 100, 100, 0, 0, 10001, None, None),
        ("oq-neg-003", 100, -50, 100, 0, 0, 0, None, None),
    ]
    def t(v):
        return None if v is None else int(Fraction(v) * 100)
    suites["kk_order_quote"] = _suite("kk_order_quote", "Kasb-kor: buyurtma kalkulyatori — tannarx, zaxira, narx tannarxdan pastligi, o'z mehnatiga qoladigan pul, avans va material (kasbkor/SPEC 3.2)", [
        _case(cid, {"currency": U, "material": _s(t(m)), "hours100": h, "hourlyRate": _s(t(r)), "travel": _s(t(tr)), "depreciation": _s(t(d)),
                    "reserveBp": bp, "price": None if pr is None else _s(t(pr)), "advance": None if av is None else _s(t(av))},
              lambda m=m, h=h, r=r, tr=tr, d=d, bp=bp, pr=pr, av=av: kk_order_quote(t(m), h, t(r), t(tr), t(d), bp, t(pr), t(av)))
        for cid, m, h, r, tr, d, bp, pr, av in oq])

    # K3: «Hisob kuni». Summalar so'mda (`Fraction` — tiyin bilan), vektorda tiyin.
    def rule(r, w, e, sd=0):
        return {"reserveBp": r, "workingBp": w, "expansionBp": e, "sadaqaBp": sd}
    def tax(base, bp=0, amount=0):
        return {"base": base, "bp": bp, "amount": _s(t(amount))}
    mc = [
        # SPEC 4.5 Nilufar: 18 mln − soliq 4 % (720 000) − chiqim 8,5 mln − to'langan yordam 1,2 mln − maosh 5 mln
        # = 2 580 000 → 30/50/20: 774 000 / 1 290 000 / 516 000.
        ("mc-001", 18000000, 9700000, 200000, 5000000, 5000000, tax("REVENUE", 400), rule(3000, 5000, 2000), False),
        # Qolgan pul manfiy — taqsimot yo'q, izoh so'raladi.
        ("mc-002", 6000000, 4500000, 150000, 4000000, 2000000, tax("NONE"), rule(3000, 5000, 2000), False),
        # Soliq foydadan (10 %), sadaqa ulushi bilan.
        ("mc-003", 10000000, 6000000, 0, 2000000, 2000000, tax("PROFIT", 1000), rule(2500, 5000, 1500, 1000), False),
        # Largest remainder: qolgan 100,01 so'm uch qismga.
        ("mc-004", Fraction(10001, 100), 0, 0, 0, 0, tax("NONE"), rule(3333, 3333, 3334), False),
        # «Egasi oldi» maoshdan 1,5 mln ko'p — maosh o'rniga olingani; ortig'i keyingi oyga ushlanadi.
        ("mc-005", 9000000, 3000000, 0, 3000000, 4500000, tax("NONE"), rule(3000, 5000, 2000), True),
        # Qat'iy soliq summasi; zaxira eskirishdan kam — belgi.
        ("mc-006", 5000000, 3000000, 900000, 700000, 0, tax("FIXED", amount=300000), rule(3000, 5000, 2000), False),
        # Maosh belgilanmagan: «egasi oldi» — egasi maoshi o'rnida.
        ("mc-007", 4000000, 1000000, 0, 0, 1000000, tax("REVENUE", 300), rule(5000, 5000, 0), False),
        # Chiqim tushumdan ko'p: foydadan soliq 0, qolgan manfiy.
        ("mc-008", 3000000, 3500000, 0, 0, 0, tax("PROFIT", 1500), rule(3000, 5000, 2000), False),
        # Qolgan aniq 0 — taqsimot nollar, izoh shart emas.
        ("mc-009", 4000000, 1000000, 0, 3000000, 0, tax("NONE"), rule(3000, 5000, 2000), False),
        ("mc-neg-001", 1000000, 0, 0, 0, 0, tax("NONE"), rule(3000, 5000, 1000), False),
        ("mc-neg-002", -1, 0, 0, 0, 0, tax("NONE"), rule(3000, 5000, 2000), False),
        ("mc-neg-003", 1000000, 0, 0, 0, 0, tax("REVENUE", 10001), rule(3000, 5000, 2000), False),
        ("mc-neg-004", 1000000, 0, 0, 0, 0, tax("FIXED", amount=-1), rule(3000, 5000, 2000), False),
        ("mc-neg-005", 1000000, 0, 0, 0, 0, tax("MONTHLY"), rule(3000, 5000, 2000), False),
    ]
    # K4: kunlik kassa yopish. Summalar so'mda.
    def cm(kind, wallet, amount, to=None):
        m = {"kind": kind, "wallet": wallet, "amount": _s(amount * 100)}
        if to:
            m["toWallet"] = to
        return m
    bahodir = [cm("SALE", "CASH", 3200000), cm("EXPENSE", "CASH", 400000), cm("OWNER_DRAW", "CASH", 300000), cm("TRANSFER", "CASH", 1500000, "CARD")]
    cc = [
        # SPEC 5.1 Bahodir aka: kutilgan 1 500 000, sanalgan 1 450 000 → −50 000.
        ("cc-001", 500000, bahodir, 1450000, "UNKNOWN", []),
        # «Egasi oldi» yozilmagan: farq aynan shu summa, sabab — egasi oldi.
        ("cc-002", 500000, bahodir[:2] + bahodir[3:], 1500000, "OWNER_TOOK", []),
        # Ortiqcha (+) farq.
        ("cc-003", 500000, bahodir, 1520000, "CHANGE_ERROR", []),
        # Karta tushumi va kartadagi chiqim kassaga ta'sir qilmaydi; aniq — sabab kerak emas.
        ("cc-004", 200000, [cm("SALE", "CARD", 900000), cm("EXPENSE", "CARD", 100000), cm("SALE", "CASH", 300000)], 500000, None, []),
        # Kartadan naqdga olindi, kapital kiritildi, maosh naqdda o'tkazildi.
        ("cc-005", 0, [cm("TRANSFER", "CARD", 400000, "CASH"), cm("OWNER_CONTRIBUTION", "CASH", 1000000), cm("OWNER_SALARY", "CASH", 600000)], 800000, None, []),
        # 4 hafta ichida uchinchi kamomad — «xato qidirish» taklifi (ayblov emas).
        ("cc-006", 100000, [cm("SALE", "CASH", 500000)], 580000, "UNKNOWN", ["-1000000", "500000", "-300000"]),
        # Ikkinchi kamomad — hali taklif yo'q.
        ("cc-007", 100000, [cm("SALE", "CASH", 500000)], 580000, "UNKNOWN", ["-1000000", "500000"]),
        ("cc-neg-001", 100000, [], 90000, None, []),
        ("cc-neg-002", 100000, [], 90000, "LOST", []),
        ("cc-neg-003", 100000, [], -1, "UNKNOWN", []),
        ("cc-neg-004", 0, [cm("SALE", "CASH", 0)], 0, None, []),
    ]
    suites["kk_cash_close"] = _suite("kk_cash_close", "Kasb-kor kunlik kassa yopish: kutilgan qoldiq, farq, sabab, takrorlanuvchi kamomad (kasbkor/SPEC 5.1)", [
        _case(cid, {"currency": U, "opening": _s(o * 100), "moves": ms, "counted": _s(c * 100), "reason": r, "recentDifferences": rec},
              lambda o=o, ms=ms, c=c, r=r, rec=rec: kk_cash_close(o * 100, ms, c * 100, r, rec))
        for cid, o, ms, c, r, rec in cc])

    # K4: nasiya. Summalar so'mda.
    def pay(d, a):
        return {"kind": "PAYMENT", "date": d, "amount": _s(a * 100)}
    def forgive(d, a):
        return {"kind": "FORGIVE", "date": d, "amount": _s(a * 100)}
    def extend(d, m):
        return {"kind": "EXTEND", "date": d, "months": m}
    cs = [
        # SPEC 5.2 Malika: naqd 600 000, nasiya 660 000 = 3 × 220 000; ikkinchi to'lov 20 kun kechikdi.
        ("cs-001", 660000, 600000, 3, "2026-11-10", [pay("2026-11-10", 220000)], "2026-12-30"),
        # Xuddi shu nasiya, yarim yildan keyin: qoldiq o'sha-o'sha (ustama yo'q), guruh 90+.
        ("cs-002", 660000, 600000, 3, "2026-11-10", [pay("2026-11-10", 220000)], "2027-06-20"),
        # Qoldiq tiyinlar birinchi to'lovlarga; qisman to'lov.
        ("cs-003", 1000000, None, 3, "2026-12-31", [pay("2026-12-31", 200000)], "2027-01-15"),
        # Muddat uzaytirildi (2 oy): yopilmagan to'lovlar suriladi, summa o'zgarmaydi.
        ("cs-004", 900000, 800000, 3, "2026-11-05", [pay("2026-11-05", 300000), extend("2026-12-01", 2)], "2027-01-20"),
        # Qisman kechirish va qolganini to'lash — yopildi.
        ("cs-005", 500000, None, 2, "2026-10-01", [pay("2026-10-01", 250000), forgive("2026-11-15", 50000), pay("2026-11-20", 200000)], "2027-03-01"),
        # Hammasi kechirildi.
        ("cs-006", 300000, None, 1, "2026-10-01", [forgive("2026-12-01", 300000)], "2027-01-01"),
        # Muddati hali kelmagan.
        ("cs-007", 1200000, 1000000, 6, "2027-02-01", [], "2027-01-10"),
        # 45 kun kechikkan.
        ("cs-008", 600000, None, 2, "2026-11-15", [], "2026-12-30"),
        ("cs-neg-001", 0, None, 3, "2026-11-01", [], "2026-11-01"),
        ("cs-neg-002", 600000, None, 0, "2026-11-01", [], "2026-11-01"),
        ("cs-neg-003", 600000, None, 3, "2026-11-01", [pay("2026-11-01", 700000)], "2026-11-01"),
        ("cs-neg-004", 600000, None, 3, "2026-11-01", [pay("2026-11-05", 100000), pay("2026-11-02", 100000)], "2026-11-10"),
        ("cs-neg-005", 600000, None, 3, "2026-11-01", [extend("2026-11-02", 25)], "2026-11-10"),
        ("cs-neg-006", 300000, None, 1, "2026-11-01", [pay("2026-11-01", 300000), extend("2026-11-02", 1)], "2026-11-10"),
    ]
    suites["kk_credit_sale"] = _suite("kk_credit_sale", "Kasb-kor nasiya: qotirilgan narx va jadval, to'lov, muddat uzaytirish, kechirish, kechikish (ustamasiz), yosh guruhlari (kasbkor/SPEC 5.2)", [
        _case(cid, {"currency": U, "creditPrice": _s(cp * 100), "cashPrice": None if cash is None else _s(cash * 100), "installments": n,
                    "firstDue": fd, "events": ev, "today": td},
              lambda cp=cp, cash=cash, n=n, fd=fd, ev=ev, td=td: kk_credit_sale(cp * 100, None if cash is None else cash * 100, n,
                                                                              date.fromisoformat(fd), ev, date.fromisoformat(td)))
        for cid, cp, cash, n, fd, ev, td in cs])

    # K5: tovar qoldig'i va tannarx. Miqdor grammda (yoki donada), summalar so'mda.
    def sm(kind, qty, amount=None):
        m = {"kind": kind, "qty": qty}
        if amount is not None:
            m["amount"] = _s(t(amount))
        return m
    sugar = [sm("PURCHASE", 50000, 550000), sm("PURCHASE", 100000, 1250000), sm("SALE", 80000)]
    cg = [
        # SPEC 4.2 Bahodir aka, shakar: o'rtacha — tannarx 960 000, qolgan 70 kg 840 000 (12 000/kg).
        ("cg-001", "AVERAGE", 1000, sugar),
        # Xuddi shu, FIFO — tannarx 925 000, qolgan 875 000.
        ("cg-002", "FIFO", 1000, sugar),
        # Oxirgi birlik: qiymat aniq 0 (3 donaga 1000 so'm, uchta alohida sotuv).
        ("cg-003", "AVERAGE", 1, [sm("PURCHASE", 3, 1000), sm("SALE", 1), sm("SALE", 1), sm("SALE", 1)]),
        ("cg-004", "FIFO", 1, [sm("PURCHASE", 3, 1000), sm("SALE", 1), sm("SALE", 1), sm("SALE", 1)]),
        # Buzilgan tovar hisobdan chiqarildi; inventarizatsiyada kamomad va ortiqcha.
        ("cg-005", "AVERAGE", 1000, sugar + [sm("WRITE_OFF", 2000), sm("ADJUST", -500), sm("ADJUST", 1000, 12000)]),
        ("cg-006", "FIFO", 1000, [sm("PURCHASE", 10000, 110000), sm("PURCHASE", 10000, 125000), sm("WRITE_OFF", 12000), sm("ADJUST", 300, 3750)]),
        # Tiyinli yaxlitlash: 7 dona 1000 so'mga, 3 ta sotuv.
        ("cg-007", "AVERAGE", 1, [sm("PURCHASE", 7, 1000), sm("SALE", 3), sm("SALE", 2)]),
        ("cg-neg-001", "AVERAGE", 1000, [sm("PURCHASE", 1000, 10000), sm("SALE", 1001)]),
        ("cg-neg-002", "FIFO", 1000, [sm("SALE", 1)]),
        ("cg-neg-003", "AVERAGE", 1000, [sm("PURCHASE", 0, 10000)]),
        ("cg-neg-004", "AVERAGE", 1000, [sm("PURCHASE", 10, 0)]),
        ("cg-neg-005", "LIFO", 1000, []),
        ("cg-neg-006", "AVERAGE", 12, []),
    ]
    suites["kk_cogs"] = _suite("kk_cogs", "Kasb-kor tovar qoldig'i va tannarx: o'rtacha tortilgan va FIFO, driftsiz (oxirgi birlik — qiymat aniq 0), hisobdan chiqarish, inventarizatsiya (kasbkor/SPEC 4.1–4.2)", [
        _case(cid, {"currency": U, "method": mt, "factor": fc, "moves": ms}, lambda mt=mt, fc=fc, ms=ms: kk_cogs(mt, fc, ms))
        for cid, mt, fc, ms in cg])

    rp = [
        # SPEC 4.3: 70 kg shakar hisobda 840 000, joriy xarid narxi 13 500/kg → 945 000, farq 105 000; 13 000 ga sotish — ogohlantirish.
        ("rp-001", 70000, 840000, 13500, 1000, 13000),
        # Narx tushdi: farq manfiy, sotuv narxi yuqori — ogohlantirish yo'q.
        ("rp-002", 70000, 840000, 11500, 1000, 14000),
        # Dona bilan, sotuv narxi kiritilmagan.
        ("rp-003", 12, 600000, 55000, 1, None),
        # Qoldiq yo'q.
        ("rp-004", 0, 0, 13500, 1000, 13000),
        # Tiyinli yaxlitlash: 333 g, 12 345,67 so'm/kg.
        ("rp-005", 333, 4000, Fraction(1234567, 100), 1000, None),
        ("rp-neg-001", 10, 100, 0, 1000, None),
        ("rp-neg-002", -1, 0, 100, 1000, None),
    ]
    suites["kk_replacement"] = _suite("kk_replacement", "Kasb-kor qayta tiklash narxi: qoldiqning bugungi xarid narxidagi qiymati, «inflyatsiya yegan kapital», sotuv narxi past — ogohlantirish (kasbkor/SPEC 4.3)", [
        _case(cid, {"currency": U, "qty": q, "bookValue": _s(t(bv)), "price": _s(t(pr)), "factor": fc, "salePrice": None if sp is None else _s(t(sp))},
              lambda q=q, bv=bv, pr=pr, fc=fc, sp=sp: kk_replacement(q, t(bv), t(pr), fc, t(sp)))
        for cid, q, bv, pr, fc, sp in rp])

    # K6: xodim bilan hisob (oylar 0 dan), summalar so'mda.
    def pm(salary, *paid):
        return {"salary": _s(t(salary)), "paid": [_s(t(x)) for x in paid]}

    def adv(aid, month, amount, n, start):
        return {"id": aid, "month": month, "amount": _s(t(amount)), "installments": n, "startMonth": start}
    py = [
        # Sardor (Bahodir akaning sotuvchisi): haq 3 000 000; noyabrda 1 000 000 avans, dekabrdan 2 oyda ushlanadi.
        ("py-001", [pm(3000000, 3000000), pm(3000000, 2500000), pm(3000000, 2500000)], [adv("a1", 0, 1000000, 2, 1)], 0),
        # Qoldiq tiyinlar birinchi ulushga: 100 000 / 3.
        ("py-002", [pm(3000000), pm(3000000), pm(3000000)], [adv("a1", 0, 100000, 3, 0)], 0),
        # Haqsiz ta'til oyi: ushlanmagan ulush keyingi oyga o'tadi, ustama yo'q.
        ("py-003", [pm(3000000), pm(0), pm(3000000)], [adv("a1", 0, 1000000, 2, 1)], 0),
        # Haq ulushdan kam: qisman ushlanadi, qolgani keyingi oyga.
        ("py-004", [pm(400000), pm(3000000)], [adv("a1", 0, 1000000, 2, 0)], 0),
        # Ikki avans: eskisi birinchi ushlanadi.
        ("py-005", [pm(2000000), pm(2000000), pm(2000000)], [adv("a2", 1, 600000, 1, 1), adv("a1", 0, 3000000, 3, 0)], 0),
        # Qisman to'lov va ortiq to'lov: qoldiq keyingi oyga o'tadi (manfiy — ortiq to'langan).
        ("py-006", [pm(3000000, 1000000), pm(3000000, 4000000, 1500000), pm(3000000, 2000000)], [], 0),
        # Ilovagacha qolgan qarz (xodimga 500 000) va avans shu oy ushlanadi.
        ("py-007", [pm(3000000, 3000000), pm(3000000, 2800000)], [adv("a1", 0, 300000, 1, 0)], t(500000)),
        ("py-neg-001", [pm(3000000)], [adv("a1", 0, 0, 2, 0)], 0),
        ("py-neg-002", [pm(3000000)], [adv("a1", 0, 1000000, 0, 0)], 0),
        ("py-neg-003", [pm(3000000)], [adv("a1", 0, 1000000, 25, 0)], 0),
        ("py-neg-004", [pm(3000000)], [adv("a1", 2, 1000000, 2, 1)], 0),
        ("py-neg-005", [pm(-1)], [], 0),
        ("py-neg-006", [pm(3000000, 0)], [], 0),
    ]
    suites["kk_payroll"] = _suite("kk_payroll", "Kasb-kor xodim bilan hisob: oylik haq, foizsiz va jarimasiz avans (teng ulushlar, ushlanmagani keyingi oyga), to'langan va qoldiq (kasbkor/SPEC 7.2)", [
        _case(cid, {"currency": U, "months": ms, "advances": ad, "opening": _s(op)}, lambda ms=ms, ad=ad, op=op: kk_payroll(ms, ad, op))
        for cid, ms, ad, op in py])

    def dv(did, on, amount, days):
        return {"id": did, "on": on, "amount": _s(t(amount)), "dueDays": days}

    def sp_pay(on, amount):
        return {"on": on, "amount": _s(t(amount))}
    sp = [
        # Bahodir aka va ulgurji baza: 5 000 000 lik shakar 30 kunlik muddat bilan, 10-noyabrda 2 000 000 to'landi.
        ("sp-001", [dv("d1", "2026-11-01", 5000000, 30)], [sp_pay("2026-11-10", 2000000)], "2026-11-20"),
        # Xuddi shu, muddatdan 4 kun o'tdi: jarima yo'q, qoldiq o'sha-o'sha.
        ("sp-002", [dv("d1", "2026-11-01", 5000000, 30)], [sp_pay("2026-11-10", 2000000)], "2026-12-05"),
        # Ikki yetkazish: to'lov birinchisini yopadi, ikkinchisining bir qismini.
        ("sp-003", [dv("d1", "2026-11-01", 2000000, 14), dv("d2", "2026-11-05", 3000000, 14)], [sp_pay("2026-11-12", 2500000)], "2026-11-14"),
        # Keyingi yetkazishning muddati qisqaroq — to'lov avval unga.
        ("sp-004", [dv("d1", "2026-11-01", 2000000, 30), dv("d2", "2026-11-03", 1000000, 7)], [sp_pay("2026-11-05", 1500000)], "2026-11-06"),
        # 7 kun ichida muddati keladi; darhol to'lanadigan (0 kun) yetkazish.
        ("sp-005", [dv("d1", "2026-11-01", 1000000, 20), dv("d2", "2026-11-15", 400000, 0)], [], "2026-11-15"),
        # To'liq to'landi.
        ("sp-006", [dv("d1", "2026-11-01", 1000000, 10)], [sp_pay("2026-11-02", 400000), sp_pay("2026-11-09", 600000)], "2026-11-30"),
        ("sp-neg-001", [dv("d1", "2026-11-01", 0, 10)], [], "2026-11-02"),
        ("sp-neg-002", [dv("d1", "2026-11-01", 1000000, 400)], [], "2026-11-02"),
        ("sp-neg-003", [dv("d1", "2026-11-01", 1000000, 10)], [sp_pay("2026-11-02", 1000001)], "2026-11-02"),
        ("sp-neg-004", [dv("d1", "2026-11-05", 1000000, 10)], [sp_pay("2026-11-02", 100000)], "2026-11-06"),
        ("sp-neg-005", [dv("d1", "2026-11-01", 1000000, 10)], [sp_pay("2026-11-05", 100000), sp_pay("2026-11-03", 100000)], "2026-11-06"),
        ("sp-neg-006", [dv("d1", "2026-11-01", 1000000, 10)], [sp_pay("2026-11-05", 0)], "2026-11-06"),
    ]
    suites["kk_supplier_balance"] = _suite("kk_supplier_balance", "Kasb-kor ta'minotchiga qarz: yetkazishlar va to'lov muddatlari, to'lovlar eng erta muddatdan yopiladi, kechikish (jarimasiz), 7 kun ichida to'lanadigani (kasbkor/SPEC 7.1)", [
        _case(cid, {"currency": U, "deliveries": ds, "payments": ps, "today": td},
              lambda ds=ds, ps=ps, td=td: kk_supplier_balance(ds, ps, date.fromisoformat(td)))
        for cid, ds, ps, td in sp])

    # K7: kengayish darvozasi. Summalar so'mda.
    gt = [
        # Hammasi bajarilgan: zaxira 30 mln, o'rtacha xarajat 8,5 mln × 3 = 25,5 mln; foyda 3 oy musbat; 90+ 5%.
        ("gt-001", 30000000, [8000000, 9000000, 8500000], 3, [2580000, 1900000, 3100000], 10000000, 500000, 1000, False, False, True),
        # Zaxira yetmaydi (qamrov 2,35 oy).
        ("gt-002", 20000000, [8000000, 9000000, 8500000], 3, [2580000, 1900000, 3100000], 10000000, 500000, 1000, False, False, True),
        # Oxirgi 3 oyning birida zarar; faqat 2 ta «Hisob kuni».
        ("gt-003", 30000000, [8500000], 3, [2580000, -400000, 3100000], 0, 0, 1000, False, False, True),
        ("gt-004", 30000000, [8500000], 3, [2580000, 3100000], 0, 0, 1000, False, False, True),
        # 90+ nasiya 15% > 10%; aynan 10% — bajarilgan.
        ("gt-005", 30000000, [8500000], 3, [1, 1, 1], 10000000, 1500000, 1000, False, False, True),
        ("gt-006", 30000000, [8500000], 3, [1, 1, 1], 10000000, 1000000, 1000, False, False, True),
        # Foizli qarz: rejasiz — yopiq, reja bilan — bajarilgan.
        ("gt-007", 30000000, [8500000], 3, [1, 1, 1], 0, 0, 1000, True, False, True),
        ("gt-008", 30000000, [8500000], 3, [1, 1, 1], 0, 0, 1000, True, True, True),
        # Reja yozilmagan; hech narsa bajarilmagan; xarajat tarixi yo'q.
        ("gt-009", 30000000, [8500000], 3, [1, 1, 1], 0, 0, 1000, False, False, False),
        ("gt-010", 0, [], 3, [], 1000000, 1000000, 1000, True, False, False),
        # Xarajat 0 — zaxira sharti bajarilgan; 6 oylik talab.
        ("gt-011", 0, [0, 0, 0], 6, [1, 1, 1], 0, 0, 1000, False, False, True),
        ("gt-neg-001", -1, [1], 3, [], 0, 0, 1000, False, False, True),
        ("gt-neg-002", 0, [1], 0, [], 0, 0, 1000, False, False, True),
        ("gt-neg-003", 0, [1], 3, [], 100, 200, 1000, False, False, True),
        ("gt-neg-004", 0, [1], 3, [], 0, 0, 10001, False, False, True),
    ]
    suites["kk_expansion_gate"] = _suite("kk_expansion_gate", "Kasb-kor kengayish darvozasi: zaxira ≥ N oylik xarajat, oxirgi 3 «Hisob kuni»da foyda, 90+ nasiya ulushi, foizli qarz va reja, kengayish rejasi — har biri alohida va birga (kasbkor/SPEC 6.1)", [
        _case(cid, {"currency": U, "reserve": _s(t(rs)), "opexMonths": [_s(t(x)) for x in om], "requiredMonths": rm,
                    "trueProfits": [_s(t(x)) for x in tp], "receivables": _s(t(rc)), "receivables90": _s(t(r9)), "maxBadBp": mb,
                    "hasInterestDebt": hd, "hasPayoffPlan": hp, "hasPlan": pl},
              lambda rs=rs, om=om, rm=rm, tp=tp, rc=rc, r9=r9, mb=mb, hd=hd, hp=hp, pl=pl: kk_expansion_gate(
                  t(rs), [t(x) for x in om], rm, [t(x) for x in tp], t(rc), t(r9), mb, hd, hp, pl))
        for cid, rs, om, rm, tp, rc, r9, mb, hd, hp, pl in gt])

    zk = [
        # SPEC 8.3 Bahodir aka: 90 + 12 + 8 − 10 = 100 mln; nisob 1 100 000 × 85 = 93,5 mln → 2 500 000.
        ("zk-001", 90000000, 12000000, 8000000, 10000000, 1100000, 85, True),
        # Nisobdan past.
        ("zk-002", 60000000, 12000000, 8000000, 10000000, 1100000, 85, True),
        # Hawl to'lmagan.
        ("zk-003", 90000000, 12000000, 8000000, 10000000, 1100000, 85, False),
        # Qarzlar bazadan katta.
        ("zk-004", 5000000, 1000000, 0, 10000000, 1100000, 85, True),
        # Aynan nisob; tiyinli yaxlitlash.
        ("zk-005", 93500000, 0, 0, 0, 1100000, 85, True),
        ("zk-006", Fraction(9350000033, 100), 0, 0, 0, 1100000, 85, True),
        ("zk-neg-001", -1, 0, 0, 0, 1100000, 85, True),
        ("zk-neg-002", 1, 0, 0, 0, 0, 85, True),
        ("zk-neg-003", 1, 0, 0, 0, 1100000, 0, True),
    ]
    suites["kk_zakat"] = _suite("kk_zakat", "Kasb-kor savdo mollari zakoti hisobi: baza, nisob (oltin × gramm), 2,5% — baza ≥ nisob va hawl to'lganda; hisob, fatvo emas (kasbkor/SPEC 8.3, OQ-D5, OQ-D7)", [
        _case(cid, {"currency": U, "stock": _s(t(st)), "cash": _s(t(ca)), "receivables": _s(t(rc)), "debts": _s(t(db)),
                    "goldPrice": _s(t(gp)), "nisabGrams": ng, "hawlComplete": hw},
              lambda st=st, ca=ca, rc=rc, db=db, gp=gp, ng=ng, hw=hw: kk_zakat(t(st), t(ca), t(rc), t(db), t(gp), ng, hw))
        for cid, st, ca, rc, db, gp, ng, hw in zk])

    def close(**kw):
        return {"kind": "CLOSE", **{k: _s(t(v)) for k, v in kw.items()}}

    def use(fund, amount):
        return {"kind": "USE", "fund": fund, "amount": _s(t(amount))}
    fd = [
        # Nilufar: oktyabr va noyabr «Hisob kuni»; soliq to'landi, zaxiradan uskuna tuzatildi.
        ("fd-001", [close(tax=720000, reserve=774000, working=1290000, expansion=516000),
                    close(tax=680000, reserve=600000, working=1000000, expansion=400000, sadaqa=100000),
                    use("TAX", 720000), use("RESERVE", 300000)]),
        # Hammasi ishlatildi — qoldiq 0.
        ("fd-002", [close(working=1000000), use("WORKING", 1000000)]),
        ("fd-neg-001", [close(reserve=100000), use("RESERVE", 100001)]),
        ("fd-neg-002", [use("SADAQA", 1)]),
        ("fd-neg-003", [close(reserve=100000), use("RESERVE", 0)]),
        ("fd-neg-004", [use("BONUS", 1)]),
    ]
    suites["kk_funds"] = _suite("kk_funds", "Kasb-kor «Hisob kuni» konvertlari: soliq zaxirasi, zaxira, aylanma, kengayish, sadaqa — qo'shilgan, ishlatilgan, qoldiq; qoldiqdan ko'p ishlatib bo'lmaydi (kasbkor/SPEC 4.5, 8.2)", [
        _case(cid, {"currency": U, "events": ev}, lambda ev=ev: kk_funds(ev)) for cid, ev in fd])

    # K8 (ADR-0003): sotuvchi smenasi. Summalar so'mda.
    def si(k, w, a):
        return {"kind": k, "wallet": w, "amount": _s(a * 100)}
    sh = [
        # Do'kon: ochilish 200 000, naqd savdo 850 000, nasiya to'lovi 150 000, kartaga 300 000 → kutilgan 1 200 000;
        # sanaldi 1 200 000, egasiga 1 000 000 topshirildi → keyingi smenaga 200 000.
        ("sh-001", 200000, [si("SALE", "CASH", 500000), si("SALE", "CASH", 350000), si("CREDIT_PAYMENT", "CASH", 150000),
                            si("SALE", "CARD", 300000)], 1200000, 1000000, None, []),
        # Kamomad 20 000 — sabab majburiy.
        ("sh-002", 200000, [si("SALE", "CASH", 850000)], 1030000, 1000000, "CHANGE_ERROR", []),
        # Ortiqcha; hech narsa topshirilmadi.
        ("sh-003", 0, [si("SALE", "CASH", 100000)], 105000, 0, "UNKNOWN", []),
        # Uchinchi kamomad 4 hafta ichida — «xato qidirish» taklifi.
        ("sh-004", 100000, [si("SALE", "CASH", 400000)], 490000, 490000, "UNKNOWN", ["-5000", "-12000"]),
        # Savdosiz smena: hammasi topshirildi.
        ("sh-005", 300000, [], 300000, 300000, None, []),
        ("sh-neg-001", 100000, [si("SALE", "CASH", 50000)], 150000, 160000, None, []),
        ("sh-neg-002", 100000, [], 90000, 0, None, []),
        ("sh-neg-003", 100000, [si("REFUND", "CASH", 50000)], 50000, 0, None, []),
        ("sh-neg-004", 100000, [], 100000, -1, None, []),
        ("sh-neg-005", 100000, [si("SALE", "CASH", 0)], 100000, 0, None, []),
    ]
    suites["kk_shift_close"] = _suite("kk_shift_close", "Kasb-kor sotuvchi smenasi: o'z naqd tushumi va nasiya to'lovlari bilan kutilgan kassa, farq va sabab, egasiga topshirilgan, keyingi smenaga qolgan (kasbkor/SPEC 12, ADR-0003)", [
        _case(cid, {"currency": U, "opening": _s(o * 100), "ins": ins, "counted": _s(c * 100), "handedOver": _s(h * 100), "reason": r,
                    "recentDifferences": [_s(int(x) * 100) for x in rec]},
              lambda o=o, ins=ins, c=c, h=h, r=r, rec=rec: kk_shift_close(o * 100, ins, c * 100, h * 100, r, [_s(int(x) * 100) for x in rec]))
        for cid, o, ins, c, h, r, rec in sh])

    suites["kk_month_close"] = _suite("kk_month_close", "Kasb-kor «Hisob kuni»: soliq zaxirasi, egasi maoshi, qolgan pul va taqsimot qoidasi (largest remainder), maoshdan ortig'ini o'tkazish (kasbkor/SPEC 4.5)", [
        _case(cid, {"currency": U, "revenue": _s(t(r)), "expenses": _s(t(ex)), "depreciation": _s(t(dp)), "ownerSalary": _s(t(sal)), "ownerPaid": _s(t(pd)),
                    "tax": tx, "rule": ru, "carryOverdraw": co},
              lambda r=r, ex=ex, dp=dp, sal=sal, pd=pd, tx=tx, ru=ru, co=co: kk_month_close(t(r), t(ex), t(dp), t(sal), t(pd), tx, ru, co))
        for cid, r, ex, dp, sal, pd, tx, ru, co in mc])

    def mv(k, a, fee=None):
        m = {"kind": k, "amount": _s(a)}
        if fee is not None:
            m["fee"] = _s(fee)
        return m
    # Rustam aka (KRW, kasrsiz): maosh 2 600 000, ijara 400 000, ovqat 350 000, telefon 60 000, uyga 1 200 000 + 5 000.
    rustam = [mv("SALARY", 2600000), mv("EXPENSE", 400000), mv("EXPENSE", 350000), mv("EXPENSE", 60000), mv("SENT_HOME", 1200000, 5000)]
    mm = [
        # O'z ulushi 20 % = 520 000 jamg'armaga qo'yildi; qo'lda 215 000 qoldi.
        ("mf-001", "KRW", 150000, 0, 2000, rustam + [mv("FUND_IN", 520000)]),
        # Ulush yetmadi: 320 000 — 200 000 kam.
        ("mf-002", "KRW", 150000, 0, 2000, rustam + [mv("FUND_IN", 320000)]),
        # Hammasi uyga: jamg'arma yo'q.
        ("mf-003", "KRW", 150000, 0, 2000, rustam[:4] + [mv("SENT_HOME", 1700000, 5000)]),
        # Jamg'armadan olindi (sof manfiy).
        ("mf-004", "KRW", 150000, 3000000, 2000, rustam + [mv("FUND_IN", 520000), mv("FUND_OUT", 800000)]),
        # Dilnoza (RUB): qo'ldagi pul manfiy.
        ("mf-005", "RUB", 0, 0, 2000, [mv("SALARY", 8000000), mv("EXPENSE", 3500000), mv("EXPENSE", 2500000), mv("EXPENSE", 600000),
                                       mv("SENT_HOME", 2000000, 30000)]),
        # Daromadsiz oy: ulushlar yo'q, ogohlantirish yo'q.
        ("mf-006", "KRW", 500000, 1000000, 2000, [mv("EXPENSE", 300000)]),
        # USD: maosh 1 234,57 + bonus 50; jamg'arma 246,91 — largest remainder va bp yaxlitlash.
        ("mf-007", "USD", 10000, 0, 2000, [mv("SALARY", 123457), mv("OTHER_INCOME", 5000), mv("FUND_IN", 24691), mv("EXPENSE", 33333)]),
        # Boshlang'ich qoldiqlar yozuv sifatida; ulush 0 % — maqsad yo'q.
        ("mf-008", "KRW", 0, 0, 0, [mv("OPENING", 100000), mv("FUND_OPENING", 2000000), mv("SALARY", 2600000), mv("SENT_HOME", 2000000)]),
        ("mf-neg-001", "KRW", 0, 0, 2000, [mv("SALARY", 0)]),
        ("mf-neg-002", "KRW", 0, 0, 2000, [mv("SALARY", 1000), mv("SENT_HOME", 500, -1)]),
        ("mf-neg-003", "KRW", 0, 0, 2000, [mv("LOAN", 1000)]),
        ("mf-neg-004", "KRW", 0, 0, 10001, [mv("SALARY", 1000)]),
        ("mf-neg-005", "KRW", 0, 100, 2000, [mv("FUND_IN", 50), mv("FUND_OUT", 151)]),
    ]
    mm = [(cid, c, o, fo, 0, bp, ms) for cid, c, o, fo, bp, ms in mm] + [
        # M4: ulush avval qorovul pulga (300 000), qolgani jamg'armaga (220 000) — ulush bajarildi.
        ("mf-009", "KRW", 150000, 6000000, 510000, 2000, [mv("SALARY", 2600000), mv("EXPENSE", 810000),
                                                      mv("SENT_HOME", 1200000, 5000), mv("RESERVE_IN", 300000), mv("FUND_IN", 220000)]),
        # Kasal bo'ldi: qorovul puldan 400 000 — ulush kamaymaydi, ogohlantirish yo'q.
        ("mf-010", "KRW", 0, 6000000, 810000, 2000, [mv("SALARY", 2600000), mv("EXPENSE", 1210000), mv("RESERVE_OUT", 400000),
                                                   mv("SENT_HOME", 1200000), mv("FUND_IN", 520000)]),
        # Boshlang'ich qorovul pul yozuv sifatida; faqat qorovulga — ulush yetmadi.
        ("mf-011", "KRW", 0, 0, 0, 2000, [mv("RESERVE_OPENING", 500000), mv("SALARY", 2600000), mv("RESERVE_IN", 200000)]),
        ("mf-neg-006", "KRW", 0, 0, 100, 2000, [mv("RESERVE_OUT", 101)]),
        ("mf-neg-007", "KRW", 0, 0, -1, 2000, [mv("SALARY", 1000)]),
    ]
    suites["mf_month"] = _suite("mf_month", "Musofir oy hisoboti: maosh, chet eldagi xarajat, uyga yuborilgan va komissiya, qaytish jamg'armasi va qorovul pul, qo'ldagi pul, o'z ulushi maqsadi va yetmagani, daromaddan ulushlar (musofir/SPEC 2–3, 6.4)", [
        _case(cid, {"currency": c, "opening": _s(o), "fundOpening": _s(fo), "reserveOpening": _s(ro), "shareBp": bp, "moves": ms},
              lambda o=o, fo=fo, ro=ro, bp=bp, ms=ms: mf_month(o, fo, bp, ms, ro))
        for cid, c, o, fo, ro, bp, ms in mm])
    rs_ = [
        # Rustam aka: oyiga ~800 000 von xarajat, 1 oy — maqsad 805 000; qoldiq 300 000; ulush 520 000 → 505 000 qorovulga.
        ("rs-001", "KRW", 300000, [810000, 790000, 815000], 1, 520000),
        # To'la — ulush to'liq jamg'armaga.
        ("rs-002", "KRW", 900000, [810000, 790000, 815000], 1, 520000),
        # 2 oy, bo'sh; ulush hammasi qorovulga.
        ("rs-003", "KRW", 0, [810000, 790000], 2, 520000),
        # Tarix yo'q — maqsad yo'q, ulush jamg'armaga.
        ("rs-004", "KRW", 0, [], 1, 520000),
        # USD, yaxlitlash: (100 001 + 100 000) × 3 / 2; ulushsiz.
        ("rs-005", "USD", 150000, [100001, 100000], 3, None),
        # Xarajatsiz oylar — maqsad 0, to'la.
        ("rs-006", "KRW", 0, [0, 0], 1, 100000),
        ("rs-neg-001", "KRW", 0, [800000], 4, None),
        ("rs-neg-002", "KRW", -1, [800000], 1, None),
        ("rs-neg-003", "KRW", 0, [800000], 1, -5),
    ]
    suites["mf_reserve"] = _suite("mf_reserve", "Musofir qorovul pul: chet eldagi o'rtacha oylik xarajat × N oy maqsad, yetmagani, holat va o'z ulushini qorovul pul va jamg'arma orasida bo'lish (musofir/SPEC 6.4)", [
        _case(cid, {"currency": c, "balance": _s(b), "monthly": [_s(x) for x in mo], "months": n, "share": None if sh_ is None else _s(sh_)},
              lambda b=b, mo=mo, n=n, sh_=sh_: mf_reserve(b, mo, n, sh_))
        for cid, c, b, mo, n, sh_ in rs_])
    su = [
        # Maqsad 120 mln, shundan ish boshlash (tikuv sexi) 30 mln — yashash uchun 90 mln.
        ("su-001", 12000000000, 3000000000),
        # Butun maqsad — ish boshlash.
        ("su-002", 12000000000, 12000000000),
        # Maqsadsiz.
        ("su-003", None, 3000000000),
        # bp yaxlitlash: 1 / 3.
        ("su-004", 300, 100),
        ("su-neg-001", 12000000000, 12000000001),
        ("su-neg-002", 12000000000, 0),
    ]
    suites["mf_startup"] = _suite("mf_startup", "Musofir ish boshlash summasi: qaytish jamg'armasi maqsadining bir qismi, yashash uchun qolgani (musofir/SPEC 6.6)", [
        _case(cid, {"currency": U, "target": None if tg is None else _s(tg), "startup": _s(st)},
              lambda tg=tg, st=st: mf_startup(tg, st))
        for cid, tg, st in su])

    krw = (91, 10)
    rf = [
        # Rustam aka: 6 mln von (54,6 mln so'm), maqsad 120 mln so'm, oyiga ~520 000 von; 2027-12-01 gacha 13 oy — yetmaydi.
        ("rf-001", "KRW", 6000000, krw, 12000000000, [520000, 500000, 540000], "2026-10-18", "2027-12-01"),
        # Qaytish 2028-03-01 — shu sur'atda yetadi.
        ("rf-002", "KRW", 6000000, krw, 12000000000, [520000, 500000, 540000], "2026-10-18", "2028-03-01"),
        # Maqsadga yetgan.
        ("rf-003", "KRW", 14000000, krw, 12000000000, [520000], "2026-10-18", None),
        # Jamg'arish yo'q (o'rtacha manfiy).
        ("rf-004", "KRW", 6000000, krw, 12000000000, [0, -100000], "2026-10-18", "2027-06-01"),
        # Maqsadsiz.
        ("rf-005", "KRW", 6000000, krw, None, [520000], "2026-10-18", "2027-06-01"),
        # Kurs yo'q — uy valyutasidagi ko'rsatkichlar yo'q.
        ("rf-006", "KRW", 6000000, None, 12000000000, [520000], "2026-10-18", "2027-06-01"),
        # USD, o'rtacha yaxlitlash (300 001 / 3).
        ("rf-007", "USD", 500000, (12650, 1), 12000000000, [100001, 100000, 100000], "2026-10-18", "2027-10-18"),
        # Qaytish sanasi o'tib ketgan — 0 oy.
        ("rf-008", "KRW", 6000000, krw, 12000000000, [520000], "2026-10-18", "2026-09-01"),
        # Yozuvli oy yo'q — prognoz yo'q.
        ("rf-009", "KRW", 6000000, krw, 12000000000, [], "2026-10-18", "2027-06-01"),
        ("rf-neg-001", "KRW", 6000000, (91, 0), 12000000000, [], "2026-10-18", None),
        ("rf-neg-002", "KRW", 6000000, krw, 0, [], "2026-10-18", None),
        ("rf-neg-003", "KRW", -1, krw, None, [], "2026-10-18", None),
    ]
    suites["mf_return_fund"] = _suite("mf_return_fund", "Musofir qaytish jamg'armasi: kurs bilan uy valyutasidagi qoldiq, maqsadgacha qolgan va necha oy, qaytish sanasidagi prognoz va holat; kurssiz — taxmin yo'q (musofir/SPEC 2.2, 4.1)", [
        _case(cid, {"currency": c, "homeCurrency": U, "balance": _s(b), "rateNum": None if r is None else r[0],
                    "rateDen": None if r is None else r[1], "target": None if tg is None else _s(tg),
                    "monthly": [_s(x) for x in mo], "today": td, "returnOn": ro},
              lambda c=c, b=b, r=r, tg=tg, mo=mo, td=td, ro=ro: mf_return_fund(c, U, b, r, tg, mo, date.fromisoformat(td),
                                                                              date.fromisoformat(ro) if ro else None))
        for cid, c, b, r, tg, mo, td, ro in rf])
    def sh(*pairs):
        return [{"purpose": p, "bp": b} for p, b in pairs]
    def sp(p, a):
        return {"purpose": p, "amount": _s(a)}
    gul = sh(("HOUSEHOLD", 5000), ("DEBT", 3000), ("BUILD", 2000))
    rm = [
        # Gulnora: 10 900 000 so'm qabul qilindi — 50/30/20; uy xarajati 2 mln, qarz to'liq.
        ("rm-001", [{"received": _s(1090000000), "shares": gul}], [sp("HOUSEHOLD", 200000000), sp("DEBT", 327000000)]),
        # Largest remainder: 100 000,01 so'm uchga (ulushlar tartibsiz berilgan).
        ("rm-002", [{"received": _s(10000001), "shares": sh(("BUILD", 3334), ("HOUSEHOLD", 3333), ("DEBT", 3333))}], []),
        # Ikki yuborish turli ulushlar bilan, bittasi hali yo'lda.
        ("rm-003", [{"received": _s(1090000000), "shares": gul},
                    {"received": _s(500000000), "shares": sh(("HOUSEHOLD", 10000))},
                    {"received": None, "shares": gul}], [sp("HOUSEHOLD", 600000000)]),
        # Uy xarajati maqsaddan ortiq.
        ("rm-004", [{"received": _s(1090000000), "shares": gul}], [sp("HOUSEHOLD", 600000000)]),
        # Ulushsiz maqsadga xarajat (marosim).
        ("rm-005", [{"received": _s(1090000000), "shares": gul}], [sp("CEREMONY", 100000000)]),
        # Faqat yo'lda.
        ("rm-006", [{"received": None, "shares": gul}], []),
        ("rm-neg-001", [{"received": _s(100), "shares": sh(("HOUSEHOLD", 9000))}], []),
        ("rm-neg-002", [{"received": _s(100), "shares": sh(("HOUSEHOLD", 5000), ("HOUSEHOLD", 5000))}], []),
        ("rm-neg-003", [{"received": _s(100), "shares": sh(("HOUSEHOLD", 10000), ("DEBT", 0))}], []),
        ("rm-neg-004", [{"received": _s(100), "shares": sh(("CAR", 10000))}], []),
        ("rm-neg-005", [{"received": _s(0), "shares": gul}], []),
        ("rm-neg-006", [{"received": _s(100), "shares": gul}], [sp("DEBT", 0)]),
    ]
    suites["mf_remittance"] = _suite("mf_remittance", "Musofir «Ikki qirg'oq»: qabul qilingan pulni maqsad ulushlariga bo'lish (largest remainder), maqsad bo'yicha sarflangan va qoldiq, yo'ldagi yuborishlar, maqsaddan ortiq sarf (musofir/SPEC 5)", [
        _case(cid, {"currency": U, "remittances": rs, "spends": ss}, lambda rs=rs, ss=ss: mf_remittance(rs, ss))
        for cid, rs, ss in rm])
    td = [
        # Yo'l qarzi 15 mln: maqsadda 3,27 mln, oyiga ~3 mln keladi → 4 oy, 6 oylik maqsadda.
        ("td-001", 1500000000, 327000000, [327000000, 300000000, 280000000], 6, "2026-10-19"),
        # Sekin: oyiga 1 mln — 12 oy, maqsad 6 oy (BEHIND), oyiga 2 mln kerak.
        ("td-002", 1500000000, 300000000, [100000000, 100000000], 6, "2026-10-19"),
        # Maqsaddagi pul qarzni yopadi.
        ("td-003", 300000000, 327000000, [327000000], 6, "2026-10-19"),
        # Hali to'lov yo'q.
        ("td-004", 1500000000, 0, [], 6, "2026-10-19"),
        # Maqsad ortiq sarflangan (manfiy qoldiq hisobga olinmaydi); 31-yanvar + 1 oy — fevral oxiri.
        ("td-005", 1000000000, -50000000, [500000000], 3, "2027-01-31"),
        # O'rtacha yaxlitlash (1 000 001 / 2) va oyiga kerak yaxlitlash (10 000 001 / 3).
        ("td-006", 10000001, 0, [500001, 500000], 3, "2026-10-19"),
        ("td-neg-001", -1, 0, [], 6, "2026-10-19"),
        ("td-neg-002", 100, 0, [], 0, "2026-10-19"),
    ]
    suites["mf_travel_debt"] = _suite("mf_travel_debt", "Musofir yo'l qarzi: «Qarz to'lovi» maqsadidagi pul bilan qolgan, oylik o'rtacha, necha oyda yopiladi va qachon, maqsadli muddat uchun oyiga kerak (musofir/SPEC 6.1)", [
        _case(cid, {"currency": U, "outstanding": _s(o), "available": _s(a), "monthly": [_s(x) for x in mo], "targetMonths": tm, "today": td_},
              lambda o=o, a=a, mo=mo, tm=tm, td_=td_: mf_travel_debt(o, a, mo, tm, date.fromisoformat(td_)))
        for cid, o, a, mo, tm, td_ in td])

    no = {"guaranteed": "NO", "lossShared": "YES", "realActivity": "YES", "recruitment": "NO", "urgency": "NO", "written": "YES",
          "licensed": "YES", "inspection": "YES", "exitEasy": "YES"}
    calm = {"approached": "NO", "upfront": "NO", "abroadJobFee": "NO", "familyDiscussed": "YES"}
    co = [
        # Qaytgandan 20 kun keyin qarindosh 15 mln qarz so'radi (olib kelingan 120 mln, 12,5 %), muddatsiz.
        ("co-001", "2026-11-08", "2026-10-19", 12000000000, "LEND", 1500000000, {**calm, "approached": "YES", "repaymentDate": "NO"}),
        # Sheriklik 50 mln (41,67 %) — kafolatlangan foyda va'da qilinmoqda, avval pul.
        ("co-002", "2026-11-08", "2026-10-19", 12000000000, "PARTNERSHIP", 5000000000,
         {**no, **calm, "guaranteed": "YES", "upfront": "YES"}),
        # Davrdan keyin, hammasi joyida — yashil.
        ("co-003", "2027-02-01", "2026-10-19", 12000000000, "PURCHASE", 5000000000, calm),
        # Davr ichida kichik xarid (5 %) — yashil, lekin davr ichida.
        ("co-004", "2026-11-08", "2026-10-19", 12000000000, "PURCHASE", 600000000, calm),
        # Chet elga qayta ish uchun pul so'rashdi — qizil (davrsiz ham).
        ("co-005", "2026-10-19", None, None, "OTHER", 300000000, {**calm, "abroadJobFee": "YES", "familyDiscussed": "NO"}),
        # Olib kelingan summa noma'lum — davr ichida har katta qaror sariq.
        ("co-006", "2026-10-25", "2026-10-19", None, "INVEST", 1000000000, {**no, **calm, "urgency": "UNKNOWN"}),
        # Davrning oxirgi kuni (89-kun) — hali ichida; 90-kun — tashqarida.
        ("co-007", "2027-01-16", "2026-10-19", 12000000000, "PURCHASE", 2000000000, calm),
        ("co-008", "2027-01-17", "2026-10-19", 12000000000, "PURCHASE", 2000000000, calm),
        # M5 — misol: migrant 18 000 $ (≈ 228 mln so'm) olib keldi, «Oltin foyda»ga 10 000 $ (≈ 126,5 mln): kafolatli 35 % oyiga,
        # shoshirish, tekshirtirmaydi, chiqish qiyin; oila bilan maslahatlashmadi; devor — 6 oy × 8 mln.
        ("co-009", "2026-10-22", "2026-10-19", 22770000000, "INVEST", 12650000000,
         {**no, "approached": "YES", "upfront": "NO", "abroadJobFee": "NO", "familyDiscussed": "NO",
          "guaranteed": "YES", "urgency": "YES", "inspection": "NO", "exitEasy": "NO", "realActivity": "UNKNOWN"},
         4800000000, 3500),
        # Davrdan keyin kichik xarid, lekin qal'a devoriga tegadi — qizil.
        ("co-010", "2027-03-01", "2026-10-19", 12000000000, "PURCHASE", 8000000000, calm, 6000000000, None),
        # Devorgacha — yashil (100 mln − 60 mln = 40 mln erkin, xarid 40 mln).
        ("co-011", "2027-03-01", "2026-10-19", 10000000000, "PURCHASE", 4000000000, calm, 6000000000, None),
        # Va'da yaxlitlash: oyiga 3,33 % — yiliga 39,96 %, 1,3996 → 1,4 barobar.
        ("co-012", "2027-03-01", None, None, "INVEST", 100000000, {**no, **calm}, None, 333),
        ("co-neg-005", "2026-10-19", None, None, "INVEST", 100, {**no, **calm}, None, 0),
        ("co-neg-001", "2026-10-19", None, None, "CAR", 100, calm),
        ("co-neg-002", "2026-10-19", None, None, "LEND", 100, calm),
        ("co-neg-003", "2026-10-19", None, None, "OTHER", 0, calm),
        ("co-neg-004", "2026-10-19", None, None, "OTHER", 100, {**calm, "upfront": "MAYBE"}),
    ]
    suites["mf_cooling"] = _suite("mf_cooling", "Musofir sovutish davri (qaytgandan keyin 90 kun) va kengaytirilgan taklif detektori: U12 savollari, musofirga xos bayroqlar, olib kelingan summadan ulush, kutish sanasi (musofir/SPEC 6.3)", [
        _case(cid, {"currency": U, "today": t_, "returnedOn": r_, "broughtHome": None if b is None else _s(b), "kind": k_, "amount": _s(a),
                    "answers": an, "wall": None if w is None else _s(w), "promisedBp": pb},
              lambda t_=t_, r_=r_, b=b, k_=k_, a=a, an=an, w=w, pb=pb: mf_cooling(date.fromisoformat(t_), date.fromisoformat(r_) if r_ else None,
                                                                                 b, k_, a, an, w, pb))
        for cid, t_, r_, b, k_, a, an, w, pb in [c if len(c) == 9 else (*c, None, None) for c in co]])
    wl = [
        # Uyda oyiga ~8 mln — 6 oylik ro'zg'or 48 mln.
        ("wl-001", [800000000, 780000000, 820000000], 6),
        # Yaxlitlash: (1 + 2) × 6 / 2 = 9 (tiyin).
        ("wl-002", [1, 2], 6),
        ("wl-003", [], 6),
        ("wl-neg-001", [100], 0),
        ("wl-neg-002", [-1], 6),
    ]
    suites["mf_wall"] = _suite("mf_wall", "Musofir «qal'a devori»: qaytgandan keyin oilaning 6 oylik ro'zg'ori — Uy makonining oxirgi oylardagi o'rtacha xarajati × 6 (musofir/SPEC 6.8)", [
        _case(cid, {"currency": U, "monthly": [_s(x) for x in mo], "months": n}, lambda mo=mo, n=n: mf_wall(mo, n))
        for cid, mo, n in wl])
    return suites


ORACLE_SUITES = ("allocate", "percent_of", "round", "fx_convert", "money_format", "amortization", "emergency_target",
                 "personal_inflation", "unexplained_gap", "profit_spike", "profit_distribution", "debt_recovery_split",
                 "journal_chain", "debt_plan", "debt_status", "debt_load", "payoff_projection", "payoff_plan", "ceremony_scenarios",
                 "partnership_rules", "buyout_schedule", "venture_period", "venture_idea", "offer_check", "review_protocol",
                 "kk_owner_pay", "kk_depreciation", "kk_true_profit", "kk_order_quote", "kk_month_close", "kk_cash_close", "kk_credit_sale", "kk_cogs", "kk_replacement",
                 "kk_payroll", "kk_supplier_balance", "kk_expansion_gate", "kk_zakat", "kk_funds", "kk_shift_close",
                 "mf_month", "mf_return_fund", "mf_remittance",
                 "mf_travel_debt", "mf_cooling", "mf_reserve", "mf_startup", "mf_wall")


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
    # M3 (musofir/SPEC 6): 15 mln yo'l qarzi, maqsadda 3,27 mln, oyiga ~3 mln → 4 oy; qarindosh 15 mln muddatsiz qarz.
    rsv = mf_reserve(300000, [810000, 790000, 815000], 1, 520000)
    assert (rsv["target"], rsv["toReserve"], rsv["toFund"], rsv["status"]) == ("805000", "505000", "15000", "PARTIAL"), rsv
    m4 = mf_month(150000, 6000000, 2000, [{"kind": "SALARY", "amount": "2600000"}, {"kind": "RESERVE_IN", "amount": "300000"},
                                          {"kind": "FUND_IN", "amount": "220000"}], 510000)
    assert (m4["savedNet"], m4["shareGap"], m4["reserveBalance"], m4["pocket"]) == ("520000", "0", "810000", "2230000"), m4
    assert mf_startup(12000000000, 3000000000)["living"] == "9000000000"
    _expect_error("STARTUP_EXCEEDS_TARGET", mf_startup, 100, 101)
    scam = offer_check({"guaranteed": "YES", "lossShared": "UNKNOWN", "realActivity": "UNKNOWN", "recruitment": "UNKNOWN",
                         "urgency": "YES", "written": "YES", "licensed": "UNKNOWN", "inspection": "NO", "exitEasy": "NO"})
    assert scam["signs"] == 4 and scam["flags"][-1]["code"] == "TWO_SIGNS", scam
    assert mf_wall([800000000, 780000000, 820000000])["wall"] == "4800000000"
    pr = mf_cooling(date(2027, 3, 1), None, None, "INVEST", 100, {**{q: "NO" for q in ("guaranteed", "recruitment", "urgency")},
                    **{q: "YES" for q in ("lossShared", "realActivity", "written", "licensed", "inspection", "exitEasy")},
                    "approached": "NO", "upfront": "NO", "abroadJobFee": "NO", "familyDiscussed": "YES"}, None, 3500)
    assert (pr["promisedYearlyBp"], pr["promisedTimesTenths"]) == (42000, 52), pr
    tdr = mf_travel_debt(1500000000, 327000000, [327000000, 300000000, 280000000], 6, date(2026, 10, 19))
    assert (tdr["remaining"], tdr["monthsToClear"], tdr["clearOn"], tdr["status"]) == ("1173000000", 4, "2027-02-19", "ON_TRACK")
    cor = mf_cooling(date(2026, 11, 8), date(2026, 10, 19), 12000000000, "LEND", 1500000000,
                     {"approached": "YES", "upfront": "NO", "abroadJobFee": "NO", "repaymentDate": "NO", "familyDiscussed": "YES"})
    assert (cor["verdict"], cor["daysLeft"], cor["waitUntil"], cor["shareBp"]) == ("YELLOW", 70, "2027-01-17", 1250)
    # M2 (musofir/SPEC 5): 10 900 000 so'm 50/30/20 — uy 5 450 000, qarz 3 270 000, qurilish 2 180 000.
    rr2 = mf_remittance([{"received": "1090000000", "shares": [{"purpose": "HOUSEHOLD", "bp": 5000}, {"purpose": "DEBT", "bp": 3000},
                                                              {"purpose": "BUILD", "bp": 2000}]}], [])
    assert [p["received"] for p in rr2["purposes"]] == ["545000000", "327000000", "218000000"]
    # M1 (musofir/SPEC 2.1): Rustam aka — ulush 520 000 von bajarildi, qo'lda 215 000; 13 oyda 116,1 mln — 3,9 mln kam.
    rm = mf_month(150000, 0, 2000, [{"kind": "SALARY", "amount": "2600000"}, {"kind": "EXPENSE", "amount": "810000"},
                                    {"kind": "SENT_HOME", "amount": "1200000", "fee": "5000"}, {"kind": "FUND_IN", "amount": "520000"}])
    assert (rm["pocket"], rm["shareGap"], rm["sentBp"], rm["warnings"]) == ("215000", "0", 4635, [])
    rr = mf_return_fund("KRW", "UZS", 6000000, (91, 10), 12000000000, [520000, 500000, 540000], date(2026, 10, 18), date(2027, 12, 1))
    assert (rr["monthsUntilReturn"], rr["monthsToTarget"], rr["shortfallAtReturn"], rr["status"]) == (13, 14, "388400000", "BEHIND")
    # K8 (ADR-0003): sotuvchi smenasi — kutilgan 1 200 000, topshirildi 1 000 000, qoldi 200 000.
    shf = kk_shift_close(20000000, [{"kind": "SALE", "wallet": "CASH", "amount": "85000000"},
                                    {"kind": "CREDIT_PAYMENT", "wallet": "CASH", "amount": "15000000"},
                                    {"kind": "SALE", "wallet": "CARD", "amount": "30000000"}], 120000000, 100000000, None, [])
    assert (shf["expected"], shf["difference"], shf["left"], shf["cardIn"]) == ("120000000", "0", "20000000", "30000000")
    # K2 (kasbkor/SPEC 3.1): Nilufar — haqiqiy foyda 3 100 000; 7 mln / 36 oy → 16 × 194 444,45 + 20 × 194 444,44.
    assert kk_true_profit(1800000000, 600000000, 250000000, 500000000, [{"hours100": 8000, "hourlyRate": "1500000", "paid": False}],
                          20000000, 0)["trueProfit"] == "310000000"
    sched = kk_depreciation(700000000, 0, 36, [])["schedule"]
    assert sched.count("19444445") == 16 and sched.count("19444444") == 20 and sum(map(int, sched)) == 700000000
    assert kk_order_quote(45000000, 600, 4000000, 5000000, 2000000, 500, 70000000)["cost"] == "79800000"
    # K5 (kasbkor/SPEC 4.2, 4.3): shakar — o'rtacha 960 000 / 840 000, FIFO 925 000 / 875 000; qayta tiklash farqi 105 000.
    sug = [{"kind": "PURCHASE", "qty": 50000, "amount": "55000000"}, {"kind": "PURCHASE", "qty": 100000, "amount": "125000000"}, {"kind": "SALE", "qty": 80000}]
    avg, fifo = kk_cogs("AVERAGE", 1000, sug), kk_cogs("FIFO", 1000, sug)
    assert (avg["moves"][2]["cost"], avg["value"], avg["unitCost"]) == ("96000000", "84000000", "1200000")
    assert (fifo["moves"][2]["cost"], fifo["value"]) == ("92500000", "87500000")
    assert kk_replacement(70000, 84000000, 1350000, 1000, 1300000) == {"replacementValue": "94500000", "inflationGap": "10500000", "saleBelowReplacement": True}
    # K4 (kasbkor/SPEC 5.1, 5.2): Bahodir — kutilgan 1 500 000, farq −50 000; Malika — 20 kun kechikkan.
    bah = kk_cash_close(50000000, [{"kind": "SALE", "wallet": "CASH", "amount": "320000000"}, {"kind": "EXPENSE", "wallet": "CASH", "amount": "40000000"},
                                   {"kind": "OWNER_DRAW", "wallet": "CASH", "amount": "30000000"},
                                   {"kind": "TRANSFER", "wallet": "CASH", "toWallet": "CARD", "amount": "150000000"}], 145000000, "UNKNOWN", [])
    assert (bah["expected"], bah["difference"]) == ("150000000", "-5000000")
    mal = kk_credit_sale(66000000, 60000000, 3, date(2026, 11, 10), [{"kind": "PAYMENT", "date": "2026-11-10", "amount": "22000000"}], date(2026, 12, 30))
    assert (mal["status"], mal["overdueDays"], mal["outstanding"]) == ("OVERDUE", 20, "44000000")
    # K3 (kasbkor/SPEC 4.5): qolgan 2 580 000 → 774 000 / 1 290 000 / 516 000.
    nil = kk_month_close(1800000000, 970000000, 20000000, 500000000, 500000000, {"base": "REVENUE", "bp": 400},
                         {"reserveBp": 3000, "workingBp": 5000, "expansionBp": 2000, "sadaqaBp": 0}, False)
    assert (nil["tax"], nil["remaining"]) == ("72000000", "258000000")
    assert nil["allocation"] == {"reserve": "77400000", "working": "129000000", "expansion": "51600000", "sadaqa": "0"}
    # K6 (kasbkor/SPEC 7.2): Sardor — 1 000 000 avans dekabrdan 2 oyda; haqsiz oyda ushlanmagani keyingi oyga.
    sar = kk_payroll([{"salary": "300000000", "paid": ["300000000"]}, {"salary": "300000000", "paid": ["250000000"]},
                      {"salary": "300000000", "paid": ["250000000"]}],
                     [{"id": "a1", "month": 0, "amount": "100000000", "installments": 2, "startMonth": 1}])
    assert [m["deducted"] for m in sar["months"]] == ["0", "50000000", "50000000"]
    assert sar["advances"][0]["outstanding"] == "0" and sar["months"][-1]["balance"] == "0"
    gap = kk_payroll([{"salary": "300000000"}, {"salary": "0"}, {"salary": "300000000"}],
                     [{"id": "a1", "month": 0, "amount": "100000000", "installments": 2, "startMonth": 1}])
    assert [m["deducted"] for m in gap["months"]] == ["0", "0", "100000000"]
    # K6 (SPEC 7.1 SUPPLY): 5 000 000 − 2 000 000 = 3 000 000; muddatdan 4 kun o'tdi — jarimasiz.
    sup = kk_supplier_balance([{"id": "d1", "on": "2026-11-01", "amount": "500000000", "dueDays": 30}],
                              [{"on": "2026-11-10", "amount": "200000000"}], date(2026, 12, 5))
    assert (sup["outstanding"], sup["overdue"], sup["deliveries"][0]["overdueDays"]) == ("300000000", "300000000", 4)
    # K7 (kasbkor/SPEC 8.3): baza 100 mln, nisob 93,5 mln → zakot 2 500 000 (shartli misol).
    zak = kk_zakat(9000000000, 1200000000, 800000000, 1000000000, 110000000, 85, True)
    assert (zak["base"], zak["nisab"], zak["zakat"]) == ("10000000000", "9350000000", "250000000")
    gate = kk_expansion_gate(3000000000, [800000000, 900000000, 850000000], 3, [1, 1, 1], 0, 0, 1000, False, False, True)
    assert gate["open"] and gate["requiredReserve"] == "2550000000"
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
    # U10: 20 mln qarz oyiga 2,4 mln bilan: 9 oy (8×2,4 = 19,2 mln), oxirgi oy 0,8 mln
    assert informal_debt_payoff(2000000000, date(2027, 5, 20), 240000000) == (9, date(2028, 1, 1))
    assert informal_debt_payoff(0, date(2027, 5, 20), 0) == (0, None)
    # U11: Nilufar Sobir Qodirovning 30 mln ulushini oyiga 3 mln dan sotib oladi — 10 oyda mustaqil.
    b = buyout_schedule(3000000000, 3000000000, 0, 10, 1, date(2026, 11, 30), 1, 800000000, 5000)
    assert (b["periods"], b["endDate"], b["rows"][1]["date"], b["rows"][-1]["buyerBp"]) == (10, "2027-08-30", "2026-12-30", 10000)
    assert [r["payment"] for r in buyout_schedule(100000001, 300000001, 200000000, 3, 2, date(2027, 1, 31), 3, None, 0)["rows"]] == ["66666668", "33333333"]
    r = partnership_rules("MUSHARAKA", [{"role": "CAPITAL_PROVIDER", "profitShareBp": 7000, "capitalItems": [{"amount": 40}]},
                                        {"role": "BOTH", "profitShareBp": 3000, "capitalItems": [{"amount": 60}]}],
                          None, "PROPORTIONAL_TO_CAPITAL", 12)
    assert (r["errors"], r["warnings"], r["lossShareBp"]) == ([], ["SILENT_PARTNER_SHARE_ABOVE_CAPITAL"], [4000, 6000])
    # U12: OQ-D1 misoli — 1-oy zarar 2 mln, 2-oy foyda 3 mln, 50/50: avval 2 mln kapitalga, 0,5 + 0,5.
    p2 = [{"id": "A", "role": "CAPITAL_PROVIDER", "profitShareBp": 5000, "capital": 800},
          {"id": "B", "role": "WORKER", "profitShareBp": 5000, "capital": 0}]
    l1 = venture_period("MUDARABA", p2, [{"kind": "EXPENSE", "amount": 200}], "CAPITAL_FIRST", [0, 0])
    assert (l1["shares"], l1["carriedAfter"], l1["capitalAfter"]) == (["-200", "0"], ["200", "0"], ["600", "0"])
    p2b = [dict(p2[0], capital=600), p2[1]]
    g2 = venture_period("MUDARABA", p2b, [{"kind": "INCOME", "amount": 300}], "CAPITAL_FIRST", [200, 0])
    assert (g2["recovered"], g2["shares"], g2["capitalAfter"]) == (["200", "0"], ["50", "50"], ["800", "0"])
    assert venture_period("MUDARABA", p2b, [{"kind": "INCOME", "amount": 300}], "PER_PERIOD", [0, 0])["shares"] == ["150", "150"]
    # CAPEX 8 mln: o'rtacha stsenariyda oyiga 2,5 mln → 4 oy; pessimistik 1 mln → 8 oy.
    i8 = venture_idea([500000000, 150000000, 150000000], [{"name": "PESSIMISTIC", "income": 400000000, "expense": 300000000},
                                                         {"name": "BASE", "income": 600000000, "expense": 350000000},
                                                         {"name": "OPTIMISTIC", "income": 800000000, "expense": 400000000}])
    assert [r["paybackMonths"] for r in i8["scenarios"]] == [8, 4, 2] and i8["capex"] == "800000000"
    assert offer_check({"guaranteed": "YES", "lossShared": "YES", "realActivity": "YES", "recruitment": "NO",
                        "urgency": "NO", "written": "YES", "licensed": "YES", "inspection": "YES",
                        "exitEasy": "YES"})["verdict"] == "RED"
    # U13: xeshlari qayta hisoblangan soxta yozuv faqat bayonnomadagi zanjir boshi bilan aniqlanadi.
    t1 = json.loads(json.dumps(CHAIN_ENTRIES))
    t1[0]["amount"]["minor"] = "1"
    assert verify_chain(t1, chain(t1)) is None
    assert review_protocol(t1, chain(t1), 2, CHAIN_HASHES[1])["status"] == "HEAD_MISMATCH"
    assert review_protocol(CHAIN_ENTRIES, CHAIN_HASHES, 3, CHAIN_HASHES[2]) == {"status": "INTACT", "firstBroken": None, "entriesAfter": 0}
    # K1 (kasbkor/SPEC 2.2, 5.1): «egasi oldi» foydani (pul oqimini) kamaytirmaydi, maoshdan hisoblanadi.
    r = kk_month_report(0, 0, 500000000, [{"kind": "SALE", "wallet": "CASH", "amount": "1800000000"},
                                          {"kind": "EXPENSE", "wallet": "CASH", "amount": "850000000"},
                                          {"kind": "OWNER_DRAW", "wallet": "CASH", "amount": "120000000"}])
    assert r["cashFlow"] == "950000000" and r["ownerPaid"] == "120000000" and r["salaryRemaining"] == "380000000"
    r = kk_month_report(50000000, 0, 0, [{"kind": "SALE", "wallet": "CASH", "amount": "320000000"},
                                         {"kind": "EXPENSE", "wallet": "CASH", "amount": "40000000"},
                                         {"kind": "OWNER_DRAW", "wallet": "CASH", "amount": "30000000"},
                                         {"kind": "TRANSFER", "wallet": "CASH", "toWallet": "CARD", "amount": "150000000"}])
    assert r["cash"] == "150000000" and r["card"] == "150000000" and r["overdrawn"] is None
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
