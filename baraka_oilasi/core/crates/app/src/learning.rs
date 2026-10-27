//! 8-tamoyil «O'zingizga sarmoya qiling» (U16, `docs/uy/SPEC.md` 2G): «Bir soatim qancha?», bilim
//! rejasi, o'qish vaqti, natijani o'lchash, «Ilm zakoti» va «O'zimga sarmoya» qatori. Uy makoni.
//!
//! Qoidalar `domain-uy::learning` da (vektorlar `hour_value`, `hour_value_change`,
//! `self_invest_share`, `learning_plan`); bu yerda faqat saqlash va yig'ish.
use std::collections::HashMap;

use baraka_domain_common::IncomeSourceType;
use baraka_domain_common::{month_period, SpaceKind};
use baraka_domain_uy::learning::{
    average_income, check_activation, hour_value, self_invest_share, HourInput, PathKind,
    PlanStatus,
};
use baraka_money::{format_percent_bp, Money};
use baraka_storage::repo::{expenses, household, incomes, learning as repo};
use baraka_storage::SpaceScope;
use chrono::NaiveDate;

use crate::app::Ctx;
use crate::events::Topic;
use crate::learn_common::{
    bp32, closed, hour_err, max_chars, measure_plan, next_status, opt_amount, parse_paths,
    paths_text, plan_status, stored_hour, u32_of, PlanFields, TOPIC_MAX_CHARS,
};
use crate::receipt::ymd;
use crate::text::{clean, clean_opt};
use crate::*;

/// Bitta o'qish yozuvi: ko'pi bilan bir hafta (10 080 daqiqa).
const STUDY_MAX_MINUTES: u32 = 10_080;

/// Rejalar kartasi uchun yig'ilgan qiymatlar: o'qish daqiqalari, (reja, valyuta) bo'yicha sarflangan
/// summa va kerakli soat qiymati hisoblari (id bo'yicha).
struct PlanTotals {
    minutes: HashMap<String, i64>,
    spent: HashMap<(String, String), i64>,
    hours: HashMap<String, repo::HourValueRow>,
    /// A'zo → oxirgi hisob id (faqat butun makon yuklanganda).
    latest: HashMap<String, String>,
}

impl App {
    /// Uy makoni (bilim rejalari va soat qiymati shu yerda).
    fn learn_scope(&self, ctx: &Ctx, space_id: &str) -> Result<SpaceScope, AppError> {
        let scope = self.scope(ctx, space_id)?;
        if !self.is_uy_space(ctx, space_id)? {
            return Err(AppError::on("NOT_UY_SPACE", "spaceId"));
        }
        Ok(scope)
    }

    fn is_uy_space(&self, ctx: &Ctx, space_id: &str) -> Result<bool, AppError> {
        Ok(self.space_kind(ctx, space_id)? == Some(SpaceKind::Uy))
    }

    fn space_kind(&self, ctx: &Ctx, space_id: &str) -> Result<Option<SpaceKind>, AppError> {
        Ok(self
            .db
            .read(|c| household::list_spaces(c, &ctx.household_id))?
            .iter()
            .find(|s| s.id == space_id)
            .and_then(|s| SpaceKind::parse(&s.kind)))
    }

    fn learn_member(&self, ctx: &Ctx, member_id: &str) -> Result<(), AppError> {
        let found = self
            .db
            .read(|c| household::list_members(c, &ctx.household_id))?
            .iter()
            .any(|m| m.id == member_id);
        if found {
            Ok(())
        } else {
            Err(AppError::on("NOT_FOUND", "memberId"))
        }
    }

    /// Oxirgi 3 to'liq oy (xonadon oylik davri bo'yicha) — a'zoning halol daromad yozuvi borlari
    /// (`RIBO` — foiz daromadi hisobga kirmaydi, 2G.1), yangisidan eskisiga: (boshi, oxiri, jami).
    fn member_month_totals(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        member_id: &str,
    ) -> Result<Vec<(NaiveDate, NaiveDate, Money)>, AppError> {
        let cur = ctx.currency;
        self.last_full_months(ctx, |start, end| {
            let rows: Vec<Money> = self
                .db
                .read(|c| incomes::list_between(c, scope, &ymd(start), &ymd(end)))?
                .into_iter()
                .filter(|r| r.member_id.as_deref() == Some(member_id) && r.currency == cur.code())
                .filter(|r| r.source_type.as_deref() != Some(IncomeSourceType::Ribo.as_str()))
                .map(|r| Money::new(r.amount_minor, cur))
                .collect();
            Ok(if rows.is_empty() {
                None
            } else {
                Some(Money::sum(rows, cur)?)
            })
        })
    }

    fn hour_dto(&self, ctx: &Ctx, r: &repo::HourValueRow) -> Result<HourValueDto, AppError> {
        // Saqlangan daromad va vaqtdan qayta hisob — «ikki barobar maqsad» va soat chegarasi uchun.
        let h = stored_hour(
            r.income_minor,
            r.minutes_per_day,
            r.days,
            r.hour_value_minor,
        )?;
        let cur = baraka_money::Currency::from_code(&r.currency)?;
        let d = |v: i64| self.money_dto(ctx, Money::new(v, cur));
        Ok(HourValueDto {
            id: r.id.clone(),
            member_id: r.member_id.clone(),
            income: d(r.income_minor),
            income_source: r.income_source.clone(),
            minutes_per_day: h.minutes_per_day,
            days: h.days,
            monthly_minutes: h.monthly_minutes,
            hour_value: d(r.hour_value_minor),
            double_target: d(h.double_target),
            over_ceiling: h.over_ceiling,
            computed_on: r.computed_on.clone(),
        })
    }

    fn hour_money(
        &self,
        ctx: &Ctx,
        r: Option<&repo::HourValueRow>,
    ) -> Result<Option<MoneyDto>, AppError> {
        let Some(r) = r else { return Ok(None) };
        let cur = baraka_money::Currency::from_code(&r.currency)?;
        Ok(Some(
            self.money_dto(ctx, Money::new(r.hour_value_minor, cur)),
        ))
    }

    /// Kartalar uchun qiymatlar: `plan` bo'lsa — faqat shu reja, aks holda butun makon (bitta so'rov
    /// har turdan).
    fn learn_plan_totals(
        &self,
        scope: &SpaceScope,
        plan: Option<&repo::PlanRow>,
    ) -> Result<PlanTotals, AppError> {
        let id = plan.map(|p| p.id.as_str());
        let minutes = self
            .db
            .read(|c| repo::study_minutes(c, scope, id))?
            .into_iter()
            .collect();
        let spent = self
            .db
            .read(|c| repo::plan_spending(c, scope, id))?
            .into_iter()
            .map(|(plan, cur, v)| ((plan, cur), v))
            .collect();
        let mut latest = HashMap::new();
        let hours = match plan {
            Some(p) => {
                let mut hours = HashMap::new();
                for hid in [&p.baseline_hour_value_id, &p.result_hour_value_id]
                    .into_iter()
                    .flatten()
                {
                    if let Some(r) = self.db.read(|c| repo::hour_value(c, scope, hid))? {
                        hours.insert(r.id.clone(), r);
                    }
                }
                hours
            }
            None => {
                let mut hours = HashMap::new();
                // Saqlangan tartibda: har a'zoning oxirgisi qoladi.
                for r in self.db.read(|c| repo::hour_values(c, scope))? {
                    latest.insert(r.member_id.clone(), r.id.clone());
                    hours.insert(r.id.clone(), r);
                }
                hours
            }
        };
        Ok(PlanTotals {
            minutes,
            spent,
            hours,
            latest,
        })
    }

    fn learn_plan_dto(
        &self,
        ctx: &Ctx,
        p: &repo::PlanRow,
        totals: &PlanTotals,
    ) -> Result<LearningPlanDto, AppError> {
        // Byudjet va sarflangan — rejaning o'z valyutasida.
        let cur = baraka_money::Currency::from_code(&p.currency)?;
        let paths = parse_paths(&p.paths);
        let open = !closed(plan_status(&p.status)?);
        let hour = |id: &Option<String>| id.as_ref().and_then(|i| totals.hours.get(i));
        let spent = totals
            .spent
            .get(&(p.id.clone(), p.currency.clone()))
            .copied()
            .unwrap_or(0);
        Ok(LearningPlanDto {
            id: p.id.clone(),
            member_id: p.member_id.clone(),
            skill: p.skill.clone(),
            purpose: p.purpose.clone(),
            course_check_suggested: paths.iter().any(|x| x == PathKind::Course.as_str()),
            paths,
            budget: p
                .budget_minor
                .map(|b| self.money_dto(ctx, Money::new(b, cur))),
            weekly_minutes: u32_of(p.weekly_minutes)?,
            review_due: open && ymd(self.today(ctx)) >= p.review_on,
            start_on: p.start_on.clone(),
            review_on: p.review_on.clone(),
            status: p.status.clone(),
            baseline_hour_value: self.hour_money(ctx, hour(&p.baseline_hour_value_id))?,
            result_hour_value: self.hour_money(ctx, hour(&p.result_hour_value_id))?,
            study_minutes: u32::try_from(totals.minutes.get(&p.id).copied().unwrap_or(0))
                .unwrap_or(u32::MAX),
            spent: self.money_dto(ctx, Money::new(spent, cur)),
        })
    }

    /// O'zgarishdan keyingi bitta reja kartasi (qiymatlar faqat shu reja bo'yicha).
    fn one_learn_plan_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        plan_id: &str,
    ) -> Result<LearningPlanDto, AppError> {
        let p = self.learn_plan(scope, plan_id)?;
        let totals = self.learn_plan_totals(scope, Some(&p))?;
        self.learn_plan_dto(ctx, &p, &totals)
    }

    fn learn_plan(&self, scope: &SpaceScope, plan_id: &str) -> Result<repo::PlanRow, AppError> {
        self.db
            .read(|c| repo::plan(c, scope, plan_id))?
            .ok_or(AppError::on("NOT_FOUND", "planId"))
    }

    /// Xarajatdagi «O'zimga sarmoya» belgisi va bilim rejasiga havola (uy/SPEC 2G.3). Belgi — Uy va
    /// Kasb-kor makonlarida (K9: «Sarmoya (o'qish)», kasbkor/SPEC 8A.3); Musofir makonida belgi faqat
    /// `mf_record_expense` orqali (M6, musofir/SPEC 6A.1). Bilim rejalari faqat Uy makonida, shuning
    /// uchun Kasb-kor chiqimi rejaga bog'lanmaydi. Havola —
    /// faqat belgi bilan, shu makondagi ochiq (`ACTIVE`/`PAUSED`) rejaga; xarajat a'zosi ko'rsatilgan
    /// bo'lsa — reja a'zosi.
    pub(crate) fn expense_plan_link(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        self_investment: bool,
        plan_id: Option<&str>,
        member_id: Option<&str>,
    ) -> Result<Option<String>, AppError> {
        let id = plan_id.map(clean).filter(|s| !s.is_empty());
        if !self_investment && id.is_none() {
            return Ok(None);
        }
        match self.space_kind(ctx, &scope.space_id)? {
            Some(SpaceKind::Uy) => {}
            // Kasb-kor: belgi bor, bilim rejalari yo'q (K9).
            Some(SpaceKind::Kasbkor) if id.is_none() => return Ok(None),
            Some(SpaceKind::Kasbkor) => {
                return Err(AppError::on("PLAN_LINK_UY_ONLY", "learningPlanId"))
            }
            // Musofir belgisi faqat `mf_record_expense` orqali (ish valyutasida, M6) — umumiy xarajat
            // yo'lida rad.
            _ => return Err(AppError::on("NOT_UY_SPACE", "selfInvestment")),
        }
        let Some(id) = id else { return Ok(None) };
        if !self_investment {
            return Err(AppError::on("SELF_INVESTMENT_REQUIRED", "learningPlanId"));
        }
        let p = self
            .db
            .read(|c| repo::plan(c, scope, &id))?
            .ok_or(AppError::on("NOT_FOUND", "learningPlanId"))?;
        if closed(plan_status(&p.status)?) {
            return Err(AppError::on("PLAN_CLOSED", "learningPlanId"));
        }
        if member_id.is_some_and(|m| m != p.member_id) {
            return Err(AppError::on("PLAN_MEMBER_MISMATCH", "learningPlanId"));
        }
        Ok(Some(id))
    }

    /// «O'zimga sarmoya: X so'm — daromadning Y %» (2G.3): davr daromadi va belgili xarajatlar.
    pub(crate) fn self_investment_dto(
        &self,
        ctx: &Ctx,
        income: Money,
        rows: &[expenses::ExpenseRow],
    ) -> Result<SelfInvestmentDto, AppError> {
        let amounts: Vec<i64> = rows
            .iter()
            .filter(|e| e.self_investment && e.currency == income.currency().code())
            .map(|e| e.amount_minor)
            .collect();
        self.self_investment_of(ctx, income, &amounts)
    }

    /// «Sarmoya» qatori daromad valyutasida (Uy — xonadon valyutasi, Musofir — ish valyutasi).
    pub(crate) fn self_investment_of(
        &self,
        ctx: &Ctx,
        income: Money,
        amounts: &[i64],
    ) -> Result<SelfInvestmentDto, AppError> {
        let s = self_invest_share(income.minor(), amounts)?;
        Ok(SelfInvestmentDto {
            total: self.money_dto(ctx, Money::new(s.total, income.currency())),
            income: self.money_dto(ctx, income),
            share_bp: s.share_bp.map(bp32),
            share_percent: s.share_bp.map(format_percent_bp),
        })
    }

    // ---- 2G.1 «Bir soatim qancha?» ----

    /// Oylik daromad taklifi: oxirgi 3 to'liq oydagi (yozuvi borlari) a'zo daromadi o'rtachasi.
    pub fn hour_value_suggest(
        &self,
        space_id: &str,
        member_id: &str,
    ) -> Result<HourValueSuggestionDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.learn_scope(&ctx, space_id)?;
        self.learn_member(&ctx, member_id)?;
        let months = self.member_month_totals(&ctx, &scope, member_id)?;
        let totals: Vec<i64> = months.iter().map(|(_, _, m)| m.minor()).collect();
        let average =
            average_income(&totals)?.map(|v| self.money_dto(&ctx, Money::new(v, ctx.currency)));
        Ok(HourValueSuggestionDto {
            member_id: member_id.to_string(),
            months: months
                .iter()
                .map(|(s, e, m)| MonthIncomeDto {
                    period_start: ymd(*s),
                    period_end: ymd(*e),
                    total: self.money_dto(&ctx, *m),
                })
                .collect(),
            average,
        })
    }

    /// Soat qiymatini hisoblaydi va o'zgarmas tarixga yozadi. Daromad bo'sh — `AUTO` (taklif).
    pub fn hour_value_save(
        &self,
        space_id: &str,
        input: HourValueInput,
    ) -> Result<HourValueDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.learn_scope(&ctx, space_id)?;
        self.learn_member(&ctx, &input.member_id)?;
        let income = opt_amount(input.income.as_deref(), ctx.currency, "income")?;
        let totals: Vec<i64> = if income.is_none() {
            self.member_month_totals(&ctx, &scope, &input.member_id)?
                .iter()
                .map(|(_, _, m)| m.minor())
                .collect()
        } else {
            Vec::new()
        };
        let h = hour_value(&HourInput {
            income,
            month_totals: &totals,
            minutes_per_day: i64::from(input.minutes_per_day),
            days: i64::from(input.days),
        })
        .map_err(hour_err)?;
        let row = repo::HourValueRow {
            id: self.new_id(),
            member_id: input.member_id,
            income_minor: h.income,
            currency: ctx.currency.code().to_string(),
            income_source: h.source.as_str().to_string(),
            minutes_per_day: i64::from(input.minutes_per_day),
            days: i64::from(input.days),
            hour_value_minor: h.hour_value,
            computed_on: ymd(self.today(&ctx)),
        };
        // Javob yozuvdan oldin tayyorlanadi: xato bo'lsa o'zgarmas yozuv qolmaydi.
        let dto = self.hour_dto(&ctx, &row)?;
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_hour_value(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning]);
        Ok(dto)
    }

    // ---- 2G.2 Bilim rejasi ----

    /// Reja ochish: bir a'zoda ko'pi bilan 2 ta faol reja; boshlang'ich nuqta — oxirgi soat qiymati.
    pub fn learning_plan_create(
        &self,
        space_id: &str,
        input: LearningPlanInput,
    ) -> Result<LearningPlanDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.learn_scope(&ctx, space_id)?;
        self.learn_member(&ctx, &input.member_id)?;
        let checked = self.check_plan(
            &ctx,
            ctx.currency,
            &PlanFields {
                skill: &input.skill,
                purpose: input.purpose.as_deref(),
                paths: &input.paths,
                budget: input.budget.as_deref(),
                weekly_minutes: input.weekly_minutes,
                start_on: input.start_on.as_deref(),
                review_on: input.review_on.as_deref(),
            },
        )?;
        let plan = checked.plan;
        let baseline = self
            .db
            .read(|c| repo::latest_hour_value(c, &scope, &input.member_id))?
            .map(|h| h.id);
        let row = repo::PlanRow {
            id: self.new_id(),
            member_id: input.member_id,
            paths: paths_text(&plan),
            skill: plan.skill,
            purpose: checked.purpose,
            budget_minor: plan.budget,
            currency: ctx.currency.code().to_string(),
            weekly_minutes: i64::from(plan.weekly_minutes),
            start_on: ymd(plan.start),
            review_on: ymd(plan.review),
            status: PlanStatus::Active.as_str().to_string(),
            baseline_hour_value_id: baseline,
            result_hour_value_id: None,
        };
        let meta = self.meta();
        // Faol rejalar sanog'i va yozuv — bitta tranzaksiyada (ikki tez so'rov chegarani oshirmaydi).
        self.db.write(|tx| {
            let others = repo::other_active_plans(tx, &scope, &row.member_id, None)?;
            if let Err(e) = check_activation(others) {
                return Ok(Err(AppError::from(e)));
            }
            repo::insert_plan(tx, &scope, &row, &meta)?;
            Ok(Ok(()))
        })??;
        self.publish(Some(space_id), &[Topic::Learning]);
        self.one_learn_plan_dto(&ctx, &scope, &row.id)
    }

    /// Holat o'zgarishi: yopilgan reja qayta ochilmaydi; `PAUSED → ACTIVE` da chegara qayta tekshiriladi.
    pub fn learning_plan_set_status(
        &self,
        space_id: &str,
        plan_id: &str,
        status: &str,
    ) -> Result<LearningPlanDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.learn_scope(&ctx, space_id)?;
        let p = self.learn_plan(&scope, plan_id)?;
        let meta = self.meta();
        // Sanoq va o'zgarish — bitta tranzaksiyada (`PAUSED → ACTIVE` chegarasi poyga holatisiz).
        self.db.write(|tx| {
            let others = repo::other_active_plans(tx, &scope, &p.member_id, Some(&p.id))?;
            let to = match next_status(&p.status, status, others) {
                Ok(to) => to,
                Err(e) => return Ok(Err(e)),
            };
            repo::set_plan_status(tx, &scope, &p.id, to.as_str(), &meta)?;
            Ok(Ok(()))
        })??;
        self.publish(Some(space_id), &[Topic::Learning]);
        self.one_learn_plan_dto(&ctx, &scope, &p.id)
    }

    // ---- 2G.5 Natijani o'lchash ----

    /// A'zoning oxirgi soat qiymati boshlang'ich nuqta bilan solishtiriladi va natija sifatida saqlanadi.
    pub fn learning_plan_result(
        &self,
        space_id: &str,
        plan_id: &str,
    ) -> Result<LearningResultDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.learn_scope(&ctx, space_id)?;
        let p = self.learn_plan(&scope, plan_id)?;
        // Qoidalar (yopilgan reja, yangi hisob yo'qligi, valyuta) — Musofir bilan umumiy.
        let current = self
            .db
            .read(|c| repo::latest_hour_value(c, &scope, &p.member_id))?;
        let m = measure_plan(
            plan_status(&p.status)?,
            p.result_hour_value_id.is_some(),
            p.baseline_hour_value_id.as_deref(),
            current,
            |id| Ok(self.db.read(|c| repo::hour_value(c, &scope, id))?),
        )?;
        let (baseline, current, change) = (m.baseline, m.current, m.change);
        // Javob avval tayyorlanadi: xato bo'lsa natija saqlanmaydi.
        let cur = baraka_money::Currency::from_code(&current.currency)?;
        let bp = change.and_then(|c| c.change_bp);
        let dto = LearningResultDto {
            plan_id: p.id.clone(),
            baseline: baseline
                .as_ref()
                .map(|b| self.hour_dto(&ctx, b))
                .transpose()?,
            current: self.hour_dto(&ctx, &current)?,
            diff: change.map(|c| self.money_dto(&ctx, Money::new(c.diff, cur))),
            change_bp: bp.map(bp32),
            change_percent: bp.map(format_percent_bp),
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::set_plan_result(tx, &scope, &p.id, &current.id, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning]);
        Ok(dto)
    }

    // ---- O'qish vaqti va «Ilm zakoti» ----

    /// «Bu hafta necha soat o'qidingiz?» — o'qish vaqti yozuvi (yopilgan rejaga yozilmaydi).
    pub fn study_log_add(
        &self,
        space_id: &str,
        plan_id: &str,
        input: StudyLogInput,
    ) -> Result<LearningPlanDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.learn_scope(&ctx, space_id)?;
        let p = self.learn_plan(&scope, plan_id)?;
        if closed(plan_status(&p.status)?) {
            return Err(AppError::on("PLAN_CLOSED", "planId"));
        }
        if !(1..=STUDY_MAX_MINUTES).contains(&input.minutes) {
            return Err(AppError::on("INVALID_TIME", "minutes"));
        }
        let on = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        let note = clean_opt(input.note.as_deref());
        max_chars(note.as_deref(), TOPIC_MAX_CHARS, "note")?;
        let row = repo::StudyLogRow {
            id: self.new_id(),
            plan_id: p.id.clone(),
            occurred_on: ymd(on),
            minutes: i64::from(input.minutes),
            note,
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_study_log(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning]);
        self.one_learn_plan_dto(&ctx, &scope, &p.id)
    }

    /// «Ilm zakoti»: kimga (ixtiyoriy), nimani, qancha vaqt. Pul hisobi yo'q.
    pub fn teaching_log_add(
        &self,
        space_id: &str,
        input: TeachingLogInput,
    ) -> Result<TeachingLogDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.learn_scope(&ctx, space_id)?;
        self.learn_member(&ctx, &input.member_id)?;
        let t = self.check_teaching(
            &ctx,
            &input.topic,
            input.learner.as_deref(),
            input.minutes,
            input.occurred_on.as_deref(),
        )?;
        let row = repo::TeachingRow {
            id: self.new_id(),
            member_id: input.member_id,
            occurred_on: ymd(t.on),
            learner: t.learner,
            topic: t.topic,
            minutes: t.minutes,
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_teaching(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning]);
        Ok(teaching_dto(&row))
    }

    /// «O'zimga sarmoya» ekrani. `date` — oy ichidagi istalgan sana (standart — bugun).
    pub fn learning_overview(
        &self,
        space_id: &str,
        date: Option<&str>,
    ) -> Result<LearningOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.learn_scope(&ctx, space_id)?;
        let day = self.date_or_today(&ctx, date, "date")?;
        let (start, end) =
            month_period(day, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let (from, to) = (ymd(start), ymd(end));
        let plans = self.db.read(|c| repo::plans(c, &scope))?;
        let totals = self.learn_plan_totals(&scope, None)?;
        let mut members = Vec::new();
        for m in self
            .db
            .read(|c| household::list_members(c, &ctx.household_id))?
        {
            let hv = totals
                .latest
                .get(&m.id)
                .and_then(|id| totals.hours.get(id))
                .map(|r| self.hour_dto(&ctx, r))
                .transpose()?;
            let active = plans
                .iter()
                .filter(|p| p.member_id == m.id && p.status == PlanStatus::Active.as_str())
                .count();
            members.push(LearningMemberDto {
                member_id: m.id,
                display_name: m.display_name,
                hour_value: hv,
                active_plans: u32::try_from(active).unwrap_or(u32::MAX),
            });
        }
        let teaching: Vec<TeachingLogDto> = self
            .db
            .read(|c| repo::teaching_between(c, &scope, &from, &to))?
            .iter()
            .map(teaching_dto)
            .collect();
        let cur = ctx.currency;
        let income = Money::sum(
            self.db
                .read(|c| incomes::list_between(c, &scope, &from, &to))?
                .iter()
                .filter(|r| r.currency == cur.code())
                .map(|r| Money::new(r.amount_minor, cur)),
            cur,
        )?;
        let exp = self
            .db
            .read(|c| expenses::list_between(c, &scope, &from, &to))?;
        Ok(LearningOverviewDto {
            period_start: from,
            period_end: to,
            members,
            plans: plans
                .iter()
                .map(|p| self.learn_plan_dto(&ctx, p, &totals))
                .collect::<Result<_, _>>()?,
            teaching_count: u32::try_from(teaching.len()).unwrap_or(u32::MAX),
            teaching,
            self_investment: self.self_investment_dto(&ctx, income, &exp)?,
        })
    }
}

fn teaching_dto(r: &repo::TeachingRow) -> TeachingLogDto {
    TeachingLogDto {
        id: r.id.clone(),
        member_id: r.member_id.clone(),
        occurred_on: r.occurred_on.clone(),
        learner: r.learner.clone(),
        topic: r.topic.clone(),
        minutes: r.minutes.and_then(|m| u32::try_from(m).ok()),
    }
}
