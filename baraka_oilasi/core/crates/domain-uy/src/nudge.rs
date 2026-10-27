//! Bosh sahifadagi yumshoq eslatmalar (U15): daromad ritmiga mos «yozib qo'ying», qarzlarni
//! inventarga kiritish taklifi va zaxira nusxa eslatmasi (`docs/BARAKA_OILASI.md` 7.2: «har oy
//! eslatiladi»), 8-tamoyilning juma ritmi (uy/SPEC 2G.2, 2G.6). Sof sana mantiqi — summa yo'q.

use baraka_domain_common::week_start;
use chrono::{Days, NaiveDate, Weekday};

/// Onboarding'da tanlangan daromad ritmi.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum IncomeRhythm {
    /// Kunlik naqd (taksi, bozor) — har kuni yoziladi.
    Daily,
    /// Buyurtma bo'yicha (usta, tikuvchi) — pul kelganda.
    Orders,
    /// Oylik maosh — oy boshlanish kuni atrofida.
    Monthly,
}

impl IncomeRhythm {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "DAILY" => Some(Self::Daily),
            "ORDERS" => Some(Self::Orders),
            "MONTHLY" => Some(Self::Monthly),
            _ => None,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Daily => "DAILY",
            Self::Orders => "ORDERS",
            Self::Monthly => "MONTHLY",
        }
    }
}

/// Buyurtma ritmida shuncha kun daromad yozilmasa — eslatma.
pub const ORDERS_QUIET_DAYS: i64 = 14;
/// Oylik maoshda oy boshidan shuncha kun ichida eslatiladi.
pub const PAYDAY_WINDOW_DAYS: u64 = 3;
/// Zaxira nusxa shuncha kundan eski bo'lsa (yoki hech olinmagan bo'lsa) — eslatma.
pub const BACKUP_EVERY_DAYS: i64 = 30;

/// Juma ritmi: eslatma haftaning (juma bilan boshlanadi) shuncha kunida ko'rinadi — juma, shanba,
/// yakshanba. Jumada ochilmagan ilova dam olish kunlarida ham so'raydi, keyin hafta tinch o'tadi.
pub const WEEKLY_CHECK_DAYS: i64 = 3;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum IncomeNudge {
    /// Bugun hali daromad yozilmagan.
    Today,
    /// Oxirgi daromad `days` kun oldin (yoki hech qachon — `None`).
    Quiet { days: Option<i64> },
    /// Maosh kuni: shu oy davrida hali daromad yo'q.
    Payday,
}

/// Daromad ritmiga qarab eslatma. `last_income` — oxirgi daromad sanasi, `period_start` —
/// joriy oy davrining boshi (`domain_common::time::month_period`).
pub fn income_nudge(
    rhythm: IncomeRhythm,
    today: NaiveDate,
    last_income: Option<NaiveDate>,
    period_start: NaiveDate,
) -> Option<IncomeNudge> {
    match rhythm {
        IncomeRhythm::Daily => (last_income != Some(today)).then_some(IncomeNudge::Today),
        IncomeRhythm::Orders => match last_income {
            None => Some(IncomeNudge::Quiet { days: None }),
            Some(d) => {
                let days = (today - d).num_days();
                (days >= ORDERS_QUIET_DAYS).then_some(IncomeNudge::Quiet { days: Some(days) })
            }
        },
        IncomeRhythm::Monthly => {
            let window_end = period_start.checked_add_days(Days::new(PAYDAY_WINDOW_DAYS))?;
            let in_window = today >= period_start && today <= window_end;
            let paid = last_income.is_some_and(|d| d >= period_start);
            (in_window && !paid).then_some(IncomeNudge::Payday)
        }
    }
}

/// Zaxira nusxa eslatmasi: oxirgi to'liq eksportdan (yoki xonadon yaratilganidan) beri
/// o'tgan kunlar. `None` — hali erta.
pub fn backup_due(
    today: NaiveDate,
    created_on: NaiveDate,
    last_full_export: Option<NaiveDate>,
) -> Option<i64> {
    let since = last_full_export.unwrap_or(created_on);
    let days = (today - since).num_days();
    (days >= BACKUP_EVERY_DAYS).then_some(days)
}

/// Juma ritmi haftasi (2G.2 «Bu hafta necha soat o'qidingiz?», 2G.6 «…kimgadir o'rgatdingizmi?»).
/// Eslatma `anchor` (juma) kuni va undan keyingi kunlarda — jami [`WEEKLY_CHECK_DAYS`] kun — ko'rinadi
/// va shu kunlarning hammasida **bitta** hafta baholanadi: eslatma kunlarining oxirgisi (yakshanba)
/// bilan tugaydigan 7 kun, ya'ni dushanba–yakshanba. Haftalar ustma-ust tushmaydi: shanba yoki
/// yakshanba yozilgani o'tayotgan haftaga kiradi va keyingi jumadagi eslatmani yashirmaydi.
/// Qaytaradi: `(boshi, oxiri)` — ikkalasi ham kiradi; boshqa kunlari — `None`.
pub fn weekly_check_window(today: NaiveDate, anchor: Weekday) -> Option<(NaiveDate, NaiveDate)> {
    let friday = week_start(today, anchor);
    if (today - friday).num_days() >= WEEKLY_CHECK_DAYS {
        return None;
    }
    let last = friday.checked_add_days(Days::new(u64::try_from(WEEKLY_CHECK_DAYS - 1).ok()?))?;
    Some((last.checked_sub_days(Days::new(6))?, last))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(s: &str) -> NaiveDate {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").unwrap_or_default()
    }

    #[test]
    fn rhythm_round_trip() {
        for r in [
            IncomeRhythm::Daily,
            IncomeRhythm::Orders,
            IncomeRhythm::Monthly,
        ] {
            assert_eq!(IncomeRhythm::parse(r.as_str()), Some(r));
        }
        assert_eq!(IncomeRhythm::parse("WEEKLY"), None);
    }

    #[test]
    fn daily_asks_every_day_until_written() {
        let t = d("2027-01-05");
        let s = d("2027-01-01");
        assert_eq!(
            income_nudge(IncomeRhythm::Daily, t, None, s),
            Some(IncomeNudge::Today)
        );
        assert_eq!(
            income_nudge(IncomeRhythm::Daily, t, Some(d("2027-01-04")), s),
            Some(IncomeNudge::Today)
        );
        assert_eq!(income_nudge(IncomeRhythm::Daily, t, Some(t), s), None);
    }

    #[test]
    fn orders_only_after_a_quiet_fortnight() {
        let t = d("2027-01-20");
        let s = d("2027-01-01");
        assert_eq!(
            income_nudge(IncomeRhythm::Orders, t, Some(d("2027-01-07")), s),
            None
        );
        assert_eq!(
            income_nudge(IncomeRhythm::Orders, t, Some(d("2027-01-06")), s),
            Some(IncomeNudge::Quiet { days: Some(14) })
        );
        assert_eq!(
            income_nudge(IncomeRhythm::Orders, t, None, s),
            Some(IncomeNudge::Quiet { days: None })
        );
    }

    #[test]
    fn monthly_only_around_payday() {
        let s = d("2027-01-10");
        let m = IncomeRhythm::Monthly;
        assert_eq!(income_nudge(m, d("2027-01-09"), None, s), None);
        assert_eq!(
            income_nudge(m, d("2027-01-10"), None, s),
            Some(IncomeNudge::Payday)
        );
        assert_eq!(
            income_nudge(m, d("2027-01-13"), None, s),
            Some(IncomeNudge::Payday)
        );
        assert_eq!(income_nudge(m, d("2027-01-14"), None, s), None);
        // O'tgan oy maoshi hisobga olinmaydi, shu davrdagisi — oladi.
        assert_eq!(
            income_nudge(m, d("2027-01-11"), Some(d("2026-12-10")), s),
            Some(IncomeNudge::Payday)
        );
        assert_eq!(
            income_nudge(m, d("2027-01-11"), Some(d("2027-01-10")), s),
            None
        );
    }

    #[test]
    fn weekly_check_friday_to_sunday_on_one_week() {
        use baraka_domain_common::WEEK_ANCHOR;
        // 2026-11-20 — juma: juma, shanba va yakshanba bitta hafta — 11-16 (dushanba) … 11-22.
        let week = Some((d("2026-11-16"), d("2026-11-22")));
        for day in ["2026-11-20", "2026-11-21", "2026-11-22"] {
            assert_eq!(weekly_check_window(d(day), WEEK_ANCHOR), week, "{day}");
        }
        // Dushanbadan payshanbagacha — eslatma yo'q.
        for day in [
            "2026-11-19",
            "2026-11-23",
            "2026-11-24",
            "2026-11-25",
            "2026-11-26",
        ] {
            assert_eq!(weekly_check_window(d(day), WEEK_ANCHOR), None, "{day}");
        }
        // Keyingi juma — keyingi hafta, oldingisi bilan ustma-ust emas.
        let next = weekly_check_window(d("2026-11-27"), WEEK_ANCHOR);
        assert_eq!(next, Some((d("2026-11-23"), d("2026-11-29"))));
        assert!(next.is_some_and(|(from, _)| week.is_some_and(|(_, last)| from > last)));
    }

    #[test]
    fn backup_every_thirty_days() {
        let created = d("2026-10-15");
        assert_eq!(backup_due(d("2026-11-13"), created, None), None);
        assert_eq!(backup_due(d("2026-11-14"), created, None), Some(30));
        assert_eq!(
            backup_due(d("2027-01-05"), created, Some(d("2027-01-01"))),
            None
        );
        assert_eq!(
            backup_due(d("2027-02-05"), created, Some(d("2027-01-01"))),
            Some(35)
        );
    }
}
