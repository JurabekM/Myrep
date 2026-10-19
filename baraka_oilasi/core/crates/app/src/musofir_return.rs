//! M3 — yo'l qarzidan chiqish, «Qaytdim» va sovutish davri (`docs/musofir/SPEC.md` 6).
//!
//! Hisob `domain-musofir::travel` va `::cooling` da (vektorlar `mf_travel_debt`, `mf_cooling`). Yo'l
//! qarzi — Uy makonidagi oddiy U8 qarzi; uni «Qarz to'lovi» maqsadidan to'lash uydagi oila qurilmasida
//! ham ochiq. Reja, qaytish va qarorlar jurnali — musofirning shaxsiy hisobi (ADR-0004).
use baraka_domain_common::month_period;
use baraka_domain_musofir::cooling::{
    cooling_check, cooling_window, questions, DecisionKind, Reply,
};
use baraka_domain_musofir::fund::startup_split;
use baraka_domain_musofir::remittance::Purpose;
use baraka_domain_musofir::reserve::{reserve_plan, DEFAULT_MONTHS, MAX_MONTHS, MIN_MONTHS};
use baraka_domain_musofir::travel::travel_debt_plan;
use baraka_money::{format_percent_bp, Money};
use baraka_storage::repo::debts::{self, Owner};
use baraka_storage::repo::{mf, ventures};
use baraka_storage::SpaceScope;
use chrono::NaiveDate;
use serde::{Deserialize, Serialize};

use crate::app::Ctx;
use crate::events::Topic;
use crate::musofir::PROGNOSIS_MONTHS;
use crate::musofir_remit::money_of;
use crate::receipt::{positive, ymd};
use crate::text::{clean_opt, required};
use crate::*;

/// «Birinchi maoshlardan» maqsadli muddat (OQ-MF8).
const DEFAULT_TARGET_MONTHS: i64 = 6;
const CHOICES: [&str; 3] = ["WAIT", "PROCEED", "DECLINE"];
const OUTCOMES: [&str; 2] = ["DONE", "DROPPED"];

#[derive(Serialize, Deserialize)]
struct StoredAnswer {
    key: String,
    reply: String,
}

#[derive(Serialize, Deserialize)]
struct StoredFlag {
    code: String,
    level: String,
}

fn date_of(s: &str) -> Result<NaiveDate, AppError> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| AppError::new("CORRUPT_ROW"))
}

fn kind_of(s: &str) -> Result<DecisionKind, AppError> {
    DecisionKind::parse(s.trim()).ok_or(AppError::on("INVALID_DECISION_KIND", "kind"))
}

fn to_json<T: Serialize>(v: &T) -> Result<String, AppError> {
    serde_json::to_string(v).map_err(|_| AppError::new("CORRUPT_ROW"))
}

fn small(v: i64) -> i32 {
    i32::try_from(v).unwrap_or(i32::MAX)
}

/// Tekshirilgan qaror (yozishga tayyor).
struct Checked {
    kind: DecisionKind,
    title: String,
    amount: Money,
    answers: Vec<(&'static str, Reply, String)>,
    dto: MfDecisionCheckDto,
    in_cooling: bool,
}

impl App {
    fn mf_require_settings(&self, scope: &SpaceScope) -> Result<(), AppError> {
        match self.db.read(|c| mf::settings(c, scope))? {
            Some(_) => Ok(()),
            None => Err(AppError::new("MF_NOT_CONFIGURED")),
        }
    }

    fn mf_debt_ref(
        &self,
        ctx: &Ctx,
        uy: &SpaceScope,
        d: &debts::DebtRow,
    ) -> Result<MfDebtRefDto, AppError> {
        let dto = self.debt_dto(ctx, uy, d)?;
        Ok(MfDebtRefDto {
            id: d.id.clone(),
            creditor: d.creditor.clone(),
            reason: d.reason.clone(),
            status: d.status.clone(),
            outstanding: dto.balance,
        })
    }

    /// Yo'l qarzi va uni yopish rejasi (faqat musofirda).
    pub fn mf_travel_debt(&self, space_id: &str) -> Result<MfTravelDebtDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let home = ctx.currency;
        let d = |m: Money| self.money_dto(&ctx, m);
        let info = self.db.read(|c| mf::return_info(c, &scope))?;
        let target = info.travel_target_months.unwrap_or(DEFAULT_TARGET_MONTHS);
        let Some(uy) = self.uy_space(&ctx)? else {
            return Ok(MfTravelDebtDto {
                debt: None,
                target_months: u32::try_from(target).unwrap_or(0),
                candidates: Vec::new(),
                plan: None,
            });
        };
        let all = self.db.read(|c| debts::list_debts(c, &uy))?;
        let mut candidates = Vec::new();
        for row in all
            .iter()
            .filter(|r| r.status == "ACTIVE" && r.currency == home.code())
        {
            candidates.push(self.mf_debt_ref(&ctx, &uy, row)?);
        }
        let debt = match info
            .travel_debt_id
            .as_deref()
            .and_then(|id| all.iter().find(|r| r.id == id))
        {
            Some(row) => Some(self.mf_debt_ref(&ctx, &uy, row)?),
            None => None,
        };
        let plan = match &debt {
            Some(r) if r.outstanding.currency == home.code() => {
                let outstanding = Money::new(
                    r.outstanding
                        .minor
                        .parse()
                        .map_err(|_| AppError::new("CORRUPT_ROW"))?,
                    home,
                );
                let sh = self.mf_shores(&ctx, &scope)?;
                let available = sh
                    .book
                    .purposes
                    .iter()
                    .find(|p| p.purpose == Purpose::Debt)
                    .map_or(Money::zero(home), |p| p.balance);
                // Oxirgi to'liq oylar (qabuli borlari): «Qarz to'lovi» maqsadiga kelgan pul.
                let mut inflow: Vec<(NaiveDate, Money)> = Vec::new();
                for (m, alloc) in sh.moves.iter().zip(&sh.book.allocations) {
                    let Some(parts) = alloc else { continue };
                    let Some(r) = sh.receipts.iter().find(|r| r.move_id == m.id) else {
                        continue;
                    };
                    let debt_part = parts
                        .iter()
                        .find(|(p, _)| *p == Purpose::Debt)
                        .map_or(Money::zero(home), |(_, v)| *v);
                    inflow.push((date_of(&r.received_on)?, debt_part));
                }
                let today = self.today(&ctx);
                let (mut cursor, _) = month_period(today, ctx.month_start_day)
                    .ok_or(AppError::new("INVALID_PERIOD"))?;
                let mut monthly = Vec::new();
                for _ in 0..PROGNOSIS_MONTHS {
                    let Some(prev) = cursor.pred_opt() else { break };
                    let (start, end) = month_period(prev, ctx.month_start_day)
                        .ok_or(AppError::new("INVALID_PERIOD"))?;
                    let inside: Vec<Money> = inflow
                        .iter()
                        .filter(|(on, _)| start <= *on && *on < end)
                        .map(|(_, v)| *v)
                        .collect();
                    if !inside.is_empty() {
                        monthly.push(Money::sum(inside, home)?);
                    }
                    cursor = start;
                }
                let p = travel_debt_plan(outstanding, available, &monthly, target, today)?;
                Some(MfTravelPlanDto {
                    remaining: d(p.remaining),
                    available: d(available),
                    avg_monthly: p.avg_monthly.map(d),
                    months_used: u32::try_from(monthly.len()).unwrap_or(0),
                    months_to_clear: p.months_to_clear.map(small),
                    clear_on: p.clear_on.map(ymd),
                    required_monthly: d(p.required_monthly),
                    status: p.status.as_str().to_string(),
                })
            }
            _ => None,
        };
        Ok(MfTravelDebtDto {
            debt,
            target_months: u32::try_from(target).unwrap_or(0),
            candidates,
            plan,
        })
    }

    /// Uy qarzini «yo'l qarzi» deb belgilash (yoki belgini olib tashlash) va maqsadli muddat.
    pub fn mf_set_travel_debt(
        &self,
        space_id: &str,
        input: MfTravelDebtInput,
    ) -> Result<MfTravelDebtDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        self.mf_require_settings(&scope)?;
        let target = match input.target_months {
            None => None,
            Some(m) if (1..=60).contains(&m) => Some(i64::from(m)),
            Some(_) => return Err(AppError::on("INVALID_MONTHS", "targetMonths")),
        };
        let debt_id = match clean_opt(input.debt_id.as_deref()) {
            None => None,
            Some(id) => {
                let uy = self.uy_required(&ctx)?;
                let row = self
                    .db
                    .read(|c| debts::get_debt(c, &uy, &id))?
                    .ok_or(AppError::on("NOT_FOUND", "debtId"))?;
                if row.currency != ctx.currency.code() {
                    return Err(AppError::on("CURRENCY_MISMATCH", "debtId"));
                }
                Some(row.id)
            }
        };
        let meta = self.meta();
        self.db
            .write(|tx| mf::set_travel_debt(tx, &scope, debt_id.as_deref(), target, &meta))?;
        self.publish(Some(space_id), &[Topic::Musofir]);
        self.mf_travel_debt(space_id)
    }

    /// «Qarz to'lovi» maqsadidan U8 to'lovi: Uy qarzi kamayadi, maqsad qoldig'i kamayadi (bitta
    /// tranzaksiyada). Uydagi oila qurilmasida ham ochiq.
    pub fn mf_pay_debt(
        &self,
        space_id: &str,
        input: MfDebtPaymentInput,
    ) -> Result<MfTwoShoresDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_space_check(&ctx, space_id)?;
        let uy = self.uy_required(&ctx)?;
        let row = self
            .db
            .read(|c| debts::get_debt(c, &uy, &input.debt_id))?
            .ok_or(AppError::on("NOT_FOUND", "debtId"))?;
        if row.currency != ctx.currency.code() {
            return Err(AppError::on("CURRENCY_MISMATCH", "debtId"));
        }
        let repayment = RepaymentInput {
            amount: input.amount,
            date: input.paid_on,
            is_prepayment: false,
            note: input.note,
            contributor_id: None,
        };
        let p = self.prepare_repayment(&ctx, &uy, Owner::Debt, &row.id, &repayment)?;
        let link_id = self.new_id();
        let meta = self.meta();
        let stored = self.db.write(|tx| {
            let stored = Self::apply_repayment(tx, &uy, &p, &meta)?;
            mf::insert_debt_payment(tx, &scope, &link_id, &p.row.id, &meta)?;
            Ok(stored)
        })?;
        let mut topics = vec![Topic::Musofir, Topic::Debts];
        if stored.is_some() {
            topics.extend([Topic::Journal, Topic::Agreements]);
        }
        self.publish(Some(&uy.space_id), &topics);
        self.publish(Some(space_id), &[Topic::Musofir]);
        self.mf_two_shores(space_id)
    }

    pub(crate) fn mf_cooling_dto(
        &self,
        ctx: &Ctx,
        info: &mf::MfReturnRow,
    ) -> Result<Option<MfCoolingDto>, AppError> {
        let Some(on) = info.returned_on.as_deref() else {
            return Ok(None);
        };
        let w = cooling_window(self.today(ctx), Some(date_of(on)?));
        let brought = match (
            info.brought_home_minor,
            info.brought_home_currency.as_deref(),
        ) {
            (Some(v), Some(c)) => Some(self.money_dto(ctx, money_of(v, c)?)),
            _ => None,
        };
        Ok(Some(MfCoolingDto {
            returned_on: on.to_string(),
            brought_home: brought,
            in_cooling: w.in_cooling,
            ends_on: w.ends_on.map(ymd),
            days_left: small(w.days_left),
        }))
    }

    /// «Qaytdim»: qaytish sanasi va olib kelingan summa — sovutish davri shundan boshlanadi.
    pub fn mf_set_return(
        &self,
        space_id: &str,
        input: MfReturnInput,
    ) -> Result<MfOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        self.mf_require_settings(&scope)?;
        let (returned_on, brought) = match clean_opt(input.returned_on.as_deref()) {
            None => (None, None),
            Some(t) => {
                let on = NaiveDate::parse_from_str(&t, "%Y-%m-%d")
                    .map_err(|_| AppError::on("INVALID_DATE", "returnedOn"))?;
                if on > self.today(&ctx) {
                    return Err(AppError::on("FUTURE_DATE", "returnedOn"));
                }
                let brought = match clean_opt(input.brought_home.as_deref()) {
                    None => None,
                    Some(b) => Some(positive(&b, ctx.currency, "broughtHome")?),
                };
                (Some(ymd(on)), brought)
            }
        };
        let code = ctx.currency.code();
        let meta = self.meta();
        self.db.write(|tx| {
            mf::set_return(
                tx,
                &scope,
                returned_on.as_deref(),
                brought.map(|b| (b.minor(), code)),
                &meta,
            )
        })?;
        self.publish(Some(space_id), &[Topic::Musofir]);
        self.mf_overview(space_id, None)
    }

    /// Qaror turi uchun savollar (kalitlar; matn — UI tarjimasida).
    pub fn mf_decision_questions(&self, kind: &str) -> Result<Vec<String>, AppError> {
        Ok(questions(kind_of(kind)?)
            .into_iter()
            .map(str::to_string)
            .collect())
    }

    fn mf_check(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        input: &MfDecisionInput,
    ) -> Result<Checked, AppError> {
        let kind = kind_of(&input.kind)?;
        let title = required(&input.title, "title")?;
        let amount = positive(&input.amount, ctx.currency, "amount")?;
        let asked = questions(kind);
        let mut answers = Vec::new();
        for a in &input.answers {
            let key = asked
                .iter()
                .find(|q| **q == a.key.trim())
                .ok_or(AppError::on("INVALID_ANSWER", "answers"))?;
            let reply =
                Reply::parse(a.reply.trim()).ok_or(AppError::on("INVALID_ANSWER", "answers"))?;
            if answers.iter().any(|(k, _, _)| k == key) {
                return Err(AppError::on("INVALID_ANSWER", "answers"));
            }
            answers.push((*key, reply, a.reply.trim().to_string()));
        }
        // Savollar tartibida saqlanadi.
        answers.sort_by_key(|(k, _, _)| asked.iter().position(|q| q == k));
        let info = self.db.read(|c| mf::return_info(c, scope))?;
        let returned_on = info.returned_on.as_deref().map(date_of).transpose()?;
        let brought = match (
            info.brought_home_minor,
            info.brought_home_currency.as_deref(),
        ) {
            (Some(v), Some(c)) if c == ctx.currency.code() => Some(Money::new(v, ctx.currency)),
            _ => None,
        };
        let pairs: Vec<(&str, Reply)> = answers.iter().map(|(k, r, _)| (*k, *r)).collect();
        let c = cooling_check(self.today(ctx), returned_on, brought, kind, amount, &pairs)?;
        let dto = MfDecisionCheckDto {
            questions: asked.iter().map(|q| (*q).to_string()).collect(),
            in_cooling: c.in_cooling,
            ends_on: c.ends_on.map(ymd),
            days_left: small(c.days_left),
            share_percent: c.share_bp.map(format_percent_bp),
            flags: c
                .flags
                .iter()
                .map(|f| MfFlagDto {
                    code: f.code.to_string(),
                    level: f.level.as_str().to_string(),
                })
                .collect(),
            verdict: c.verdict.as_str().to_string(),
            wait_until: c.wait_until.map(ymd),
        };
        Ok(Checked {
            kind,
            title,
            amount,
            answers,
            dto,
            in_cooling: c.in_cooling,
        })
    }

    /// Katta qaror oldidan tekshiruv (yozmaydi). Qaror taqiqlanmaydi — natija faqat ogohlantiradi.
    pub fn mf_check_decision(
        &self,
        space_id: &str,
        input: MfDecisionInput,
    ) -> Result<MfDecisionCheckDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        Ok(self.mf_check(&ctx, &scope, &input)?.dto)
    }

    /// Tekshiruv va musofirning tanlovi o'zgarmas qarorlar jurnaliga yoziladi.
    pub fn mf_record_decision(
        &self,
        space_id: &str,
        input: MfDecisionInput,
    ) -> Result<Vec<MfDecisionDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let choice = input
            .choice
            .as_deref()
            .map(str::trim)
            .filter(|c| CHOICES.contains(c))
            .ok_or(AppError::on("INVALID_CHOICE", "choice"))?
            .to_string();
        let ch = self.mf_check(&ctx, &scope, &input)?;
        let answers: Vec<StoredAnswer> = ch
            .answers
            .iter()
            .map(|(k, _, r)| StoredAnswer {
                key: (*k).into(),
                reply: r.clone(),
            })
            .collect();
        let flags: Vec<StoredFlag> = ch
            .dto
            .flags
            .iter()
            .map(|f| StoredFlag {
                code: f.code.clone(),
                level: f.level.clone(),
            })
            .collect();
        let row = mf::MfDecisionRow {
            id: self.new_id(),
            decided_on: ymd(self.today(&ctx)),
            kind: ch.kind.as_str().to_string(),
            title: ch.title,
            amount_minor: ch.amount.minor(),
            currency: ch.amount.currency().code().to_string(),
            answers_json: to_json(&answers)?,
            verdict: ch.dto.verdict,
            flags_json: to_json(&flags)?,
            in_cooling: ch.in_cooling,
            wait_until: ch.dto.wait_until,
            choice,
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db
            .write(|tx| mf::insert_decision(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Musofir]);
        self.mf_decisions(space_id)
    }

    /// Qarorlar jurnali (yangisi tepada).
    pub fn mf_decisions(&self, space_id: &str) -> Result<Vec<MfDecisionDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let corrupt = |_| AppError::new("CORRUPT_ROW");
        let outcomes = self.db.read(|c| mf::outcomes(c, &scope))?;
        self.db
            .read(|c| mf::decisions(c, &scope))?
            .into_iter()
            .map(|r| {
                let answers: Vec<StoredAnswer> =
                    serde_json::from_str(&r.answers_json).map_err(corrupt)?;
                let flags: Vec<StoredFlag> =
                    serde_json::from_str(&r.flags_json).map_err(corrupt)?;
                let outcome =
                    outcomes
                        .iter()
                        .find(|o| o.decision_id == r.id)
                        .map(|o| MfOutcomeDto {
                            outcome: o.outcome.clone(),
                            outcome_on: o.outcome_on.clone(),
                            note: o.note.clone(),
                        });
                Ok(MfDecisionDto {
                    outcome,
                    amount: self.money_dto(&ctx, money_of(r.amount_minor, &r.currency)?),
                    id: r.id,
                    decided_on: r.decided_on,
                    kind: r.kind,
                    title: r.title,
                    answers: answers
                        .into_iter()
                        .map(|a| MfAnswerDto {
                            key: a.key,
                            reply: a.reply,
                        })
                        .collect(),
                    flags: flags
                        .into_iter()
                        .map(|f| MfFlagDto {
                            code: f.code,
                            level: f.level,
                        })
                        .collect(),
                    verdict: r.verdict,
                    in_cooling: r.in_cooling,
                    wait_until: r.wait_until,
                    choice: r.choice,
                    note: r.note,
                })
            })
            .collect()
    }
}

impl App {
    pub(crate) fn mf_reserve_months(&self, scope: &SpaceScope) -> Result<i64, AppError> {
        Ok(self
            .db
            .read(|c| mf::plan_info(c, scope))?
            .reserve_months
            .unwrap_or(DEFAULT_MONTHS))
    }

    /// Qorovul pul kartasi: qoldiq va oxirgi oylardagi chet el xarajatidan maqsad (SPEC 6.4).
    pub(crate) fn mf_reserve_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        balance: Money,
        spent: &[Money],
    ) -> Result<MfReserveDto, AppError> {
        let months = self.mf_reserve_months(scope)?;
        let r = reserve_plan(balance, spent, months, None)?;
        let d = |m: Money| self.money_dto(ctx, m);
        Ok(MfReserveDto {
            balance: d(balance),
            months: u32::try_from(months).unwrap_or(1),
            months_used: u32::try_from(spent.len()).unwrap_or(0),
            avg_monthly: r.avg_monthly.map(d),
            target: r.target.map(d),
            gap: r.gap.map(d),
            progress_bp: r.progress_bp.map(small),
            progress_percent: r.progress_bp.map(format_percent_bp),
            status: r.status.as_str().to_string(),
        })
    }

    /// Ish boshlash summasi: maqsadning bir qismi (SPEC 6.6). Maqsad keyin kamaytirilgan bo'lsa —
    /// `exceeds_target`.
    pub(crate) fn mf_startup_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        target: Option<Money>,
    ) -> Result<Option<MfStartupDto>, AppError> {
        let plan = self.db.read(|c| mf::plan_info(c, scope))?;
        let startup = match (plan.startup_minor, plan.startup_currency.as_deref()) {
            (Some(v), Some(c)) if c == ctx.currency.code() => Money::new(v, ctx.currency),
            _ => return Ok(None),
        };
        let d = |m: Money| self.money_dto(ctx, m);
        let (living, bp, exceeds) = match startup_split(target, startup) {
            Ok(s) => (s.living, s.startup_bp, false),
            Err(e) if e.code == "STARTUP_EXCEEDS_TARGET" => (None, None, true),
            Err(e) => return Err(e.into()),
        };
        let idea_title = match (&plan.startup_idea_id, self.uy_space(ctx)?) {
            (Some(id), Some(uy)) => self
                .db
                .read(|c| ventures::ideas(c, &uy))?
                .into_iter()
                .find(|i| &i.id == id)
                .map(|i| i.title),
            _ => None,
        };
        Ok(Some(MfStartupDto {
            startup: d(startup),
            living: living.map(d),
            startup_percent: bp.map(format_percent_bp),
            exceeds_target: exceeds,
            idea_id: plan.startup_idea_id.filter(|_| idea_title.is_some()),
            idea_title,
        }))
    }

    /// Qorovul pul muddati va ish boshlash summasi (ixtiyoriy «Hunardan ishga» g'oyasi bilan).
    pub fn mf_set_plan(
        &self,
        space_id: &str,
        input: MfPlanInput,
    ) -> Result<MfOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let settings = self
            .db
            .read(|c| mf::settings(c, &scope))?
            .ok_or(AppError::new("MF_NOT_CONFIGURED"))?;
        let months = match input.reserve_months {
            None => None,
            Some(m) if (MIN_MONTHS..=MAX_MONTHS).contains(&i64::from(m)) => Some(i64::from(m)),
            Some(_) => return Err(AppError::on("INVALID_MONTHS", "reserveMonths")),
        };
        let startup = clean_opt(input.startup.as_deref())
            .map(|t| positive(&t, ctx.currency, "startup"))
            .transpose()?;
        if let Some(s) = startup {
            let target = match (settings.target_minor, settings.target_currency.as_deref()) {
                (Some(v), Some(c)) if c == ctx.currency.code() => Some(Money::new(v, ctx.currency)),
                _ => None,
            };
            startup_split(target, s).map_err(|e| AppError::on(e.code, "startup"))?;
        }
        let idea_id = match clean_opt(input.startup_idea_id.as_deref()) {
            None => None,
            Some(id) => {
                let uy = self.uy_required(&ctx)?;
                if !self
                    .db
                    .read(|c| ventures::ideas(c, &uy))?
                    .iter()
                    .any(|i| i.id == id)
                {
                    return Err(AppError::on("NOT_FOUND", "startupIdeaId"));
                }
                Some(id)
            }
        };
        let row = mf::MfPlanRow {
            reserve_months: months,
            startup_minor: startup.map(|s| s.minor()),
            startup_currency: startup.map(|s| s.currency().code().to_string()),
            startup_idea_id: idea_id,
        };
        let meta = self.meta();
        self.db.write(|tx| mf::set_plan(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Musofir]);
        self.mf_overview(space_id, None)
    }

    /// Qarorning natijasi — bir marta: «qildim» yoki «qilmadim» (o'zgarmas).
    pub fn mf_set_outcome(
        &self,
        space_id: &str,
        decision_id: &str,
        input: MfOutcomeInput,
    ) -> Result<Vec<MfDecisionDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let decision = self
            .db
            .read(|c| mf::decisions(c, &scope))?
            .into_iter()
            .find(|d| d.id == decision_id)
            .ok_or(AppError::on("NOT_FOUND", "decisionId"))?;
        if self
            .db
            .read(|c| mf::outcomes(c, &scope))?
            .iter()
            .any(|o| o.decision_id == decision_id)
        {
            return Err(AppError::on("OUTCOME_ALREADY_SET", "decisionId"));
        }
        let outcome = input.outcome.trim();
        if !OUTCOMES.contains(&outcome) {
            return Err(AppError::on("INVALID_OUTCOME", "outcome"));
        }
        let on = self.date_or_today(&ctx, input.outcome_on.as_deref(), "outcomeOn")?;
        if on > self.today(&ctx) {
            return Err(AppError::on("FUTURE_DATE", "outcomeOn"));
        }
        if on < date_of(&decision.decided_on)? {
            return Err(AppError::on("BEFORE_DECISION", "outcomeOn"));
        }
        let row = mf::MfOutcomeRow {
            id: self.new_id(),
            decision_id: decision.id,
            outcome: outcome.to_string(),
            outcome_on: ymd(on),
            note: clean_opt(input.note.as_deref()),
        };
        let meta = self.meta();
        self.db
            .write(|tx| mf::insert_outcome(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Musofir]);
        self.mf_decisions(space_id)
    }
}
