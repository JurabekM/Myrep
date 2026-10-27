//! M6 — Musofir makonida 8-tamoyil «O'zingizga sarmoya qiling» (`docs/musofir/SPEC.md` 6A): soat
//! qiymati ish valyutasida (va kurs bilan uy valyutasida), ikki maqsadli bilim rejasi (`ABROAD` /
//! `HOME`), «Ilm zakoti» (hamyurtlarga yordam) va oy hisobidagi «Sarmoya» qatori.
//!
//! Qoidalar umumiy: `domain-uy::learning` (soat qiymati, reja tekshiruvi, holat o'tishlari, natija,
//! sarmoya ulushi — Uy U16 bilan bir xil, app qatlami `learn_common` da) va `domain-musofir::invest`
//! (uy valyutasidagi ko'rinish, vektor `mf_hour_value`). Bu yerda saqlash va yig'ish.
//!
//! Hammasi musofirning shaxsiy hisobi: soat qiymati chet eldagi maoshdan hisoblanadi, shuning uchun
//! jadvallar `space_id = Musofir` — uydagi oila qurilmasiga umuman yuborilmaydi (ADR-0004), use-case'lar
//! u yerda `ROLE_FORBIDDEN`.
use std::collections::HashMap;

use baraka_domain_common::month_period;
use baraka_domain_musofir::invest::{home_hour_value, RateAt};
use baraka_domain_uy::learning::{
    average_income, check_activation, hour_value, HourInput, PathKind, PlanStatus, AVG_MONTHS,
};
use baraka_money::{format_percent_bp, Currency, FxRate, Money};
use baraka_storage::repo::{expenses, incomes, mf, mf_learning as repo, ventures};
use baraka_storage::SpaceScope;
use chrono::NaiveDate;

use crate::app::Ctx;
use crate::events::Topic;
use crate::learn_common::{
    bp32, closed, hour_err, max_chars, measure_plan, next_status, opt_amount, parse_paths,
    paths_text, plan_status, u32_of, PlanFields,
};
use crate::receipt::ymd;
use crate::text::clean_opt;
use crate::*;

const GOALS: [&str; 2] = ["ABROAD", "HOME"];
const AREAS: [&str; 4] = ["WORK", "LANGUAGE", "DOCUMENTS", "OTHER"];
/// Bitta o'rgatish yozuvi: ko'pi bilan bir kun (Uy 2G.6 bilan bir xil).
const TEACH_MAX_MINUTES: u32 = 1_440;
const TOPIC_MAX_CHARS: usize = 200;
const LEARNER_MAX_CHARS: usize = 120;

/// Amaldagi kurs (so'rovda bir marta o'qiladi).
type Rate = Option<(FxRate, MfRateDto)>;

/// Makonning soat qiymati hisoblari (id bo'yicha) va ish valyutasidagi oxirgisi — bitta so'rov bilan.
struct Hours {
    by_id: HashMap<String, repo::MfHourRow>,
    latest: Option<repo::MfHourRow>,
}

impl Hours {
    fn money(&self, app: &App, ctx: &Ctx, id: Option<&str>) -> Result<Option<MoneyDto>, AppError> {
        let Some(r) = id.and_then(|i| self.by_id.get(i)) else {
            return Ok(None);
        };
        let cur = Currency::from_code(&r.currency)?;
        Ok(Some(
            app.money_dto(ctx, Money::new(r.hour_value_minor, cur)),
        ))
    }
}

impl App {
    /// Musofir shaxsiy bo'limi va sozlangan ish valyutasi.
    fn mfl_scope(&self, ctx: &Ctx, space_id: &str) -> Result<(SpaceScope, Currency), AppError> {
        let scope = self.mf_scope(ctx, space_id)?;
        let row = self
            .db
            .read(|c| mf::settings(c, &scope))?
            .ok_or(AppError::new("MF_NOT_CONFIGURED"))?;
        let work =
            Currency::from_code(&row.work_currency).map_err(|_| AppError::new("CORRUPT_ROW"))?;
        Ok((scope, work))
    }

    /// `[from, to)` dagi oy daromadi ish valyutasida — `mf_month` ta'rifidagidek (maosh + boshqa daromad).
    fn mf_month_income(
        &self,
        scope: &SpaceScope,
        work: Currency,
        from: &str,
        to: &str,
    ) -> Result<Option<Money>, AppError> {
        let rows: Vec<Money> = self
            .db
            .read(|c| incomes::list_between(c, scope, from, to))?
            .into_iter()
            .filter(|r| r.currency == work.code())
            .map(|r| Money::new(r.amount_minor, work))
            .collect();
        if rows.is_empty() {
            Ok(None)
        } else {
            Ok(Some(Money::sum(rows, work)?))
        }
    }

    /// Oxirgi 3 to'liq oy (xonadon oylik davri bo'yicha) — daromad yozuvi borlari, ish valyutasida,
    /// yangisidan eskisiga: (boshi, oxiri `[start, end)`, jami).
    fn mf_income_months(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        work: Currency,
    ) -> Result<Vec<(NaiveDate, NaiveDate, Money)>, AppError> {
        let (mut cursor, _) = month_period(self.today(ctx), ctx.month_start_day)
            .ok_or(AppError::new("INVALID_PERIOD"))?;
        let mut out = Vec::new();
        for _ in 0..AVG_MONTHS {
            let Some(prev) = cursor.pred_opt() else { break };
            let (start, end) =
                month_period(prev, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
            if let Some(total) = self.mf_month_income(scope, work, &ymd(start), &ymd(end))? {
                out.push((start, end, total));
            }
            cursor = start;
        }
        Ok(out)
    }

    /// Oy hisobidagi «Sarmoya» qatori (bosh sahifadagi oy hisobi va «O'zimga sarmoya» ekrani — bitta
    /// manba): `[from, last]` dagi belgili xarajatlar ish valyutasida va oy daromadidagi ulushi. Belgi oy
    /// hisobini o'zgartirmaydi — xarajat o'z toifasida qoladi.
    pub(crate) fn mf_self_investment(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        income: Money,
        from: &str,
        last: &str,
    ) -> Result<SelfInvestmentDto, AppError> {
        let cur = income.currency().code();
        let amounts: Vec<i64> = self
            .db
            .read(|c| expenses::self_investment_between(c, scope, from, last))?
            .into_iter()
            .filter(|(_, c, _)| c == cur)
            .map(|(_, _, v)| v)
            .collect();
        self.self_investment_of(ctx, income, &amounts)
    }

    /// Makonning hisoblari bitta so'rov bilan.
    fn mf_hours(&self, scope: &SpaceScope, work: Currency) -> Result<Hours, AppError> {
        // Saqlangan tartibda (yangisi birinchi): ish valyutasidagi birinchisi — oxirgi hisob.
        let rows = self.db.read(|c| repo::hours(c, scope))?;
        let latest = rows.iter().find(|h| h.currency == work.code()).cloned();
        Ok(Hours {
            by_id: rows.into_iter().map(|r| (r.id.clone(), r)).collect(),
            latest,
        })
    }

    /// Uy valyutasidagi ko'rinish — amaldagi kurs bilan (kurs yo'q — qiymat yo'q).
    fn mf_hour_home(&self, ctx: &Ctx, rate: &Rate, hour: Money) -> Result<MfHourHomeDto, AppError> {
        let at = match rate {
            Some((fx, dto)) => {
                let on = NaiveDate::parse_from_str(&dto.rate_on, "%Y-%m-%d")
                    .map_err(|_| AppError::new("CORRUPT_ROW"))?;
                Some(RateAt {
                    rate: *fx,
                    age_days: Some((self.today(ctx) - on).num_days()),
                })
            }
            None => None,
        };
        let h = home_hour_value(hour, ctx.currency, at.as_ref())?;
        Ok(MfHourHomeDto {
            rate_status: h.status.as_str().to_string(),
            hour_value: h.hour_value.map(|m| self.money_dto(ctx, m)),
            double_target: h.double_target.map(|m| self.money_dto(ctx, m)),
            rate: rate.as_ref().map(|(_, dto)| dto.clone()),
        })
    }

    fn mf_hour_dto(
        &self,
        ctx: &Ctx,
        rate: &Rate,
        r: &repo::MfHourRow,
    ) -> Result<MfHourDto, AppError> {
        // Saqlangan daromad va vaqtdan qayta hisob — «ikki barobar maqsad» va soat chegarasi uchun.
        let h = hour_value(&HourInput {
            income: Some(r.income_minor),
            month_totals: &[],
            minutes_per_day: r.minutes_per_day,
            days: r.days,
        })?;
        let cur = Currency::from_code(&r.currency)?;
        let d = |v: i64| self.money_dto(ctx, Money::new(v, cur));
        Ok(MfHourDto {
            id: r.id.clone(),
            income: d(r.income_minor),
            income_source: r.income_source.clone(),
            months: u32_of(r.months)?,
            minutes_per_day: u32_of(r.minutes_per_day)?,
            days: u32_of(r.days)?,
            monthly_minutes: h.monthly_minutes,
            hour_value: d(r.hour_value_minor),
            double_target: d(h.double_target),
            over_ceiling: h.over_ceiling,
            computed_on: r.computed_on.clone(),
            home: self.mf_hour_home(ctx, rate, Money::new(r.hour_value_minor, cur))?,
        })
    }

    /// Uy makonidagi «Hunardan ishga» g'oyalari (Uy makoni bo'lmasa — bo'sh).
    fn mf_ideas(&self, ctx: &Ctx) -> Result<Vec<MfIdeaOptionDto>, AppError> {
        let Some(uy) = self.uy_space(ctx)? else {
            return Ok(Vec::new());
        };
        Ok(self
            .db
            .read(|c| ventures::ideas(c, &uy))?
            .into_iter()
            .map(|i| MfIdeaOptionDto {
                id: i.id,
                title: i.title,
            })
            .collect())
    }

    fn mf_plan_dto(
        &self,
        ctx: &Ctx,
        p: &repo::MfPlanRow,
        ideas: &[MfIdeaOptionDto],
        hours: &Hours,
    ) -> Result<MfLearningPlanDto, AppError> {
        let cur = Currency::from_code(&p.currency)?;
        let paths = parse_paths(&p.paths);
        let open = !closed(plan_status(&p.status)?);
        Ok(MfLearningPlanDto {
            id: p.id.clone(),
            goal: p.goal.clone(),
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
            baseline_hour_value: hours.money(self, ctx, p.baseline_hour_value_id.as_deref())?,
            result_hour_value: hours.money(self, ctx, p.result_hour_value_id.as_deref())?,
            venture_idea_title: p
                .venture_idea_id
                .as_ref()
                .and_then(|id| ideas.iter().find(|i| &i.id == id))
                .map(|i| i.title.clone()),
            venture_idea_id: p.venture_idea_id.clone(),
        })
    }

    fn mf_plan(&self, scope: &SpaceScope, id: &str) -> Result<repo::MfPlanRow, AppError> {
        self.db
            .read(|c| repo::plan(c, scope, id))?
            .ok_or(AppError::on("NOT_FOUND", "planId"))
    }

    /// O'zgarishdan keyingi bitta reja kartasi.
    fn one_mf_plan_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        work: Currency,
        plan_id: &str,
    ) -> Result<MfLearningPlanDto, AppError> {
        let p = self.mf_plan(scope, plan_id)?;
        let hours = self.mf_hours(scope, work)?;
        self.mf_plan_dto(ctx, &p, &self.mf_ideas(ctx)?, &hours)
    }

    // ---- Soat qiymati ----

    /// Oylik daromad taklifi: oxirgi 3 to'liq oydagi (daromad yozuvi borlari) maosh + boshqa daromad.
    pub fn mf_hour_suggest(&self, space_id: &str) -> Result<MfHourSuggestionDto, AppError> {
        let ctx = self.ctx()?;
        let (scope, work) = self.mfl_scope(&ctx, space_id)?;
        let months = self.mf_income_months(&ctx, &scope, work)?;
        let totals: Vec<i64> = months.iter().map(|(_, _, m)| m.minor()).collect();
        Ok(MfHourSuggestionDto {
            average: average_income(&totals)?.map(|v| self.money_dto(&ctx, Money::new(v, work))),
            // Oy oxiri — oxirgi kun (bosh sahifadagi oy hisobi kabi), `[start, end)` emas.
            months: months
                .iter()
                .map(|(s, e, m)| MonthIncomeDto {
                    period_start: ymd(*s),
                    period_end: ymd(e.pred_opt().unwrap_or(*e)),
                    total: self.money_dto(&ctx, *m),
                })
                .collect(),
        })
    }

    /// Soat qiymatini hisoblaydi va o'zgarmas tarixga yozadi (ish valyutasida). Daromad bo'sh — `AUTO`.
    pub fn mf_hour_save(&self, space_id: &str, input: MfHourInput) -> Result<MfHourDto, AppError> {
        let ctx = self.ctx()?;
        let (scope, work) = self.mfl_scope(&ctx, space_id)?;
        let income = opt_amount(input.income.as_deref(), work, "income")?;
        let totals: Vec<i64> = if income.is_none() {
            self.mf_income_months(&ctx, &scope, work)?
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
        let row = repo::MfHourRow {
            id: self.new_id(),
            income_minor: h.income,
            currency: work.code().to_string(),
            income_source: h.source.as_str().to_string(),
            months: i64::try_from(totals.len()).unwrap_or(0),
            minutes_per_day: i64::from(input.minutes_per_day),
            days: i64::from(input.days),
            hour_value_minor: h.hour_value,
            computed_on: ymd(self.today(&ctx)),
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_hour(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning, Topic::Musofir]);
        let rate = self.mf_rate(&ctx, &scope, work)?;
        self.mf_hour_dto(&ctx, &rate, &row)
    }

    // ---- Bilim rejasi (ikki maqsad) ----

    /// Reja ochish: musofirda ko'pi bilan 2 ta faol reja (ikkala maqsad birga); boshlang'ich nuqta —
    /// oxirgi soat qiymati. `HOME` reja «Hunardan ishga» g'oyasiga bog'lanishi mumkin. Kiritmalar
    /// tekshiruvi Uy bilan umumiy (`check_plan`), byudjet — ish valyutasida.
    pub fn mf_learning_plan_create(
        &self,
        space_id: &str,
        input: MfLearningPlanInput,
    ) -> Result<MfLearningPlanDto, AppError> {
        let ctx = self.ctx()?;
        let (scope, work) = self.mfl_scope(&ctx, space_id)?;
        let goal = input.goal.trim();
        if !GOALS.contains(&goal) {
            return Err(AppError::on("INVALID_GOAL", "goal"));
        }
        let checked = self.check_plan(
            &ctx,
            work,
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
        let ideas = self.mf_ideas(&ctx)?;
        let idea = match clean_opt(input.venture_idea_id.as_deref()) {
            None => None,
            Some(_) if goal != "HOME" => {
                return Err(AppError::on("IDEA_HOME_ONLY", "ventureIdeaId"))
            }
            Some(id) if ideas.iter().any(|i| i.id == id) => Some(id),
            Some(_) => return Err(AppError::on("NOT_FOUND", "ventureIdeaId")),
        };
        check_activation(
            self.db
                .read(|c| repo::other_active_plans(c, &scope, None))?,
        )?;
        let hours = self.mf_hours(&scope, work)?;
        let row = repo::MfPlanRow {
            id: self.new_id(),
            goal: goal.to_string(),
            paths: paths_text(&plan),
            skill: plan.skill,
            purpose: checked.purpose,
            budget_minor: plan.budget,
            currency: work.code().to_string(),
            weekly_minutes: i64::from(plan.weekly_minutes),
            start_on: ymd(plan.start),
            review_on: ymd(plan.review),
            status: PlanStatus::Active.as_str().to_string(),
            baseline_hour_value_id: hours.latest.as_ref().map(|h| h.id.clone()),
            result_hour_value_id: None,
            venture_idea_id: idea,
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_plan(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning, Topic::Musofir]);
        self.mf_plan_dto(&ctx, &row, &ideas, &hours)
    }

    /// Holat o'zgarishi: yopilgan reja qayta ochilmaydi; `PAUSED → ACTIVE` da chegara qayta tekshiriladi.
    pub fn mf_learning_plan_set_status(
        &self,
        space_id: &str,
        plan_id: &str,
        status: &str,
    ) -> Result<MfLearningPlanDto, AppError> {
        let ctx = self.ctx()?;
        let (scope, work) = self.mfl_scope(&ctx, space_id)?;
        let p = self.mf_plan(&scope, plan_id)?;
        let others = self
            .db
            .read(|c| repo::other_active_plans(c, &scope, Some(&p.id)))?;
        let to = next_status(&p.status, status, others)?;
        let meta = self.meta();
        self.db
            .write(|tx| repo::set_plan_status(tx, &scope, &p.id, to.as_str(), &meta))?;
        self.publish(Some(space_id), &[Topic::Learning, Topic::Musofir]);
        self.one_mf_plan_dto(&ctx, &scope, work, &p.id)
    }

    /// Natijani o'lchash (Uy 2G.5 bilan umumiy qoidalar): oxirgi soat qiymati boshlang'ich nuqta bilan,
    /// ish valyutasida. Ilova o'sishni va'da qilmaydi — farq faqat ko'rsatiladi.
    pub fn mf_learning_plan_result(
        &self,
        space_id: &str,
        plan_id: &str,
    ) -> Result<MfLearningResultDto, AppError> {
        let ctx = self.ctx()?;
        let (scope, work) = self.mfl_scope(&ctx, space_id)?;
        let p = self.mf_plan(&scope, plan_id)?;
        let mut hours = self.mf_hours(&scope, work)?;
        let latest = hours.latest.take();
        let m = measure_plan(
            plan_status(&p.status)?,
            p.result_hour_value_id.is_some(),
            p.baseline_hour_value_id.as_deref(),
            latest,
            |id| Ok(hours.by_id.get(id).cloned()),
        )?;
        let meta = self.meta();
        self.db
            .write(|tx| repo::set_plan_result(tx, &scope, &p.id, &m.current.id, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning, Topic::Musofir]);
        let rate = self.mf_rate(&ctx, &scope, work)?;
        let bp = m.change.and_then(|c| c.change_bp);
        Ok(MfLearningResultDto {
            plan_id: p.id,
            baseline: m
                .baseline
                .as_ref()
                .map(|b| self.mf_hour_dto(&ctx, &rate, b))
                .transpose()?,
            current: self.mf_hour_dto(&ctx, &rate, &m.current)?,
            diff: m
                .change
                .map(|c| self.money_dto(&ctx, Money::new(c.diff, work))),
            change_bp: bp.map(bp32),
            change_percent: bp.map(format_percent_bp),
        })
    }

    // ---- «Ilm zakoti» ----

    /// Yangi kelgan hamyurtlarga ish, til yoki hujjat bo'yicha yordam ham o'rgatish. Pul hisobi yo'q.
    pub fn mf_teaching_add(
        &self,
        space_id: &str,
        input: MfTeachingInput,
    ) -> Result<MfTeachingDto, AppError> {
        let ctx = self.ctx()?;
        let (scope, _) = self.mfl_scope(&ctx, space_id)?;
        let area = input.area.trim();
        if !AREAS.contains(&area) {
            return Err(AppError::on("INVALID_AREA", "area"));
        }
        let topic = crate::text::required(&input.topic, "topic")?;
        max_chars(Some(&topic), TOPIC_MAX_CHARS, "topic")?;
        let learner = clean_opt(input.learner.as_deref());
        max_chars(learner.as_deref(), LEARNER_MAX_CHARS, "learner")?;
        if input
            .minutes
            .is_some_and(|m| !(1..=TEACH_MAX_MINUTES).contains(&m))
        {
            return Err(AppError::on("INVALID_TIME", "minutes"));
        }
        let on = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        if on > self.today(&ctx) {
            return Err(AppError::on("FUTURE_DATE", "occurredOn"));
        }
        let row = repo::MfTeachingRow {
            id: self.new_id(),
            occurred_on: ymd(on),
            area: area.to_string(),
            learner,
            topic,
            minutes: input.minutes.map(i64::from),
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_teaching(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning, Topic::Musofir]);
        Ok(teaching_dto(&row))
    }

    /// Musofir «O'zimga sarmoya» ekrani. `date` — oy ichidagi istalgan sana (standart — bugun).
    pub fn mf_learning_overview(
        &self,
        space_id: &str,
        date: Option<&str>,
    ) -> Result<MfLearningOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let (scope, work) = self.mfl_scope(&ctx, space_id)?;
        let day = self.date_or_today(&ctx, date, "date")?;
        let (start, end) =
            month_period(day, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let last = end.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?;
        let (from, to) = (ymd(start), ymd(end));
        let ideas = self.mf_ideas(&ctx)?;
        let plans = self.db.read(|c| repo::plans(c, &scope))?;
        let teaching: Vec<MfTeachingDto> = self
            .db
            .read(|c| repo::teaching_between(c, &scope, &from, &to))?
            .iter()
            .map(teaching_dto)
            .collect();
        // Kurs va hisoblar — bir marta.
        let rate = self.mf_rate(&ctx, &scope, work)?;
        let hours = self.mf_hours(&scope, work)?;
        let hour = hours
            .latest
            .as_ref()
            .map(|r| self.mf_hour_dto(&ctx, &rate, r))
            .transpose()?;
        // «Sarmoya» qatori — bosh sahifadagi oy hisobi bilan bitta yordamchi.
        let income = self
            .mf_month_income(&scope, work, &from, &to)?
            .unwrap_or(Money::zero(work));
        let invest = self.mf_self_investment(&ctx, &scope, income, &from, &ymd(last))?;
        let startup = self
            .db
            .read(|c| mf::plan_info(c, &scope))?
            .startup_idea_id
            .filter(|id| ideas.iter().any(|i| &i.id == id));
        Ok(MfLearningOverviewDto {
            period_start: from,
            period_end: ymd(last),
            work_currency: work.code().to_string(),
            home_currency: ctx.currency.code().to_string(),
            hour_value: hour,
            active_plans: u32::try_from(
                plans
                    .iter()
                    .filter(|p| p.status == PlanStatus::Active.as_str())
                    .count(),
            )
            .unwrap_or(u32::MAX),
            plans: plans
                .iter()
                .map(|p| self.mf_plan_dto(&ctx, p, &ideas, &hours))
                .collect::<Result<_, _>>()?,
            startup_idea_id: startup,
            ideas,
            teaching_count: u32::try_from(teaching.len()).unwrap_or(u32::MAX),
            teaching,
            self_investment: invest,
        })
    }
}

fn teaching_dto(r: &repo::MfTeachingRow) -> MfTeachingDto {
    MfTeachingDto {
        id: r.id.clone(),
        occurred_on: r.occurred_on.clone(),
        area: r.area.clone(),
        learner: r.learner.clone(),
        topic: r.topic.clone(),
        minutes: r.minutes.and_then(|m| u32::try_from(m).ok()),
    }
}
