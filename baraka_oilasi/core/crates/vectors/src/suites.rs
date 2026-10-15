use baraka_agreements::{check_completeness, AgreementDraft, AgreementType};
use baraka_domain_common::WEEK_ANCHOR;
use baraka_domain_uy::{
    amortization::{simulate, LoanTerms, ScheduleKind},
    audit::{unexplained_gap, GapInput},
    debt::{
        build_plan, debt_load_bp, goal_coverage_bp, plan_status, plan_total, true_cost, PlanKind,
        PlanLine, PlanSpec, TrueCostInput,
    },
    emergency::emergency_target,
    gate::{evaluate_gate, GateInput, GatePolicy, InterestDebtPolicy},
    inflation::{personal_index, BasketPoint},
    partnership::{
        distribute, DistributionInput, Negligence, Partner, PartnerRole, PartnershipKind,
    },
    recovery::RecoverySplit,
    spike::{profit_spike, SpikePolicy},
    streak::compute_streak,
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
    let st = plan_status(&plan_lines(v, c)?, money(v, "paid", c)?, date(&v["today"])?)?;
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
