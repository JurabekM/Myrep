//! Bob jarayoni: haftalik vazifa bajarilishi va «Daftar sahifasi» (SPEC 1.1, 2C.6).
//!
//! Vazifa belgisi har hafta alohida yoziladi (`week_start` — shu haftaning jumasi). Belgi olib tashlansa
//! yozuv mantiqiy o'chiriladi, lekin birinchi bajarilish tarixi saqlanadi (ochilish shunga bog'liq).

use time::{Date, OffsetDateTime};

use crate::{DomainError, Meta, validate_uuid_v7};

/// «Daftar sahifasi» matnining eng ko'p belgisi.
pub const DAFTAR_BODY_MAX_CHARS: usize = 5000;

/// Bitta haftalik vazifaning bajarilishi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TaskCompletion {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Vazifa ID (`ch01.t1`).
    pub task_id: String,
    /// Vazifa bajarilgan haftaning boshi (juma, Toshkent).
    pub week_start: Date,
    /// Ilova avtomatik belgilaganmi (`true`) yoki foydalanuvchi qo'lda.
    pub is_auto: bool,
    /// Metama'lumot.
    pub meta: Meta,
}

impl TaskCompletion {
    /// Yangi bajarilish. Identifikatorlar UUIDv7, vazifa ID bo'sh bo'lmasligi kerak.
    pub fn create(
        id: &str,
        household_id: &str,
        task_id: &str,
        week_start: Date,
        is_auto: bool,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if task_id.trim().is_empty() {
            return Err(DomainError::InvalidId);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            task_id: task_id.to_owned(),
            week_start,
            is_auto,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// «Daftar sahifasi»: bob qonunini foydalanuvchi o'z so'zlari bilan yozgan sahifa. Har bob uchun bitta.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DaftarPage {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Bob ID.
    pub chapter_id: String,
    /// Qonun raqami (sarlavha uchun).
    pub law_number: u32,
    /// Foydalanuvchi matni (bo'sh emas, [`DAFTAR_BODY_MAX_CHARS`] gacha).
    pub body: String,
    /// Metama'lumot.
    pub meta: Meta,
}

impl DaftarPage {
    /// Yangi sahifa.
    pub fn create(
        id: &str,
        household_id: &str,
        chapter_id: &str,
        law_number: u32,
        body: &str,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if chapter_id.trim().is_empty() {
            return Err(DomainError::InvalidId);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            chapter_id: chapter_id.to_owned(),
            law_number,
            body: validate_body(body)?,
            meta: Meta::created(now, origin_device_id),
        })
    }

    /// Matnni yangilaydi. Versiya oshadi, `updated_at` yangilanadi.
    pub fn with_body(mut self, body: &str, now: OffsetDateTime) -> Result<Self, DomainError> {
        self.body = validate_body(body)?;
        self.meta.updated_at = now;
        self.meta.version += 1;
        Ok(self)
    }
}

/// Matnni tekshiradi: chetki bo'shliqlar olib tashlanadi, bo'sh bo'lmasligi va chegaradan oshmasligi kerak.
pub fn validate_body(body: &str) -> Result<String, DomainError> {
    let trimmed = body.trim();
    if trimmed.is_empty() {
        return Err(DomainError::BodyRequired);
    }
    if trimmed.chars().count() > DAFTAR_BODY_MAX_CHARS {
        return Err(DomainError::BodyTooLong);
    }
    Ok(trimmed.to_owned())
}

#[cfg(test)]
mod tests {
    use time::macros::{date, datetime};

    use super::*;

    const ID: &str = "0190f2a0-0000-7000-8000-000000000001";
    const HOUSEHOLD: &str = "0190f2a0-0000-7000-8000-0000000000aa";

    #[test]
    fn bosh_daftar_sahifasi_rad_etiladi() {
        let now = datetime!(2026-10-14 06:00 UTC);
        let result = DaftarPage::create(ID, HOUSEHOLD, "ch05", 5, "   \n ", now, "desktop");
        assert_eq!(result, Err(DomainError::BodyRequired));
    }

    #[test]
    fn juda_uzun_daftar_sahifasi_rad_etiladi() {
        let body = "a".repeat(DAFTAR_BODY_MAX_CHARS + 1);
        assert_eq!(validate_body(&body), Err(DomainError::BodyTooLong));
        assert!(validate_body(&"a".repeat(DAFTAR_BODY_MAX_CHARS)).is_ok());
    }

    #[test]
    fn matn_yangilanganda_versiya_oshadi() {
        let now = datetime!(2026-10-14 06:00 UTC);
        let page = DaftarPage::create(ID, HOUSEHOLD, "ch05", 5, "Birinchi", now, "desktop")
            .expect("yaratilsin");
        let later = datetime!(2026-10-15 06:00 UTC);
        let edited = page.with_body("  Ikkinchi  ", later).expect("yangilansin");
        assert_eq!(edited.body, "Ikkinchi");
        assert_eq!(edited.meta.version, 2);
        assert_eq!(edited.meta.updated_at, later);
    }

    #[test]
    fn vazifa_bajarilishi_hafta_bilan_yoziladi() {
        let now = datetime!(2026-10-14 06:00 UTC);
        let done = TaskCompletion::create(
            ID,
            HOUSEHOLD,
            "ch01.t1",
            date!(2026 - 10 - 09),
            true,
            now,
            "desktop",
        )
        .expect("yaratilsin");
        assert!(done.is_auto);
        assert_eq!(done.week_start, date!(2026 - 10 - 09));
    }

    #[test]
    fn bosh_vazifa_idsi_rad_etiladi() {
        let now = datetime!(2026-10-14 06:00 UTC);
        let result = TaskCompletion::create(
            ID,
            HOUSEHOLD,
            " ",
            date!(2026 - 10 - 09),
            false,
            now,
            "desktop",
        );
        assert_eq!(result, Err(DomainError::InvalidId));
    }
}
