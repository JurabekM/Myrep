//! U15: sozlamalar (qurilma tili, daromad ritmi, «qarzim bor») va bosh sahifadagi yumshoq
//! eslatmalar — daromad ritmiga mos, qarz inventari va oylik zaxira nusxa
//! (`docs/BARAKA_OILASI.md` 7.2). Qoidalar `domain-uy::nudge` da.
use baraka_domain_common::{local_date, month_period};
use baraka_domain_uy::nudge::{backup_due, income_nudge, IncomeNudge, IncomeRhythm};
use baraka_money::Locale;
use baraka_storage::repo::{debts, household, incomes, sync};
use chrono::{DateTime, NaiveDate, Utc};

use crate::*;

/// `None` yoki bo'sh — ritm tanlanmagan (eslatma yo'q).
pub(crate) fn parse_rhythm(s: Option<&str>) -> Result<Option<&'static str>, AppError> {
    match s.map(str::trim).filter(|s| !s.is_empty()) {
        None => Ok(None),
        Some(v) => IncomeRhythm::parse(v)
            .map(|r| Some(r.as_str()))
            .ok_or(AppError::on("INVALID_INCOME_RHYTHM", "incomeRhythm")),
    }
}

fn date_of(stamp: &str, tz: chrono_tz::Tz) -> Option<NaiveDate> {
    DateTime::parse_from_rfc3339(stamp)
        .ok()
        .map(|d| local_date(d.with_timezone(&Utc), tz))
}

fn days32(d: i64) -> u32 {
    u32::try_from(d).unwrap_or(u32::MAX)
}

impl App {
    /// Shu qurilma va xonadon sozlamalari.
    pub fn settings(&self) -> Result<SettingsDto, AppError> {
        let ctx = self.ctx()?;
        let h = self
            .db
            .read(household::get_household)?
            .ok_or(AppError::new("NOT_INITIALIZED"))?;
        let prefs = self.db.read(|c| household::prefs(c, &ctx.household_id))?;
        let device_locale = self
            .db
            .read(|c| household::device_locale(c, &self.device_id))?;
        Ok(SettingsDto {
            locale: device_locale.clone().unwrap_or(h.locale.clone()),
            household_locale: h.locale,
            device_locale,
            income_rhythm: prefs.income_rhythm,
            debts_declared: prefs.debts_declared,
        })
    }

    /// Til shu qurilma uchun saqlanadi (sinxronlanmaydi); daromad ritmi va «qarzim bor» —
    /// xonadonniki.
    pub fn update_settings(&self, input: SettingsInput) -> Result<SettingsDto, AppError> {
        let ctx = self.ctx()?;
        if let Some(l) = input.locale.as_deref() {
            Locale::from_tag(l).ok_or(AppError::on("INVALID_LOCALE", "locale"))?;
        }
        let rhythm = parse_rhythm(input.income_rhythm.as_deref())?;
        let meta = self.meta();
        // Rolli qurilmada (K8) faqat shu qurilmaning tili; xonadon sozlamalari — egasida.
        let owner = matches!(
            self.access(&ctx)?.role,
            crate::access::Role::Owner | crate::access::Role::Home
        );
        self.db.write_sync(|tx| {
            household::set_device_locale(tx, input.locale.as_deref(), &meta)?;
            if owner {
                household::set_prefs(tx, &ctx.household_id, rhythm, input.debts_declared, &meta)?;
            }
            Ok(())
        })?;
        // Til o'zgarsa, barcha formatlangan summalar qayta so'raladi.
        self.publish(None, &crate::sync::ALL_TOPICS);
        self.settings()
    }

    /// Bosh sahifa eslatmalari: daromad ritmi, qarz inventari, zaxira nusxa.
    pub fn home_nudges(&self, space_id: &str) -> Result<Vec<NudgeDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let today = self.today(&ctx);
        let prefs = self.db.read(|c| household::prefs(c, &ctx.household_id))?;
        let mut out = Vec::new();

        if let Some(rhythm) = prefs.income_rhythm.as_deref().and_then(IncomeRhythm::parse) {
            let last = self
                .db
                .read(|c| incomes::last_occurred_on(c, &scope))?
                .and_then(|s| NaiveDate::parse_from_str(&s, "%Y-%m-%d").ok());
            let (start, _) =
                month_period(today, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
            match income_nudge(rhythm, today, last, start) {
                Some(IncomeNudge::Today) => out.push(NudgeDto::new("INCOME_TODAY", None)),
                Some(IncomeNudge::Quiet { days }) => {
                    out.push(NudgeDto::new("INCOME_QUIET", days.map(days32)));
                }
                Some(IncomeNudge::Payday) => out.push(NudgeDto::new("PAYDAY", None)),
                None => {}
            }
        }

        if prefs.debts_declared && self.db.read(|c| debts::list_debts(c, &scope))?.is_empty() {
            out.push(NudgeDto::new("DEBT_INVENTORY", None));
        }

        let created = date_of(&prefs.created_at, ctx.tz).unwrap_or(today);
        let last_full = self
            .db
            .read(|c| sync::last_export_at(c, &ctx.household_id, "FULL"))?
            .and_then(|s| date_of(&s, ctx.tz));
        if let Some(days) = backup_due(today, created, last_full) {
            out.push(NudgeDto::new("BACKUP", Some(days32(days))));
        }
        Ok(out)
    }
}

impl NudgeDto {
    fn new(kind: &str, days: Option<u32>) -> Self {
        Self {
            kind: kind.to_string(),
            days,
        }
    }
}
