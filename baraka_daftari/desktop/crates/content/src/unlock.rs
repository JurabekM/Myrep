//! Odat asosidagi bob ochilishi (SPEC 2C.6: «Shoshilmang»). Keyingi bob faqat vaqt o'tgani uchun
//! emas: oldingi bobning vazifalari kamida minimal darajada bajarilgan bo'lishi kerak.
//! Baholash faqat **tugagan** haftalar bo'yicha (juma kuni «o'tgan haftadagi vazifalar tekshiriladi»).

use domain::{week_start, Date};
use time::{Duration, Weekday};

use crate::TASKS_PER_CHAPTER;

#[derive(Debug, Clone, Copy, PartialEq, Eq, thiserror::Error)]
pub enum PolicyError {
    #[error("oyna 1..6 hafta bo'lishi kerak")]
    Window,
    #[error("talab qilinadigan haftalar oynadan ko'p bo'lmasligi kerak")]
    MinWeeks,
    #[error("haftalik minimal vazifalar 0..3 bo'lishi kerak")]
    MinTasks,
}

/// Sozlanadigan shart. Standart: «3 hafta ichida 2 tasida kamida 2 ta vazifa».
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct UnlockPolicy {
    window_weeks: u32,
    min_satisfied_weeks: u32,
    min_tasks_per_week: u32,
}

impl UnlockPolicy {
    pub const DEFAULT: Self = Self {
        window_weeks: 3,
        min_satisfied_weeks: 2,
        min_tasks_per_week: 2,
    };

    /// # Errors
    /// Qiymatlar chegaradan chiqsa.
    pub const fn new(
        window_weeks: u32,
        min_satisfied_weeks: u32,
        min_tasks_per_week: u32,
    ) -> Result<Self, PolicyError> {
        if window_weeks == 0 || window_weeks > 6 {
            return Err(PolicyError::Window);
        }
        if min_satisfied_weeks > window_weeks {
            return Err(PolicyError::MinWeeks);
        }
        if min_tasks_per_week as usize > TASKS_PER_CHAPTER {
            return Err(PolicyError::MinTasks);
        }
        Ok(Self {
            window_weeks,
            min_satisfied_weeks,
            min_tasks_per_week,
        })
    }

    #[must_use]
    pub const fn window_weeks(self) -> u32 {
        self.window_weeks
    }

    #[must_use]
    pub const fn min_satisfied_weeks(self) -> u32 {
        self.min_satisfied_weeks
    }

    #[must_use]
    pub const fn min_tasks_per_week(self) -> u32 {
        self.min_tasks_per_week
    }
}

impl Default for UnlockPolicy {
    fn default() -> Self {
        Self::DEFAULT
    }
}

/// Bir haftada bajarilgan vazifalar soni (`week_start` — hafta boshi).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct WeekResult {
    pub week_start: Date,
    pub completed_tasks: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnlockDecision {
    Unlocked,
    Locked {
        /// Oynadagi minimal darajaga yetgan haftalar.
        satisfied_weeks: u32,
        needed_weeks: u32,
        /// Oynaga tushgan tugagan haftalar soni (`0` — hali birorta hafta tugamagan).
        weeks_in_window: u32,
    },
}

/// `opened_week` — joriy bob ochilgan hafta boshi; `results` — tugagan haftalar natijalari
/// (yo'q hafta = 0 vazifa). Joriy (tugamagan) hafta hisobga olinmaydi.
#[must_use]
pub fn decide(
    policy: UnlockPolicy,
    opened_week: Date,
    today: Date,
    anchor: Weekday,
    results: &[WeekResult],
) -> UnlockDecision {
    let this_week = week_start(today, anchor);
    let week = Duration::days(7);

    let mut completed: Vec<u32> = Vec::new();
    let mut w = week_start(opened_week, anchor);
    while w < this_week {
        let tasks = results
            .iter()
            .find(|r| r.week_start == w)
            .map_or(0, |r| r.completed_tasks);
        completed.push(tasks);
        w += week;
    }
    let skip = completed.len().saturating_sub(policy.window_weeks as usize);
    let window = &completed[skip..];
    let satisfied = window
        .iter()
        .filter(|t| **t >= policy.min_tasks_per_week)
        .count();
    let satisfied = u32::try_from(satisfied).unwrap_or(u32::MAX);
    let weeks_in_window = u32::try_from(window.len()).unwrap_or(u32::MAX);

    if weeks_in_window >= 1 && satisfied >= policy.min_satisfied_weeks {
        UnlockDecision::Unlocked
    } else {
        UnlockDecision::Locked {
            satisfied_weeks: satisfied,
            needed_weeks: policy.min_satisfied_weeks,
            weeks_in_window,
        }
    }
}

#[cfg(test)]
mod tests {
    use time::macros::date;

    use super::*;

    const FRI: Weekday = Weekday::Friday;
    // Juma kunlari: 09-04, 09-11, 09-18, 09-25, 10-02, 10-09.
    const W0: Date = date!(2026 - 09 - 04);

    fn r(week_start: Date, completed_tasks: u32) -> WeekResult {
        WeekResult {
            week_start,
            completed_tasks,
        }
    }

    #[test]
    fn policy_validation() {
        assert!(UnlockPolicy::new(3, 2, 2).is_ok());
        assert_eq!(UnlockPolicy::new(0, 0, 0), Err(PolicyError::Window));
        assert_eq!(UnlockPolicy::new(7, 1, 1), Err(PolicyError::Window));
        assert_eq!(UnlockPolicy::new(3, 4, 1), Err(PolicyError::MinWeeks));
        assert_eq!(UnlockPolicy::new(3, 1, 4), Err(PolicyError::MinTasks));
        assert_eq!(UnlockPolicy::default(), UnlockPolicy::new(3, 2, 2).unwrap());
    }

    #[test]
    fn nothing_completes_in_the_opening_week() {
        let d = decide(
            UnlockPolicy::DEFAULT,
            W0,
            date!(2026 - 09 - 07),
            FRI,
            &[r(W0, 3)],
        );
        assert_eq!(
            d,
            UnlockDecision::Locked {
                satisfied_weeks: 0,
                needed_weeks: 2,
                weeks_in_window: 0
            }
        );
    }

    #[test]
    fn two_good_weeks_unlock_on_the_next_friday() {
        let res = [r(W0, 2), r(date!(2026 - 09 - 11), 3)];
        // 09-17 (payshanba): ikkinchi hafta hali tugamagan.
        let mid = decide(UnlockPolicy::DEFAULT, W0, date!(2026 - 09 - 17), FRI, &res);
        assert_eq!(
            mid,
            UnlockDecision::Locked {
                satisfied_weeks: 1,
                needed_weeks: 2,
                weeks_in_window: 1
            }
        );
        // 09-18 (juma): ikki hafta tugadi.
        assert_eq!(
            decide(UnlockPolicy::DEFAULT, W0, date!(2026 - 09 - 18), FRI, &res),
            UnlockDecision::Unlocked
        );
    }

    #[test]
    fn weak_weeks_do_not_count_and_missing_weeks_are_zero() {
        let res = [r(W0, 1), r(date!(2026 - 09 - 11), 1)];
        let d = decide(UnlockPolicy::DEFAULT, W0, date!(2026 - 09 - 18), FRI, &res);
        assert_eq!(
            d,
            UnlockDecision::Locked {
                satisfied_weeks: 0,
                needed_weeks: 2,
                weeks_in_window: 2
            }
        );
        let d = decide(UnlockPolicy::DEFAULT, W0, date!(2026 - 09 - 18), FRI, &[]);
        assert_eq!(
            d,
            UnlockDecision::Locked {
                satisfied_weeks: 0,
                needed_weeks: 2,
                weeks_in_window: 2
            }
        );
    }

    #[test]
    fn window_rolls_so_old_failures_are_forgotten() {
        // 5 hafta tugadi: dastlabki 2 tasi yomon, oxirgi 3 tasidan 2 tasi yaxshi.
        let res = [
            r(W0, 0),
            r(date!(2026 - 09 - 11), 0),
            r(date!(2026 - 09 - 18), 2),
            r(date!(2026 - 09 - 25), 0),
            r(date!(2026 - 10 - 02), 3),
        ];
        let d = decide(UnlockPolicy::DEFAULT, W0, date!(2026 - 10 - 09), FRI, &res);
        assert_eq!(d, UnlockDecision::Unlocked);
        // Oyna 2 haftaga qisqarsa — faqat oxirgi 2 tasi (0, 3): 1 ta yaxshi hafta yetmaydi.
        let narrow = UnlockPolicy::new(2, 2, 2).unwrap();
        let d = decide(narrow, W0, date!(2026 - 10 - 09), FRI, &res);
        assert_eq!(
            d,
            UnlockDecision::Locked {
                satisfied_weeks: 1,
                needed_weeks: 2,
                weeks_in_window: 2
            }
        );
    }

    #[test]
    fn configurable_thresholds() {
        let res = [r(W0, 1)];
        let lenient = UnlockPolicy::new(3, 1, 1).unwrap();
        assert_eq!(
            decide(lenient, W0, date!(2026 - 09 - 11), FRI, &res),
            UnlockDecision::Unlocked
        );
        let strict = UnlockPolicy::new(3, 3, 3).unwrap();
        let all = [
            r(W0, 3),
            r(date!(2026 - 09 - 11), 3),
            r(date!(2026 - 09 - 18), 2),
        ];
        assert!(matches!(
            decide(strict, W0, date!(2026 - 09 - 25), FRI, &all),
            UnlockDecision::Locked { .. }
        ));
    }

    #[test]
    fn zero_requirements_still_need_one_finished_week() {
        let p = UnlockPolicy::new(1, 0, 0).unwrap();
        assert!(matches!(
            decide(p, W0, date!(2026 - 09 - 10), FRI, &[]),
            UnlockDecision::Locked { .. }
        ));
        assert_eq!(
            decide(p, W0, date!(2026 - 09 - 11), FRI, &[]),
            UnlockDecision::Unlocked
        );
    }

    #[test]
    fn opened_date_is_normalized_to_its_week() {
        let res = [r(W0, 2), r(date!(2026 - 09 - 11), 2)];
        let d = decide(
            UnlockPolicy::DEFAULT,
            date!(2026 - 09 - 06),
            date!(2026 - 09 - 18),
            FRI,
            &res,
        );
        assert_eq!(d, UnlockDecision::Unlocked);
    }
}
