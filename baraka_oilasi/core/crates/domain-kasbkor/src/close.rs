//! K3 — «Hisob kuni» (SPEC 4.5): oy yakunida soliq zaxirasi, egasi maoshi va qolgan pulning
//! taqsimoti.
//!
//! 1. **Soliq zaxirasi** — egasi kiritgan qoida (OQ-K3): tushumdan yoki foydadan (tushum − chiqim,
//!    manfiy bo'lsa 0) foiz, yoki qat'iy summa. Ilova stavka tavsiya qilmaydi.
//! 2. **Egasi maoshi** — belgilangan maosh; olingan (maosh o'tkazmasi + «egasi oldi») undan ko'p
//!    bo'lsa — olingani. Ortig'i tanlansa keyingi oy maoshidan ushlanadi.
//! 3. **Qolgan** = tushum − soliq − chiqim − maosh. Manfiy bo'lmasa — taqsimot qoidasi (zaxira,
//!    aylanma, kengayish, sadaqa; bp, jami 10 000) bo'yicha largest remainder. Manfiy — taqsimot
//!    yo'q, izoh so'raladi. Zaxira ulushi eskirishdan kam bo'lsa — belgi («uskunani almashtirish puli»).
//!
//! Vektorlar: `spec/test-vectors/kk_month_close.json`.
use baraka_money::{allocate, percent_of, Money, BP_ONE};

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TaxRule {
    None,
    /// Tushumdan foiz (bp).
    Revenue {
        bp: i64,
    },
    /// Foydadan (tushum − chiqim) foiz (bp).
    Profit {
        bp: i64,
    },
    Fixed {
        amount: Money,
    },
}

impl TaxRule {
    pub fn base(&self) -> &'static str {
        match self {
            Self::None => "NONE",
            Self::Revenue { .. } => "REVENUE",
            Self::Profit { .. } => "PROFIT",
            Self::Fixed { .. } => "FIXED",
        }
    }
}

/// Taqsimot qoidasi (bp). Jami 10 000.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SplitRule {
    pub reserve_bp: i64,
    pub working_bp: i64,
    pub expansion_bp: i64,
    pub sadaqa_bp: i64,
}

impl SplitRule {
    pub fn validate(&self) -> Result<[i64; 4], DomainError> {
        let parts = [
            self.reserve_bp,
            self.working_bp,
            self.expansion_bp,
            self.sadaqa_bp,
        ];
        if parts.iter().any(|p| *p < 0) || parts.iter().sum::<i64>() != BP_ONE {
            return Err(DomainError::on("INVALID_RULE", "rule"));
        }
        Ok(parts)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CloseInput {
    pub revenue: Money,
    pub expenses: Money,
    pub depreciation: Money,
    pub owner_salary: Money,
    pub owner_paid: Money,
    pub tax: TaxRule,
    pub rule: SplitRule,
    pub carry_overdraw: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Allocation {
    pub reserve: Money,
    pub working: Money,
    pub expansion: Money,
    pub sadaqa: Money,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MonthClose {
    pub tax: Money,
    pub owner_pay: Money,
    pub overdrawn: Money,
    pub carry_forward: Money,
    pub remaining: Money,
    pub needs_explanation: bool,
    pub allocation: Option<Allocation>,
    pub reserve_below_depreciation: bool,
}

pub fn month_close(i: CloseInput) -> Result<MonthClose, DomainError> {
    let fields = [
        (i.revenue, "revenue"),
        (i.expenses, "expenses"),
        (i.depreciation, "depreciation"),
        (i.owner_salary, "ownerSalary"),
        (i.owner_paid, "ownerPaid"),
    ];
    for (m, field) in fields {
        if m.is_negative() {
            return Err(DomainError::on("AMOUNT_NEGATIVE", field));
        }
    }
    let parts = i.rule.validate()?;
    let tax = match i.tax {
        TaxRule::None => Money::zero(i.revenue.currency()),
        TaxRule::Revenue { bp } => percent_of(i.revenue, bp)?,
        TaxRule::Profit { bp } => {
            percent_of(i.revenue.checked_sub(i.expenses)?.clamp_non_negative(), bp)?
        }
        TaxRule::Fixed { amount } if amount.is_negative() => {
            return Err(DomainError::on("AMOUNT_NEGATIVE", "tax"))
        }
        TaxRule::Fixed { amount } => amount,
    };
    let owner_pay = i.owner_salary.max(i.owner_paid)?;
    let overdrawn = if i.owner_salary.is_positive() {
        i.owner_paid
            .checked_sub(i.owner_salary)?
            .clamp_non_negative()
    } else {
        Money::zero(i.revenue.currency())
    };
    let remaining = i
        .revenue
        .checked_sub(tax)?
        .checked_sub(i.expenses)?
        .checked_sub(owner_pay)?;
    let allocation = if remaining.is_negative() {
        None
    } else {
        let a = allocate(remaining, &parts)?;
        Some(Allocation {
            reserve: a[0],
            working: a[1],
            expansion: a[2],
            sadaqa: a[3],
        })
    };
    let reserve_below_depreciation = match allocation {
        Some(a) => a.reserve.compare(&i.depreciation)?.is_lt(),
        None => false,
    };
    Ok(MonthClose {
        tax,
        owner_pay,
        overdrawn,
        carry_forward: if i.carry_overdraw {
            overdrawn
        } else {
            Money::zero(i.revenue.currency())
        },
        remaining,
        needs_explanation: remaining.is_negative(),
        allocation,
        reserve_below_depreciation,
    })
}
