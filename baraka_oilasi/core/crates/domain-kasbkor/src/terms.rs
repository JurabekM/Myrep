//! K6 — xodim (`EMPLOYMENT`) va ta'minotchi (`SUPPLY`) kelishuvlarining pul shartlari (SPEC 7.1–7.2).
//! Foiz, ustama yoki jarima maydoni **yo'q**; avans qoidasi — eng ko'p qoldiq va necha oyda ushlanishi.
use baraka_money::Money;

use crate::payroll::MAX_ADVANCE_INSTALLMENTS;
use crate::supply::MAX_SUPPLY_DAYS;
use crate::DomainError;

pub const MAX_PAY_DAY: u32 = 28;
pub const MAX_NOTICE_DAYS: u32 = 90;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct EmploymentTerms {
    /// Oylik qat'iy haq (foyda ulushi — OQ-D5, hali yo'q).
    pub salary: Money,
    /// Har oyning qaysi kuni to'lanadi (1–28).
    pub pay_day: u32,
    /// Ajralishdan necha kun oldin ogohlantiriladi.
    pub notice_days: u32,
    /// Avans qoldig'i bundan oshmaydi; `None` — chegara kelishilmagan.
    pub max_advance: Option<Money>,
    /// Avans eng ko'pi bilan necha oyda ushlanadi.
    pub max_advance_installments: u32,
}

impl EmploymentTerms {
    pub fn validate(&self) -> Result<(), DomainError> {
        if !self.salary.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "salary"));
        }
        if !(1..=MAX_PAY_DAY).contains(&self.pay_day) {
            return Err(DomainError::on("INVALID_PAY_DAY", "payDay"));
        }
        if self.notice_days > MAX_NOTICE_DAYS {
            return Err(DomainError::on("INVALID_DAYS", "noticeDays"));
        }
        if self.max_advance.is_some_and(|m| !m.is_positive()) {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "maxAdvance"));
        }
        if !(1..=MAX_ADVANCE_INSTALLMENTS).contains(&self.max_advance_installments) {
            return Err(DomainError::on(
                "INVALID_INSTALLMENTS",
                "maxAdvanceInstallments",
            ));
        }
        Ok(())
    }

    /// Yangi avans kelishilgan qoidaga mosmi: `outstanding` — hali ushlanmagan avanslar.
    pub fn check_advance(
        &self,
        amount: Money,
        installments: u32,
        outstanding: Money,
    ) -> Result<(), DomainError> {
        if !amount.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
        }
        if installments == 0 || installments > self.max_advance_installments {
            return Err(DomainError::on("INVALID_INSTALLMENTS", "installments"));
        }
        if let Some(max) = self.max_advance {
            if outstanding.checked_add(amount)?.compare(&max)?.is_gt() {
                return Err(DomainError::on("ADVANCE_ABOVE_LIMIT", "amount"));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SupplyTerms {
    /// Qotirilgan narx, ko'rsatish birligiga (1 kg, 1 l, 1 m yoki 1 dona); `None` — har yetkazishda summa.
    pub unit_price: Option<Money>,
    /// Yetkazishdan necha kun ichida to'lanadi (0 — darhol).
    pub payment_days: u32,
}

impl SupplyTerms {
    pub fn validate(&self) -> Result<(), DomainError> {
        if self.unit_price.is_some_and(|p| !p.is_positive()) {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "unitPrice"));
        }
        if self.payment_days > MAX_SUPPLY_DAYS {
            return Err(DomainError::on("INVALID_DAYS", "paymentDays"));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use baraka_money::Currency;

    use super::*;

    fn so(v: i64) -> Money {
        Money::new(v * 100, Currency::Uzs)
    }

    fn sardor() -> EmploymentTerms {
        EmploymentTerms {
            salary: so(3_000_000),
            pay_day: 5,
            notice_days: 14,
            max_advance: Some(so(1_500_000)),
            max_advance_installments: 3,
        }
    }

    #[test]
    fn employment_terms_and_advance_rule() {
        sardor().validate().unwrap();
        let bad_day = EmploymentTerms {
            pay_day: 31,
            ..sardor()
        };
        assert_eq!(bad_day.validate().unwrap_err().code, "INVALID_PAY_DAY");
        let t = sardor();
        t.check_advance(so(1_000_000), 2, so(0)).unwrap();
        assert_eq!(
            t.check_advance(so(1_000_000), 2, so(600_000))
                .unwrap_err()
                .code,
            "ADVANCE_ABOVE_LIMIT"
        );
        assert_eq!(
            t.check_advance(so(100_000), 4, so(0)).unwrap_err().code,
            "INVALID_INSTALLMENTS"
        );
    }

    #[test]
    fn supply_terms() {
        SupplyTerms {
            unit_price: Some(so(12_500)),
            payment_days: 30,
        }
        .validate()
        .unwrap();
        assert_eq!(
            SupplyTerms {
                unit_price: None,
                payment_days: 366
            }
            .validate()
            .unwrap_err()
            .code,
            "INVALID_DAYS"
        );
    }
}
