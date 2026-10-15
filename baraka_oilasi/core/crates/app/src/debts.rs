//! 4-qonun use-case'lari (U8, U9): qarz inventari, bergan qarzlar, haqiqiy narx, oylik yuk,
//! «to'xta va o'yla», to'lovlar (tilxatga bog'langanlari jurnal orqali) va maqsadlar.
//!
//! Har bir qarzning holati (qoldiq, keyingi to'lov, kechikkan summa, «Qarzsiz kun») to'lovlar
//! tarixidan `domain-uy::payoff` bilan qayta hisoblanadi: bank qarzida muddatidan oldingi to'lov
//! asosiy qarzni kamaytiradi, ustamali/foizsiz rejada reja oxiridan yopiladi.
use baraka_domain_common::month_period;
use baraka_domain_uy::debt::{
    build_plan, debt_load_bp, due_between, evaluate_borrow, goal_coverage_bp, plan_total,
    status_of, true_cost, Alternative, BorrowNeed, CreditorType, PlanKind, PlanLine, PlanSpec,
    PlanStatus, Receivable, TrueCost, TrueCostInput, LOAD_HIGH_BP,
};
use baraka_domain_uy::payoff::{
    payoff_plan, Amortizing, BankTerms, DebtState, Payment, PlanDebt, Scheduled,
};
use baraka_journal::{short_code, EntryKind, JournalAmount, JournalEntry};
use baraka_money::{format_percent_bp, round_half_up, Currency, Money};
use baraka_storage::repo::debts::{self, GoalRow, Owner, PlanLineRow, RepaymentRow};
use baraka_storage::repo::{agreements, incomes, journal, recovery};
use baraka_storage::SpaceScope;
use chrono::{Duration, NaiveDate};
use serde_json::json;

use crate::app::Ctx;
use crate::events::Topic;
use crate::receipt::{amount_in, date, plan_refs, positive, ymd, BORROWER};
use crate::text::{clean_opt, required};
use crate::*;

fn parse_owner(s: &str) -> Result<Owner, AppError> {
    match s {
        "DEBT" => Ok(Owner::Debt),
        "RECEIVABLE" => Ok(Owner::Receivable),
        _ => Err(AppError::on("INVALID_OWNER", "ownerType")),
    }
}

fn percent(bp: i64) -> String {
    format_percent_bp(bp)
}

fn parse_date(s: &str) -> Result<NaiveDate, AppError> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| AppError::new("CORRUPT_ROW"))
}

/// Saqlangan qarz yozuvining ribo belgisi (reja turi bo'yicha).
fn row_is_ribo(d: &debts::DebtRow) -> bool {
    match PlanKind::parse(&d.plan_kind) {
        Some(PlanKind::Annuity | PlanKind::Differentiated) => d.annual_bp > 0,
        _ => d.markup_minor > 0,
    }
}

/// Tekshirilgan, hali saqlanmagan to'lov.
pub(crate) struct PreparedRepayment {
    owner: Owner,
    id: String,
    amount: Money,
    entry: Option<JournalEntry>,
    pub(crate) row: RepaymentRow,
    closes: bool,
    agreement_id: Option<String>,
    debt_free: bool,
    return_mode: Option<recovery::BudgetRow>,
    freed: Option<Money>,
    budget_row_id: String,
    today: String,
}

/// Qarzdorlik hisobi uchun kerakli yozuv ma'lumotlari.
pub(crate) struct Ledger {
    pub(crate) currency: Currency,
    pub(crate) status: String,
    pub(crate) agreement_id: Option<String>,
    pub(crate) lines: Vec<PlanLine>,
    pub(crate) payments: Vec<RepaymentRow>,
    /// Bank qarzi (annuitet yoki differensial) shartlari.
    pub(crate) bank: Option<BankTerms>,
}

impl Ledger {
    pub(crate) fn paid(&self) -> Result<Money, AppError> {
        Ok(Money::sum(
            self.payments
                .iter()
                .map(|p| Money::new(p.amount_minor, self.currency)),
            self.currency,
        )?)
    }

    /// Bugungi holat; `extra` — hali saqlanmagan to'lov (yopilishni oldindan bilish uchun).
    pub(crate) fn state(&self, extra: Option<&RepaymentRow>) -> Result<DebtState, AppError> {
        let payments = self
            .payments
            .iter()
            .chain(extra)
            .map(|p| {
                Ok(Payment {
                    date: parse_date(&p.paid_on)?,
                    amount: Money::new(p.amount_minor, self.currency),
                    prepayment: p.is_prepayment,
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        Ok(match &self.bank {
            Some(t) => DebtState::Amortizing(Amortizing::replay(t, &payments)?),
            None => DebtState::Scheduled(Scheduled::new(&self.lines, &payments)?),
        })
    }
}

/// Qarzning hisoblangan ko'rinishi.
pub(crate) struct View {
    pub(crate) state: DebtState,
    /// Qolgan odatiy to'lovlar (bank qarzida — prognozdan).
    pub(crate) installments: Vec<PlanLine>,
    pub(crate) status: PlanStatus,
}

fn bank_terms(d: &debts::DebtRow, cur: Currency) -> Result<Option<BankTerms>, AppError> {
    let kind = PlanKind::parse(&d.plan_kind).ok_or(AppError::new("CORRUPT_ROW"))?;
    Ok(match kind {
        PlanKind::Annuity | PlanKind::Differentiated => Some(BankTerms {
            differentiated: kind == PlanKind::Differentiated,
            principal: Money::new(d.principal_minor, cur),
            annual_bp: d.annual_bp,
            months: d.months,
            first_date: parse_date(&d.started_on)?,
        }),
        _ => None,
    })
}

impl App {
    pub(crate) fn plan_rows(&self, lines: &[PlanLine]) -> Vec<PlanLineRow> {
        lines
            .iter()
            .map(|l| PlanLineRow {
                id: self.new_id(),
                due_on: ymd(l.date),
                amount_minor: l.amount.minor(),
                currency: l.amount.currency().code().to_string(),
            })
            .collect()
    }

    pub(crate) fn load_plan(
        &self,
        scope: &SpaceScope,
        owner: Owner,
        id: &str,
        cur: Currency,
    ) -> Result<Vec<PlanLine>, AppError> {
        self.db
            .read(|c| debts::plan(c, scope, owner, id))?
            .iter()
            .map(|r| {
                if r.currency != cur.code() {
                    return Err(AppError::new("CORRUPT_ROW"));
                }
                Ok(PlanLine {
                    date: parse_date(&r.due_on)?,
                    amount: Money::new(r.amount_minor, cur),
                })
            })
            .collect()
    }

    pub(crate) fn debt_ledger(
        &self,
        scope: &SpaceScope,
        d: &debts::DebtRow,
    ) -> Result<Ledger, AppError> {
        let currency = Currency::from_code(&d.currency)?;
        Ok(Ledger {
            lines: self.load_plan(scope, Owner::Debt, &d.id, currency)?,
            payments: self
                .db
                .read(|c| debts::repayments(c, scope, Owner::Debt, &d.id))?,
            bank: bank_terms(d, currency)?,
            currency,
            status: d.status.clone(),
            agreement_id: d.agreement_id.clone(),
        })
    }

    fn receivable_ledger(
        &self,
        scope: &SpaceScope,
        r: &debts::ReceivableRow,
    ) -> Result<Ledger, AppError> {
        let currency = Currency::from_code(&r.currency)?;
        Ok(Ledger {
            lines: self.load_plan(scope, Owner::Receivable, &r.id, currency)?,
            payments: self
                .db
                .read(|c| debts::repayments(c, scope, Owner::Receivable, &r.id))?,
            bank: None,
            currency,
            status: r.status.clone(),
            agreement_id: r.agreement_id.clone(),
        })
    }

    fn ledger(&self, scope: &SpaceScope, owner: Owner, id: &str) -> Result<Ledger, AppError> {
        match owner {
            Owner::Debt => {
                let d = self
                    .db
                    .read(|c| debts::get_debt(c, scope, id))?
                    .ok_or(AppError::on("NOT_FOUND", "id"))?;
                self.debt_ledger(scope, &d)
            }
            Owner::Receivable => {
                let r = self
                    .db
                    .read(|c| debts::get_receivable(c, scope, id))?
                    .ok_or(AppError::on("NOT_FOUND", "id"))?;
                self.receivable_ledger(scope, &r)
            }
        }
    }

    /// Holat, qolgan to'lovlar va eslatma (qo'shimcha to'lovsiz prognoz).
    pub(crate) fn view(
        &self,
        ctx: &Ctx,
        l: &Ledger,
        extra: Option<&RepaymentRow>,
    ) -> Result<View, AppError> {
        let state = l.state(extra)?;
        let today = self.today(ctx);
        let (proj, _) = payoff_plan(
            vec![PlanDebt {
                id: String::new(),
                state: state.clone(),
                fee_bp: 0,
            }],
            today,
            Money::zero(l.currency),
        )?;
        let installments = proj
            .into_iter()
            .next()
            .map(|p| p.installments)
            .unwrap_or_default();
        let status = status_of(&installments, today, l.currency)?;
        Ok(View {
            state,
            installments,
            status,
        })
    }

    /// Oylik yuk uchun daromad: oxirgi 3 to'liq oy o'rtachasi; u 0 bo'lsa — shu oy daromadi.
    pub(crate) fn monthly_income(&self, ctx: &Ctx, scope: &SpaceScope) -> Result<Money, AppError> {
        let cur = ctx.currency;
        let sum_between = |from: NaiveDate, to: NaiveDate| -> Result<Money, AppError> {
            let rows = self
                .db
                .read(|c| incomes::list_between(c, scope, &ymd(from), &ymd(to)))?;
            Ok(Money::sum(
                rows.iter()
                    .filter(|r| r.currency == cur.code())
                    .map(|r| Money::new(r.amount_minor, cur)),
                cur,
            )?)
        };
        let period = |d: NaiveDate| {
            month_period(d, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))
        };
        let (start, end) = period(self.today(ctx))?;
        let current = sum_between(start, end)?;
        let mut past = Money::zero(cur);
        let mut cursor = start;
        for _ in 0..3 {
            let (s, e) = period(cursor - Duration::days(1))?;
            past = past.checked_add(sum_between(s, e)?)?;
            cursor = s;
        }
        if past.is_positive() {
            let avg = round_half_up(i128::from(past.minor()), 3)?;
            Ok(Money::new(
                i64::try_from(avg).map_err(|_| AppError::new("OVERFLOW"))?,
                cur,
            ))
        } else {
            Ok(current)
        }
    }

    /// Shu oy davrida faol qarzlar bo'yicha reja to'lovlari (asosiy valyutada) va
    /// boshqa valyutadagi qarz bormi.
    fn monthly_due(&self, ctx: &Ctx, scope: &SpaceScope) -> Result<(Money, bool), AppError> {
        let cur = ctx.currency;
        let (start, end) = month_period(self.today(ctx), ctx.month_start_day)
            .ok_or(AppError::new("INVALID_PERIOD"))?;
        let mut due = Money::zero(cur);
        let mut foreign = false;
        for d in self.db.read(|c| debts::list_debts(c, scope))? {
            if d.status != "ACTIVE" {
                continue;
            }
            if d.currency != cur.code() {
                foreign = true;
                continue;
            }
            let v = self.view(ctx, &self.debt_ledger(scope, &d)?, None)?;
            due = due.checked_add(due_between(&v.installments, start, end, cur)?)?;
        }
        Ok((due, foreign))
    }

    fn debt_spec(&self, ctx: &Ctx, input: &NewDebtInput) -> Result<(PlanSpec, Currency), AppError> {
        let cur = Currency::from_code(&input.currency)?;
        let kind = PlanKind::parse(&input.plan_kind)
            .ok_or(AppError::on("INVALID_PLAN_KIND", "planKind"))?;
        let first_date = match input.first_date.as_deref() {
            Some(d) => date(d, "firstDate")?,
            None => self.today(ctx),
        };
        let markup = match input.markup.as_deref().map(str::trim) {
            None | Some("") => Money::zero(cur),
            Some(m) => amount_in(m, cur, "markup")?,
        };
        let lines = input
            .schedule
            .iter()
            .map(|l| {
                Ok(PlanLine {
                    date: date(&l.date, "schedule")?,
                    amount: positive(&l.amount, cur, "schedule")?,
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        Ok((
            PlanSpec {
                kind,
                principal: positive(&input.principal, cur, "principal")?,
                markup,
                annual_bp: i64::from(input.annual_bp.unwrap_or(0)),
                months: input.months.unwrap_or(0),
                first_date,
                lines,
            },
            cur,
        ))
    }

    fn true_cost_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        tc: &TrueCost,
    ) -> Result<TrueCostDto, AppError> {
        let goals = self.db.read(|c| debts::list_goals(c, scope))?;
        let cur = tc.overpay.currency();
        let goal_equivalents = if tc.overpay.is_positive() {
            goals
                .iter()
                .filter(|g| g.currency == cur.code())
                .map(|g| {
                    let bp = goal_coverage_bp(tc.overpay, Money::new(g.target_minor, cur))?;
                    Ok(GoalEquivalentDto {
                        goal_id: g.id.clone(),
                        title: g.title.clone(),
                        percent: percent(bp),
                    })
                })
                .collect::<Result<Vec<_>, AppError>>()?
        } else {
            Vec::new()
        };
        let d = |m: Money| self.money_dto(ctx, m);
        Ok(TrueCostDto {
            original_principal: d(tc.original_principal),
            total_cost: d(tc.total_cost),
            overpay: d(tc.overpay),
            overpay_percent: percent(tc.overpay_bp),
            goal_equivalents,
        })
    }

    fn plan_dto(&self, ctx: &Ctx, lines: &[PlanLine]) -> Vec<PlanLineDto> {
        lines
            .iter()
            .map(|l| PlanLineDto {
                date: ymd(l.date),
                amount: self.money_dto(ctx, l.amount),
            })
            .collect()
    }

    fn status_dto(&self, ctx: &Ctx, paid: Money, st: &PlanStatus) -> PlanStatusDto {
        PlanStatusDto {
            paid: self.money_dto(ctx, paid),
            remaining: self.money_dto(ctx, st.remaining),
            next_due: st.next.map(|n| PlanLineDto {
                date: ymd(n.date),
                amount: self.money_dto(ctx, n.amount),
            }),
            overdue: self.money_dto(ctx, st.overdue),
            payoff_date: st.payoff_date.map(ymd),
            reminder: st.reminder.map(|r| r.as_str().to_string()),
        }
    }

    fn repayment_dtos(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        l: &Ledger,
    ) -> Result<Vec<RepaymentDto>, AppError> {
        let hashes = match &l.agreement_id {
            Some(a) => self.db.read(|c| journal::list(c, scope, a))?,
            None => Vec::new(),
        };
        Ok(l.payments
            .iter()
            .map(|p| RepaymentDto {
                id: p.id.clone(),
                amount: self.money_dto(ctx, Money::new(p.amount_minor, l.currency)),
                date: p.paid_on.clone(),
                is_prepayment: p.is_prepayment,
                note: p.note.clone(),
                journal_short_code: p.journal_entry_id.as_ref().and_then(|jid| {
                    hashes
                        .iter()
                        .find(|h| &h.entry.id == jid)
                        .map(|h| short_code(&h.hash))
                }),
                contributor_id: p.contributor_id.clone(),
            })
            .collect())
    }

    fn debt_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        d: &debts::DebtRow,
    ) -> Result<DebtDto, AppError> {
        let l = self.debt_ledger(scope, d)?;
        let cur = l.currency;
        let paid = l.paid()?;
        let v = self.view(ctx, &l, None)?;
        let st = v.status;
        // Jami narx = ilovagacha + yozilgan to'lovlar + prognozdagi qolgan to'lovlar.
        let tc = true_cost(&TrueCostInput {
            principal: Money::new(d.principal_minor, cur),
            original_principal: Some(Money::new(d.original_principal_minor, cur)),
            paid_before: Money::new(d.paid_before_minor, cur),
            plan_total: paid.checked_add(st.remaining)?,
            paid_since: paid,
        })?;
        let contributors = self
            .db
            .read(|c| recovery::contributors(c, scope, &d.id))?
            .into_iter()
            .map(|c| {
                let share = c
                    .monthly_share_minor
                    .map(|m| self.money_dto(ctx, Money::new(m, cur)));
                let by = Money::sum(
                    l.payments
                        .iter()
                        .filter(|p| p.contributor_id.as_deref() == Some(c.id.as_str()))
                        .map(|p| Money::new(p.amount_minor, cur)),
                    cur,
                )?;
                Ok(ContributorDto {
                    id: c.id,
                    name: c.name,
                    monthly_share: share,
                    paid: self.money_dto(ctx, by),
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        let warnings = d
            .borrow_check_json
            .as_deref()
            .and_then(|j| serde_json::from_str::<serde_json::Value>(j).ok())
            .and_then(|v| {
                v["warnings"].as_array().map(|a| {
                    a.iter()
                        .filter_map(|w| w.as_str().map(str::to_string))
                        .collect()
                })
            })
            .unwrap_or_default();
        Ok(DebtDto {
            id: d.id.clone(),
            creditor_type: d.creditor_type.clone(),
            creditor: d.creditor.clone(),
            reason: d.reason.clone(),
            plan_kind: d.plan_kind.clone(),
            is_ribo: row_is_ribo(d),
            annual_bp: i32::try_from(d.annual_bp).map_err(|_| AppError::new("CORRUPT_ROW"))?,
            status: d.status.clone(),
            principal: self.money_dto(ctx, Money::new(d.principal_minor, cur)),
            true_cost: self.true_cost_dto(ctx, scope, &tc)?,
            status_info: self.status_dto(ctx, paid, &st),
            plan: self.plan_dto(ctx, &l.lines),
            payments: self.repayment_dtos(ctx, scope, &l)?,
            early_repayment_terms: d.early_repayment_terms.clone(),
            prepayment_fee_bp: i32::try_from(d.prepayment_fee_bp)
                .map_err(|_| AppError::new("CORRUPT_ROW"))?,
            priority: d.priority.and_then(|p| i32::try_from(p).ok()),
            balance: self.money_dto(ctx, v.state.balance()),
            contributors,
            borrow_warnings: warnings,
            agreement_id: d.agreement_id.clone(),
        })
    }

    fn receivable_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        r: &debts::ReceivableRow,
    ) -> Result<ReceivableDto, AppError> {
        let l = self.receivable_ledger(scope, r)?;
        let paid = l.paid()?;
        let st = self.view(ctx, &l, None)?.status;
        Ok(ReceivableDto {
            id: r.id.clone(),
            debtor: r.debtor.clone(),
            amount: self.money_dto(ctx, Money::new(r.amount_minor, l.currency)),
            lent_on: r.lent_on.clone(),
            note: r.note.clone(),
            status: r.status.clone(),
            status_info: self.status_dto(ctx, paid, &st),
            plan: self.plan_dto(ctx, &l.lines),
            payments: self.repayment_dtos(ctx, scope, &l)?,
            agreement_id: r.agreement_id.clone(),
        })
    }

    /// Yangi qarzdan keyingi oylik yuk (bp): joriy reja to'lovlari + yangi qarzning o'rtacha
    /// to'lovi (reja yig'indisi / qatorlar soni). Daromad yoki valyuta mos kelmasa — `None`.
    fn projected_load(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        lines: &[PlanLine],
    ) -> Result<Option<i64>, AppError> {
        let Some(first) = lines.first() else {
            return Ok(None);
        };
        if first.amount.currency() != ctx.currency {
            return Ok(None);
        }
        let total = plan_total(lines, ctx.currency)?;
        let n = i128::try_from(lines.len()).map_err(|_| AppError::new("OVERFLOW"))?;
        let avg = i64::try_from(round_half_up(i128::from(total.minor()), n)?)
            .map_err(|_| AppError::new("OVERFLOW"))?;
        let (due, _) = self.monthly_due(ctx, scope)?;
        let income = self.monthly_income(ctx, scope)?;
        Ok(debt_load_bp(
            due.checked_add(Money::new(avg, ctx.currency))?,
            income,
        )?)
    }

    /// «To'xta va o'yla» javoblarini tekshirib, saqlanadigan JSON'ni qaytaradi.
    /// Yangi qarzda javoblar majburiy; eski qarzni inventarga kiritishda — ixtiyoriy.
    pub(crate) fn borrow_check_json(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        spec: &PlanSpec,
        lines: &[PlanLine],
        is_new: bool,
        check: Option<&BorrowCheckInput>,
    ) -> Result<Option<String>, AppError> {
        let Some(check) = check else {
            return if is_new {
                Err(AppError::on("BORROW_CHECK_REQUIRED", "borrowCheck"))
            } else {
                Ok(None)
            };
        };
        let need =
            BorrowNeed::parse(&check.need).ok_or(AppError::on("INVALID_NEED", "borrowCheck"))?;
        let mut alternatives = check
            .alternatives
            .iter()
            .map(|a| {
                Alternative::parse(a).ok_or(AppError::on("INVALID_ALTERNATIVE", "borrowCheck"))
            })
            .collect::<Result<Vec<_>, _>>()?;
        alternatives.sort();
        alternatives.dedup();
        let load = self.projected_load(ctx, scope, lines)?;
        let warnings = evaluate_borrow(need, &alternatives, spec.is_ribo(), load);
        Ok(Some(
            json!({
                "need": need.as_str(),
                "alternatives": alternatives.iter().map(|a| a.as_str()).collect::<Vec<_>>(),
                "projectedLoadBp": load,
                "warnings": warnings.iter().map(|w| w.as_str()).collect::<Vec<_>>(),
                "checkedOn": ymd(self.today(ctx)),
            })
            .to_string(),
        ))
    }

    fn validated_debt(
        &self,
        ctx: &Ctx,
        input: &NewDebtInput,
    ) -> Result<(PlanSpec, Vec<PlanLine>, TrueCost, Currency), AppError> {
        let (spec, cur) = self.debt_spec(ctx, input)?;
        let lines = build_plan(&spec)?;
        let original = match input.original_principal.as_deref().map(str::trim) {
            None | Some("") => None,
            Some(s) => Some(positive(s, cur, "originalPrincipal")?),
        };
        let paid_before = match input.paid_before.as_deref().map(str::trim) {
            None | Some("") => Money::zero(cur),
            Some(s) => amount_in(s, cur, "paidBefore")?,
        };
        let tc = true_cost(&TrueCostInput {
            principal: spec.principal,
            original_principal: original,
            paid_before,
            plan_total: plan_total(&lines, cur)?,
            paid_since: Money::zero(cur),
        })?;
        Ok((spec, lines, tc, cur))
    }

    /// Yangi qarz qo'shishdan oldin «to'xta va o'yla» natijasi (hech narsa saqlanmaydi).
    pub fn preview_borrow_check(
        &self,
        space_id: &str,
        input: NewDebtInput,
    ) -> Result<BorrowCheckDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let (spec, lines, tc, _) = self.validated_debt(&ctx, &input)?;
        let load = self.projected_load(&ctx, &scope, &lines)?;
        let (need, alts) = match &input.borrow_check {
            Some(c) => (
                BorrowNeed::parse(&c.need).unwrap_or(BorrowNeed::Necessity),
                c.alternatives
                    .iter()
                    .filter_map(|a| Alternative::parse(a))
                    .collect(),
            ),
            None => (BorrowNeed::Necessity, Vec::new()),
        };
        Ok(BorrowCheckDto {
            is_ribo: spec.is_ribo(),
            projected_load_percent: load.map(percent),
            warnings: evaluate_borrow(need, &alts, spec.is_ribo(), load)
                .iter()
                .map(|w| w.as_str().to_string())
                .collect(),
            plan: self.plan_dto(&ctx, &lines),
            true_cost: self.true_cost_dto(&ctx, &scope, &tc)?,
        })
    }

    /// Qarzni inventarga qo'shish. To'lov rejasisiz qarz saqlanmaydi.
    pub fn add_debt(&self, space_id: &str, input: NewDebtInput) -> Result<DebtDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let creditor_type = CreditorType::parse(&input.creditor_type)
            .ok_or(AppError::on("INVALID_CREDITOR_TYPE", "creditorType"))?;
        let creditor = required(&input.creditor, "creditor")?;
        let (spec, lines, tc, cur) = self.validated_debt(&ctx, &input)?;
        let fee_bp = i64::from(input.prepayment_fee_bp.unwrap_or(0));
        if !(0..=10_000).contains(&fee_bp) {
            return Err(AppError::on("INVALID_BP", "prepaymentFeeBp"));
        }
        let check = self.borrow_check_json(
            &ctx,
            &scope,
            &spec,
            &lines,
            input.is_new,
            input.borrow_check.as_ref(),
        )?;
        let row = debts::DebtRow {
            id: self.new_id(),
            creditor_type: creditor_type.as_str().to_string(),
            creditor,
            reason: clean_opt(input.reason.as_deref()),
            currency: cur.code().to_string(),
            principal_minor: spec.principal.minor(),
            original_principal_minor: tc.original_principal.minor(),
            paid_before_minor: tc.paid_total.minor(),
            plan_kind: spec.kind.as_str().to_string(),
            annual_bp: spec.annual_bp,
            markup_minor: spec.markup.minor(),
            months: spec.months,
            started_on: ymd(spec.first_date),
            early_repayment_terms: clean_opt(input.early_repayment_terms.as_deref()),
            priority: None,
            borrow_check_json: check,
            agreement_id: None,
            status: "ACTIVE".to_string(),
            prepayment_fee_bp: fee_bp,
        };
        let plan_rows = self.plan_rows(&lines);
        let meta = self.meta();
        self.db.write(|tx| {
            debts::insert_debt(tx, &scope, &row, &meta)?;
            debts::insert_plan(tx, &scope, Owner::Debt, &row.id, &plan_rows, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Debts]);
        self.debt_dto(&ctx, &scope, &row)
    }

    /// Bergan qarz (foizsiz; foiz maydoni yo'q). Qaytarish rejasi majburiy.
    pub fn add_receivable(
        &self,
        space_id: &str,
        input: NewReceivableInput,
    ) -> Result<ReceivableDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let cur = Currency::from_code(&input.currency)?;
        let lent_on = match input.lent_on.as_deref() {
            Some(d) => date(d, "lentOn")?,
            None => self.today(&ctx),
        };
        let r = Receivable {
            debtor: required(&input.debtor, "debtor")?,
            amount: positive(&input.amount, cur, "amount")?,
            lent_on,
            lines: input
                .schedule
                .iter()
                .map(|l| {
                    Ok(PlanLine {
                        date: date(&l.date, "schedule")?,
                        amount: positive(&l.amount, cur, "schedule")?,
                    })
                })
                .collect::<Result<Vec<_>, AppError>>()?,
        };
        r.validate()?;
        let row = debts::ReceivableRow {
            id: self.new_id(),
            debtor: r.debtor.clone(),
            currency: cur.code().to_string(),
            amount_minor: r.amount.minor(),
            lent_on: ymd(r.lent_on),
            note: clean_opt(input.note.as_deref()),
            agreement_id: None,
            status: "ACTIVE".to_string(),
        };
        let plan_rows = self.plan_rows(&r.lines);
        let meta = self.meta();
        self.db.write(|tx| {
            debts::insert_receivable(tx, &scope, &row, &meta)?;
            debts::insert_plan(tx, &scope, Owner::Receivable, &row.id, &plan_rows, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Debts]);
        self.receivable_dto(&ctx, &scope, &row)
    }

    /// To'lovni tekshiradi va yozishga tayyorlaydi (yozuvlar hali saqlanmagan).
    pub(crate) fn prepare_repayment(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        owner: Owner,
        id: &str,
        input: &RepaymentInput,
    ) -> Result<PreparedRepayment, AppError> {
        let l = self.ledger(scope, owner, id)?;
        if l.status != "ACTIVE" {
            return Err(AppError::new("ALREADY_CLOSED"));
        }
        let amount = positive(&input.amount, l.currency, "amount")?;
        let now = self.view(ctx, &l, None)?;
        // Bank qarzida muddatidan oldingi to'lov asosiy qarzdan oshmaydi; boshqa holatda — qolgan
        // to'lovlardan.
        let cap = if input.is_prepayment && l.bank.is_some() {
            now.state.balance()
        } else {
            now.status.remaining
        };
        if amount.compare(&cap)?.is_gt() {
            return Err(AppError::on("PAYMENT_EXCEEDS_REMAINING", "amount"));
        }
        if let Some(cid) = input.contributor_id.as_deref() {
            let ok = owner == Owner::Debt
                && self
                    .db
                    .read(|c| recovery::contributors(c, scope, id))?
                    .iter()
                    .any(|c| c.id == cid);
            if !ok {
                return Err(AppError::on("NOT_FOUND", "contributorId"));
            }
        }
        let paid_on = self.date_or_today(ctx, input.date.as_deref(), "date")?;
        let note = clean_opt(input.note.as_deref());
        let entry = match &l.agreement_id {
            Some(aid) => {
                let agreement = self
                    .db
                    .read(|c| agreements::get(c, scope, aid))?
                    .ok_or(AppError::new("NOT_FOUND"))?;
                if agreement.keeper_device_id != self.device_id {
                    return Err(AppError::new("NOT_JOURNAL_KEEPER"));
                }
                let e = JournalEntry {
                    id: self.new_id(),
                    agreement_id: aid.clone(),
                    kind: EntryKind::Repayment,
                    party_id: Some(BORROWER.to_string()),
                    amount: Some(JournalAmount {
                        minor: amount.minor(),
                        currency: l.currency.code().to_string(),
                    }),
                    date: ymd(paid_on),
                    note: note.clone(),
                    corrects_entry_id: None,
                    refs: if input.is_prepayment {
                        vec!["prepayment".to_string()]
                    } else {
                        Vec::new()
                    },
                };
                e.validate()?;
                Some(e)
            }
            None => None,
        };
        let row = RepaymentRow {
            id: self.new_id(),
            amount_minor: amount.minor(),
            currency: l.currency.code().to_string(),
            paid_on: ymd(paid_on),
            is_prepayment: input.is_prepayment,
            note,
            journal_entry_id: entry.as_ref().map(|e| e.id.clone()),
            contributor_id: input.contributor_id.clone(),
        };
        let closes = !self
            .view(ctx, &l, Some(&row))?
            .state
            .balance()
            .is_positive();
        let (debt_free, mode_returned, freed) = if closes && owner == Owner::Debt {
            let others = self
                .db
                .read(|c| debts::list_debts(c, scope))?
                .iter()
                .any(|d| d.status == "ACTIVE" && d.id != id);
            let budget = self.db.read(|c| recovery::budget(c, scope))?;
            let returns = !others && budget.as_ref().is_some_and(|b| b.mode == "DEBT_RECOVERY");
            // Bo'shagan oylik to'lov — reja qatorlarining o'rtachasi.
            let n = i128::try_from(l.lines.len().max(1)).map_err(|_| AppError::new("OVERFLOW"))?;
            let avg = round_half_up(i128::from(plan_total(&l.lines, l.currency)?.minor()), n)?;
            let avg = i64::try_from(avg).map_err(|_| AppError::new("OVERFLOW"))?;
            (
                !others,
                returns.then_some(budget).flatten(),
                Some(Money::new(avg, l.currency)),
            )
        } else {
            (false, None, None)
        };
        Ok(PreparedRepayment {
            owner,
            id: id.to_string(),
            amount,
            entry,
            row,
            closes,
            agreement_id: l.agreement_id,
            debt_free,
            return_mode: mode_returned,
            freed,
            budget_row_id: self.new_id(),
            today: ymd(self.today(ctx)),
        })
    }

    /// Tayyorlangan to'lovni tranzaksiya ichida yozadi: jurnal, to'lov, yopish, rejim qaytishi.
    pub(crate) fn apply_repayment(
        tx: &baraka_storage::Transaction<'_>,
        scope: &SpaceScope,
        p: &PreparedRepayment,
        meta: &baraka_storage::Meta,
    ) -> Result<Option<journal::StoredEntry>, baraka_storage::StorageError> {
        let stored = match &p.entry {
            Some(e) => Some(journal::append(tx, scope, e, meta)?),
            None => None,
        };
        debts::insert_repayment(tx, scope, p.owner, &p.id, &p.row, meta)?;
        if p.closes {
            debts::set_status(tx, scope, p.owner, &p.id, "CLOSED", meta)?;
            if let Some(aid) = &p.agreement_id {
                agreements::set_status(tx, scope, aid, "CLOSED", meta)?;
            }
        }
        if let Some(b) = &p.return_mode {
            let back = recovery::BudgetRow {
                mode: "STANDARD".to_string(),
                changed_on: p.today.clone(),
                ..b.clone()
            };
            recovery::upsert_budget(tx, scope, &p.budget_row_id, &back, meta)?;
        }
        Ok(stored)
    }

    pub(crate) fn repayment_result(
        &self,
        ctx: &Ctx,
        p: PreparedRepayment,
        stored: Option<journal::StoredEntry>,
    ) -> RepaymentResultDto {
        RepaymentResultDto {
            repayment: RepaymentDto {
                id: p.row.id,
                amount: self.money_dto(ctx, p.amount),
                date: p.row.paid_on,
                is_prepayment: p.row.is_prepayment,
                note: p.row.note,
                journal_short_code: stored.map(|s| short_code(&s.hash)),
                contributor_id: p.row.contributor_id,
            },
            closed: p.closes,
            debt_free: p.debt_free,
            mode_returned: p.return_mode.is_some(),
            freed_monthly: p.freed.map(|m| self.money_dto(ctx, m)),
        }
    }

    /// To'lov yozish. Tilxatga bog'langan yozuvda to'lov jurnalga (`REPAYMENT`) ham yoziladi;
    /// qoldiq 0 bo'lsa, yozuv va kelishuv yopiladi; oxirgi qarz yopilsa, `DEBT_RECOVERY`
    /// rejimi avtomatik `STANDARD` ga qaytadi.
    pub fn record_repayment(
        &self,
        space_id: &str,
        owner_type: &str,
        id: &str,
        input: RepaymentInput,
    ) -> Result<RepaymentResultDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let owner = parse_owner(owner_type)?;
        let p = self.prepare_repayment(&ctx, &scope, owner, id, &input)?;
        let meta = self.meta();
        let stored = self
            .db
            .write(|tx| Self::apply_repayment(tx, &scope, &p, &meta))?;
        let mut topics = vec![Topic::Debts];
        if stored.is_some() {
            topics.extend([Topic::Journal, Topic::Agreements]);
        }
        if p.return_mode.is_some() {
            topics.push(Topic::Budget);
        }
        self.publish(Some(space_id), &topics);
        Ok(self.repayment_result(&ctx, p, stored))
    }

    /// Qarzlar ekrani: inventar, bergan qarzlar, jami, oylik yuk, maqsadlar.
    pub fn debts_overview(&self, space_id: &str) -> Result<DebtsOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let debts: Vec<DebtDto> = self
            .db
            .read(|c| debts::list_debts(c, &scope))?
            .iter()
            .map(|d| self.debt_dto(&ctx, &scope, d))
            .collect::<Result<_, _>>()?;
        let receivables: Vec<ReceivableDto> = self
            .db
            .read(|c| debts::list_receivables(c, &scope))?
            .iter()
            .map(|r| self.receivable_dto(&ctx, &scope, r))
            .collect::<Result<_, _>>()?;
        let totals = |items: Vec<(String, &MoneyDto)>| -> Result<Vec<MoneyDto>, AppError> {
            let mut by: Vec<(Currency, Money)> = Vec::new();
            for (status, m) in items {
                if status != "ACTIVE" {
                    continue;
                }
                let cur = Currency::from_code(&m.currency)?;
                let v = Money::new(
                    m.minor.parse().map_err(|_| AppError::new("CORRUPT_ROW"))?,
                    cur,
                );
                match by.iter_mut().find(|(c, _)| *c == cur) {
                    Some((_, t)) => *t = t.checked_add(v)?,
                    None => by.push((cur, v)),
                }
            }
            by.sort_by_key(|(c, _)| (*c != ctx.currency, c.code()));
            Ok(by
                .into_iter()
                .map(|(_, m)| self.money_dto(&ctx, m))
                .collect())
        };
        let total_debt = totals(
            debts
                .iter()
                .map(|d| (d.status.clone(), &d.status_info.remaining))
                .collect(),
        )?;
        let total_receivable = totals(
            receivables
                .iter()
                .map(|r| (r.status.clone(), &r.status_info.remaining))
                .collect(),
        )?;
        let (due, foreign) = self.monthly_due(&ctx, &scope)?;
        let income = self.monthly_income(&ctx, &scope)?;
        let load = debt_load_bp(due, income)?;
        let goals = self
            .db
            .read(|c| debts::list_goals(c, &scope))?
            .into_iter()
            .map(|g| self.goal_dto(&ctx, &scope, g))
            .collect::<Result<_, _>>()?;
        let (plan, _) = self.plan_debts(&ctx, &scope)?;
        let today = self.today(&ctx);
        let (_, base) = payoff_plan(plan.clone(), today, Money::zero(ctx.currency))?;
        let budget = self.db.read(|c| recovery::budget(c, &scope))?;
        let with_plan = match &budget {
            Some(b) if b.mode == "DEBT_RECOVERY" => {
                let extra = self.recovery_extra(&ctx, &scope, b)?;
                payoff_plan(plan, today, extra)?.1.payoff_date.map(ymd)
            }
            _ => None,
        };
        let budget_mode = budget.map_or_else(|| "STANDARD".to_string(), |b| b.mode);
        Ok(DebtsOverviewDto {
            debt_free_date_with_plan: with_plan,
            debt_free_date: base.payoff_date.map(ymd),
            debt_free_months: base.months,
            budget_mode,
            has_ribo_debt: debts.iter().any(|d| d.is_ribo && d.status == "ACTIVE"),
            debts,
            receivables,
            total_debt,
            total_receivable,
            monthly_due: self.money_dto(&ctx, due),
            monthly_income: income.is_positive().then(|| self.money_dto(&ctx, income)),
            load_percent: load.map(percent),
            load_high: load.is_some_and(|bp| bp > LOAD_HIGH_BP),
            load_excludes_foreign: foreign,
            goals,
        })
    }

    pub(crate) fn goal_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        g: GoalRow,
    ) -> Result<GoalDto, AppError> {
        let cur = Currency::from_code(&g.currency)?;
        let rows = self
            .db
            .read(|c| baraka_storage::repo::ceremonies::contributions(c, scope, &g.id))?;
        let collected = Money::sum(
            rows.iter()
                .filter(|r| r.currency == cur.code())
                .map(|r| Money::new(r.amount_minor, cur)),
            cur,
        )?;
        let target = Money::new(g.target_minor, cur);
        Ok(GoalDto {
            collected_percent: percent(goal_coverage_bp(collected, target)?),
            collected: self.money_dto(ctx, collected),
            contributions: rows
                .into_iter()
                .map(|r| GoalContributionDto {
                    id: r.id,
                    contributor: r.contributor,
                    amount: self.money_dto(ctx, Money::new(r.amount_minor, cur)),
                    given_on: r.given_on,
                })
                .collect(),
            id: g.id,
            title: g.title,
            target: self.money_dto(ctx, target),
        })
    }

    /// Imkoniyat narxi uchun maqsad (masalan, «qizimning kontrakti»).
    pub fn add_goal(&self, space_id: &str, input: NewGoalInput) -> Result<GoalDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let cur = Currency::from_code(&input.currency)?;
        let row = GoalRow {
            id: self.new_id(),
            title: required(&input.title, "title")?,
            target_minor: positive(&input.target, cur, "target")?.minor(),
            currency: cur.code().to_string(),
        };
        let meta = self.meta();
        self.db
            .write(|tx| debts::insert_goal(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Debts]);
        self.goal_dto(&ctx, &scope, row)
    }

    pub fn delete_goal(&self, space_id: &str, goal_id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db
            .write(|tx| debts::delete_goal(tx, &scope, goal_id, &meta))?;
        self.publish(Some(space_id), &[Topic::Debts]);
        Ok(())
    }

    /// Jurnal yozuvlarini qayta yozmasdan, tilxatdagi reja `refs` bilan mosligini tekshirish.
    pub(crate) fn plan_matches_journal(
        &self,
        scope: &SpaceScope,
        agreement_id: &str,
        lines: &[PlanLine],
    ) -> Result<bool, AppError> {
        let entries = self.db.read(|c| journal::list(c, scope, agreement_id))?;
        Ok(entries
            .first()
            .is_some_and(|e| e.entry.refs == plan_refs(lines)))
    }
}
