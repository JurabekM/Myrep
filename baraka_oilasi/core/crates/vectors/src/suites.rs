use baraka_agreements::{check_completeness, AgreementDraft, AgreementType};
use baraka_domain_common::WEEK_ANCHOR;
use baraka_domain_kasbkor::cash::{cash_close, CashReason};
use baraka_domain_kasbkor::close::{month_close, CloseInput, SplitRule, TaxRule};
use baraka_domain_kasbkor::credit::{CreditEvent, CreditTerms};
use baraka_domain_kasbkor::equipment::{Disposal, Equipment};
use baraka_domain_kasbkor::funds::{funds, Fund, FundEvent};
use baraka_domain_kasbkor::gate::{expansion_gate, GateInput as KkGateInput};
use baraka_domain_kasbkor::owner::{month_report, Move, MoveKind, Wallet};
use baraka_domain_kasbkor::payroll::{payroll, Advance, PayMonth};
use baraka_domain_kasbkor::profit::{true_profit, FamilyLabor, ProfitInput};
use baraka_domain_kasbkor::quote::{order_quote, QuoteInput};
use baraka_domain_kasbkor::shift::{shift_close, ShiftIn, ShiftInKind};
use baraka_domain_kasbkor::stock::{replacement, validate_factor, CostMethod, Stock, StockMove};
use baraka_domain_kasbkor::supply::{supplier_balance, Delivery, SupplyPayment};
use baraka_domain_kasbkor::zakat::{zakat, ZakatInput};
use baraka_domain_musofir::fund::return_fund;
use baraka_domain_musofir::month::{month_report as mf_month_report, MfKind, MfMove};
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
        "kk_depreciation" => kk_depreciation(input),
        "kk_true_profit" => kk_true_profit(input),
        "kk_order_quote" => kk_order_quote(input),
        "kk_month_close" => kk_month_close(input),
        "kk_cash_close" => kk_cash_close(input),
        "kk_credit_sale" => kk_credit_sale(input),
        "kk_cogs" => kk_cogs(input),
        "kk_replacement" => kk_replacement(input),
        "kk_payroll" => kk_payroll(input),
        "kk_supplier_balance" => kk_supplier_balance(input),
        "kk_expansion_gate" => kk_expansion_gate(input),
        "kk_zakat" => kk_zakat(input),
        "kk_funds" => kk_funds(input),
        "kk_shift_close" => kk_shift_close(input),
        "mf_month" => mf_month(input),
        "mf_return_fund" => mf_return_fund(input),
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
            "EQUIPMENT_PURCHASE" => MoveKind::EquipmentPurchase,
            "EQUIPMENT_SALE" => MoveKind::EquipmentSale,
            "CASH_SHORT" => MoveKind::CashShort,
            "CASH_OVER" => MoveKind::CashOver,
            "STOCK_PURCHASE" => MoveKind::StockPurchase,
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
        "equipmentPurchases": r.equipment_purchases.minor().to_string(),
        "equipmentSales": r.equipment_sales.minor().to_string(),
        "cashDifference": r.cash_difference.minor().to_string(),
        "stockPurchases": r.stock_purchases.minor().to_string(),
        "cash": r.cash.minor().to_string(),
        "card": r.card.minor().to_string(),
        "negativeWallets": r.negative_wallets.iter().map(|w| w.as_str()).collect::<Vec<_>>(),
    }))
}

fn month_index(v: &Value) -> Result<u32, E> {
    let m = v.as_i64().ok_or_else(|| bad("month"))?;
    u32::try_from(m).map_err(|_| E("INVALID_MONTH".into()))
}

fn kk_depreciation(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let disposal = if v["disposal"].is_null() {
        None
    } else {
        Some(Disposal {
            month: month_index(&v["disposal"]["month"])?,
            proceeds: money(&v["disposal"], "proceeds", c)?,
        })
    };
    let e = Equipment {
        cost: money(v, "cost", c)?,
        salvage: money(v, "salvage", c)?,
        useful_months: u32::try_from(i(v, "usefulMonths")?)
            .map_err(|_| E("INVALID_USEFUL_LIFE".into()))?,
        disposal,
    };
    let schedule = e.schedule()?;
    let mut months = Vec::new();
    for q in v["queryMonths"]
        .as_array()
        .ok_or_else(|| bad("queryMonths"))?
    {
        let m = month_index(q)?;
        let r = e.month(m)?;
        months.push(json!({
            "month": m,
            "depreciation": r.depreciation.minor().to_string(),
            "disposal": r.disposal.minor().to_string(),
            "bookValue": r.book_value.minor().to_string(),
        }));
    }
    Ok(json!({
        "schedule": strs(&schedule),
        "total": Money::sum(schedule, c)?.minor().to_string(),
        "months": months,
    }))
}

fn kk_true_profit(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let mut family = Vec::new();
    for f in v["familyLabor"]
        .as_array()
        .ok_or_else(|| bad("familyLabor"))?
    {
        family.push(FamilyLabor {
            hours100: i(f, "hours100")?,
            hourly_rate: money(f, "hourlyRate", c)?,
            paid: b(f, "paid")?,
        });
    }
    let r = true_profit(
        c,
        ProfitInput {
            revenue: money(v, "revenue", c)?,
            cogs: money(v, "cogs", c)?,
            operating_expenses: money(v, "operatingExpenses", c)?,
            owner_labor: money(v, "ownerLabor", c)?,
            depreciation: money(v, "depreciation", c)?,
            disposal: money(v, "disposal", c)?,
            stock_losses: money(v, "stockLosses", c)?,
        },
        &family,
    )?;
    Ok(json!({
        "visibleProfit": r.visible_profit.minor().to_string(),
        "stockLosses": r.stock_losses.minor().to_string(),
        "ownerLabor": r.owner_labor.minor().to_string(),
        "familyLabor": r.family_labor.minor().to_string(),
        "familyLaborPaid": r.family_labor_paid.minor().to_string(),
        "depreciation": r.depreciation.minor().to_string(),
        "disposal": r.disposal.minor().to_string(),
        "trueProfit": r.true_profit.minor().to_string(),
    }))
}

fn kk_order_quote(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let opt = |k: &str| -> Result<Option<Money>, E> {
        if v[k].is_null() {
            Ok(None)
        } else {
            Ok(Some(money(v, k, c)?))
        }
    };
    let q = order_quote(QuoteInput {
        material: money(v, "material", c)?,
        hours100: i(v, "hours100")?,
        hourly_rate: money(v, "hourlyRate", c)?,
        travel: money(v, "travel", c)?,
        depreciation: money(v, "depreciation", c)?,
        reserve_bp: i(v, "reserveBp")?,
        price: opt("price")?,
        advance: opt("advance")?,
    })?;
    let m = |x: Money| x.minor().to_string();
    let p = q.price;
    let a = q.advance;
    Ok(json!({
        "labor": m(q.labor),
        "subtotal": m(q.subtotal),
        "reserve": m(q.reserve),
        "cost": m(q.cost),
        "margin": p.map(|p| m(p.margin)),
        "laborPaid": p.map(|p| m(p.labor_paid)),
        "belowCost": p.map(|p| p.below_cost),
        "effectiveHourlyRate": p.and_then(|p| p.effective_hourly_rate).map(m),
        "materialShortfall": a.map(|a| m(a.material_shortfall)),
        "advanceAfterMaterial": a.map(|a| m(a.advance_after_material)),
    }))
}

fn kk_month_close(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let t = &v["tax"];
    let tax = match s(t, "base")? {
        "NONE" => TaxRule::None,
        "REVENUE" => TaxRule::Revenue { bp: i(t, "bp")? },
        "PROFIT" => TaxRule::Profit { bp: i(t, "bp")? },
        "FIXED" => TaxRule::Fixed {
            amount: money(t, "amount", c)?,
        },
        _ => return Err(E("INVALID_TAX_BASE".into())),
    };
    let r = &v["rule"];
    let out = month_close(CloseInput {
        revenue: money(v, "revenue", c)?,
        expenses: money(v, "expenses", c)?,
        depreciation: money(v, "depreciation", c)?,
        owner_salary: money(v, "ownerSalary", c)?,
        owner_paid: money(v, "ownerPaid", c)?,
        tax,
        rule: SplitRule {
            reserve_bp: i(r, "reserveBp")?,
            working_bp: i(r, "workingBp")?,
            expansion_bp: i(r, "expansionBp")?,
            sadaqa_bp: i(r, "sadaqaBp")?,
        },
        carry_overdraw: b(v, "carryOverdraw")?,
    })?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "tax": m(out.tax),
        "ownerPay": m(out.owner_pay),
        "overdrawn": m(out.overdrawn),
        "carryForward": m(out.carry_forward),
        "remaining": m(out.remaining),
        "needsExplanation": out.needs_explanation,
        "allocation": out.allocation.map(|a| json!({
            "reserve": m(a.reserve),
            "working": m(a.working),
            "expansion": m(a.expansion),
            "sadaqa": m(a.sadaqa),
        })),
        "reserveBelowDepreciation": out.reserve_below_depreciation,
    }))
}

fn kk_moves(v: &Value, c: Currency) -> Result<Vec<Move>, E> {
    let wallet = |m: &Value, k: &str| -> Result<Wallet, E> {
        Wallet::parse(s(m, k)?).ok_or_else(|| E("INVALID_WALLET".into()))
    };
    let mut moves = Vec::new();
    for m in v.as_array().ok_or_else(|| bad("moves"))? {
        let kind = match s(m, "kind")? {
            "SALE" => MoveKind::Sale,
            "EXPENSE" => MoveKind::Expense,
            "OWNER_DRAW" => MoveKind::OwnerDraw,
            "OWNER_CONTRIBUTION" => MoveKind::OwnerContribution,
            "OWNER_SALARY" => MoveKind::OwnerSalary,
            "EQUIPMENT_PURCHASE" => MoveKind::EquipmentPurchase,
            "EQUIPMENT_SALE" => MoveKind::EquipmentSale,
            "CASH_SHORT" => MoveKind::CashShort,
            "CASH_OVER" => MoveKind::CashOver,
            "STOCK_PURCHASE" => MoveKind::StockPurchase,
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
    Ok(moves)
}

fn kk_cash_close(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let reason = match v["reason"].as_str() {
        None => None,
        Some(r) => Some(CashReason::parse(r).ok_or_else(|| E("INVALID_REASON".into()))?),
    };
    let recent = v["recentDifferences"]
        .as_array()
        .ok_or_else(|| bad("recentDifferences"))?
        .iter()
        .map(|d| int_str(d).map(|m| Money::new(m, c)))
        .collect::<Result<Vec<_>, _>>()?;
    let r = cash_close(
        money(v, "opening", c)?,
        &kk_moves(&v["moves"], c)?,
        money(v, "counted", c)?,
        reason,
        &recent,
    )?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "cashSales": m(r.cash_sales),
        "cashExpenses": m(r.cash_expenses),
        "ownerDraws": m(r.owner_draws),
        "handedOver": m(r.handed_over),
        "otherIn": m(r.other_in),
        "otherOut": m(r.other_out),
        "expected": m(r.expected),
        "difference": m(r.difference),
        "status": r.status.as_str(),
        "reason": r.reason.map(CashReason::as_str),
        "suggestSearch": r.suggest_search,
    }))
}

fn kk_shift_close(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let reason = match v["reason"].as_str() {
        None => None,
        Some(r) => Some(CashReason::parse(r).ok_or_else(|| E("INVALID_REASON".into()))?),
    };
    let recent = v["recentDifferences"]
        .as_array()
        .ok_or_else(|| bad("recentDifferences"))?
        .iter()
        .map(|d| int_str(d).map(|m| Money::new(m, c)))
        .collect::<Result<Vec<_>, _>>()?;
    let mut ins = Vec::new();
    for m in v["ins"].as_array().ok_or_else(|| bad("ins"))? {
        ins.push(ShiftIn {
            kind: ShiftInKind::parse(s(m, "kind")?).ok_or_else(|| E("INVALID_KIND".into()))?,
            wallet: Wallet::parse(s(m, "wallet")?).ok_or_else(|| E("INVALID_WALLET".into()))?,
            amount: money(m, "amount", c)?,
        });
    }
    let r = shift_close(
        money(v, "opening", c)?,
        &ins,
        money(v, "counted", c)?,
        money(v, "handedOver", c)?,
        reason,
        &recent,
    )?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "cashSales": m(r.cash_sales),
        "creditPayments": m(r.credit_payments),
        "cardIn": m(r.card_in),
        "expected": m(r.expected),
        "difference": m(r.difference),
        "status": r.status.as_str(),
        "reason": r.reason.map(CashReason::as_str),
        "suggestSearch": r.suggest_search,
        "handedOver": m(r.handed_over),
        "left": m(r.left),
    }))
}

fn kk_credit_sale(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let terms = CreditTerms {
        credit_price: money(v, "creditPrice", c)?,
        cash_price: if v["cashPrice"].is_null() {
            None
        } else {
            Some(money(v, "cashPrice", c)?)
        },
        installments: u32::try_from(i(v, "installments")?)
            .map_err(|_| E("INVALID_INSTALLMENTS".into()))?,
        first_due: date(&v["firstDue"])?,
    };
    let mut events = Vec::new();
    for e in v["events"].as_array().ok_or_else(|| bad("events"))? {
        let on = date(&e["date"])?;
        events.push(match s(e, "kind")? {
            "PAYMENT" => CreditEvent::Payment {
                on,
                amount: money(e, "amount", c)?,
            },
            "FORGIVE" => CreditEvent::Forgive {
                on,
                amount: money(e, "amount", c)?,
            },
            "EXTEND" => CreditEvent::Extend {
                on,
                months: u32::try_from(i(e, "months")?)
                    .map_err(|_| E("INVALID_EXTENSION".into()))?,
            },
            _ => return Err(E("INVALID_KIND".into())),
        });
    }
    let st = terms.state(&events, date(&v["today"])?)?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "schedule": st.schedule.iter().map(|r| json!({
            "due": r.due.format("%Y-%m-%d").to_string(),
            "amount": m(r.amount),
            "covered": m(r.covered),
            "state": r.state.as_str(),
        })).collect::<Vec<_>>(),
        "paid": m(st.paid),
        "forgiven": m(st.forgiven),
        "outstanding": m(st.outstanding),
        "status": st.status.as_str(),
        "overdueDays": st.overdue_days,
        "bucket": st.bucket.map(|b| b.as_str()),
        "nextDue": st.next_due.map(|(d, a)| json!({ "date": d.format("%Y-%m-%d").to_string(), "amount": m(a) })),
        "creditMarkup": st.credit_markup.map(m),
    }))
}

fn kk_cogs(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let method = CostMethod::parse(s(v, "method")?).ok_or_else(|| E("INVALID_METHOD".into()))?;
    let factor = i(v, "factor")?;
    validate_factor(factor)?;
    let mut stock = Stock::new(method, c);
    let mut out = Vec::new();
    for m in v["moves"].as_array().ok_or_else(|| bad("moves"))? {
        let qty = i(m, "qty")?;
        let amount = || {
            if m["amount"].is_null() {
                Ok(Money::zero(c))
            } else {
                money(m, "amount", c)
            }
        };
        let kind = s(m, "kind")?;
        let mv = match kind {
            "PURCHASE" => StockMove::Purchase {
                qty,
                amount: amount()?,
            },
            "SALE" => StockMove::Sale { qty },
            "WRITE_OFF" => StockMove::WriteOff { qty },
            "ADJUST" => StockMove::Adjust {
                qty,
                amount: amount()?,
            },
            _ => return Err(E("INVALID_KIND".into())),
        };
        let cost = stock.apply(mv)?;
        out.push(json!({ "kind": kind, "cost": cost.minor().to_string() }));
    }
    Ok(json!({
        "moves": out,
        "qty": stock.qty,
        "value": stock.value.minor().to_string(),
        "unitCost": stock.unit_cost(factor)?.map(|m| m.minor().to_string()),
        "layers": match method {
            CostMethod::Fifo => json!(stock.layers.iter().map(|(q, v)| json!({ "qty": q, "value": v.minor().to_string() })).collect::<Vec<_>>()),
            CostMethod::Average => Value::Null,
        },
    }))
}

fn kk_replacement(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let sale = if v["salePrice"].is_null() {
        None
    } else {
        Some(money(v, "salePrice", c)?)
    };
    let r = replacement(
        i(v, "qty")?,
        money(v, "bookValue", c)?,
        money(v, "price", c)?,
        i(v, "factor")?,
        sale,
    )?;
    Ok(json!({
        "replacementValue": r.replacement_value.minor().to_string(),
        "inflationGap": r.inflation_gap.minor().to_string(),
        "saleBelowReplacement": r.sale_below_replacement,
    }))
}

fn u32_of(v: &Value, k: &str, code: &str) -> Result<u32, E> {
    u32::try_from(i(v, k)?).map_err(|_| E(code.into()))
}

fn kk_payroll(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let mut months = Vec::new();
    for m in v["months"].as_array().ok_or_else(|| bad("months"))? {
        let mut paid = Vec::new();
        for p in m["paid"].as_array().ok_or_else(|| bad("paid"))? {
            paid.push(Money::new(int_str(p)?, c));
        }
        months.push(PayMonth {
            salary: money(m, "salary", c)?,
            paid,
        });
    }
    let mut advances = Vec::new();
    for a in v["advances"].as_array().ok_or_else(|| bad("advances"))? {
        advances.push(Advance {
            id: s(a, "id")?.to_string(),
            month: u32_of(a, "month", "INVALID_START")?,
            amount: money(a, "amount", c)?,
            installments: u32_of(a, "installments", "INVALID_INSTALLMENTS")?,
            start_month: u32_of(a, "startMonth", "INVALID_START")?,
        });
    }
    let r = payroll(c, &months, &advances, money(v, "opening", c)?)?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "months": r.months.iter().map(|p| json!({
            "salary": m(p.salary),
            "scheduled": m(p.scheduled),
            "deducted": m(p.deducted),
            "net": m(p.net),
            "paid": m(p.paid),
            "balance": m(p.balance),
        })).collect::<Vec<_>>(),
        "advances": r.advances.iter().map(|a| json!({
            "id": a.id,
            "schedule": a.schedule.iter().map(|(mo, x)| json!({ "month": mo, "amount": m(*x) })).collect::<Vec<_>>(),
            "deducted": m(a.deducted),
            "outstanding": m(a.outstanding),
        })).collect::<Vec<_>>(),
    }))
}

fn kk_supplier_balance(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let mut deliveries = Vec::new();
    for d in v["deliveries"]
        .as_array()
        .ok_or_else(|| bad("deliveries"))?
    {
        deliveries.push(Delivery {
            id: s(d, "id")?.to_string(),
            on: date(&d["on"])?,
            amount: money(d, "amount", c)?,
            due_days: u32_of(d, "dueDays", "INVALID_DAYS")?,
        });
    }
    let mut payments = Vec::new();
    for p in v["payments"].as_array().ok_or_else(|| bad("payments"))? {
        payments.push(SupplyPayment {
            on: date(&p["on"])?,
            amount: money(p, "amount", c)?,
        });
    }
    let r = supplier_balance(c, &deliveries, &payments, date(&v["today"])?)?;
    let m = |x: Money| x.minor().to_string();
    let ymd = |d: NaiveDate| d.format("%Y-%m-%d").to_string();
    Ok(json!({
        "deliveries": r.deliveries.iter().map(|d| json!({
            "id": d.id,
            "due": ymd(d.due),
            "amount": m(d.amount),
            "paid": m(d.paid),
            "outstanding": m(d.outstanding),
            "state": d.state.as_str(),
            "overdueDays": d.overdue_days,
        })).collect::<Vec<_>>(),
        "paid": m(r.paid),
        "outstanding": m(r.outstanding),
        "overdue": m(r.overdue),
        "dueSoon": m(r.due_soon),
        "nextDue": r.next_due.map(|(d, a)| json!({ "date": ymd(d), "amount": m(a) })),
    }))
}

fn moneys(v: &Value, k: &str, c: Currency) -> Result<Vec<Money>, E> {
    v[k].as_array()
        .ok_or_else(|| bad(k))?
        .iter()
        .map(|x| Ok(Money::new(int_str(x)?, c)))
        .collect()
}

fn kk_expansion_gate(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let r = expansion_gate(&KkGateInput {
        reserve: money(v, "reserve", c)?,
        opex_months: moneys(v, "opexMonths", c)?,
        required_months: u32_of(v, "requiredMonths", "INVALID_MONTHS")?,
        true_profits: moneys(v, "trueProfits", c)?,
        receivables: money(v, "receivables", c)?,
        receivables_90: money(v, "receivables90", c)?,
        max_bad_bp: i(v, "maxBadBp")?,
        has_interest_debt: b(v, "hasInterestDebt")?,
        has_payoff_plan: b(v, "hasPayoffPlan")?,
        has_plan: b(v, "hasPlan")?,
    })?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "open": r.open,
        "conditions": r.conditions.iter().map(|(c, ok)| json!({ "code": c.as_str(), "ok": ok })).collect::<Vec<_>>(),
        "reasons": r.reasons().iter().map(|c| c.as_str()).collect::<Vec<_>>(),
        "averageOpex": r.average_opex.map(m),
        "requiredReserve": r.required_reserve.map(m),
        "coverageCentiMonths": r.coverage_centi_months,
        "badDebtBp": r.bad_debt_bp,
    }))
}

fn kk_zakat(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let r = zakat(&ZakatInput {
        stock: money(v, "stock", c)?,
        cash: money(v, "cash", c)?,
        receivables: money(v, "receivables", c)?,
        debts: money(v, "debts", c)?,
        gold_price: money(v, "goldPrice", c)?,
        nisab_grams: u32_of(v, "nisabGrams", "INVALID_NISAB")?,
        hawl_complete: b(v, "hawlComplete")?,
    })?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "base": m(r.base),
        "nisab": m(r.nisab),
        "due": r.reason.is_none(),
        "zakat": m(r.zakat),
        "reason": r.reason.map(|x| x.as_str()),
    }))
}

fn kk_funds(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let mut events = Vec::new();
    for e in v["events"].as_array().ok_or_else(|| bad("events"))? {
        events.push(match s(e, "kind")? {
            "CLOSE" => {
                let mut a = [Money::zero(c); 5];
                for (slot, f) in a.iter_mut().zip(Fund::ALL) {
                    let k = f.as_str().to_lowercase();
                    if !e[k.as_str()].is_null() {
                        *slot = money(e, &k, c)?;
                    }
                }
                FundEvent::Close(a)
            }
            "USE" => FundEvent::Use {
                fund: Fund::parse(s(e, "fund")?).ok_or_else(|| E("INVALID_FUND".into()))?,
                amount: money(e, "amount", c)?,
            },
            _ => return Err(E("INVALID_KIND".into())),
        });
    }
    let r = funds(c, &events)?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "funds": r.iter().map(|f| json!({
            "fund": f.fund.as_str(),
            "added": m(f.added),
            "used": m(f.used),
            "balance": m(f.balance),
        })).collect::<Vec<_>>(),
    }))
}

fn mf_month(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let mut moves = Vec::new();
    for m in v["moves"].as_array().ok_or_else(|| bad("moves"))? {
        moves.push(MfMove {
            kind: MfKind::parse(s(m, "kind")?).ok_or_else(|| E("INVALID_KIND".into()))?,
            amount: money(m, "amount", c)?,
            fee: if m["fee"].is_null() {
                None
            } else {
                Some(money(m, "fee", c)?)
            },
        });
    }
    let r = mf_month_report(
        money(v, "opening", c)?,
        money(v, "fundOpening", c)?,
        i(v, "shareBp")?,
        &moves,
    )?;
    let m = |x: Money| x.minor().to_string();
    Ok(json!({
        "income": m(r.income),
        "expenses": m(r.expenses),
        "sentHome": m(r.sent_home),
        "fees": m(r.fees),
        "fundIn": m(r.fund_in),
        "fundOut": m(r.fund_out),
        "fundNet": m(r.fund_net),
        "fundBalance": m(r.fund_balance),
        "pocket": m(r.pocket),
        "shareTarget": m(r.share_target),
        "shareGap": m(r.share_gap),
        "expensesBp": r.expenses_bp,
        "sentBp": r.sent_bp,
        "fundBp": r.fund_bp,
        "warnings": r.warnings.iter().map(|w| w.as_str()).collect::<Vec<_>>(),
    }))
}

fn mf_return_fund(v: &Value) -> R {
    let c = cur(v, "currency")?;
    let home = cur(v, "homeCurrency")?;
    let rate = if v["rateNum"].is_null() {
        None
    } else {
        Some(FxRate {
            from: c,
            to: home,
            rate_num: i(v, "rateNum")?,
            rate_den: i(v, "rateDen")?,
        })
    };
    let target = if v["target"].is_null() {
        None
    } else {
        Some(money(v, "target", home)?)
    };
    let return_on = if v["returnOn"].is_null() {
        None
    } else {
        Some(date(&v["returnOn"])?)
    };
    let r = return_fund(
        money(v, "balance", c)?,
        rate.as_ref(),
        target,
        &moneys(v, "monthly", c)?,
        date(&v["today"])?,
        return_on,
    )?;
    let m = |x: Option<Money>| x.map(|x| x.minor().to_string());
    Ok(json!({
        "avgMonthly": m(r.avg_monthly),
        "monthsUntilReturn": r.months_until_return,
        "balanceHome": m(r.balance_home),
        "avgMonthlyHome": m(r.avg_monthly_home),
        "remainingHome": m(r.remaining_home),
        "progressBp": r.progress_bp,
        "monthsToTarget": r.months_to_target,
        "projectedHome": m(r.projected_home),
        "shortfallAtReturn": m(r.shortfall_at_return),
        "status": r.status.as_str(),
    }))
}
