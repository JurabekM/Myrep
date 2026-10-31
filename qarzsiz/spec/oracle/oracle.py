#!/usr/bin/env python3
"""«Qarzsiz» — mustaqil Python oracle.

Kotlin yadrodan (android/core) alohida yozilgan ikkinchi implementatsiya. Oltin vektorlarning
`expected` maydonlari shu fayl bilan hisoblanadi; Kotlin testlari ularni aynan takrorlashi shart.

    python3 -I spec/oracle/oracle.py --selftest
    python3 -I spec/oracle/oracle.py --check spec/test-vectors
    python3 -I spec/oracle/oracle.py --generate spec/test-vectors   # expected'ni qayta yozadi

Faqat standart kutubxona. Pul — butun son (kichik birlik), foiz — bazis punkt.
"""
from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal
from pathlib import Path

BP = 10_000
MINOR = 100
MAX_MONTHS = 600
# Jami qoldiq boshlang'ichdan shuncha marta oshsa — qarz «portlayapti», simulyatsiya to'xtaydi.
BLOWUP_FACTOR = 10


# --- pul arifmetikasi -------------------------------------------------------

def mul_div_half_up(a: int, b: int, c: int) -> int:
    if c == 0:
        raise ZeroDivisionError
    num = a * b
    neg = (num < 0) != (c < 0)
    q, r = divmod(abs(num), abs(c))
    if 2 * r >= abs(c):
        q += 1
    return -q if neg else q


def mul_div_floor(a: int, b: int, c: int) -> int:
    assert a >= 0 and b >= 0 and c > 0
    return (a * b) // c


def monthly_interest(balance: int, rate_bp: int) -> int:
    if balance <= 0 or rate_bp <= 0:
        return 0
    return mul_div_half_up(balance, rate_bp, 12 * BP)


def debt_budget(income: int, share_bp: int) -> int:
    if income <= 0:
        return 0
    return mul_div_half_up(income, max(0, min(share_bp, BP)), BP)


def safe_share_bp(income: int, living: int) -> int:
    if income <= 0:
        return 0
    free = income - max(living, 0)
    if free <= 0:
        return 0
    return mul_div_floor(free, BP, income)


def to_uzs(amount: int, rate_minor_per_unit: int) -> int:
    return mul_div_half_up(amount, rate_minor_per_unit, MINOR)


# --- rejalovchi -------------------------------------------------------------

def _order(debts, bal, strategy):
    idx = [i for i in range(len(debts)) if bal[i] > 0]
    if strategy == "AVALANCHE":
        key = lambda i: (-debts[i]["annualRateBp"], bal[i], debts[i]["id"])
    elif strategy == "SNOWBALL":
        key = lambda i: (bal[i], -debts[i]["annualRateBp"], debts[i]["id"])
    else:  # PRO_RATA, MINIMUM_ONLY
        key = lambda i: (-bal[i], debts[i]["id"])
    return sorted(idx, key=key)


def simulate(debts, budget: int, strategy: str, max_months: int = MAX_MONTHS):
    n = len(debts)
    bal = [max(d["balance"], 0) for d in debts]
    payoff = [None] * n
    first = [0] * n
    shortfall = False
    total_interest = 0
    total_paid = 0
    month = 0
    limit = sum(bal) * BLOWUP_FACTOR
    while any(b > 0 for b in bal) and month < max_months:
        month += 1
        for i in range(n):
            if bal[i] > 0:
                it = monthly_interest(bal[i], debts[i]["annualRateBp"])
                bal[i] += it
                total_interest += it
        pay = [0] * n
        req = [min(max(debts[i]["minPayment"], 0), bal[i]) for i in range(n)]
        sum_req = sum(req)
        if strategy == "MINIMUM_ONLY":
            pay = list(req)
            extra = 0
        elif sum_req > budget:
            if month == 1:
                shortfall = True
            b = max(budget, 0)
            pay = [mul_div_floor(b, req[i], sum_req) for i in range(n)]
            left = b - sum(pay)
            for i in _order(debts, bal, strategy):
                if left == 0:
                    break
                if pay[i] < req[i]:
                    pay[i] += 1
                    left -= 1
            extra = 0
        else:
            pay = list(req)
            extra = budget - sum_req
        for i in range(n):
            bal[i] -= pay[i]

        if extra > 0:
            if strategy in ("AVALANCHE", "SNOWBALL"):
                for i in _order(debts, bal, strategy):
                    if extra == 0:
                        break
                    p = min(extra, bal[i])
                    bal[i] -= p
                    pay[i] += p
                    extra -= p
            elif strategy == "PRO_RATA":
                total = sum(bal)
                if total > 0:
                    if extra >= total:
                        for i in range(n):
                            pay[i] += bal[i]
                            bal[i] = 0
                    else:
                        share = [mul_div_floor(extra, bal[i], total) for i in range(n)]
                        for i in range(n):
                            bal[i] -= share[i]
                            pay[i] += share[i]
                        rem = extra - sum(share)
                        for i in _order(debts, bal, strategy):
                            if rem == 0:
                                break
                            bal[i] -= 1
                            pay[i] += 1
                            rem -= 1

        total_paid += sum(pay)
        if month == 1:
            first = list(pay)
        for i in range(n):
            if bal[i] == 0 and payoff[i] is None:
                payoff[i] = month
        if sum(bal) > limit:
            break
    for i in range(n):
        if bal[i] == 0 and payoff[i] is None:
            payoff[i] = 0
    return {
        "months": month,
        "finished": all(b == 0 for b in bal),
        "totalInterest": total_interest,
        "totalPaid": total_paid,
        "payoffMonth": payoff,
        "firstMonth": first,
        "shortfall": shortfall,
    }


# --- bo'lib to'lash kalkulyatori -------------------------------------------

CTX = Context(prec=50, rounding=ROUND_HALF_EVEN)
ITERATIONS = 120


def _pv(pmt: Decimal, n: int, r: Decimal) -> Decimal:
    d = CTX.divide(Decimal(1), CTX.add(Decimal(1), r))
    p = Decimal(1)
    acc = Decimal(0)
    for _ in range(n):
        p = CTX.multiply(p, d)
        acc = CTX.add(acc, p)
    return CTX.multiply(acc, pmt)


def _monthly_rate(financed: int, pmt: int, n: int) -> Decimal:
    f = Decimal(financed)
    pm = Decimal(pmt)
    lo, hi = Decimal(0), Decimal(1)
    guard = 0
    while _pv(pm, n, hi) > f and guard < 30:
        hi = CTX.multiply(hi, Decimal(2))
        guard += 1
    for _ in range(ITERATIONS):
        mid = CTX.divide(CTX.add(lo, hi), Decimal(2))
        if _pv(pm, n, mid) > f:
            lo = mid
        else:
            hi = mid
    return CTX.divide(CTX.add(lo, hi), Decimal(2))


def installment(cash: int, down: int, monthly: int, months: int):
    financed = cash - down
    total = down + monthly * months
    overpay = total - cash
    overpay_bp = 0 if cash <= 0 else mul_div_half_up(overpay, BP, cash)
    if financed <= 0 or monthly * months <= financed:
        nominal = effective = 0
    else:
        r = _monthly_rate(financed, monthly, months)
        nominal = int(CTX.multiply(r, Decimal(120_000)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        g = Decimal(1)
        one_plus = CTX.add(Decimal(1), r)
        for _ in range(12):
            g = CTX.multiply(g, one_plus)
        effective = int(CTX.multiply(CTX.subtract(g, Decimal(1)), Decimal(BP))
                        .quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return {
        "financed": financed,
        "totalPaid": total,
        "overpay": overpay,
        "overpayBp": overpay_bp,
        "nominalAnnualBp": nominal,
        "effectiveAnnualBp": effective,
    }


# --- vektorlar ---------------------------------------------------------------

def compute(suite: str, inp: dict):
    if suite == "interest":
        return monthly_interest(inp["balance"], inp["annualRateBp"])
    if suite == "budget":
        return {
            "debtBudget": debt_budget(inp["income"], inp["shareBp"]),
            "safeShareBp": safe_share_bp(inp["income"], inp["livingMinimum"]),
        }
    if suite == "fx":
        return to_uzs(inp["amount"], inp["rate"])
    if suite == "planner":
        return simulate(inp["debts"], inp["budget"], inp["strategy"])
    if suite == "installment":
        return installment(inp["cash"], inp["down"], inp["monthly"], inp["months"])
    raise ValueError(f"noma'lum suite: {suite}")


def _files(directory: Path):
    return sorted(directory.glob("*.json"))


def generate(directory: Path) -> None:
    for f in _files(directory):
        data = json.loads(f.read_text(encoding="utf-8"))
        for case in data["cases"]:
            case["expected"] = compute(data["suite"], case["input"])
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"yozildi: {f.name} ({len(data['cases'])} case)")


def check(directory: Path) -> int:
    bad = 0
    total = 0
    for f in _files(directory):
        data = json.loads(f.read_text(encoding="utf-8"))
        for case in data["cases"]:
            total += 1
            got = compute(data["suite"], case["input"])
            if got != case.get("expected"):
                bad += 1
                print(f"XATO {f.name}:{case['name']}\n  kutilgan: {case.get('expected')}\n  oracle:   {got}")
    print(f"{total} case, {bad} xato")
    return 1 if bad else 0


def selftest() -> int:
    assert mul_div_half_up(5, 1, 2) == 3
    assert mul_div_half_up(-5, 1, 2) == -3
    assert mul_div_half_up(4, 1, 3) == 1
    assert monthly_interest(1_200_000, 2400) == 24_000
    assert debt_budget(10_000_000, 7000) == 7_000_000
    assert safe_share_bp(10_000_000, 4_000_000) == 6000
    assert to_uzs(100, 1_265_000) == 1_265_000
    # Bitta foizsiz qarz: 1000 / oyiga 300 → 4 oy, oxirgi oy 100.
    r = simulate([{"id": "a", "balance": 1000, "annualRateBp": 0, "minPayment": 300}], 300, "AVALANCHE")
    assert r["months"] == 4 and r["finished"] and r["totalPaid"] == 1000, r
    # Byudjet foiz o'sishiga yetmaydi → tugamaydi.
    r = simulate([{"id": "a", "balance": 1_000_000, "annualRateBp": 12000, "minPayment": 1}], 5000, "AVALANCHE")
    assert not r["finished"] and r["months"] < MAX_MONTHS
    # Ustamasiz nasiya: yashirin foiz 0.
    assert installment(1200, 0, 100, 12)["nominalAnnualBp"] == 0
    # 1000 → 2000 (36 oy): annuitet omili 18 → oyiga ~4,36%, yillik nominal ~52%.
    x = installment(100_000, 0, 5556, 36)
    assert 5150 < x["nominalAnnualBp"] < 5300, x
    print("selftest: OK")
    return 0


def main(argv) -> int:
    if len(argv) >= 2 and argv[1] == "--selftest":
        return selftest()
    if len(argv) >= 3 and argv[1] == "--check":
        return check(Path(argv[2]))
    if len(argv) >= 3 and argv[1] == "--generate":
        generate(Path(argv[2]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
