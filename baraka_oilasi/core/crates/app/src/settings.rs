//! U15: sozlamalar (qurilma tili, daromad ritmi, «qarzim bor») va bosh sahifadagi yumshoq
//! eslatmalar — daromad ritmiga mos, qarz inventari va oylik zaxira nusxa
//! (`docs/BARAKA_OILASI.md` 7.2) hamda 8-tamoyilning juma ritmi (uy/SPEC 2G.2, 2G.6; Kasb-kor va
//! Musofir makonlarida ham). Qoidalar `domain-uy::nudge` da.
use std::collections::HashSet;

use baraka_domain_common::{local_date, month_period, SpaceKind, WEEK_ANCHOR};
use baraka_domain_uy::nudge::{
    backup_due, income_nudge, weekly_check_window, IncomeNudge, IncomeRhythm,
};
use baraka_money::Locale;
use baraka_storage::repo::{debts, household, incomes, kk_learning, learning, mf_learning, sync};
use baraka_storage::SpaceScope;
use chrono::{DateTime, Days, NaiveDate, Utc};

use crate::app::Ctx;
use crate::receipt::ymd;
use crate::*;

/// Juma ritmi eslatmalari: o'qish vaqti (faqat Uy — o'qish yozuvi faqat Uy bilim rejasida bor) va
/// «Ilm zakoti» (har makonning o'z yozuvi).
const STUDY_WEEK: &str = "STUDY_WEEK";
const TEACH_WEEK: &str = "TEACH_WEEK";
const KK_TEACH_WEEK: &str = "KK_TEACH_WEEK";
const MF_TEACH_WEEK: &str = "MF_TEACH_WEEK";

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

    /// Bosh sahifa eslatmalari. Uy: daromad ritmi, qarz inventari, juma ritmi (o'qish va «Ilm
    /// zakoti»), zaxira nusxa. Kasb-kor va Musofir bosh sahifalari: faqat juma ritmi («Ilm zakoti»).
    pub fn home_nudges(&self, space_id: &str) -> Result<Vec<NudgeDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let today = self.today(&ctx);
        // Juma ritmi: eslatma kuni bo'lsa va shu qurilmada «Ilm zakoti» yozib bo'lsa (o'sha use-case
        // qoidalari bilan) — makon va hafta oralig'i `[boshi, oxiri + 1)`.
        let week = match weekly_check_window(today, WEEK_ANCHOR) {
            Some((from, last)) => self
                .learning_write_scope(&ctx, space_id)?
                .zip(last.checked_add_days(Days::new(1)))
                .map(|(s, to)| (s, ymd(from), ymd(to))),
            None => None,
        };
        match self.space_kind(&ctx, space_id)? {
            Some(SpaceKind::Kasbkor) => return self.kk_week_nudges(week.as_ref()),
            Some(SpaceKind::Musofir) => return self.mf_week_nudges(week.as_ref()),
            _ => {}
        }
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

        out.extend(self.uy_week_nudges(&ctx, week.as_ref())?);

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

/// Juma ritmi eslatmasi uchun: yozish mumkin bo'lgan makon va hafta oralig'i `[boshi, oxiri)`.
type Week = (SpaceScope, String, String);

impl App {
    /// Uy: bilim rejasi `ACTIVE` bo'lgan, shu juma haftasida (`weekly_check_window`) o'qish vaqti
    /// yozilmagan a'zolar — «Bu hafta necha soat o'qidingiz?»; rejasi yoki soat qiymati hisobi bor,
    /// shu hafta o'rgatish yozuvi yo'q a'zolar — «Ilm zakoti». A'zolar ismi eslatmaga qo'shiladi.
    /// Hamma kiritma bitta o'qishda (bir xil holat, bitta qulf).
    fn uy_week_nudges(&self, ctx: &Ctx, week: Option<&Week>) -> Result<Vec<NudgeDto>, AppError> {
        let Some((scope, from, to)) = week else {
            return Ok(Vec::new());
        };
        let (members, active, started, studied, taught) = self.db.read(|c| {
            let set = |v: Vec<String>| v.into_iter().collect::<HashSet<_>>();
            Ok((
                household::list_members(c, &ctx.household_id)?,
                set(learning::active_plan_members(c, scope)?),
                set(learning::started_members(c, scope)?),
                set(learning::studied_members_between(c, scope, from, to)?),
                set(learning::taught_members_between(c, scope, from, to)?),
            ))
        })?;
        let (mut study, mut teach) = (Vec::new(), Vec::new());
        for m in members {
            if active.contains(&m.id) && !studied.contains(&m.id) {
                study.push(m.display_name.clone());
            }
            if started.contains(&m.id) && !taught.contains(&m.id) {
                teach.push(m.display_name);
            }
        }
        let mut out = Vec::new();
        if !study.is_empty() {
            out.push(NudgeDto::for_members(STUDY_WEEK, study));
        }
        if !teach.is_empty() {
            out.push(NudgeDto::for_members(TEACH_WEEK, teach));
        }
        Ok(out)
    }

    /// Kasb-kor (egasi bo'limi): soat qiymati hisoblangan, shu hafta xodimga yoki boshqa kishiga
    /// o'rgatish yozilmagan — «Ilm zakoti». Kasb-korda bilim rejasi va o'qish vaqti yozuvi yo'q (K9),
    /// shuning uchun o'qish eslatmasi ham yo'q.
    fn kk_week_nudges(&self, week: Option<&Week>) -> Result<Vec<NudgeDto>, AppError> {
        let Some((scope, from, to)) = week else {
            return Ok(Vec::new());
        };
        let due = self.db.read(|c| {
            Ok(kk_learning::has_owner_hours(c, scope)?
                && !kk_learning::teaching_exists_between(c, scope, from, to)?)
        })?;
        Ok(due
            .then(|| NudgeDto::new(KK_TEACH_WEEK, None))
            .into_iter()
            .collect())
    }

    /// Musofir (shaxsiy hisob): bilim rejasi yoki soat qiymati bor, shu hafta o'rgatish yozuvi yo'q —
    /// «Ilm zakoti». Musofir rejasida o'qish vaqti yozuvi yo'q (M6), shuning uchun o'qish eslatmasi
    /// ham yo'q. Uydagi oila qurilmasida (`HOME`) `mfl_scope` yopiq — eslatma yo'q.
    fn mf_week_nudges(&self, week: Option<&Week>) -> Result<Vec<NudgeDto>, AppError> {
        let Some((scope, from, to)) = week else {
            return Ok(Vec::new());
        };
        let due = self.db.read(|c| {
            Ok(mf_learning::has_plan_or_hour(c, scope)?
                && !mf_learning::teaching_exists_between(c, scope, from, to)?)
        })?;
        Ok(due
            .then(|| NudgeDto::new(MF_TEACH_WEEK, None))
            .into_iter()
            .collect())
    }
}

impl NudgeDto {
    fn new(kind: &str, days: Option<u32>) -> Self {
        Self {
            kind: kind.to_string(),
            days,
            members: Vec::new(),
        }
    }

    fn for_members(kind: &str, members: Vec<String>) -> Self {
        Self {
            members,
            ..Self::new(kind, None)
        }
    }
}
