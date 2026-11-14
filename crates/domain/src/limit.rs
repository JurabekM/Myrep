//! Havas uchun oylik chegara (SPEC 2B.3, MVP_PLAN VAZIFA 7).
//!
//! Chegara faqat barcha kattalar (`ADULT`) o'z PIN'i bilan rozilik bergandan keyin faol bo'ladi.
//! Ogohlantirish yumshoq: 80% va 100% da xabar chiqadi, bloklash yo'q. Havas hisobiga faqat `HAVAS`
//! toifadagi, sovg'a bo'lmagan va sadaqa bo'lmagan xarajatlar kiradi (SPEC 2B.8).

use money::{Currency, Money};
use time::OffsetDateTime;

use crate::necessity::Necessity;
use crate::{DomainError, Meta, validate_uuid_v7};

/// Ogohlantirish chegarasi: 80% (basis points).
pub const WARNING_BP: i128 = 8_000;
/// Chegara to'liq: 100% (basis points).
pub const FULL_BP: i128 = 10_000;

/// Oylik havas chegarasi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HavasLimit {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Oylik summa (musbat).
    pub monthly: Money,
    /// Metama'lumot.
    pub meta: Meta,
}

impl HavasLimit {
    /// Yangi chegara. Summa musbat bo'lishi kerak; rozilik alohida yoziladi ([`LimitConsent`]).
    pub fn create(
        id: &str,
        household_id: &str,
        monthly: Money,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if monthly.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            monthly,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Bitta kattaning roziligi. Bir kishi bir chegaraga bir marta rozi bo'ladi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LimitConsent {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Chegara (UUIDv7).
    pub limit_id: String,
    /// Rozilik bergan kattalar a'zosi (UUIDv7).
    pub member_id: String,
    /// Metama'lumot (`created_at` — rozilik vaqti).
    pub meta: Meta,
}

impl LimitConsent {
    /// Yangi rozilik yozuvi.
    pub fn create(
        id: &str,
        household_id: &str,
        limit_id: &str,
        member_id: &str,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        validate_uuid_v7(limit_id)?;
        validate_uuid_v7(member_id)?;
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            limit_id: limit_id.to_owned(),
            member_id: member_id.to_owned(),
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Chegara faolmi: kattalar ro'yxati bo'sh bo'lmasligi va har bir kattaning roziligi bo'lishi kerak.
/// Bitta kattaning roziligi yetarli emas (SPEC 2B.3: «bir tomonlama» chegara qabul qilinmaydi).
pub fn is_active(adult_ids: &[&str], consented_ids: &[&str]) -> bool {
    !adult_ids.is_empty() && adult_ids.iter().all(|adult| consented_ids.contains(adult))
}

/// Xarajat havas hisobiga kiradimi: `HAVAS` toifa, sovg'a emas, sadaqa emas.
pub fn counts_as_havas(necessity: Necessity, is_gift: bool, is_sadaqa: bool) -> bool {
    necessity == Necessity::Havas && !is_gift && !is_sadaqa
}

/// Havas hisobi uchun bitta xarajat qatori.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SpendLine {
    /// Toifa.
    pub necessity: Necessity,
    /// Sovg'a belgisi.
    pub is_gift: bool,
    /// Kategoriya sadaqa mi.
    pub is_sadaqa: bool,
    /// Summa.
    pub amount: Money,
}

/// Havas sarfi: faqat hisobga kiruvchi qatorlar yig'iladi.
pub fn spent_on_havas(lines: &[SpendLine], currency: Currency) -> Money {
    let minor = lines
        .iter()
        .filter(|line| counts_as_havas(line.necessity, line.is_gift, line.is_sadaqa))
        .fold(0_i64, |acc, line| acc.saturating_add(line.amount.minor()));
    Money::new(minor, currency)
}

/// Chegaraga nisbatan ogohlantirish darajasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LimitLevel {
    /// 80% dan kam.
    Ok,
    /// 80% dan 100% gacha (yumshoq ogohlantirish).
    Warning,
    /// 100% va undan ko'p (yumshoq ogohlantirish, bloklash yo'q).
    Reached,
}

/// Sarfning chegaraga nisbatan darajasi. Chegara nolga teng bo'lsa — `Reached`.
pub fn level(spent: Money, limit: Money) -> LimitLevel {
    let spent = i128::from(spent.minor());
    let limit = i128::from(limit.minor());
    if limit <= 0 || spent * FULL_BP >= limit * FULL_BP {
        LimitLevel::Reached
    } else if spent * FULL_BP >= limit * WARNING_BP {
        LimitLevel::Warning
    } else {
        LimitLevel::Ok
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use time::macros::datetime;

    const LIMIT: &str = "0192c000-0000-7000-8000-000000000011";
    const HOUSEHOLD: &str = "0192c000-0000-7000-8000-0000000000aa";
    const ADULT_1: &str = "0192c000-0000-7000-8000-0000000000b1";
    const ADULT_2: &str = "0192c000-0000-7000-8000-0000000000b2";

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    #[test]
    fn ikki_kattadan_bittasi_tasdiqlasa_chegara_faol_emas() {
        assert!(!is_active(&[ADULT_1, ADULT_2], &[ADULT_1]));
        assert!(is_active(&[ADULT_1, ADULT_2], &[ADULT_1, ADULT_2]));
    }

    #[test]
    fn kattalar_bolmasa_chegara_faol_emas() {
        assert!(!is_active(&[], &[]));
    }

    #[test]
    fn sadaqa_havas_hisobiga_kirmaydi() {
        let lines = [
            SpendLine {
                necessity: Necessity::Havas,
                is_gift: false,
                is_sadaqa: false,
                amount: uzs(100_000),
            },
            SpendLine {
                necessity: Necessity::Havas,
                is_gift: false,
                is_sadaqa: true,
                amount: uzs(500_000),
            },
        ];
        assert_eq!(spent_on_havas(&lines, Currency::Uzs), uzs(100_000));
    }

    #[test]
    fn sovga_havas_hisobiga_kirmaydi() {
        let lines = [SpendLine {
            necessity: Necessity::Havas,
            is_gift: true,
            is_sadaqa: false,
            amount: uzs(200_000),
        }];
        assert_eq!(spent_on_havas(&lines, Currency::Uzs), uzs(0));
    }

    #[test]
    fn zarur_va_kerak_havas_hisobiga_kirmaydi() {
        assert!(!counts_as_havas(Necessity::Zarur, false, false));
        assert!(!counts_as_havas(Necessity::Kerak, false, false));
        assert!(counts_as_havas(Necessity::Havas, false, false));
    }

    #[test]
    fn daraja_80_va_100_foizda() {
        let limit = uzs(1_000);
        assert_eq!(level(uzs(799), limit), LimitLevel::Ok);
        assert_eq!(level(uzs(800), limit), LimitLevel::Warning);
        assert_eq!(level(uzs(999), limit), LimitLevel::Warning);
        assert_eq!(level(uzs(1_000), limit), LimitLevel::Reached);
        assert_eq!(level(uzs(1_500), limit), LimitLevel::Reached);
    }

    #[test]
    fn nol_summali_chegara_rad_etiladi() {
        let now = datetime!(2026-10-15 06:00 UTC);
        assert_eq!(
            HavasLimit::create(LIMIT, HOUSEHOLD, uzs(0), now, "desktop"),
            Err(DomainError::AmountNotPositive)
        );
    }
}
