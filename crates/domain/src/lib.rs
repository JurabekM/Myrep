//! Domen modeli: entitylar va qoidalar. Bu crate sof: vaqt, tasodifiylik va IO yo'q.
//!
//! Joriy vaqt [`Clock`] orqali, identifikatorlar [`IdGen`] orqali beriladi (DESKTOP_PROMPT.md 3.2).
//! Barcha entitylar umumiy konvensiyalarga ega: UUIDv7 identifikator, UTC vaqt, mantiqiy o'chirish
//! va versiya raqami (DESKTOP_PROMPT.md 6.1).

pub mod calendar;
pub mod category;
pub mod content;
pub mod content_parser;
pub mod debt;
pub mod expense;
pub mod habit;
pub mod income;
pub mod ledger;
pub mod limit;
pub mod necessity;
pub mod obligation;
pub mod progress;
pub mod report;
pub mod share;
pub mod treat;
pub mod unlock;
pub mod vault;

pub use category::{Category, CategoryKey};
pub use content::{Chapter, ContentBlock, ContentLoadResult, TaskTrigger};
pub use debt::{DebtPayment, ShopDebt};
pub use expense::{Expense, ExpenseDraft};
pub use habit::{HabitStats, habit_stats, streak_since};
pub use income::{Channel, Income, IncomeDraft};
pub use ledger::{
    LedgerInput, MoneyOwner, MonthLedger, ObligationLine, build_month_ledger, whose_money,
};
pub use limit::{HavasLimit, LimitConsent, LimitLevel};
pub use necessity::{Necessity, NecessityChange};
pub use obligation::{Obligation, ObligationDraft, ObligationKind};
pub use progress::{DaftarPage, TaskCompletion};
pub use report::MonthlyReport;
pub use share::{ShareRule, ShareTarget, progression_offer, suggest_share};
pub use treat::ScheduledTreat;
pub use unlock::{ChapterUnlock, ChapterUnlockPolicy, HabitUnlockPolicy, UnlockContext};
pub use vault::{VaultEntry, VaultMovement};

use thiserror::Error;
use time::OffsetDateTime;

/// Nom uzunligi chegarasi (belgilarda).
pub const NAME_MAX_CHARS: usize = 100;

/// Joriy UTC vaqt manbai. Ishlab chiqarishda tizim soati, testlarda qo'lda berilgan vaqt.
pub trait Clock: Send + Sync {
    /// Joriy vaqt (UTC).
    fn now_utc(&self) -> OffsetDateTime;
}

/// Identifikator generatori. Ishlab chiqarishda UUIDv7.
pub trait IdGen: Send + Sync {
    /// Yangi identifikator (36 belgili kichik harfli UUID satri).
    fn next_id(&self) -> String;
}

/// Domen qoidalari buzilganda qaytariladigan xatolar. [`DomainError::code`] barqaror kod beradi.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum DomainError {
    /// Identifikator UUIDv7 formatida emas.
    #[error("identifikator UUIDv7 formatida emas")]
    InvalidId,
    /// Nom bo'sh yoki chegaradan uzun.
    #[error("nom bo'sh yoki 100 belgidan uzun")]
    InvalidName,
    /// Noma'lum a'zo roli.
    #[error("noma'lum a'zo roli")]
    InvalidRole,
    /// Sabab (masalan, pul olish sababi) bo'sh.
    #[error("sabab kiritilishi shart")]
    ReasonRequired,
    /// Summa nol yoki manfiy.
    #[error("summa musbat bo'lishi kerak")]
    AmountNotPositive,
    /// «Kelajagim» balansidan ko'p olib bo'lmaydi.
    #[error("balansda mablag' yetarli emas")]
    InsufficientBalance,
    /// Boshlang'ich balans (ro'molcha) allaqachon kiritilgan.
    #[error("boshlang'ich balans allaqachon kiritilgan")]
    InitialAlreadySet,
    /// Shu daromaddan ulush allaqachon ajratilgan.
    #[error("bu daromaddan ulush allaqachon ajratilgan")]
    IncomeAlreadyShared,
    /// Ajratilgan ulush daromaddan katta.
    #[error("ajratilgan summa daromaddan katta bo'lmasligi kerak")]
    ShareExceedsIncome,
    /// Ulush qoidasi noto'g'ri (foiz chegaradan tashqarida, progressiv qat'iy summa bilan).
    #[error("ulush qoidasi noto'g'ri")]
    InvalidRule,
    /// Nasiyani ortiqcha to'lash (qoldiqdan katta).
    #[error("to'lov nasiya qoldig'idan katta")]
    DebtOverpaid,
    /// Oylik to'lov kuni 1 dan 31 gacha bo'lishi kerak.
    #[error("kun 1 dan 31 gacha bo'lishi kerak")]
    InvalidDay,
    /// Shu oy uchun audit allaqachon yakunlangan.
    #[error("bu oy uchun audit allaqachon yakunlangan")]
    AuditAlreadyDone,
    /// Izohsiz qolgan summa yo'q: belgilash uchun hech narsa yo'q.
    #[error("izohsiz qolgan summa yo'q")]
    NothingToMark,
    /// Bob hali ochilmagan: uning sahifasi va vazifalari ochiq emas.
    #[error("bob hali ochilmagan")]
    ChapterLocked,
    /// Vazifa joriy bobga tegishli emas (faqat joriy bobning haftalik vazifalari belgilanadi).
    #[error("vazifa joriy bobga tegishli emas")]
    TaskNotCurrent,
    /// «Daftar sahifasi» matni bo'sh.
    #[error("sahifa matni bo'sh bo'lmasligi kerak")]
    BodyRequired,
    /// «Daftar sahifasi» matni chegaradan uzun.
    #[error("sahifa matni 5000 belgidan oshmasligi kerak")]
    BodyTooLong,
    /// Toifa o'zgarmagan: yangi va eski toifa bir xil.
    #[error("toifa o'zgarmagan")]
    NecessityUnchanged,
    /// A'zoning PIN'i hali o'rnatilmagan: rozilik berib bo'lmaydi.
    #[error("a'zoning PIN'i o'rnatilmagan")]
    PinNotSet,
    /// Pul amalidagi xato (valyuta mosligi va boshqalar).
    #[error(transparent)]
    Money(#[from] money::MoneyError),
}

impl DomainError {
    /// Barqaror xato kodi (SCREAMING_SNAKE_CASE). Frontend shu kod bo'yicha matn tanlaydi.
    pub fn code(&self) -> &'static str {
        match self {
            Self::InvalidId => "INVALID_ID",
            Self::InvalidName => "INVALID_NAME",
            Self::InvalidRole => "INVALID_ROLE",
            Self::ReasonRequired => "REASON_REQUIRED",
            Self::AmountNotPositive => "AMOUNT_NOT_POSITIVE",
            Self::InsufficientBalance => "INSUFFICIENT_BALANCE",
            Self::InitialAlreadySet => "INITIAL_ALREADY_SET",
            Self::IncomeAlreadyShared => "INCOME_ALREADY_SHARED",
            Self::ShareExceedsIncome => "SHARE_EXCEEDS_INCOME",
            Self::InvalidRule => "INVALID_RULE",
            Self::DebtOverpaid => "DEBT_OVERPAID",
            Self::InvalidDay => "INVALID_DAY",
            Self::AuditAlreadyDone => "AUDIT_ALREADY_DONE",
            Self::NothingToMark => "NOTHING_TO_MARK",
            Self::ChapterLocked => "CHAPTER_LOCKED",
            Self::TaskNotCurrent => "TASK_NOT_CURRENT",
            Self::BodyRequired => "BODY_REQUIRED",
            Self::BodyTooLong => "BODY_TOO_LONG",
            Self::NecessityUnchanged => "NECESSITY_UNCHANGED",
            Self::PinNotSet => "PIN_NOT_SET",
            Self::Money(error) => error.code(),
        }
    }
}

/// UUIDv7 formatini tekshiradi: 8-4-4-4-12 kichik harfli hex, versiya belgisi `7`, variant `8`/`9`/`a`/`b`.
pub fn validate_uuid_v7(id: &str) -> Result<(), DomainError> {
    let bytes = id.as_bytes();
    let well_formed = bytes.len() == 36
        && bytes.iter().enumerate().all(|(index, &byte)| match index {
            8 | 13 | 18 | 23 => byte == b'-',
            _ => byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte),
        });
    let version_ok = bytes.get(14) == Some(&b'7');
    let variant_ok = matches!(bytes.get(19), Some(b'8' | b'9' | b'a' | b'b'));
    if well_formed && version_ok && variant_ok {
        Ok(())
    } else {
        Err(DomainError::InvalidId)
    }
}

/// Nomni tekshiradi va chetki bo'shliqlarini olib tashlaydi.
pub fn validate_name(name: &str) -> Result<String, DomainError> {
    let trimmed = name.trim();
    let length = trimmed.chars().count();
    if (1..=NAME_MAX_CHARS).contains(&length) {
        Ok(trimmed.to_owned())
    } else {
        Err(DomainError::InvalidName)
    }
}

/// Yozuv metama'lumoti: yaratilgan va yangilangan vaqt, mantiqiy o'chirish, versiya, qurilma.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Meta {
    /// Yaratilgan vaqt (UTC).
    pub created_at: OffsetDateTime,
    /// Oxirgi o'zgarish vaqti (UTC).
    pub updated_at: OffsetDateTime,
    /// Mantiqiy o'chirilgan vaqt; `None` bo'lsa yozuv faol.
    pub deleted_at: Option<OffsetDateTime>,
    /// Optimistik parallelizm uchun versiya; har o'zgarishda oshadi.
    pub version: i64,
    /// Yozuvni yaratgan qurilma (sinxronlashda kerak bo'ladi).
    pub origin_device_id: String,
}

impl Meta {
    /// Yangi yozuv uchun metama'lumot (versiya 1).
    pub fn created(now: OffsetDateTime, origin_device_id: &str) -> Self {
        Self {
            created_at: now,
            updated_at: now,
            deleted_at: None,
            version: 1,
            origin_device_id: origin_device_id.to_owned(),
        }
    }
}

/// Xonadon: byudjet va a'zolar birligi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Household {
    /// UUIDv7.
    pub id: String,
    /// Xonadon nomi.
    pub name: String,
    /// Oylik davr boshlanadigan kun (1..31); standart — 1.
    pub month_start_day: u8,
    /// Umumiy metama'lumot.
    pub meta: Meta,
}

impl Household {
    /// Yangi xonadon. Identifikator va nom qoidalarga javob berishi kerak.
    pub fn create(
        id: &str,
        name: &str,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        Ok(Self {
            id: id.to_owned(),
            name: validate_name(name)?,
            month_start_day: calendar::DEFAULT_MONTH_START_DAY,
            meta: Meta::created(now, origin_device_id),
        })
    }

    /// Oylik kunni o'zgartiradi (1..31). Noto'g'ri qiymat — [`DomainError::InvalidDay`].
    pub fn with_month_start_day(mut self, day: u8) -> Result<Self, DomainError> {
        if !(1..=31).contains(&day) {
            return Err(DomainError::InvalidDay);
        }
        self.month_start_day = day;
        Ok(self)
    }
}

/// Xonadon a'zosi roli: kattalar kelishuvni tasdiqlaydi, bolalar tasdiqlamaydi (SPEC 2B.3).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MemberRole {
    /// Kattalar: havas chegarasini va kelishuvlarni tasdiqlaydi.
    Adult,
    /// Bola: ko'rsatiladi, lekin tasdiqlamaydi.
    Child,
}

impl MemberRole {
    /// Bazada saqlanadigan kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Adult => "ADULT",
            Self::Child => "CHILD",
        }
    }

    /// Koddan rol. Noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "ADULT" => Some(Self::Adult),
            "CHILD" => Some(Self::Child),
            _ => None,
        }
    }
}

/// Xonadon a'zosi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Member {
    /// UUIDv7.
    pub id: String,
    /// A'zo tegishli bo'lgan xonadon.
    pub household_id: String,
    /// A'zo ismi.
    pub name: String,
    /// Rol.
    pub role: MemberRole,
    /// Umumiy metama'lumot.
    pub meta: Meta,
}

impl Member {
    /// Yangi a'zo. Ikkala identifikator ham UUIDv7 bo'lishi kerak.
    pub fn create(
        id: &str,
        household_id: &str,
        name: &str,
        role: MemberRole,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            name: validate_name(name)?,
            role,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use time::macros::datetime;

    const ID: &str = "0192a000-0000-7000-8000-0000000000a1";

    #[test]
    fn uuid_v7_togri_qabul_qilinadi() {
        assert_eq!(validate_uuid_v7(ID), Ok(()));
    }

    #[test]
    fn uuid_v7_notogri_formatlar_rad_etiladi() {
        // v4 versiyasi
        assert_eq!(
            validate_uuid_v7("0192a000-0000-4000-8000-0000000000a1"),
            Err(DomainError::InvalidId)
        );
        // katta harf
        assert_eq!(
            validate_uuid_v7("0192A000-0000-7000-8000-0000000000A1"),
            Err(DomainError::InvalidId)
        );
        // noto'g'ri variant
        assert_eq!(
            validate_uuid_v7("0192a000-0000-7000-c000-0000000000a1"),
            Err(DomainError::InvalidId)
        );
        // qisqa va bo'sh
        assert_eq!(validate_uuid_v7("abc"), Err(DomainError::InvalidId));
        assert_eq!(validate_uuid_v7(""), Err(DomainError::InvalidId));
    }

    #[test]
    fn nom_tekshiriladi_va_tozalanadi() {
        assert_eq!(validate_name("  Anvar oila  "), Ok("Anvar oila".to_owned()));
        assert_eq!(validate_name("   "), Err(DomainError::InvalidName));
        let long = "a".repeat(NAME_MAX_CHARS + 1);
        assert_eq!(validate_name(&long), Err(DomainError::InvalidName));
        let max = "a".repeat(NAME_MAX_CHARS);
        assert!(validate_name(&max).is_ok());
    }

    #[test]
    fn rol_kodlari_qaytariladi() {
        for role in [MemberRole::Adult, MemberRole::Child] {
            assert_eq!(MemberRole::from_code(role.code()), Some(role));
        }
        assert_eq!(MemberRole::from_code("ADMIN"), None);
    }

    #[test]
    fn xonadon_va_azo_yaratiladi_metama_bilan() {
        let now = datetime!(2026-10-14 09:00 UTC);
        let household = Household::create(ID, "Oila", now, "device-1").expect("to'g'ri");
        assert_eq!(household.meta.version, 1);
        assert_eq!(household.meta.created_at, now);
        assert_eq!(household.meta.deleted_at, None);

        let member =
            Member::create(ID, ID, "Dilshod", MemberRole::Adult, now, "device-1").expect("to'g'ri");
        assert_eq!(member.household_id, ID);
        assert_eq!(member.role, MemberRole::Adult);

        assert_eq!(
            Household::create("noto'g'ri", "Oila", now, "device-1"),
            Err(DomainError::InvalidId)
        );
    }
}
