//! 8-tamoyil «O'zingizga sarmoya qiling» — uchala makon (Uy U16, Kasb-kor K9, Musofir M6) uchun
//! umumiy yordamchilar: kiritmalarni o'qish, xato kodlari, bilim rejasi tekshiruvi va natijani
//! o'lchash qoidalari. Qoidalarning o'zi `domain-uy::learning` da; bu yerda faqat bitta joyda
//! yig'ilgan app qatlami (xato kodlari va tartibi makonlarda bir xil qolishi uchun).
use baraka_domain_uy::learning::{
    hour_value_change, transition, validate_plan, HourChange, PathKind, PlanDraft, PlanStatus,
    ValidPlan,
};
use baraka_money::{parse_amount, Currency};
use chrono::NaiveDate;

use crate::app::Ctx;
use crate::text::{clean, clean_opt};
use crate::{App, AppError};

/// Reja maqsadi (`purpose`) matni chegarasi.
const PURPOSE_MAX_CHARS: usize = 200;

/// Bazadagi butun son DTO uchun (manfiy yoki juda katta — buzilgan yozuv).
pub(crate) fn u32_of(v: i64) -> Result<u32, AppError> {
    u32::try_from(v).map_err(|_| AppError::new("CORRUPT_ROW"))
}

/// Bazis punkt DTO uchun (i32 ga sig'masa — chegarada; matn ko'rinishi aniq qoladi).
pub(crate) fn bp32(v: i64) -> i32 {
    i32::try_from(v).unwrap_or(if v < 0 { i32::MIN } else { i32::MAX })
}

/// «Bir soatim qancha?» xatolari: domen kodi `INVALID_DAYS` boshqa bo'limlarda ham bor — bu yerda
/// ish kunlari uchun aniq kod; daromad yo'qligi — `income` maydoniga.
pub(crate) fn hour_err(e: baraka_domain_common::DomainError) -> AppError {
    match e.code {
        "INVALID_DAYS" => AppError::on("INVALID_WORK_DAYS", "days"),
        "NO_INCOME" => AppError::on("NO_INCOME", "income"),
        _ => e.into(),
    }
}

/// Matn uzunligi chegarasi (mavzu, ism, maqsad va h.k.) — bitta qoida va bitta kod.
pub(crate) fn max_chars(s: Option<&str>, max: usize, field: &str) -> Result<(), AppError> {
    if s.is_some_and(|t| t.chars().count() > max) {
        Err(AppError::on("TOO_LONG", field))
    } else {
        Ok(())
    }
}

/// Majburiy summa (chetlari kesiladi) — minor birlikda.
pub(crate) fn amount(s: &str, cur: Currency, field: &str) -> Result<i64, AppError> {
    Ok(parse_amount(s.trim(), cur)
        .map_err(|e| AppError::on(e.code(), field))?
        .minor())
}

/// Ixtiyoriy summa: yo'q yoki bo'sh — `None`.
pub(crate) fn opt_amount(
    s: Option<&str>,
    cur: Currency,
    field: &str,
) -> Result<Option<i64>, AppError> {
    match s.map(str::trim) {
        None | Some("") => Ok(None),
        Some(t) => amount(t, cur, field).map(Some),
    }
}

pub(crate) fn plan_status(s: &str) -> Result<PlanStatus, AppError> {
    PlanStatus::parse(s).ok_or(AppError::new("CORRUPT_ROW"))
}

/// Yopilgan reja (`DONE`, `DROPPED`).
pub(crate) fn closed(status: PlanStatus) -> bool {
    matches!(status, PlanStatus::Done | PlanStatus::Dropped)
}

/// Tartiblangan yo'l kodlari (`BOOK,COURSE`) → ro'yxat.
pub(crate) fn parse_paths(s: &str) -> Vec<String> {
    s.split(',')
        .filter(|p| !p.is_empty())
        .map(str::to_string)
        .collect()
}

/// Holat o'zgarishi: avval yangi holat o'qiladi (`INVALID_STATUS`), keyin domen qoidasi —
/// yopilgan reja qayta ochilmaydi, `PAUSED → ACTIVE` da faol rejalar chegarasi qayta tekshiriladi.
pub(crate) fn next_status(
    from: &str,
    to: &str,
    other_active: usize,
) -> Result<PlanStatus, AppError> {
    let to = PlanStatus::parse(to).ok_or(AppError::on("INVALID_STATUS", "status"))?;
    Ok(transition(plan_status(from)?, to, other_active)?)
}

/// Bilim rejasi kiritmalari (Uy va Musofir formasi bir xil).
pub(crate) struct PlanFields<'a> {
    pub skill: &'a str,
    pub purpose: Option<&'a str>,
    pub paths: &'a [String],
    pub budget: Option<&'a str>,
    pub weekly_minutes: u32,
    pub start_on: Option<&'a str>,
    pub review_on: Option<&'a str>,
}

/// Saqlov qoidalari bilan tekshirilgan reja.
pub(crate) struct PlanChecked {
    pub plan: ValidPlan,
    pub purpose: Option<String>,
}

/// Tekshirilgan saqlangan soat qiymati hisobi (Uy `learning_hour_values`, Musofir `mf_hour_values`).
pub(crate) trait HourRecord {
    fn record_id(&self) -> &str;
    fn record_currency(&self) -> &str;
    fn record_hour_minor(&self) -> i64;
}

impl HourRecord for baraka_storage::repo::learning::HourValueRow {
    fn record_id(&self) -> &str {
        &self.id
    }
    fn record_currency(&self) -> &str {
        &self.currency
    }
    fn record_hour_minor(&self) -> i64 {
        self.hour_value_minor
    }
}

impl HourRecord for baraka_storage::repo::mf_learning::MfHourRow {
    fn record_id(&self) -> &str {
        &self.id
    }
    fn record_currency(&self) -> &str {
        &self.currency
    }
    fn record_hour_minor(&self) -> i64 {
        self.hour_value_minor
    }
}

/// Natijani o'lchash (2G.5) natijasi: boshlang'ich nuqta, hozirgi hisob va farq.
pub(crate) struct Measured<R> {
    pub baseline: Option<R>,
    pub current: R,
    pub change: Option<HourChange>,
}

/// Natijani o'lchash qoidalari (Uy va Musofir bir xil, xato kodlari tartibi bilan): yopilgan reja
/// natijasi bir marta o'lchanadi (`PLAN_CLOSED`); hisob yo'q — `NO_HOUR_VALUE`; boshlang'ich nuqtadan
/// keyin yangi hisob yo'q — `NO_NEW_HOUR_VALUE`; boshlang'ich yozuv topilmasa — `CORRUPT_ROW`;
/// valyuta boshqa — `CURRENCY_MISMATCH`; farq — `hour_value_change`.
pub(crate) fn measure_plan<R: HourRecord>(
    status: PlanStatus,
    has_result: bool,
    baseline_id: Option<&str>,
    current: Option<R>,
    load: impl FnOnce(&str) -> Result<Option<R>, AppError>,
) -> Result<Measured<R>, AppError> {
    if closed(status) && has_result {
        return Err(AppError::on("PLAN_CLOSED", "planId"));
    }
    let current = current.ok_or(AppError::new("NO_HOUR_VALUE"))?;
    if baseline_id == Some(current.record_id()) {
        return Err(AppError::new("NO_NEW_HOUR_VALUE"));
    }
    let baseline = match baseline_id {
        None => None,
        Some(id) => Some(load(id)?.ok_or(AppError::new("CORRUPT_ROW"))?),
    };
    let change = match &baseline {
        Some(b) if b.record_currency() != current.record_currency() => {
            return Err(AppError::new("CURRENCY_MISMATCH"))
        }
        Some(b) => Some(hour_value_change(
            b.record_hour_minor(),
            current.record_hour_minor(),
        )?),
        None => None,
    };
    Ok(Measured {
        baseline,
        current,
        change,
    })
}

impl App {
    /// Ixtiyoriy sana: yo'q yoki bo'sh satr — `None` (masalan, ko'rik sanasi — standart +3 oy).
    pub(crate) fn optional_date(
        &self,
        ctx: &Ctx,
        s: Option<&str>,
        field: &str,
    ) -> Result<Option<NaiveDate>, AppError> {
        match s.map(str::trim) {
            None | Some("") => Ok(None),
            Some(t) => self.date_or_today(ctx, Some(t), field).map(Some),
        }
    }

    /// Reja kiritmalari tartibda: yo'llar (`INVALID_PATH`), byudjet (reja valyutasida), boshlanish
    /// (bo'sh — bugun), ko'rik sanasi (yo'q yoki bo'sh — +3 oy), maqsad matni (`TOO_LONG`), keyin domen
    /// `validate_plan`.
    pub(crate) fn check_plan(
        &self,
        ctx: &Ctx,
        cur: Currency,
        f: &PlanFields<'_>,
    ) -> Result<PlanChecked, AppError> {
        let paths = f
            .paths
            .iter()
            .map(|p| PathKind::parse(p).ok_or(AppError::on("INVALID_PATH", "paths")))
            .collect::<Result<Vec<_>, _>>()?;
        let budget = opt_amount(f.budget, cur, "budget")?;
        let start = self.date_or_today(ctx, f.start_on, "startOn")?;
        let review = self.optional_date(ctx, f.review_on, "reviewOn")?;
        let purpose = clean_opt(f.purpose);
        max_chars(purpose.as_deref(), PURPOSE_MAX_CHARS, "purpose")?;
        let plan = validate_plan(&PlanDraft {
            skill: clean(f.skill),
            paths,
            budget,
            weekly_minutes: f.weekly_minutes,
            start,
            review,
        })?;
        Ok(PlanChecked { plan, purpose })
    }
}

/// Reja yo'llari saqlash ko'rinishida: `BOOK,COURSE`.
pub(crate) fn paths_text(plan: &ValidPlan) -> String {
    plan.paths
        .iter()
        .map(|p| p.as_str())
        .collect::<Vec<_>>()
        .join(",")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn paths_round_trip_and_bp_saturates() {
        assert_eq!(parse_paths("BOOK,COURSE"), vec!["BOOK", "COURSE"]);
        assert!(parse_paths("").is_empty());
        assert_eq!(bp32(10_000), 10_000);
        assert_eq!(bp32(i64::MAX), i32::MAX);
        assert_eq!(bp32(i64::MIN), i32::MIN);
    }

    #[test]
    fn status_parsing_order() {
        assert_eq!(
            next_status("ACTIVE", "X", 0).unwrap_err().code,
            "INVALID_STATUS"
        );
        assert_eq!(
            next_status("??", "ACTIVE", 0).unwrap_err().code,
            "CORRUPT_ROW"
        );
        assert_eq!(
            next_status("PAUSED", "ACTIVE", 2).unwrap_err().code,
            "ACTIVE_PLAN_LIMIT"
        );
    }
}
