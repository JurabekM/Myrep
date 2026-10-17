//! «Kelajagim» jamg'armasi (SPEC 2.2): kirim (ulush, ro'molcha) va chiqim (friction bilan pul olish).
//!
//! Balans — barcha yozuvlar yig'indisi: boshlang'ich balans va ulushlar qo'shiladi, pul olish ayiriladi.
//! Odatga (streak) faqat daromad ulushi kiradi: boshlang'ich balans va pul olish — odat emas.

use money::{Currency, Money, MoneyError};
use time::Date;

use crate::calendar::DateRange;
use crate::{DomainError, Meta};

/// Yozuv turi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VaultMovement {
    /// Boshlang'ich balans («ro'molcha»): ilovadan oldin yig'ilgan jamg'arma, bir marta.
    Initial,
    /// Daromaddan ajratilgan ulush.
    IncomeShare {
        /// Manba daromad (UUIDv7).
        income_id: String,
    },
    /// Pul olish. Sabab majburiy.
    Withdrawal {
        /// Nima uchun olinmoqda.
        reason: String,
    },
    /// «Qutqarilgan pul»dan o'tkazilgan (D7). `rescue_id` — `TRANSFER` turidagi qutqarish yozuvi (UUIDv7).
    RescueDeposit {
        /// Qutqarilgan pul yozuvi.
        rescue_id: String,
    },
}

/// «Kelajagim» yozuvi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VaultEntry {
    /// UUIDv7.
    pub id: String,
    /// Summa (musbat). Yo'nalish [`VaultMovement`] dan.
    pub amount: Money,
    /// Yozuv sanasi (Toshkent).
    pub occurred_on: Date,
    /// Yozuv turi.
    pub movement: VaultMovement,
    /// Metama'lumot.
    pub meta: Meta,
}

impl VaultEntry {
    /// Pul olish yozuvimi.
    pub fn is_withdrawal(&self) -> bool {
        matches!(self.movement, VaultMovement::Withdrawal { .. })
    }

    /// Odatga kiradimi: faqat daromad ulushi.
    pub fn counts_as_habit(&self) -> bool {
        matches!(self.movement, VaultMovement::IncomeShare { .. })
    }
}

/// Balans: kirimlar − chiqimlar. Boshqa valyutadagi yozuvlar hisobga olinmaydi.
pub fn balance(entries: &[VaultEntry], currency: Currency) -> Result<Money, DomainError> {
    let mut total = Money::zero(currency);
    for entry in entries.iter().filter(|e| e.amount.currency() == currency) {
        total = if entry.is_withdrawal() {
            total.checked_sub(entry.amount)?
        } else {
            total.checked_add(entry.amount)?
        };
    }
    Ok(total)
}

/// [`range`] ichida ulush sifatida ajratilgan summa (odat va «o'zingizga to'langan» uchun).
pub fn saved_in(
    entries: &[VaultEntry],
    range: DateRange,
    currency: Currency,
) -> Result<Money, DomainError> {
    let mut total = Money::zero(currency);
    for entry in entries.iter().filter(|e| {
        e.counts_as_habit() && e.amount.currency() == currency && range.contains(e.occurred_on)
    }) {
        total = total.checked_add(entry.amount)?;
    }
    Ok(total)
}

/// Pul olishni tekshiradi: sabab bo'sh bo'lmasligi, summa musbat va balansdan oshmasligi kerak.
/// Muvaffaqiyatda — tozalangan sabab.
pub fn validate_withdrawal(
    balance: Money,
    amount: Money,
    reason: &str,
) -> Result<String, DomainError> {
    let reason = reason.trim();
    if reason.is_empty() {
        return Err(DomainError::ReasonRequired);
    }
    if amount.minor() <= 0 {
        return Err(DomainError::AmountNotPositive);
    }
    if balance.checked_sub(amount)?.minor() < 0 {
        return Err(DomainError::InsufficientBalance);
    }
    Ok(reason.to_owned())
}

/// Boshlang'ich balans hali kiritilmaganmi (bir marta).
pub fn validate_initial(entries: &[VaultEntry]) -> Result<(), DomainError> {
    if entries.iter().any(|e| e.movement == VaultMovement::Initial) {
        return Err(DomainError::InitialAlreadySet);
    }
    Ok(())
}

/// Daromaddan ulushni tekshiradi: musbat, shu daromaddan oldin ajratilmagan va daromaddan oshmaydi.
pub fn validate_share(
    entries: &[VaultEntry],
    income_id: &str,
    income_amount: Money,
    share: Money,
) -> Result<(), DomainError> {
    if share.currency() != income_amount.currency() {
        return Err(DomainError::Money(MoneyError::CurrencyMismatch {
            expected: income_amount.currency(),
            actual: share.currency(),
        }));
    }
    if share.minor() <= 0 {
        return Err(DomainError::AmountNotPositive);
    }
    let already = entries.iter().any(
        |e| matches!(&e.movement, VaultMovement::IncomeShare { income_id: id } if id == income_id),
    );
    if already {
        return Err(DomainError::IncomeAlreadyShared);
    }
    if share.minor() > income_amount.minor() {
        return Err(DomainError::ShareExceedsIncome);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency::Uzs;
    use time::macros::date;

    fn entry(movement: VaultMovement, minor: i64) -> VaultEntry {
        VaultEntry {
            id: "0192a000-0000-7000-8000-0000000000c1".to_owned(),
            amount: Money::new(minor, Uzs),
            occurred_on: date!(2026 - 10 - 14),
            movement,
            meta: Meta::created(time::OffsetDateTime::UNIX_EPOCH, "device-1"),
        }
    }

    #[test]
    fn balans_kirim_minus_chiqim() {
        let entries = [
            entry(VaultMovement::Initial, 1_000_000),
            entry(
                VaultMovement::IncomeShare {
                    income_id: "i".to_owned(),
                },
                800_000,
            ),
            entry(
                VaultMovement::Withdrawal {
                    reason: "Dori".to_owned(),
                },
                300_000,
            ),
        ];
        assert_eq!(balance(&entries, Uzs).expect("balans").minor(), 1_500_000);
    }

    #[test]
    fn sababsiz_va_ortiqcha_pul_olinmaydi() {
        let balance_now = Money::new(100_000, Uzs);
        assert_eq!(
            validate_withdrawal(balance_now, Money::new(1, Uzs), "  "),
            Err(DomainError::ReasonRequired)
        );
        assert_eq!(
            validate_withdrawal(balance_now, Money::new(100_001, Uzs), "Dori"),
            Err(DomainError::InsufficientBalance)
        );
        assert_eq!(
            validate_withdrawal(balance_now, Money::new(100_000, Uzs), " Dori "),
            Ok("Dori".to_owned())
        );
    }

    #[test]
    fn boshlangich_balans_bir_marta() {
        let entries = [entry(VaultMovement::Initial, 1)];
        assert_eq!(
            validate_initial(&entries),
            Err(DomainError::InitialAlreadySet)
        );
        assert_eq!(validate_initial(&[]), Ok(()));
    }

    #[test]
    fn ulush_daromaddan_oshmaydi_va_takrorlanmaydi() {
        let entries = [entry(
            VaultMovement::IncomeShare {
                income_id: "inc-1".to_owned(),
            },
            8_000,
        )];
        let income = Money::new(150_000, Uzs);
        assert_eq!(
            validate_share(&entries, "inc-1", income, Money::new(1_000, Uzs)),
            Err(DomainError::IncomeAlreadyShared)
        );
        assert_eq!(
            validate_share(&entries, "inc-2", income, Money::new(150_001, Uzs)),
            Err(DomainError::ShareExceedsIncome)
        );
        assert_eq!(
            validate_share(&entries, "inc-2", income, Money::new(8_000, Uzs)),
            Ok(())
        );
    }
}
