//! M3 — sovutish davri va kengaytirilgan taklif detektori (musofir/SPEC 6.3).
//!
//! * Sheriklik va sarmoyada — U12 «Taklifni tekshirish» 6 savoli (`docs/uy/SPEC.md` 2E.5; jadval
//!   `domain-uy::venture::offer_check` bilan bir xil — vektorlar tekshiradi; domen qatlamlari bir-biriga
//!   bog'lanmaydi).
//! * Musofirga xos savollar: qaytgandan keyin tanish orqali kelgan taklif, avval pul, chet elga qayta ish
//!   uchun pul, qarzni qaytarish muddati, oila bilan maslahat.
//! * Sovutish qoidasi: qaytgandan keyin 90 kun ichida olib kelinganning 10 %idan ko'pi — sariq,
//!   30 %idan ko'pi — qizil (OQ-MF8). Qaror taqiqlanmaydi.
//!
//! Vektorlar: `spec/test-vectors/mf_cooling.json`.
use baraka_money::Money;
use chrono::{Days, NaiveDate};

use crate::{bp_of, DomainError};

pub const COOLING_DAYS: u64 = 90;
pub const BIG_DECISION_BP: i64 = 1_000;
pub const LARGE_SHARE_BP: i64 = 3_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DecisionKind {
    Lend,
    Partnership,
    Invest,
    Purchase,
    Other,
}

impl DecisionKind {
    pub fn parse(s: &str) -> Option<Self> {
        Some(match s {
            "LEND" => Self::Lend,
            "PARTNERSHIP" => Self::Partnership,
            "INVEST" => Self::Invest,
            "PURCHASE" => Self::Purchase,
            "OTHER" => Self::Other,
            _ => return None,
        })
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Lend => "LEND",
            Self::Partnership => "PARTNERSHIP",
            Self::Invest => "INVEST",
            Self::Purchase => "PURCHASE",
            Self::Other => "OTHER",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Reply {
    Yes,
    No,
    Unknown,
}

impl Reply {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "YES" => Some(Self::Yes),
            "NO" => Some(Self::No),
            "UNKNOWN" => Some(Self::Unknown),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Level {
    Green,
    Yellow,
    Red,
}

impl Level {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Green => "GREEN",
            Self::Yellow => "YELLOW",
            Self::Red => "RED",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Flag {
    pub code: &'static str,
    pub level: Level,
}

/// Savol: kalit va (javob → bayroq) jadvali.
type Question = (&'static str, &'static [(Reply, &'static str, Level)]);

/// U12 «Taklifni tekshirish» (2E.5) — sheriklik va sarmoyada.
pub const OFFER_QUESTIONS: [Question; 6] = [
    (
        "guaranteed",
        &[
            (Reply::Yes, "GUARANTEED_PROFIT", Level::Red),
            (Reply::Unknown, "GUARANTEED_UNKNOWN", Level::Yellow),
        ],
    ),
    (
        "lossShared",
        &[
            (Reply::No, "LOSS_NOT_SHARED", Level::Red),
            (Reply::Unknown, "LOSS_SHARING_UNKNOWN", Level::Yellow),
        ],
    ),
    (
        "realActivity",
        &[
            (Reply::No, "NO_REAL_ACTIVITY", Level::Red),
            (Reply::Unknown, "REAL_ACTIVITY_UNKNOWN", Level::Yellow),
        ],
    ),
    (
        "recruitment",
        &[
            (Reply::Yes, "RECRUITMENT_REQUIRED", Level::Red),
            (Reply::Unknown, "RECRUITMENT_UNKNOWN", Level::Yellow),
        ],
    ),
    (
        "urgency",
        &[
            (Reply::Yes, "URGENCY", Level::Yellow),
            (Reply::Unknown, "URGENCY_UNKNOWN", Level::Yellow),
        ],
    ),
    (
        "written",
        &[
            (Reply::No, "NO_WRITTEN_CONTRACT", Level::Yellow),
            (Reply::Unknown, "WRITTEN_UNKNOWN", Level::Yellow),
        ],
    ),
];

/// Musofirga xos savollar; `repaymentDate` — faqat qarz berishda.
pub const EXTRA_QUESTIONS: [Question; 5] = [
    (
        "approached",
        &[(Reply::Yes, "FRESH_RETURN_APPROACH", Level::Yellow)],
    ),
    (
        "upfront",
        &[
            (Reply::Yes, "UPFRONT_BEFORE_DOCUMENTS", Level::Red),
            (Reply::Unknown, "UPFRONT_UNKNOWN", Level::Yellow),
        ],
    ),
    (
        "abroadJobFee",
        &[(Reply::Yes, "ABROAD_JOB_FEE", Level::Red)],
    ),
    (
        "repaymentDate",
        &[
            (Reply::No, "NO_REPAYMENT_DATE", Level::Yellow),
            (Reply::Unknown, "REPAYMENT_DATE_UNKNOWN", Level::Yellow),
        ],
    ),
    (
        "familyDiscussed",
        &[(Reply::No, "NOT_DISCUSSED", Level::Yellow)],
    ),
];

/// Shu qaror turi uchun beriladigan savollar (tartibi — bayroqlar tartibi).
pub fn questions(kind: DecisionKind) -> Vec<&'static str> {
    let mut out = Vec::new();
    if matches!(kind, DecisionKind::Partnership | DecisionKind::Invest) {
        out.extend(OFFER_QUESTIONS.iter().map(|q| q.0));
    }
    out.extend(
        EXTRA_QUESTIONS
            .iter()
            .map(|q| q.0)
            .filter(|q| *q != "repaymentDate" || kind == DecisionKind::Lend),
    );
    out
}

/// Sovutish davri: qaytgandan keyin 90 kun (qaytish sanasi kuni ham ichida, 90-kun — tashqarida).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CoolingWindow {
    pub in_cooling: bool,
    pub ends_on: Option<NaiveDate>,
    pub days_left: i64,
}

pub fn cooling_window(today: NaiveDate, returned_on: Option<NaiveDate>) -> CoolingWindow {
    let ends_on = returned_on.and_then(|r| r.checked_add_days(Days::new(COOLING_DAYS)));
    let in_cooling =
        matches!((returned_on, ends_on), (Some(r), Some(e)) if r <= today && today < e);
    CoolingWindow {
        in_cooling,
        ends_on,
        days_left: match (in_cooling, ends_on) {
            (true, Some(e)) => (e - today).num_days(),
            _ => 0,
        },
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CoolingCheck {
    pub in_cooling: bool,
    pub ends_on: Option<NaiveDate>,
    pub days_left: i64,
    pub share_bp: Option<i64>,
    pub flags: Vec<Flag>,
    pub verdict: Level,
    pub wait_until: Option<NaiveDate>,
}

/// `answers` — (savol kaliti, javob); `brought` — qaytishda olib kelingan summa (uy valyutasida).
pub fn cooling_check(
    today: NaiveDate,
    returned_on: Option<NaiveDate>,
    brought: Option<Money>,
    kind: DecisionKind,
    amount: Money,
    answers: &[(&str, Reply)],
) -> Result<CoolingCheck, DomainError> {
    if !amount.is_positive() {
        return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
    }
    if brought.is_some_and(|b| b.is_negative()) {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "broughtHome"));
    }
    let mut flags = Vec::new();
    for key in questions(kind) {
        let reply = answers
            .iter()
            .find(|(k, _)| *k == key)
            .map(|(_, r)| *r)
            .ok_or(DomainError::on("MISSING_ANSWER", "answers"))?;
        let table = OFFER_QUESTIONS
            .iter()
            .chain(EXTRA_QUESTIONS.iter())
            .find(|q| q.0 == key)
            .map(|q| q.1)
            .unwrap_or(&[]);
        if let Some((_, code, level)) = table.iter().find(|(r, _, _)| *r == reply) {
            flags.push(Flag {
                code,
                level: *level,
            });
        }
    }
    let CoolingWindow {
        in_cooling,
        ends_on,
        days_left,
    } = cooling_window(today, returned_on);
    let share_bp = match brought {
        Some(b) if b.is_positive() => {
            if b.currency() != amount.currency() {
                return Err(DomainError::new("CURRENCY_MISMATCH"));
            }
            Some(bp_of(amount.minor(), b.minor())?)
        }
        _ => None,
    };
    if in_cooling {
        let flag = match share_bp {
            None => Some(("COOLING_PERIOD", Level::Yellow)),
            Some(s) if s > LARGE_SHARE_BP => Some(("LARGE_SHARE", Level::Red)),
            Some(s) if s > BIG_DECISION_BP => Some(("COOLING_BIG_DECISION", Level::Yellow)),
            Some(_) => None,
        };
        if let Some((code, level)) = flag {
            flags.push(Flag { code, level });
        }
    }
    let verdict = flags.iter().map(|f| f.level).max().unwrap_or(Level::Green);
    Ok(CoolingCheck {
        in_cooling,
        ends_on,
        days_left,
        share_bp,
        wait_until: ends_on.filter(|_| in_cooling && verdict != Level::Green),
        flags,
        verdict,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn d(y: i32, m: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(y, m, day).unwrap()
    }

    #[test]
    fn relative_asks_for_open_ended_loan() {
        let u = |m| Money::new(m, Currency::Uzs);
        let answers = [
            ("approached", Reply::Yes),
            ("upfront", Reply::No),
            ("abroadJobFee", Reply::No),
            ("repaymentDate", Reply::No),
            ("familyDiscussed", Reply::Yes),
        ];
        let c = cooling_check(
            d(2026, 11, 8),
            Some(d(2026, 10, 19)),
            Some(u(12_000_000_000)),
            DecisionKind::Lend,
            u(1_500_000_000),
            &answers,
        )
        .unwrap();
        assert_eq!(c.verdict, Level::Yellow);
        assert_eq!(c.days_left, 70);
        assert_eq!(c.wait_until, Some(d(2027, 1, 17)));
        assert_eq!(c.flags.len(), 3);
    }

    #[test]
    fn offer_questions_only_for_partnership_and_invest() {
        assert_eq!(questions(DecisionKind::Purchase).len(), 4);
        assert_eq!(questions(DecisionKind::Lend).len(), 5);
        assert_eq!(questions(DecisionKind::Invest).len(), 10);
    }
}
