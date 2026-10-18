//! Hijriy (qamariy) sana — **jadvalli (arifmetik) kalendar**, «Calendrical Calculations» formulasi
//! (epoxa: milodiy 622-yil 16-iyul, Yulian). Kuzatilgan oy chiqishidan ±1–2 kun farq qilishi mumkin —
//! faqat eslatma va taxminiy sana uchun («Zakot kuni», kasbkor/SPEC 8.3).
use chrono::{Datelike, NaiveDate};

/// Hijriy kalendar boshi — `NaiveDate::num_days_from_ce` hisobida.
const EPOCH: i64 = 227_015;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct HijriDate {
    pub year: i64,
    pub month: u32,
    pub day: u32,
}

fn fixed(y: i64, m: u32, d: u32) -> i64 {
    let (m, d) = (i64::from(m), i64::from(d));
    d + 29 * (m - 1)
        + (6 * m - 1).div_euclid(11)
        + (y - 1) * 354
        + (3 + 11 * y).div_euclid(30)
        + EPOCH
        - 1
}

/// Oyning kunlari soni (29 yoki 30).
pub fn month_length(year: i64, month: u32) -> u32 {
    let next = if month >= 12 {
        fixed(year + 1, 1, 1)
    } else {
        fixed(year, month + 1, 1)
    };
    u32::try_from(next - fixed(year, month, 1)).unwrap_or(29)
}

pub fn to_gregorian(h: HijriDate) -> Option<NaiveDate> {
    if !(1..=12).contains(&h.month) || h.day == 0 || h.day > month_length(h.year, h.month) {
        return None;
    }
    NaiveDate::from_num_days_from_ce_opt(i32::try_from(fixed(h.year, h.month, h.day)).ok()?)
}

pub fn from_gregorian(d: NaiveDate) -> HijriDate {
    let f = i64::from(d.num_days_from_ce());
    let year = (30 * (f - EPOCH) + 10_646).div_euclid(10_631);
    let prior = f - fixed(year, 1, 1);
    let month = u32::try_from((11 * prior + 330).div_euclid(325)).unwrap_or(1);
    let day = u32::try_from(f - fixed(year, month, 1) + 1).unwrap_or(1);
    HijriDate { year, month, day }
}

/// `from` dan keyingi (shu kun ham) hijriy `month`/`day` sanasi; oyda kun kam bo'lsa — oyning oxirgi kuni.
pub fn next_occurrence(month: u32, day: u32, from: NaiveDate) -> Option<NaiveDate> {
    if !(1..=12).contains(&month) || !(1..=30).contains(&day) {
        return None;
    }
    let mut year = from_gregorian(from).year;
    for _ in 0..3 {
        let d = day.min(month_length(year, month));
        let g = to_gregorian(HijriDate {
            year,
            month,
            day: d,
        })?;
        if g >= from {
            return Some(g);
        }
        year += 1;
    }
    None
}

/// Bir qamariy yil (hawl) — jadvalli kalendarda 354 yoki 355 kun; `since` dan `today` gacha to'ldimi.
pub fn hawl_complete(since: NaiveDate, today: NaiveDate) -> bool {
    let h = from_gregorian(since);
    let day = h.day.min(month_length(h.year + 1, h.month));
    to_gregorian(HijriDate {
        year: h.year + 1,
        month: h.month,
        day,
    })
    .is_some_and(|anniversary| today >= anniversary)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(s: &str) -> NaiveDate {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").unwrap()
    }

    fn h(year: i64, month: u32, day: u32) -> HijriDate {
        HijriDate { year, month, day }
    }

    #[test]
    fn matches_tabular_values_and_round_trips() {
        // Kuzatilgan: 1446-ramazon 1 — 2025-03-01, 1447-ramazon 1 — 2026-02-18, 1447-muharram 1 — 2025-06-26.
        assert_eq!(to_gregorian(h(1446, 9, 1)), Some(d("2025-03-01")));
        assert_eq!(to_gregorian(h(1447, 9, 1)), Some(d("2026-02-18")));
        assert_eq!(to_gregorian(h(1447, 1, 1)), Some(d("2025-06-27")));
        assert_eq!(to_gregorian(h(1447, 12, 10)), Some(d("2026-05-27")));
        assert_eq!(from_gregorian(d("2026-10-18")), h(1448, 5, 6));
        for s in ["2024-01-01", "2025-06-27", "2026-12-31", "2030-02-28"] {
            assert_eq!(to_gregorian(from_gregorian(d(s))), Some(d(s)));
        }
        assert_eq!(to_gregorian(h(1447, 2, 30)), None);
    }

    #[test]
    fn next_zakat_day_and_hawl() {
        // 1-ramazon: 2026-02-18 o'tgan bo'lsa — keyingi yilniki.
        assert_eq!(
            next_occurrence(9, 1, d("2026-02-18")),
            Some(d("2026-02-18"))
        );
        assert_eq!(
            next_occurrence(9, 1, d("2026-02-19")),
            to_gregorian(h(1448, 9, 1))
        );
        assert!(!hawl_complete(d("2025-03-01"), d("2026-02-17")));
        assert!(hawl_complete(d("2025-03-01"), d("2026-02-18")));
    }
}
