use baraka_agreements::{check_completeness, AgreementDraft, AgreementType};
use baraka_domain_common::WEEK_ANCHOR;
use baraka_domain_kasbkor::owner::{month_report, Move, MoveKind, Wallet};
use baraka_domain_uy::{
    amortization::{simulate, LoanTerms, ScheduleKind},
    audit::{unexplained_gap, GapInput},
    ceremony::{informal_debt_payoff, scenario_totals, BudgetLine, FundingSource, LineKind},
    debt::{
        build_plan, debt_load_bp, goal_coverage_bp, plan_status, plan_total, true_cost, PlanKind,
        PlanLine, PlanSpec, TrueCostInput,
    },
    emergency::emergency_target,
    gate::{evaluate_gate, GateInput, GatePolicy, InterestDebtPolicy},
    inflation::{personal_index, BasketPoint},
    partnership::{
        buyout_schedule, check_rules, distribute, BuyoutInput, CapitalItem, CapitalKind,
        DistributionInput, LossRule, Negligence, Partner, PartnerRole, PartnerTerms,
        PartnershipKind, RulesInput,
    },
    payoff::{
        default_order, payoff_plan, Amortizing, BankTerms, DebtState, OrderKey, Payment, PlanDebt,
        Scheduled,
    },
    recovery::RecoverySplit,
    review::check_protocol,
    spike::{profit_spike, SpikePolicy},
    streak::compute_streak,
    venture::{
        close_period, offer_check, venture_idea, BuyoutDue, EntryKind as VentureEntryKind,
        IdeaInput, IdeaScenario, Installment, LossPolicy, OfferAnswers, PeriodEntry, PeriodInput,
        Reply, ScenarioName,
    },
};
use baraka_journal::{
    compute_chain, short_code, verify_chain, ChainError, EntryKind, JournalAmount, JournalEntry,
};
use baraka_money::{
    allocate_minor, convert, format_minor, percent_of, round_half_up, Currency, FxRate, Locale,
    Money,
};
use chrono::NaiveDate;
use serde_json::{json, Value};

/// Runner ichidagi xato: vektor fayli noto'g'ri yoki domen xatosi.
struct E(String);

impl From<baraka_money::MoneyError> for E {
    fn from(e: baraka_money::MoneyError) -> Self {
        E(e.code().to_string())
    }
}

impl From<baraka_domain_common::DomainError> for E {
    fn from(e: baraka_domain_common::DomainError) -> Self {
        E(e.code.to_string())
    }
}

type R = Result<Value, E>;

fn bad(what: &str) -> E {
    E(format!("BAD_VECTOR:{what}"))
}

fn s<'a>(v: &'a Value, k: &str) -> Result<&'a str, E> {
    v[k].as_str().ok_or_else(|| bad(k))
}

fn i(v: &Value, k: &str) -> Result<i64, E> {
    v[k].as_i64().ok_or_else(|| bad(k))
}

fn b(v: &Value, k: &str) -> Result<bool, E> {
    v[k].as_bool().ok_or_else(|| bad(k))
}

fn int_str(v: &Value) -> Result<i64, E> {
    v.as_str()
        .and_then(|t| t.parse().ok())
        .ok_or_else(|| bad("int-string"))
}

fn cur(v: &Value, k: &str) -> Result<Currency, E> {
    Ok(Currency::from_code(s(v, k)?)?)
}

fn money(v: &Value, k: &str, c: Currency) -> Result<Money, E> {
    Ok(Money::new(int_str(&v[k])?, c))
}

fn strs(ms: &[Money]) -> Value {
    json!(ms.iter().map(|m| m.minor().to_string()).collect::<Vec<_>>())
}

fn date(v: &Value) -> Result<NaiveDate, E> {
    v.as_str()
        .and_then(|t| NaiveDate::parse_from_str(t, "%Y-%m-%d").ok())
        .ok_or_else(|| bad("date"))
}

pub fn run(suite: &str, input: &Value) -> Value {
    let r = match suite {
        "allocate" => allocate(input),
        "percent_of" => percent(input),
        "round" => round(input),
        "fx_convert" => fx(input),
        "money_format" => fmt(input),
        "amortization" => amort(input),
        "emergency_target" => emergency(input),
        "personal_inflation" => inflation(input),
        "unexplained_gap" => gap(input),
        "profit_spike" => spike(input),
        "profit_distribution" => distribution(input),
        "debt_recovery_split" => recovery(input),
        "journal_chain" => journal(input),
        "readiness_gate" => gate(input),
        "streak" => streak(input),
        "agreement_completeness" => agreement(input),
        "debt_plan" => debt_plan(input),
        "debt_status" => debt_status(input),
        "debt_load" => debt_load(input),
        "payoff_projection" => projection(input),
        "payoff_plan" => plan_all(input),
        "ceremony_scenarios" => ceremony(input),
        "partnership_rules" => partnership_rules(input),
        "buyout_schedule" => buyout(input),
        "venture_period" => venture_period(input),
        "venture_idea" => idea(input),
        "offer_check" => offer(input),
        "review_protocol" => protocol(input),
        "kk_owner_pay" => kk_owner_pay(input),
        other => Err(E(format!("UNKNOWN_SUITE:{other}"))),
    };
    r.unwrap_or_else(|E(code)| json!({ "error": code }))
}

fn allocate(v: &Value) -> R {
    let ratios: Vec<i64> = v["ratios"]
        .as_array()
        .ok_or_else(|| bad("ratios"))?
        .iter()
        .filter_map(Value::as_i64)
        .collect();
    let parts = allocate_minor(int_str(&v["total"])?, &ratios)?;
    Ok(json!({ "parts": parts.iter().map(i64::to_string).collect::<Vec<_>>() }))
}

fn percent(v: &Value) -> R {
    let c = cur(v, "currency")?;
    Ok(json!({ "result": percent_of(money(v, "amount", c)?, i(v, "bp")?)?.minor().to_string() }))
}

fn round(v: &Value) -> R {
    let r = round_half_up(
        i128::from(int_str(&v["num"])?),
        i128::from(int_str(&v["den"])?),
    )?;
    Ok(json!({ "result": r.to_string() }))
}

fn fx(v: &Value) -> R {
    let rate = FxRate {
        from: cur(v, "rateFrom")?,
        to: cur(v, "rateTo")?,
        rate_num: int_str(&v["rateNum"])?,
        rate_den: int_str(&v["rateDen"])?,
    };
    let r = convert(money(v, "amount", cur(v, "currency")?)?, &rate)?;
    Ok(json!({ "result": r.minor().to_string(), "currency": r.currency().code() }))
}

fn fmt(v: &Value) -> R {
    let locale = Locale::from_tag(s(v, "locale")?).ok_or_else(|| bad("locale"))?;
    let text = format_minor(int_str(&v["amount"])?, cur(v, "currency")?, locale);
    let hex: String = text.as_bytes().iter().map(|b| format!("{b:02x}")).collect();
    Ok(json!({ "text": text, "utf8Hex": hex }))
}

fn amort(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let terms = LoanTerms {
        principal: money(v, "principal", c)?,
        annual_bp: i(v, "annualBp")?,
        months: u32::try_from(i(v, "months")?).map_err(|_| bad("months"))?,
        kind: ScheduleKind::Annuity,
    };
    let s = simulate(&terms, money(v, "extraPerMonth", c)?)?;
    let rows: Vec<Value> = s
        .rows
        .iter()
        .map(|r| {
            json!({
                "month": r.month,
                "interest": r.interest.minor().to_string(),
                "principal": r.principal.minor().to_string(),
                "extra": r.extra.minor().to_string(),
                "balance": r.balance.minor().to_string(),
            })
        })
        .collect();
    Ok(json!({
        "payment": s.payment.minor().to_string(),
        "months": s.months(),
        "totalInterest": s.total_interest.minor().to_string(),
        "schedule": rows,
    }))
}

fn emergency(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let months: Result<Vec<Money>, E> = v["monthlyEssentials"]
        .as_array()
        .ok_or_else(|| bad("monthlyEssentials"))?
        .iter()
        .map(|m| Ok(Money::new(int_str(m)?, c)))
        .collect();
    let n = u32::try_from(i(v, "months")?).map_err(|_| bad("months"))?;
    Ok(json!({ "target": emergency_target(&months?, n)?.minor().to_string() }))
}

fn inflation(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let items: Result<Vec<BasketPoint>, E> = v["items"]
        .as_array()
        .ok_or_else(|| bad("items"))?
        .iter()
        .map(|it| {
            Ok(BasketPoint {
                weight_bp: i(it, "weightBp")?,
                old_price: money(it, "oldPrice", c)?,
                new_price: money(it, "newPrice", c)?,
            })
        })
        .collect();
    let (changes, index) = personal_index(&items?)?;
    Ok(json!({ "changesBp": changes, "indexBp": index }))
}

fn gap(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let g = unexplained_gap(&GapInput {
        income: money(v, "income", c)?,
        obligations_paid: money(v, "obligations", c)?,
        expenses: money(v, "expenses", c)?,
        vault_net: money(v, "vaultNet", c)?,
        balance_delta: money(v, "balanceDelta", c)?,
    })?;
    Ok(json!({ "gap": g.minor().to_string() }))
}

fn spike(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let plan = if v["plan"].is_null() {
        None
    } else {
        Some(money(v, "plan", c)?)
    };
    let last_three = match v["lastThree"].as_array() {
        None => None,
        Some(a) => {
            let m: Result<Vec<Money>, E> =
                a.iter().map(|x| Ok(Money::new(int_str(x)?, c))).collect();
            Some(<[Money; 3]>::try_from(m?).map_err(|_| bad("lastThree"))?)
        }
    };
    let alert = profit_spike(
        plan,
        last_three,
        money(v, "actual", c)?,
        SpikePolicy::default(),
    )?;
    Ok(json!({ "alert": alert }))
}

fn distribution(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let kind = match s(v, "kind")? {
        "MUDARABA" => PartnershipKind::Mudaraba,
        "MUSHARAKA" => PartnershipKind::Musharaka,
        _ => return Err(bad("kind")),
    };
    let partners: Result<Vec<Partner>, E> = v["partners"]
        .as_array()
        .ok_or_else(|| bad("partners"))?
        .iter()
        .map(|p| {
            Ok(Partner {
                id: s(p, "id")?.to_string(),
                role: match s(p, "role")? {
                    "CAPITAL_PROVIDER" => PartnerRole::CapitalProvider,
                    "WORKER" => PartnerRole::Worker,
                    "BOTH" => PartnerRole::Both,
                    _ => return Err(bad("role")),
                },
                profit_share_bp: i(p, "profitShareBp")?,
                capital: money(p, "capital", c)?,
            })
        })
        .collect();
    let input = DistributionInput {
        kind,
        result: money(v, "result", c)?,
        partners: partners?,
        negligence: if v["negligence"].is_null() {
            None
        } else {
            Some(Negligence {
                partner_id: s(&v["negligence"], "partnerId")?.to_string(),
                note: s(&v["negligence"], "note")?.to_string(),
            })
        },
        fixed_return: if v["fixedReturn"].is_null() {
            None
        } else {
            Some(money(v, "fixedReturn", c)?)
        },
    };
    Ok(json!({ "parts": strs(&distribute(&input)?) }))
}

fn recovery(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let split = RecoverySplit {
        household_bp: i(v, "householdBp")?,
        extra_debt_bp: i(v, "extraDebtBp")?,
        savings_bp: i(v, "savingsBp")?,
    };
    let p = split.apply(money(v, "income", c)?)?;
    Ok(json!({
        "household": p.household.minor().to_string(),
        "extraDebt": p.extra_debt.minor().to_string(),
        "savings": p.savings.minor().to_string(),
    }))
}

fn opt_str(v: &Value, k: &str) -> Option<String> {
    v[k].as_str().map(str::to_string)
}

fn entry(v: &Value) -> Result<JournalEntry, E> {
    Ok(JournalEntry {
        id: s(v, "id")?.to_string(),
        agreement_id: s(v, "agreementId")?.to_string(),
        kind: EntryKind::parse(s(v, "kind")?).ok_or_else(|| bad("kind"))?,
        party_id: opt_str(v, "partyId"),
        amount: match v.get("amount") {
            None => None,
            Some(a) => Some(JournalAmount {
                minor: int_str(&a["minor"])?,
                currency: s(a, "currency")?.to_string(),
            }),
        },
        date: s(v, "date")?.to_string(),
        note: opt_str(v, "note"),
        corrects_entry_id: opt_str(v, "correctsEntryId"),
        refs: v["refs"]
            .as_array()
            .map(|a| {
                a.iter()
                    .filter_map(|r| r.as_str().map(str::to_string))
                    .collect()
            })
            .unwrap_or_default(),
    })
}

fn journal(v: &Value) -> R {
    let entries: Result<Vec<JournalEntry>, E> = v["entries"]
        .as_array()
        .ok_or_else(|| bad("entries"))?
        .iter()
        .map(entry)
        .collect();
    let entries = entries?;
    if let Some(stored) = v["storedHashes"].as_array() {
        let stored: Vec<String> = stored
            .iter()
            .filter_map(|h| h.as_str().map(str::to_string))
            .collect();
        return Ok(match verify_chain(&entries, &stored) {
            Ok(head) => json!({ "head": head }),
            Err(ChainError::FirstBroken { seq }) => json!({ "firstBroken": seq }),
            Err(e) => json!({ "error": e.code() }),
        });
    }
    let hashes = compute_chain(&entries).map_err(|e| E(e.code().to_string()))?;
    let mut out = json!({ "hashes": hashes });
    if v["withShortCodes"].as_bool() == Some(true) {
        out["shortCodes"] = json!(hashes.iter().map(|h| short_code(h)).collect::<Vec<_>>());
    }
    Ok(out)
}

fn gate(v: &Value) -> R {
    let policy = GatePolicy {
        interest_debt: match s(v, "policy")? {
            "ALLOW_WITH_PLAN" => InterestDebtPolicy::AllowWithPlan,
            "BLOCK_UNTIL_PAID" => InterestDebtPolicy::BlockUntilPaid,
            _ => return Err(bad("policy")),
        },
        ..GatePolicy::default()
    };
    let r = evaluate_gate(
        GateInput {
            coverage_centi_months: i(v, "coverageCentiMonths")?,
            has_interest_debt: b(v, "hasInterestDebt")?,
            has_payoff_plan: b(v, "hasPayoffPlan")?,
        },
        policy,
    );
    Ok(json!({ "open": r.open, "reasons": r.reasons.iter().map(|x| x.code()).collect::<Vec<_>>() }))
}

fn streak(v: &Value) -> R {
    let deposits: Result<Vec<NaiveDate>, E> = v["deposits"]
        .as_array()
        .ok_or_else(|| bad("deposits"))?
        .iter()
        .map(date)
        .collect();
    let st = compute_streak(&deposits?, date(&v["today"])?, WEEK_ANCHOR);
    Ok(json!({
        "currentWeeks": st.current_weeks,
        "longestWeeks": st.longest_weeks,
        "totalWeeks": st.total_weeks,
        "currentWeekDone": st.current_week_done,
    }))
}

fn agreement(v: &Value) -> R {
    let kind: AgreementType = serde_json::from_value(v["type"].clone()).map_err(|_| bad("type"))?;
    let draft: AgreementDraft = serde_json::from_value(v["draft"].clone())
        .map_err(|e| E(format!("BAD_VECTOR:draft:{e}")))?;
    let c = check_completeness(kind, &draft);
    serde_json::to_value(c).map_err(|_| bad("completeness"))
}

fn opt_money(v: &Value, k: &str, c: Currency) -> Result<Money, E> {
    if v[k].is_null() {
        Ok(Money::zero(c))
    } else {
        money(v, k, c)
    }
}

fn plan_lines(v: &Value, c: Currency) -> Result<Vec<PlanLine>, E> {
    v["lines"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or_default()
        .iter()
        .map(|l| {
            Ok(PlanLine {
                date: date(&l["date"])?,
                amount: money(l, "amount", c)?,
            })
        })
        .collect()
}

fn lines_json(lines: &[PlanLine]) -> Value {
    json!(lines
        .iter()
        .map(|l| json!({ "date": l.date.to_string(), "amount": l.amount.minor().to_string() }))
        .collect::<Vec<_>>())
}

fn debt_plan(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let spec = PlanSpec {
        kind: PlanKind::parse(s(v, "kind")?).ok_or_else(|| bad("kind"))?,
        principal: money(v, "principal", c)?,
        markup: opt_money(v, "markup", c)?,
        annual_bp: v["annualBp"].as_i64().unwrap_or(0),
        months: u32::try_from(v["months"].as_i64().unwrap_or(0)).map_err(|_| bad("months"))?,
        first_date: date(&v["firstDate"])?,
        lines: plan_lines(v, c)?,
    };
    let lines = build_plan(&spec)?;
    let total = plan_total(&lines, c)?;
    let original = if v["originalPrincipal"].is_null() {
        None
    } else {
        Some(money(v, "originalPrincipal", c)?)
    };
    let tc = true_cost(&TrueCostInput {
        principal: spec.principal,
        original_principal: original,
        paid_before: opt_money(v, "paidBefore", c)?,
        plan_total: total,
        paid_since: opt_money(v, "paidSince", c)?,
    })?;
    let goals = v["goals"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or_default()
        .iter()
        .map(|g| Ok(goal_coverage_bp(tc.overpay, Money::new(int_str(g)?, c))?))
        .collect::<Result<Vec<i64>, E>>()?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "lines": lines_json(&lines),
        "planTotal": m(total),
        "trueCost": {
            "originalPrincipal": m(tc.original_principal),
            "totalCost": m(tc.total_cost),
            "overpay": m(tc.overpay),
            "overpayBp": tc.overpay_bp,
            "paidTotal": m(tc.paid_total),
            "remaining": m(tc.remaining),
            "goalsBp": goals,
        },
    }))
}

fn debt_status(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let st = plan_status(
        &plan_lines(v, c)?,
        money(v, "paid", c)?,
        opt_money(v, "prepaid", c)?,
        date(&v["today"])?,
    )?;
    Ok(json!({
        "remaining": st.remaining.minor().to_string(),
        "nextDate": st.next.map(|n| n.date.to_string()),
        "nextAmount": st.next.map(|n| n.amount.minor().to_string()),
        "overdue": st.overdue.minor().to_string(),
        "payoffDate": st.payoff_date.map(|d| d.to_string()),
        "reminder": st.reminder.map(|r| r.as_str()),
    }))
}

fn debt_load(v: &Value) -> R {
    let c = cur(v, "currency")?;
    Ok(json!({ "loadBp": debt_load_bp(money(v, "payments", c)?, money(v, "income", c)?)? }))
}

fn debt_state(debt: &Value, payments: &Value, c: Currency) -> Result<DebtState, E> {
    let pays = payments
        .as_array()
        .ok_or_else(|| bad("payments"))?
        .iter()
        .map(|p| {
            Ok(Payment {
                date: date(&p["date"])?,
                amount: money(p, "amount", c)?,
                prepayment: b(p, "prepayment")?,
            })
        })
        .collect::<Result<Vec<_>, E>>()?;
    Ok(match s(debt, "kind")? {
        k @ ("ANNUITY" | "DIFFERENTIATED") => DebtState::Amortizing(Amortizing::replay(
            &BankTerms {
                differentiated: k == "DIFFERENTIATED",
                principal: money(debt, "principal", c)?,
                annual_bp: i(debt, "annualBp")?,
                months: u32::try_from(i(debt, "months")?).map_err(|_| bad("months"))?,
                first_date: date(&debt["firstDate"])?,
            },
            &pays,
        )?),
        _ => DebtState::Scheduled(Scheduled::new(&plan_lines(debt, c)?, &pays)?),
    })
}

fn iso(d: Option<NaiveDate>) -> Value {
    d.map_or(Value::Null, |d| json!(d.to_string()))
}

fn projection(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let state = debt_state(&v["debt"], &v["payments"], c)?;
    let st = json!({
        "balance": state.balance().minor().to_string(),
        "nextDate": iso(state.next_date()?),
    });
    let (p, _) = payoff_plan(
        vec![PlanDebt {
            id: "d".into(),
            state,
            fee_bp: i(v, "prepaymentFeeBp")?,
        }],
        date(&v["today"])?,
        money(v, "extraPerMonth", c)?,
    )?;
    let p = p.into_iter().next().ok_or_else(|| bad("projection"))?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "state": st,
        "rows": p.rows.iter().map(|r| json!({
            "date": r.date.to_string(), "due": m(r.due), "interest": m(r.interest),
            "extra": m(r.extra), "fee": m(r.fee), "balance": m(r.balance),
        })).collect::<Vec<_>>(),
        "months": p.months,
        "payoffDate": iso(p.payoff_date),
        "totalInterest": m(p.interest),
        "totalFees": m(p.fees),
        "totalPaid": m(p.paid),
    }))
}

fn plan_all(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let today = date(&v["today"])?;
    let items = v["debts"].as_array().ok_or_else(|| bad("debts"))?;
    let build = |d: &Value| -> Result<PlanDebt, E> {
        Ok(PlanDebt {
            id: s(d, "id")?.to_string(),
            state: debt_state(&d["debt"], &d["payments"], c)?,
            fee_bp: i(d, "prepaymentFeeBp")?,
        })
    };
    let mut keys = Vec::new();
    for d in items {
        let one = build(d)?;
        let (base, _) = payoff_plan(vec![one], today, Money::zero(c))?;
        keys.push(OrderKey {
            id: s(d, "id")?.to_string(),
            ribo: b(d, "ribo")?,
            cost_bp: i(d, "costBp")?,
            payoff_date: base.first().and_then(|p| p.payoff_date),
            priority: d["priority"].as_i64(),
        });
    }
    let order = default_order(&keys);
    let ordered = || -> Result<Vec<PlanDebt>, E> {
        order
            .iter()
            .map(|id| {
                let d = items
                    .iter()
                    .find(|d| d["id"].as_str() == Some(id))
                    .ok_or_else(|| bad("id"))?;
                build(d)
            })
            .collect()
    };
    let (_, base) = payoff_plan(ordered()?, today, Money::zero(c))?;
    let (per, acc) = payoff_plan(ordered()?, today, money(v, "poolPerMonth", c)?)?;
    let m = |x: Money| x.minor().to_string();
    let saved = base.interest.checked_sub(acc.interest)?;
    Ok(json!({
        "order": order,
        "base": {"payoffDate": iso(base.payoff_date), "months": base.months,
                 "totalInterest": m(base.interest), "totalFees": m(base.fees)},
        "accelerated": {
            "payoffDate": iso(acc.payoff_date), "months": acc.months,
            "totalInterest": m(acc.interest), "totalFees": m(acc.fees),
            "debts": per.iter().map(|p| json!({
                "id": p.id, "payoffDate": iso(p.payoff_date), "months": p.months,
                "interest": m(p.interest), "fees": m(p.fees),
            })).collect::<Vec<_>>(),
        },
        "monthsSaved": i64::from(base.months) - i64::from(acc.months),
        "interestSaved": m(saved),
        "netSaved": m(saved.checked_sub(acc.fees)?),
    }))
}

fn ceremony(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let start = date(&v["start"])?;
    let capacity = money(v, "monthlyCapacity", c)?;
    let scenarios = v["scenarios"].as_array().ok_or_else(|| bad("scenarios"))?;
    let mut totals = Vec::new();
    for sc in scenarios {
        let lines = sc["lines"]
            .as_array()
            .ok_or_else(|| bad("lines"))?
            .iter()
            .map(|l| {
                Ok(BudgetLine {
                    kind: LineKind::parse(s(l, "kind")?)
                        .ok_or_else(|| E("INVALID_LINE_KIND".into()))?,
                    amount: money(l, "amount", c)?,
                    source: FundingSource::parse(s(l, "source")?)
                        .ok_or_else(|| E("INVALID_SOURCE".into()))?,
                })
            })
            .collect::<Result<Vec<_>, E>>()?;
        totals.push(scenario_totals(&lines, i(sc, "guests")?, c)?);
    }
    let max = totals.iter().map(|t| t.total.minor()).max().unwrap_or(0);
    let goals: Vec<i64> = v["goals"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or_default()
        .iter()
        .map(int_str)
        .collect::<Result<_, _>>()?;
    let mut out = Vec::new();
    for (sc, t) in scenarios.iter().zip(&totals) {
        let pay = informal_debt_payoff(t.debt, start, capacity)?;
        let saved = Money::new(max, c).checked_sub(t.total)?;
        let gbp = goals
            .iter()
            .map(|g| {
                i64::try_from(round_half_up(
                    i128::from(saved.minor()) * 10_000,
                    i128::from(*g),
                )?)
                .map_err(|_| bad("overflow"))
            })
            .collect::<Result<Vec<_>, E>>()?;
        let m = |x: Money| x.minor().to_string();
        out.push(json!({
            "name": s(sc, "name")?,
            "total": m(t.total),
            "bySource": {
                "SAVINGS": m(t.savings), "FAMILY": m(t.family),
                "EXPECTED_GIFTS": m(t.expected_gifts), "DEBT": m(t.debt),
            },
            "payoffMonths": pay.map(|p| p.0),
            "payoffDate": pay.and_then(|p| p.1).map(|d| d.to_string()),
            "savedVsMax": m(saved),
            "goalsBp": gbp,
        }));
    }
    Ok(json!({ "scenarios": out }))
}

fn u(v: &Value, k: &str) -> Result<u32, E> {
    u32::try_from(i(v, k)?).map_err(|_| bad(k))
}

fn partnership_rules(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let kind = PartnershipKind::parse(s(v, "kind")?).ok_or_else(|| E("INVALID_KIND".into()))?;
    let partners = v["partners"]
        .as_array()
        .ok_or_else(|| bad("partners"))?
        .iter()
        .map(|p| {
            Ok(PartnerTerms {
                role: PartnerRole::parse(s(p, "role")?).ok_or_else(|| E("INVALID_ROLE".into()))?,
                profit_share_bp: i(p, "profitShareBp")?,
                capital_items: p["capitalItems"]
                    .as_array()
                    .ok_or_else(|| bad("capitalItems"))?
                    .iter()
                    .map(|x| {
                        Ok(CapitalItem {
                            kind: CapitalKind::parse(s(x, "kind")?).ok_or_else(|| bad("kind"))?,
                            description: s(x, "description")?.to_string(),
                            amount: money(x, "amount", c)?,
                        })
                    })
                    .collect::<Result<_, E>>()?,
            })
        })
        .collect::<Result<Vec<_>, E>>()?;
    let r = check_rules(&RulesInput {
        kind,
        currency: c,
        partners,
        fixed_return: if v["fixedReturn"].is_null() {
            None
        } else {
            Some(money(v, "fixedReturn", c)?)
        },
        loss_rule: LossRule::parse(s(v, "lossRule")?).ok_or_else(|| bad("lossRule"))?,
        duration_months: Some(u(v, "durationMonths")?),
    })?;
    Ok(json!({
        "errors": r.errors,
        "warnings": r.warnings,
        "capital": strs(&r.capital),
        "lossShareBp": r.loss_share_bp,
    }))
}

fn buyout(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let sch = buyout_schedule(&BuyoutInput {
        stake: money(v, "stake", c)?,
        total_capital: money(v, "totalCapital", c)?,
        buyer_capital: money(v, "buyerCapital", c)?,
        units: u(v, "units")?,
        units_per_period: u(v, "unitsPerPeriod")?,
        start: date(&v["start"])?,
        period_months: u(v, "periodMonths")?,
        expected_profit: if v["expectedProfit"].is_null() {
            None
        } else {
            Some(money(v, "expectedProfit", c)?)
        },
        buyer_share_bp: i(v, "buyerShareBp")?,
    })?;
    let rows: Vec<Value> = sch
        .rows
        .iter()
        .map(|r| {
            json!({
                "period": r.period,
                "date": r.date.to_string(),
                "units": r.units,
                "payment": r.payment.minor().to_string(),
                "remainingStake": r.remaining_stake.minor().to_string(),
                "sellerBp": r.seller_bp,
                "buyerBp": r.buyer_bp,
                "exceedsShare": r.exceeds_share,
            })
        })
        .collect();
    Ok(json!({
        "periods": rows.len(),
        "endDate": sch.end_date().map(|d| d.to_string()),
        "buyerProfit": sch.buyer_profit.map(|m| m.minor().to_string()),
        "rows": rows,
    }))
}

fn arr<'a>(v: &'a Value, k: &str) -> Result<&'a Vec<Value>, E> {
    v[k].as_array().ok_or_else(|| bad(k))
}

fn venture_period(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let kind = PartnershipKind::parse(s(v, "kind")?).ok_or_else(|| E("INVALID_KIND".into()))?;
    let policy =
        LossPolicy::parse(s(v, "lossPolicy")?).ok_or_else(|| E("INVALID_POLICY".into()))?;
    let partners = arr(v, "partners")?
        .iter()
        .map(|p| {
            Ok(Partner {
                id: s(p, "id")?.to_string(),
                role: PartnerRole::parse(s(p, "role")?).ok_or_else(|| E("INVALID_ROLE".into()))?,
                profit_share_bp: i(p, "profitShareBp")?,
                capital: money(p, "capital", c)?,
            })
        })
        .collect::<Result<Vec<_>, E>>()?;
    let entries = arr(v, "entries")?
        .iter()
        .map(|e| {
            Ok(PeriodEntry {
                kind: VentureEntryKind::parse(s(e, "kind")?)
                    .ok_or_else(|| E("INVALID_ENTRY_KIND".into()))?,
                amount: money(e, "amount", c)?,
            })
        })
        .collect::<Result<Vec<_>, E>>()?;
    let carried = arr(v, "carriedLoss")?
        .iter()
        .map(|x| Ok(Money::new(int_str(x)?, c)))
        .collect::<Result<Vec<_>, E>>()?;
    let negligence = if v["negligence"].is_null() {
        None
    } else {
        Some(Negligence {
            partner_id: s(&v["negligence"], "partnerId")?.to_string(),
            note: s(&v["negligence"], "note")?.to_string(),
        })
    };
    let buyout = if v["buyout"].is_null() {
        None
    } else {
        let b = &v["buyout"];
        Some(BuyoutDue {
            seller_id: s(b, "sellerId")?.to_string(),
            buyer_id: s(b, "buyerId")?.to_string(),
            due: arr(b, "due")?
                .iter()
                .map(|d| {
                    Ok(Installment {
                        no: u(d, "no")?,
                        units: u(d, "units")?,
                        capital: money(d, "capital", c)?,
                        price: money(d, "price", c)?,
                    })
                })
                .collect::<Result<_, E>>()?,
        })
    };
    let r = close_period(&PeriodInput {
        kind,
        currency: c,
        partners,
        entries,
        policy,
        carried,
        negligence,
        buyout,
    })?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "income": m(r.income),
        "expense": m(r.expense),
        "forceMajeure": m(r.force_majeure),
        "corrections": m(r.corrections),
        "result": m(r.result),
        "recovered": strs(&r.recovered),
        "distributable": m(r.distributable),
        "shares": strs(&r.shares),
        "liability": strs(&r.liability),
        "carriedAfter": strs(&r.carried_after),
        "buyout": r.buyout.map(|b| json!({
            "paid": b.paid,
            "amount": m(b.amount),
            "capital": m(b.capital),
            "unpaid": b.unpaid,
        })),
        "payouts": strs(&r.payouts),
        "capitalAfter": strs(&r.capital_after),
    }))
}

fn idea(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let capex = arr(v, "capex")?
        .iter()
        .map(|x| Ok(Money::new(int_str(x)?, c)))
        .collect::<Result<Vec<_>, E>>()?;
    let scenarios = arr(v, "scenarios")?
        .iter()
        .map(|x| {
            Ok(IdeaScenario {
                name: ScenarioName::parse(s(x, "name")?)
                    .ok_or_else(|| E("INVALID_SCENARIOS".into()))?,
                income: money(x, "income", c)?,
                expense: money(x, "expense", c)?,
            })
        })
        .collect::<Result<Vec<_>, E>>()?;
    let r = venture_idea(&IdeaInput {
        currency: c,
        capex,
        scenarios,
        worker_share_bp: v["workerShareBp"].as_i64(),
    })?;
    let partnered = !v["workerShareBp"].is_null();
    let rows: Vec<Value> = r
        .scenarios
        .iter()
        .map(|x| {
            let mut o = json!({
                "name": x.name.as_str(),
                "net": x.net.minor().to_string(),
                "annualNet": x.annual_net.minor().to_string(),
                "paybackMonths": x.payback_months,
            });
            if partnered {
                o["workerMonthly"] = json!(x.worker_monthly.map(|m| m.minor().to_string()));
                o["investorMonthly"] = json!(x.investor_monthly.map(|m| m.minor().to_string()));
                o["investorPaybackMonths"] = json!(x.investor_payback_months);
            }
            o
        })
        .collect();
    Ok(json!({
        "capex": r.capex.minor().to_string(),
        "scenarios": rows,
        "warnings": r.warnings,
    }))
}

fn offer(v: &Value) -> R {
    let a = &v["answers"];
    let q = |k: &str| -> Result<Reply, E> {
        let t = a[k].as_str().ok_or_else(|| E("MISSING_ANSWER".into()))?;
        Reply::parse(t).ok_or_else(|| E("INVALID_ANSWER".into()))
    };
    let r = offer_check(&OfferAnswers {
        guaranteed: q("guaranteed")?,
        loss_shared: q("lossShared")?,
        real_activity: q("realActivity")?,
        recruitment: q("recruitment")?,
        urgency: q("urgency")?,
        written: q("written")?,
    });
    let flags: Vec<Value> = r
        .flags
        .iter()
        .map(|f| json!({ "code": f.code, "level": f.level.as_str() }))
        .collect();
    Ok(json!({ "verdict": r.verdict.as_str(), "flags": flags }))
}

fn protocol(v: &Value) -> R {
    let entries = arr(v, "entries")?
        .iter()
        .map(entry)
        .collect::<Result<Vec<_>, E>>()?;
    let stored = arr(v, "storedHashes")?
        .iter()
        .map(|h| {
            h.as_str()
                .map(str::to_string)
                .ok_or_else(|| bad("storedHashes"))
        })
        .collect::<Result<Vec<_>, E>>()?;
    let seq = usize::try_from(i(v, "protocolSeq")?).map_err(|_| E("INVALID_PROTOCOL".into()))?;
    let r = check_protocol(&entries, &stored, seq, s(v, "protocolHead")?)?;
    let first = match r.status {
        baraka_domain_uy::review::ProtocolStatus::ChainBroken { seq } => json!(seq),
        _ => Value::Null,
    };
    Ok(json!({
        "status": r.status.as_str(),
        "firstBroken": first,
        "entriesAfter": r.entries_after,
    }))
}

fn kk_owner_pay(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let wallet = |m: &Value, k: &str| -> Result<Wallet, E> {
        Wallet::parse(s(m, k)?).ok_or_else(|| E("INVALID_WALLET".into()))
    };
    let mut moves = Vec::new();
    for m in v["moves"].as_array().ok_or_else(|| bad("moves"))? {
        let kind = match s(m, "kind")? {
            "SALE" => MoveKind::Sale,
            "EXPENSE" => MoveKind::Expense,
            "OWNER_DRAW" => MoveKind::OwnerDraw,
            "OWNER_CONTRIBUTION" => MoveKind::OwnerContribution,
            "OWNER_SALARY" => MoveKind::OwnerSalary,
            "TRANSFER" => MoveKind::Transfer {
                to: wallet(m, "toWallet")?,
            },
            _ => return Err(E("INVALID_KIND".into())),
        };
        moves.push(Move {
            kind,
            wallet: wallet(m, "wallet")?,
            amount: money(m, "amount", c)?,
        });
    }
    let r = month_report(
        c,
        money(v, "openingCash", c)?,
        money(v, "openingCard", c)?,
        money(v, "ownerSalary", c)?,
        &moves,
    )?;
    let opt = |m: Option<Money>| m.map(|m| m.minor().to_string());
    Ok(json!({
        "revenue": r.revenue.minor().to_string(),
        "expenses": r.expenses.minor().to_string(),
        "cashFlow": r.cash_flow.minor().to_string(),
        "ownerDraws": r.owner_draws.minor().to_string(),
        "ownerSalaryTransferred": r.owner_salary_transferred.minor().to_string(),
        "contributions": r.contributions.minor().to_string(),
        "ownerPaid": r.owner_paid.minor().to_string(),
        "salaryRemaining": opt(r.salary_remaining),
        "overdrawn": opt(r.overdrawn),
        "cash": r.cash.minor().to_string(),
        "card": r.card.minor().to_string(),
        "negativeWallets": r.negative_wallets.iter().map(|w| w.as_str()).collect::<Vec<_>>(),
    }))
}
