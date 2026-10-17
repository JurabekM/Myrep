//! Uch toifali tasnif (SPEC 2B.2): `ZARUR` → `KERAK` → `HAVAS`. Byudjet taqsimoti shu tartibda hisoblanadi.
//!
//! Har bir kategoriyaning standart toifasi bor (lekin oila uni o'zgartira oladi). Toifa o'zgarganda
//! kim va qachon o'zgartirgani tarixda saqlanadi ([`NecessityChange`]).

use time::OffsetDateTime;

use crate::{DomainError, Meta, validate_uuid_v7};

/// Xarajat yoki kategoriya toifasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Necessity {
    /// Usiz yashab bo'lmaydi: non, dori, ijara, kredit, yo'lkira.
    Zarur,
    /// Usiz yashasa bo'ladi, lekin qiyin: bola ta'limi, kiyim.
    Kerak,
    /// Usiz bemalol yashasa bo'ladi: ulfatchilik, ortiqcha ichimlik, o'yinlar.
    Havas,
}

impl Necessity {
    /// Barcha toifalar, ustuvorlik tartibida (avval `ZARUR`).
    pub const ALL: [Self; 3] = [Self::Zarur, Self::Kerak, Self::Havas];

    /// Bazada saqlanadigan kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Zarur => "ZARUR",
            Self::Kerak => "KERAK",
            Self::Havas => "HAVAS",
        }
    }

    /// Koddan toifa. Noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|level| level.code() == code)
    }
}

/// Toifa o'zgarishi: kim, qaysi kategoriyada, qanday o'zgartirdi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NecessityChange {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Kategoriya (UUIDv7).
    pub category_id: String,
    /// Oldingi toifa.
    pub from: Necessity,
    /// Yangi toifa.
    pub to: Necessity,
    /// O'zgartirgan a'zo (UUIDv7).
    pub changed_by: String,
    /// Metama'lumot.
    pub meta: Meta,
}

impl NecessityChange {
    /// Yangi o'zgarish yozuvi. Toifa haqiqatan o'zgargan bo'lishi kerak.
    pub fn create(
        id: &str,
        household_id: &str,
        category_id: &str,
        (from, to): (Necessity, Necessity),
        changed_by: &str,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        validate_uuid_v7(category_id)?;
        validate_uuid_v7(changed_by)?;
        if from == to {
            return Err(DomainError::NecessityUnchanged);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            category_id: category_id.to_owned(),
            from,
            to,
            changed_by: changed_by.to_owned(),
            meta: Meta::created(now, origin_device_id),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use time::macros::datetime;

    const ID: &str = "0192c000-0000-7000-8000-000000000001";
    const HOUSEHOLD: &str = "0192c000-0000-7000-8000-0000000000aa";
    const CATEGORY: &str = "0192c000-0000-7000-8000-0000000000cc";
    const MEMBER: &str = "0192c000-0000-7000-8000-0000000000bb";

    #[test]
    fn kod_qaytarilib_oqiladi() {
        for level in Necessity::ALL {
            assert_eq!(Necessity::from_code(level.code()), Some(level));
        }
        assert_eq!(Necessity::from_code("NOMA_LUM"), None);
    }

    #[test]
    fn ustuvorlik_zarur_avval() {
        assert!(Necessity::Zarur < Necessity::Kerak);
        assert!(Necessity::Kerak < Necessity::Havas);
    }

    #[test]
    fn ozgarish_tarixi_yaratiladi() {
        let now = datetime!(2026-10-15 06:00 UTC);
        let change = NecessityChange::create(
            ID,
            HOUSEHOLD,
            CATEGORY,
            (Necessity::Havas, Necessity::Kerak),
            MEMBER,
            now,
            "desktop",
        )
        .expect("o'zgarish");
        assert_eq!(change.from, Necessity::Havas);
        assert_eq!(change.to, Necessity::Kerak);
        assert_eq!(change.changed_by, MEMBER);
        assert_eq!(change.category_id, CATEGORY);
    }

    #[test]
    fn ozgarmagan_toifa_rad_etiladi() {
        let now = datetime!(2026-10-15 06:00 UTC);
        let result = NecessityChange::create(
            ID,
            HOUSEHOLD,
            CATEGORY,
            (Necessity::Kerak, Necessity::Kerak),
            MEMBER,
            now,
            "desktop",
        );
        assert_eq!(result, Err(DomainError::NecessityUnchanged));
    }
}
