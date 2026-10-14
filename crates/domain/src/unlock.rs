//! Bob ochilishi qoidalari (SPEC 2C.6, MVP_PLAN Vazifa 6). Vaqtning o'zi bob ochmaydi — odat ochadi.
//!
//! Standart qoida — [`HabitUnlockPolicy`]: 1-bob darhol; keyingisi oldingi bob ochilgandan kamida
//! [`HabitUnlockPolicy::min_days`] kun o'tib, uning vazifalaridan kamida
//! [`HabitUnlockPolicy::required_tasks`] tasi bajarilganda ochiladi. Ochilgan bob qayta yopilmaydi:
//! vazifa belgisi olib tashlansa ham birinchi bajarilish sanasi hisoblanadi.

use std::collections::BTreeMap;

use time::Date;

use crate::calendar::{shift_days, week_of};
use crate::content::Chapter;

/// Bob ochilishi uchun kontekst.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnlockContext {
    /// Dastur boshlangan sana (Toshkent, birinchi ishga tushirish).
    pub program_start: Date,
    /// Bugungi sana (Toshkent).
    pub today: Date,
    /// Vazifa ID → u birinchi marta bajarilgan sana (Toshkent). Keyin belgisi olib tashlangan bo'lsa ham
    /// saqlanadi — ochilgan bob qayta yopilmaydi.
    pub first_completed: BTreeMap<String, Date>,
}

/// Bitta bob uchun qoida natijasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ChapterUnlock {
    /// Ochilish sanasi (kelajakda bo'lishi mumkin). `None` — hali aniq emas
    /// (oldingi bobning vazifalari yetarli bajarilmagan).
    pub date: Option<Date>,
    /// Oldingi bobdan yana nechta vazifa bajarilishi kerak.
    pub tasks_remaining: u32,
    /// Kun sharti bo'yicha eng erta sana (odat qoidasida).
    pub not_before: Option<Date>,
}

impl ChapterUnlock {
    /// [`today`](Self::date) kuni bob ochiqmi.
    pub fn is_unlocked_on(&self, today: Date) -> bool {
        matches!(self.date, Some(date) if today >= date)
    }
}

/// Bob qachon ochilishi qoidasi. Natija [`Chapter`] ro'yxati bilan bir xil tartibda.
pub trait ChapterUnlockPolicy {
    /// `chapters` — `order` bo'yicha tartiblangan ro'yxat.
    fn evaluate(&self, chapters: &[Chapter], ctx: &UnlockContext) -> Vec<ChapterUnlock>;
}

/// Odat asosidagi qoida (SPEC 2C.6). Standart: 2 ta vazifa, 7 kun.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct HabitUnlockPolicy {
    /// Oldingi bobdan kamida shuncha vazifa bajarilishi kerak.
    pub required_tasks: u32,
    /// Oldingi bob ochilgandan keyin kamida shuncha kun o'tishi kerak.
    pub min_days: i64,
}

impl Default for HabitUnlockPolicy {
    fn default() -> Self {
        Self {
            required_tasks: 2,
            min_days: 7,
        }
    }
}

impl ChapterUnlockPolicy for HabitUnlockPolicy {
    fn evaluate(&self, chapters: &[Chapter], ctx: &UnlockContext) -> Vec<ChapterUnlock> {
        let mut out: Vec<ChapterUnlock> = Vec::with_capacity(chapters.len());
        for index in 0..chapters.len() {
            if index == 0 {
                out.push(ChapterUnlock {
                    date: Some(ctx.program_start),
                    tasks_remaining: 0,
                    not_before: None,
                });
                continue;
            }
            let previous = &chapters[index - 1];
            let previous_date = out[index - 1].date;
            let required = self
                .required_tasks
                .min(u32::try_from(previous.weekly_tasks.len()).unwrap_or(u32::MAX));
            let Some(previous_date) = previous_date else {
                out.push(ChapterUnlock {
                    date: None,
                    tasks_remaining: required,
                    not_before: None,
                });
                continue;
            };
            let not_before = shift_days(previous_date, self.min_days);
            let mut done: Vec<Date> = previous
                .weekly_tasks
                .iter()
                .filter_map(|task| ctx.first_completed.get(&task.id).copied())
                .collect();
            done.sort();
            let done_count = u32::try_from(done.len()).unwrap_or(u32::MAX);
            if done_count < required {
                out.push(ChapterUnlock {
                    date: None,
                    tasks_remaining: required - done_count,
                    not_before,
                });
                continue;
            }
            let tasks_met = if required == 0 {
                previous_date
            } else {
                done[(required - 1) as usize]
            };
            let date = match not_before {
                Some(floor) if floor > tasks_met => floor,
                _ => tasks_met,
            };
            out.push(ChapterUnlock {
                date: Some(date),
                tasks_remaining: 0,
                not_before,
            });
        }
        out
    }
}

/// Vaqt asosidagi qoida: har juma yangi bob (SPEC 1.1). 1-bob darhol, k-bob dastur boshlangan
/// haftadan (k−1) hafta keyin, haftaning birinchi kuni (juma).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct TimeBasedUnlockPolicy;

impl ChapterUnlockPolicy for TimeBasedUnlockPolicy {
    fn evaluate(&self, chapters: &[Chapter], ctx: &UnlockContext) -> Vec<ChapterUnlock> {
        let first_week = week_of(ctx.program_start).map(|week| week.start);
        chapters
            .iter()
            .map(|chapter| {
                let date = if chapter.order <= 1 {
                    Some(ctx.program_start)
                } else {
                    first_week.and_then(|start| shift_days(start, 7 * i64::from(chapter.order - 1)))
                };
                ChapterUnlock {
                    date,
                    tasks_remaining: 0,
                    not_before: None,
                }
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use time::macros::date;

    use super::*;
    use crate::content::{Chapter, ContentBlock, LANG_UZ, Law, LocalizedText, WeeklyTask};

    fn text(value: &str) -> LocalizedText {
        LocalizedText::new(BTreeMap::from([(LANG_UZ.to_owned(), value.to_owned())]))
            .expect("uz bor")
    }

    /// `count` bobli kontent; har bobda 3 ta vazifa (`chNN.t1..t3`).
    fn chapters(count: u32) -> Vec<Chapter> {
        (1..=count)
            .map(|order| {
                let id = format!("ch{order:02}");
                Chapter {
                    id: id.clone(),
                    order,
                    title: text("Bob"),
                    blocks: vec![ContentBlock::Paragraph(text("Matn"))],
                    law: Law {
                        number: order,
                        text: text("Qonun"),
                    },
                    weekly_tasks: (1..=3)
                        .map(|n| WeeklyTask {
                            id: format!("{id}.t{n}"),
                            text: text("Vazifa"),
                            trigger: None,
                        })
                        .collect(),
                    audio_url: None,
                }
            })
            .collect()
    }

    fn ctx(today: Date, done: &[(&str, Date)]) -> UnlockContext {
        UnlockContext {
            program_start: date!(2026 - 10 - 14),
            today,
            first_completed: done
                .iter()
                .map(|(id, day)| ((*id).to_owned(), *day))
                .collect(),
        }
    }

    #[test]
    fn birinchi_bob_darhol_ochiladi() {
        let list = chapters(3);
        let unlocks =
            HabitUnlockPolicy::default().evaluate(&list, &ctx(date!(2026 - 10 - 14), &[]));
        assert!(unlocks[0].is_unlocked_on(date!(2026 - 10 - 14)));
        assert!(!unlocks[1].is_unlocked_on(date!(2026 - 10 - 14)));
    }

    #[test]
    fn ikkinchi_bob_vaqt_bilan_emas_odat_bilan_ochiladi() {
        // 7 kun o'tgan, lekin vazifa yo'q — bob ochilmaydi.
        let list = chapters(2);
        let today = date!(2026 - 10 - 30);
        let unlocks = HabitUnlockPolicy::default().evaluate(&list, &ctx(today, &[]));
        assert_eq!(unlocks[1].date, None);
        assert_eq!(unlocks[1].tasks_remaining, 2);
        assert_eq!(unlocks[1].not_before, Some(date!(2026 - 10 - 21)));
        assert!(!unlocks[1].is_unlocked_on(today));
    }

    #[test]
    fn ikki_vazifa_bajarilsa_ham_kun_sharti_kutiladi() {
        // Vazifalar 15-sanada bajarildi, ammo kun sharti 21-sanagacha — ochilish 21-sana.
        let list = chapters(2);
        let done = [
            ("ch01.t1", date!(2026 - 10 - 15)),
            ("ch01.t2", date!(2026 - 10 - 16)),
        ];
        let unlocks =
            HabitUnlockPolicy::default().evaluate(&list, &ctx(date!(2026 - 10 - 20), &done));
        assert_eq!(unlocks[1].date, Some(date!(2026 - 10 - 21)));
        assert_eq!(unlocks[1].tasks_remaining, 0);
        assert!(!unlocks[1].is_unlocked_on(date!(2026 - 10 - 20)));
        assert!(unlocks[1].is_unlocked_on(date!(2026 - 10 - 21)));
    }

    #[test]
    fn kun_sharti_otgach_ikkinchi_vazifa_sanasi_ochadi() {
        // Kun sharti 21-sana, ikkinchi vazifa 25-sanada — ochilish 25-sana.
        let list = chapters(2);
        let done = [
            ("ch01.t1", date!(2026 - 10 - 15)),
            ("ch01.t2", date!(2026 - 10 - 25)),
        ];
        let unlocks =
            HabitUnlockPolicy::default().evaluate(&list, &ctx(date!(2026 - 10 - 26), &done));
        assert_eq!(unlocks[1].date, Some(date!(2026 - 10 - 25)));
    }

    #[test]
    fn ochilgan_bob_sana_otgach_ham_ochiq_qoladi() {
        // Birinchi bajarilish sanalari saqlanadi; keyingi kunlarda bob yopilmaydi.
        let list = chapters(2);
        let done = [
            ("ch01.t1", date!(2026 - 10 - 15)),
            ("ch01.t2", date!(2026 - 10 - 16)),
        ];
        let early =
            HabitUnlockPolicy::default().evaluate(&list, &ctx(date!(2026 - 10 - 21), &done));
        let later =
            HabitUnlockPolicy::default().evaluate(&list, &ctx(date!(2026 - 11 - 30), &done));
        assert!(early[1].is_unlocked_on(date!(2026 - 10 - 21)));
        assert!(later[1].is_unlocked_on(date!(2026 - 11 - 30)));
    }

    #[test]
    fn oldingi_bob_ochilmasa_keyingisi_sanasiz_qoladi() {
        let list = chapters(3);
        let unlocks =
            HabitUnlockPolicy::default().evaluate(&list, &ctx(date!(2026 - 12 - 01), &[]));
        assert_eq!(unlocks[2].date, None);
        assert_eq!(unlocks[2].tasks_remaining, 2);
        assert_eq!(unlocks[2].not_before, None);
    }

    #[test]
    fn talab_nol_bolsa_oldingi_bob_sanasi_va_kun_sharti_yetarli() {
        let list = chapters(2);
        let policy = HabitUnlockPolicy {
            required_tasks: 0,
            min_days: 3,
        };
        let unlocks = policy.evaluate(&list, &ctx(date!(2026 - 10 - 20), &[]));
        assert_eq!(unlocks[1].date, Some(date!(2026 - 10 - 17)));
    }

    #[test]
    fn vazifa_soni_bobdan_kop_bolsa_mavjud_soniga_kesiladi() {
        let mut list = chapters(2);
        list[0].weekly_tasks.truncate(1);
        let done = [("ch01.t1", date!(2026 - 10 - 15))];
        let unlocks =
            HabitUnlockPolicy::default().evaluate(&list, &ctx(date!(2026 - 10 - 22), &done));
        // Oldingi bobda faqat 1 ta vazifa — talab 1 taga kesiladi; kun sharti 21-sana hal qiluvchi.
        assert_eq!(unlocks[1].tasks_remaining, 0);
        assert_eq!(unlocks[1].date, Some(date!(2026 - 10 - 21)));
    }

    #[test]
    fn vaqt_qoidasi_har_juma_yangi_bob() {
        // 2026-10-14 — chorshanba. Shu haftaning jumasi — 2026-10-09; 2-bob 10-16, 3-bob 10-23.
        let list = chapters(3);
        let unlocks = TimeBasedUnlockPolicy.evaluate(&list, &ctx(date!(2026 - 10 - 14), &[]));
        assert_eq!(unlocks[0].date, Some(date!(2026 - 10 - 14)));
        assert_eq!(unlocks[1].date, Some(date!(2026 - 10 - 16)));
        assert_eq!(unlocks[2].date, Some(date!(2026 - 10 - 23)));
    }
}
