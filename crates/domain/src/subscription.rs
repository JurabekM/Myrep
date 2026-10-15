//! Obunalar (SPEC 2B.5): takroriy to'lovlar, oylik va yillik narx, oxirgi ishlatilgan sana.
//!
//! «Unutilgan obuna»: bekor qilinmagan, lekin uzoq vaqt «ishlatdim» deb belgilanmagan obuna. Ilova faqat
//! ogohlantiradi; hech narsani avtomatik bekor qilmaydi.

use money::Money;
use time::{Date, OffsetDateTime};

use crate::{DomainError, Meta, validate_name, validate_uuid_v7};

/// «Unutilgan» deb hisoblash chegarasi (kunlarda).
pub const FORGOTTEN_AFTER_DAYS: i64 = 30;

/// Obuna yozuvi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Subscription {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Nomi.
    pub name: String,
    /// Oylik narx (musbat).
    pub monthly: Money,
    /// Yillik narx, bo'lsa (musbat).
    pub yearly: Option<Money>,
    /// Oxirgi «ishlatdim» sanasi.
    pub last_used_on: Option<Date>,
    /// Bekor qilingan sana; `None` — faol.
    pub cancelled_on: Option<Date>,
    /// Metama'lumot.
    pub meta: Meta,
}

impl Subscription {
    /// Yangi obuna. Narxlar musbat bo'lishi kerak.
    pub fn create(
        id: &str,
        household_id: &str,
        name: &str,
        monthly: Money,
        yearly: Option<Money>,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if monthly.minor() <= 0 || yearly.is_some_and(|y| y.minor() <= 0) {
            return Err(DomainError::AmountNotPositive);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            name: validate_name(name)?,
            monthly,
            yearly,
            last_used_on: None,
            cancelled_on: None,
            meta: Meta::created(now, origin_device_id),
        })
    }

    /// «Ishlatdim» deb belgilaydi (oxirgi sana yangilanadi).
    pub fn mark_used(mut self, on: Date) -> Result<Self, DomainError> {
        if self.cancelled_on.is_some() {
            return Err(DomainError::SubscriptionCancelled);
        }
        self.last_used_on = Some(on);
        Ok(self)
    }

    /// Bekor qiladi. Ikkinchi marta bekor qilib bo'lmaydi.
    pub fn cancel(mut self, on: Date) -> Result<Self, DomainError> {
        if self.cancelled_on.is_some() {
            return Err(DomainError::SubscriptionCancelled);
        }
        self.cancelled_on = Some(on);
        Ok(self)
    }

    /// Unutilgan obunami: faol va oxirgi ishlatilishidan [`FORGOTTEN_AFTER_DAYS`] dan ko'p o'tgan.
    /// Hech qachon ishlatilmagan bo'lsa — yaratilgan sanadan hisoblanadi.
    pub fn is_forgotten(&self, today: Date) -> bool {
        if self.cancelled_on.is_some() {
            return false;
        }
        let since = self
            .last_used_on
            .unwrap_or_else(|| self.meta.created_at.date());
        (today - since).whole_days() > FORGOTTEN_AFTER_DAYS
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;
    use time::macros::{date, datetime};

    const ID: &str = "0192f000-0000-7000-8000-000000000011";
    const HOUSEHOLD: &str = "0192f000-0000-7000-8000-0000000000aa";

    fn subscription() -> Subscription {
        Subscription::create(
            ID,
            HOUSEHOLD,
            "Telegram Premium",
            Money::new(3_000_000, Currency::Uzs),
            None,
            datetime!(2026-09-01 06:00 UTC),
            "desktop",
        )
        .expect("obuna")
    }

    #[test]
    fn yangi_obuna_unutilgan_emas_va_otgan_oy_unutilgan() {
        let sub = subscription();
        assert!(!sub.is_forgotten(date!(2026 - 09 - 20)));
        assert!(sub.is_forgotten(date!(2026 - 10 - 15)));
    }

    #[test]
    fn ishlatilgan_obuna_qayta_unutilmaydi() {
        let sub = subscription()
            .mark_used(date!(2026 - 10 - 10))
            .expect("belgilandi");
        assert!(!sub.is_forgotten(date!(2026 - 10 - 15)));
    }

    #[test]
    fn bekor_qilingan_obuna_ikki_marta_bekor_qilinmaydi() {
        let sub = subscription().cancel(date!(2026 - 10 - 01)).expect("bekor");
        assert_eq!(
            sub.clone().cancel(date!(2026 - 10 - 02)),
            Err(DomainError::SubscriptionCancelled)
        );
        assert!(!sub.is_forgotten(date!(2026 - 12 - 01)));
    }

    #[test]
    fn nol_narx_rad_etiladi() {
        assert!(matches!(
            Subscription::create(
                ID,
                HOUSEHOLD,
                "Bekor",
                Money::new(0, Currency::Uzs),
                None,
                datetime!(2026-09-01 06:00 UTC),
                "desktop",
            ),
            Err(DomainError::AmountNotPositive)
        ));
    }
}
