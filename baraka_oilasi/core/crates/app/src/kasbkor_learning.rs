//! K9 — Kasb-kor makonida 8-tamoyil «O'zingizga sarmoya qiling» (`docs/kasbkor/SPEC.md` 8A):
//! egasining soat qiymati (yopilgan oylardan taklif), «O'zim qilaymi yoki o'rgatib topshiraymi?»,
//! xodimga o'rgatish («Ilm zakoti») va «Sarmoya (o'qish)» qatori.
//!
//! Qoidalar `domain-kasbkor::invest` (vektorlar `kk_owner_hour`, `kk_delegate`) va umumiy
//! `domain-uy::learning::hour_value` (Uy U16 bilan bir xil formula) da; bu yerda saqlash va yig'ish.
//! Hammasi egasi bo'limi: sotuvchi qurilmasida yopiq (soat qiymati foydadan hisoblanadi).
use baraka_domain_common::month_period;
use baraka_domain_kasbkor::invest::{delegate, owner_earnings, DelegateInput, OWNER_AVG_MONTHS};
use baraka_domain_uy::learning::{average_income, hour_value, HourInput};
use baraka_money::{Currency, Money};
use baraka_storage::repo::{kk_learning as repo, kk_staff};
use baraka_storage::SpaceScope;

use crate::app::Ctx;
use crate::events::Topic;
use crate::learn_common::{amount, hour_err, max_chars, u32_of};
use crate::receipt::ymd;
use crate::text::{clean, clean_opt};
use crate::*;

const EMPLOYMENT: &str = "EMPLOYMENT";
const TASK_MAX_CHARS: usize = 120;
const TOPIC_MAX_CHARS: usize = 200;
const LEARNER_MAX_CHARS: usize = 120;
/// Bitta o'rgatish yozuvi: ko'pi bilan bir kun (Uy 2G.6 bilan bir xil).
const TEACH_MAX_MINUTES: u32 = 1_440;

/// Qaror kalkulyatorining daqiqa chegarasi (oyiga) va soat qiymati yo'qligi — aniq kodlar.
fn delegate_err(e: baraka_domain_common::DomainError) -> AppError {
    match e.code {
        "INVALID_TIME" => AppError::on("INVALID_TASK_TIME", e.field.unwrap_or("taskMinutes")),
        "NO_HOUR_VALUE" => AppError::on("KK_NO_HOUR_VALUE", "ownerHourValue"),
        _ => e.into(),
    }
}

/// Bitta yopilgan oy: davr, o'z mehnati bahosi, haqiqiy foyda va egasi topgani.
struct OwnerMonth {
    start: String,
    end: String,
    labor: Money,
    profit: Money,
    earned: Money,
}

impl App {
    /// Oxirgi ko'pi bilan 3 ta yopilgan oy (yangisidan eskisiga): qotirilgan bayonnoma raqamlaridan
    /// egasi topgani `max(0, o'z mehnati + haqiqiy foyda)`. Sozlamalar (o'z mehnati, oilaviy mehnat,
    /// uskuna, oy boshi kuni) keyin o'zgarsa ham natija o'zgarmaydi; daftar qayta o'ynalmaydi.
    fn kk_owner_months(&self, ctx: &Ctx, scope: &SpaceScope) -> Result<Vec<OwnerMonth>, AppError> {
        self.kk_closed_owner_months(ctx, scope, OWNER_AVG_MONTHS)?
            .into_iter()
            .map(|(start, end, labor, profit)| {
                Ok(OwnerMonth {
                    earned: owner_earnings(labor, profit)?,
                    start,
                    end,
                    labor,
                    profit,
                })
            })
            .collect()
    }

    fn kk_hour_dto(&self, ctx: &Ctx, r: &repo::KkOwnerHourRow) -> Result<KkOwnerHourDto, AppError> {
        // Saqlangan daromad va vaqtdan qayta hisob — «ikki barobar maqsad» va soat chegarasi uchun.
        let h = hour_value(&HourInput {
            income: Some(r.income_minor),
            month_totals: &[],
            minutes_per_day: r.minutes_per_day,
            days: r.days,
        })?;
        let cur = Currency::from_code(&r.currency)?;
        let d = |v: i64| self.money_dto(ctx, Money::new(v, cur));
        Ok(KkOwnerHourDto {
            id: r.id.clone(),
            income: d(r.income_minor),
            income_source: r.income_source.clone(),
            months: u32_of(r.months)?,
            minutes_per_day: u32_of(r.minutes_per_day)?,
            days: u32_of(r.days)?,
            monthly_minutes: h.monthly_minutes,
            hour_value: d(r.hour_value_minor),
            double_target: d(r
                .hour_value_minor
                .checked_mul(2)
                .ok_or(AppError::new("OVERFLOW"))?),
            over_ceiling: h.over_ceiling,
            computed_on: r.computed_on.clone(),
        })
    }

    /// Xodim kartochkalari (`EMPLOYMENT`): (id, ism, tugaganmi).
    fn kk_staff_cards(&self, scope: &SpaceScope) -> Result<Vec<(String, String, bool)>, AppError> {
        Ok(self
            .db
            .read(|c| kk_staff::agreements(c, scope))?
            .into_iter()
            .filter(|a| a.kind == EMPLOYMENT)
            .map(|a| (a.id, a.party_name, a.status == "ENDED"))
            .collect())
    }

    /// Bog'lanadigan xodim kartochkasi: shu makondagi tugamagan `EMPLOYMENT` kelishuvi (tanlov ro'yxati
    /// bilan bir xil qoida).
    fn kk_staff_link(
        &self,
        scope: &SpaceScope,
        id: Option<&str>,
    ) -> Result<Option<String>, AppError> {
        let Some(id) = id.map(clean).filter(|s| !s.is_empty()) else {
            return Ok(None);
        };
        let a = self
            .db
            .read(|c| kk_staff::agreements(c, scope))?
            .into_iter()
            .find(|a| a.id == id)
            .ok_or(AppError::on("NOT_FOUND", "agreementId"))?;
        if a.kind != EMPLOYMENT {
            return Err(AppError::on("NOT_EMPLOYMENT", "agreementId"));
        }
        if a.status == "ENDED" {
            return Err(AppError::on("AGREEMENT_ENDED", "agreementId"));
        }
        Ok(Some(id))
    }

    /// Oxirgi saqlangan soat qiymati xonadonning hozirgi valyutasida (ekran va kalkulyator — bir xil).
    fn kk_latest_hour(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
    ) -> Result<Option<repo::KkOwnerHourRow>, AppError> {
        Ok(self
            .db
            .read(|c| repo::owner_hours(c, scope))?
            .into_iter()
            .find(|h| h.currency == ctx.currency.code()))
    }

    /// Kiritmalardan hisob (egasining soat qiymati bo'sh bo'lsa — oxirgi saqlangan hisob).
    fn kk_delegate_compute(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        input: &KkDelegateInput,
    ) -> Result<(DelegateInput, KkDelegateResultDto), AppError> {
        let cur = ctx.currency;
        let owner = match input.owner_hour_value.as_deref().map(str::trim) {
            None | Some("") => self
                .kk_latest_hour(ctx, scope)?
                .map(|h| h.hour_value_minor)
                .ok_or(AppError::on("KK_NO_HOUR_VALUE", "ownerHourValue"))?,
            Some(s) => amount(s, cur, "ownerHourValue")?,
        };
        let d = DelegateInput {
            owner_hour_value: owner,
            task_minutes: input.task_minutes,
            helper_hour_cost: amount(&input.helper_hour_cost, cur, "helperHourCost")?,
            training_money: match input.training_money.as_deref().map(str::trim) {
                None | Some("") => 0,
                Some(s) => amount(s, cur, "trainingMoney")?,
            },
            training_minutes: input.training_minutes,
        };
        let r = self.kk_delegate_result(ctx, cur, &d)?;
        Ok((d, r))
    }

    fn kk_delegate_result(
        &self,
        ctx: &Ctx,
        cur: Currency,
        d: &DelegateInput,
    ) -> Result<KkDelegateResultDto, AppError> {
        let r = delegate(d).map_err(delegate_err)?;
        let m = |v: i64| self.money_dto(ctx, Money::new(v, cur));
        Ok(KkDelegateResultDto {
            owner_hour_value: m(d.owner_hour_value),
            monthly_benefit: m(r.monthly_benefit),
            training_time_cost: m(r.training_time_cost),
            full_cost: m(r.full_cost),
            payback_months: r
                .payback_months
                .map(|v| u32::try_from(v).unwrap_or(u32::MAX)),
            verdict: r.verdict.as_str().into(),
        })
    }

    fn kk_delegation_dto(
        &self,
        ctx: &Ctx,
        r: &repo::KkDelegationRow,
        staff: &[(String, String, bool)],
    ) -> Result<KkDelegationDto, AppError> {
        let cur = Currency::from_code(&r.currency)?;
        let d = DelegateInput {
            owner_hour_value: r.owner_hour_value_minor,
            task_minutes: u32_of(r.task_minutes)?,
            helper_hour_cost: r.helper_hour_cost_minor,
            training_money: r.training_money_minor,
            training_minutes: u32_of(r.training_minutes)?,
        };
        let m = |v: i64| self.money_dto(ctx, Money::new(v, cur));
        Ok(KkDelegationDto {
            id: r.id.clone(),
            task: r.task.clone(),
            agreement_id: r.agreement_id.clone(),
            staff_name: staff_name(staff, r.agreement_id.as_deref()),
            task_minutes: d.task_minutes,
            helper_hour_cost: m(d.helper_hour_cost),
            training_money: m(d.training_money),
            training_minutes: d.training_minutes,
            decided_on: r.decided_on.clone(),
            result: self.kk_delegate_result(ctx, cur, &d)?,
        })
    }

    // ---- 8A.1 Egasining soat qiymati ----

    /// Oylik topgani taklifi: oxirgi 3 yopilgan oy («Hisob kuni») — o'z mehnati + haqiqiy foyda (manfiy
    /// bo'lsa 0); egasiga to'langan maosh qo'shilmaydi.
    pub fn kk_owner_hour_suggest(
        &self,
        space_id: &str,
    ) -> Result<KkOwnerHourSuggestionDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let months = self.kk_owner_months(&ctx, &scope)?;
        let totals: Vec<i64> = months.iter().map(|m| m.earned.minor()).collect();
        let average = average_income(&totals)?
            .filter(|v| *v > 0)
            .map(|v| self.money_dto(&ctx, Money::new(v, ctx.currency)));
        Ok(KkOwnerHourSuggestionDto {
            months: months
                .iter()
                .map(|m| KkOwnerMonthDto {
                    period_start: m.start.clone(),
                    period_end: m.end.clone(),
                    owner_labor: self.money_dto(&ctx, m.labor),
                    true_profit: self.money_dto(&ctx, m.profit),
                    earnings: self.money_dto(&ctx, m.earned),
                })
                .collect(),
            average,
        })
    }

    /// Egasining soat qiymatini hisoblaydi va o'zgarmas tarixga yozadi. Daromad bo'sh — `AUTO`.
    pub fn kk_owner_hour_save(
        &self,
        space_id: &str,
        input: KkOwnerHourInput,
    ) -> Result<KkOwnerHourDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let income = match input.income.as_deref().map(str::trim) {
            None | Some("") => None,
            Some(s) => Some(amount(s, ctx.currency, "income")?),
        };
        let totals: Vec<i64> = if income.is_none() {
            self.kk_owner_months(&ctx, &scope)?
                .iter()
                .map(|m| m.earned.minor())
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
        let row = repo::KkOwnerHourRow {
            id: self.new_id(),
            income_minor: h.income,
            currency: ctx.currency.code().to_string(),
            income_source: h.source.as_str().to_string(),
            months: i64::try_from(totals.len()).unwrap_or(0),
            minutes_per_day: i64::from(input.minutes_per_day),
            days: i64::from(input.days),
            hour_value_minor: h.hour_value,
            computed_on: ymd(self.today(&ctx)),
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_owner_hour(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning]);
        self.kk_hour_dto(&ctx, &row)
    }

    // ---- 8A.2 «O'zim qilaymi yoki o'rgatib topshiraymi?» ----

    /// Hisob (hech narsa saqlanmaydi). Ilova ish haqi miqdorini tavsiya qilmaydi — narxni egasi kiritadi.
    pub fn kk_delegate_calc(
        &self,
        space_id: &str,
        input: KkDelegateInput,
    ) -> Result<KkDelegateResultDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        Ok(self.kk_delegate_compute(&ctx, &scope, &input)?.1)
    }

    /// Qarorni saqlash (ixtiyoriy xodim kartochkasi bilan).
    pub fn kk_delegation_save(
        &self,
        space_id: &str,
        input: KkDelegateInput,
    ) -> Result<KkDelegationDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let task = crate::text::required(&input.task, "task")?;
        max_chars(Some(&task), TASK_MAX_CHARS, "task")?;
        let agreement_id = self.kk_staff_link(&scope, input.agreement_id.as_deref())?;
        let (d, _) = self.kk_delegate_compute(&ctx, &scope, &input)?;
        let row = repo::KkDelegationRow {
            id: self.new_id(),
            task,
            agreement_id,
            currency: ctx.currency.code().to_string(),
            owner_hour_value_minor: d.owner_hour_value,
            task_minutes: i64::from(d.task_minutes),
            helper_hour_cost_minor: d.helper_hour_cost,
            training_money_minor: d.training_money,
            training_minutes: i64::from(d.training_minutes),
            decided_on: ymd(self.today(&ctx)),
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_delegation(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning]);
        let staff = self.kk_staff_cards(&scope)?;
        self.kk_delegation_dto(&ctx, &row, &staff)
    }

    pub fn kk_delegation_delete(&self, space_id: &str, id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db
            .write(|tx| repo::delete_delegation(tx, &scope, id, &meta))
            .map_err(|e| match e {
                baraka_storage::StorageError::NotFound => AppError::on("NOT_FOUND", "id"),
                other => other.into(),
            })?;
        self.publish(Some(space_id), &[Topic::Learning]);
        Ok(())
    }

    // ---- 8A.3 «Ilm zakoti» — xodimga o'rgatish ----

    /// Kimga: xodim kartochkasi yoki boshqa kishi (ikkalasi birga emas), nimani, qancha vaqt.
    pub fn kk_teaching_add(
        &self,
        space_id: &str,
        input: KkTeachingInput,
    ) -> Result<KkTeachingDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let topic = crate::text::required(&input.topic, "topic")?;
        max_chars(Some(&topic), TOPIC_MAX_CHARS, "topic")?;
        let agreement_id = self.kk_staff_link(&scope, input.agreement_id.as_deref())?;
        let learner = clean_opt(input.learner.as_deref());
        max_chars(learner.as_deref(), LEARNER_MAX_CHARS, "learner")?;
        if agreement_id.is_some() && learner.is_some() {
            return Err(AppError::on("LEARNER_TWICE", "learner"));
        }
        if input
            .minutes
            .is_some_and(|m| !(1..=TEACH_MAX_MINUTES).contains(&m))
        {
            return Err(AppError::on("INVALID_TIME", "minutes"));
        }
        let on = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        let row = repo::KkTeachingRow {
            id: self.new_id(),
            occurred_on: ymd(on),
            agreement_id,
            learner,
            topic,
            minutes: input.minutes.map(i64::from),
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_teaching(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Learning]);
        let staff = self.kk_staff_cards(&scope)?;
        Ok(teaching_dto(&row, &staff))
    }

    /// Kasb-kor «O'zimga sarmoya» ekrani. `date` — oy ichidagi istalgan sana (standart — bugun).
    pub fn kk_learning_overview(
        &self,
        space_id: &str,
        date: Option<&str>,
    ) -> Result<KkLearningOverviewDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.kk_scope(&ctx, space_id)?;
        let day = self.date_or_today(&ctx, date, "date")?;
        let (start, end) =
            month_period(day, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let (from, to) = (ymd(start), ymd(end));
        let staff = self.kk_staff_cards(&scope)?;
        let hour_value = self
            .kk_latest_hour(&ctx, &scope)?
            .map(|r| self.kk_hour_dto(&ctx, &r))
            .transpose()?;
        let delegations = self
            .db
            .read(|c| repo::delegations(c, &scope))?
            .iter()
            .map(|r| self.kk_delegation_dto(&ctx, r, &staff))
            .collect::<Result<Vec<_>, _>>()?;
        let teaching: Vec<KkTeachingDto> = self
            .db
            .read(|c| repo::teaching_between(c, &scope, &from, &to))?
            .iter()
            .map(|r| teaching_dto(r, &staff))
            .collect();
        let last = ymd(end.pred_opt().ok_or(AppError::new("INVALID_PERIOD"))?);
        let invested = self.kk_self_investment_totals(&ctx, &scope, &[(from.clone(), last)])?[0];
        Ok(KkLearningOverviewDto {
            period_start: from,
            period_end: to,
            hour_value,
            delegations,
            staff: staff
                .iter()
                .filter(|(_, _, ended)| !ended)
                .map(|(id, name, _)| KkStaffOptionDto {
                    id: id.clone(),
                    name: name.clone(),
                })
                .collect(),
            teaching_count: u32::try_from(teaching.len()).unwrap_or(u32::MAX),
            teaching,
            self_investment: self.money_dto(&ctx, invested),
        })
    }
}

fn staff_name(staff: &[(String, String, bool)], id: Option<&str>) -> Option<String> {
    let id = id?;
    staff
        .iter()
        .find(|(sid, _, _)| sid == id)
        .map(|(_, name, _)| name.clone())
}

fn teaching_dto(r: &repo::KkTeachingRow, staff: &[(String, String, bool)]) -> KkTeachingDto {
    KkTeachingDto {
        id: r.id.clone(),
        occurred_on: r.occurred_on.clone(),
        agreement_id: r.agreement_id.clone(),
        learner: staff_name(staff, r.agreement_id.as_deref()).or_else(|| r.learner.clone()),
        topic: r.topic.clone(),
        minutes: r.minutes.and_then(|m| u32::try_from(m).ok()),
    }
}
