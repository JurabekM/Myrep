//! K2 — uskunalar va eskirish (SPEC 3.1, 3.3).
//!
//! - Oylik eskirish = (narx − qoldiq qiymati) ni foydali muddat oylariga largest remainder bilan teng
//!   bo'lish: qoldiq tiyinlar birinchi oylarga, yig'indi aniq (narx − qoldiq qiymati).
//! - 0-oy — xarid qilingan oy. Eskirish pul harakati emas.
//! - `d`-oyda sotilsa yoki yaroqsiz bo'lsa: shu oydan oddiy eskirish yo'q; `d`-oyda bir martalik
//!   «chiqib ketish» = balans qiymati − tushgan pul (manfiy — foyda); keyin balans 0.
//!
//! Vektorlar: `spec/test-vectors/kk_depreciation.json`.
use baraka_money::{allocate, Money};

use crate::DomainError;

/// Foydali muddatning yuqori chegarasi (50 yil).
pub const MAX_USEFUL_MONTHS: u32 = 600;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Disposal {
    /// Xarid oyidan boshlab nechanchi oy (0 — xarid oyi).
    pub month: u32,
    pub proceeds: Money,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Equipment {
    pub cost: Money,
    pub salvage: Money,
    pub useful_months: u32,
    pub disposal: Option<Disposal>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct EquipmentMonth {
    pub depreciation: Money,
    /// Faqat chiqib ketish oyida; manfiy — balansdan qimmatga sotilgan.
    pub disposal: Money,
    /// Oy oxiridagi balans qiymati.
    pub book_value: Money,
}

impl Equipment {
    pub fn validate(&self) -> Result<(), DomainError> {
        if !self.cost.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "cost"));
        }
        if self.salvage.is_negative() || self.salvage.compare(&self.cost)?.is_gt() {
            return Err(DomainError::on("INVALID_SALVAGE", "salvage"));
        }
        if !(1..=MAX_USEFUL_MONTHS).contains(&self.useful_months) {
            return Err(DomainError::on("INVALID_USEFUL_LIFE", "usefulMonths"));
        }
        if let Some(d) = self.disposal {
            if d.proceeds.is_negative() {
                return Err(DomainError::on("AMOUNT_NEGATIVE", "proceeds"));
            }
            // Valyuta bir xil bo'lishi shart.
            d.proceeds.compare(&self.cost)?;
        }
        Ok(())
    }

    /// Oylik eskirish jadvali (uzunligi — foydali muddat).
    pub fn schedule(&self) -> Result<Vec<Money>, DomainError> {
        self.validate()?;
        let n = usize::try_from(self.useful_months)
            .map_err(|_| DomainError::on("INVALID_USEFUL_LIFE", "usefulMonths"))?;
        Ok(allocate(self.cost.checked_sub(self.salvage)?, &vec![1; n])?)
    }

    /// `month`-oy (0 — xarid oyi) natijasi.
    pub fn month(&self, month: u32) -> Result<EquipmentMonth, DomainError> {
        let schedule = self.schedule()?;
        let zero = Money::zero(self.cost.currency());
        let book_before = |m: u32| -> Result<Money, DomainError> {
            let k = usize::try_from(m.min(self.useful_months)).unwrap_or(schedule.len());
            Ok(self.cost.checked_sub(Money::sum(
                schedule[..k].iter().copied(),
                self.cost.currency(),
            )?)?)
        };
        if let Some(d) = self.disposal.filter(|d| month >= d.month) {
            let disposal = if month == d.month {
                book_before(d.month)?.checked_sub(d.proceeds)?
            } else {
                zero
            };
            return Ok(EquipmentMonth {
                depreciation: zero,
                disposal,
                book_value: zero,
            });
        }
        let depreciation = usize::try_from(month)
            .ok()
            .and_then(|i| schedule.get(i).copied())
            .unwrap_or(zero);
        Ok(EquipmentMonth {
            depreciation,
            disposal: zero,
            book_value: book_before(month.saturating_add(1))?,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(major: i64) -> Money {
        Money::from_major(major, Currency::Uzs).unwrap()
    }

    #[test]
    fn remainder_tiyins_go_to_first_months_and_sum_is_exact() {
        let e = Equipment {
            cost: uzs(7_000_000),
            salvage: uzs(0),
            useful_months: 36,
            disposal: None,
        };
        let s = e.schedule().unwrap();
        assert_eq!(s.iter().filter(|m| m.minor() == 19_444_445).count(), 16);
        assert_eq!(s[16].minor(), 19_444_444);
        assert_eq!(Money::sum(s, Currency::Uzs).unwrap(), uzs(7_000_000));
        assert_eq!(e.month(35).unwrap().book_value, uzs(0));
    }
}
