//! Standart kategoriyalar. Har kategoriya tizim kaliti bilan keladi: «Kimning puli?» va
//! majburiyatlarni qoplash shu kalit bo'yicha ishlaydi (foydalanuvchi nomini o'zgartirsa ham).

use time::OffsetDateTime;

use crate::{DomainError, Meta, validate_uuid_v7};

/// Kategoriya yozuvi. Tizim kategoriyasida [`Category::system_key`] bor.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Category {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Nomi (standart nom yoki foydalanuvchi o'zgartirgani).
    pub name: String,
    /// Tizim kaliti; foydalanuvchi kategoriyasida `None`.
    pub system_key: Option<CategoryKey>,
    /// Metama'lumot.
    pub meta: Meta,
}

impl Category {
    /// Standart (tizim) kategoriya. Nomi — [`CategoryKey::default_name`].
    pub fn system(
        id: &str,
        household_id: &str,
        key: CategoryKey,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            name: key.default_name().to_owned(),
            system_key: Some(key),
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Tizim kategoriyasi kaliti.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum CategoryKey {
    /// Ijara.
    Rent,
    /// Kredit.
    Credit,
    /// Oziq-ovqat.
    Groceries,
    /// Mayda kundalik xarajatlar (izohsiz summa shu kategoriyaga yoziladi).
    DailySmall,
    /// Gazak va ichimlik.
    Snacks,
    /// Kommunal xizmatlar.
    Utilities,
    /// Telefon.
    Phone,
    /// Yoqilg'i.
    Fuel,
    /// Yo'lkira.
    Transport,
    /// Sadaqa (isrof emas, alohida).
    Sadaqa,
    /// Bolalar.
    Children,
    /// Kafe.
    Cafe,
    /// Boshqa.
    Other,
}

impl CategoryKey {
    /// Barcha standart kategoriyalar, ko'rsatish tartibida.
    pub const ALL: [Self; 13] = [
        Self::Rent,
        Self::Credit,
        Self::Groceries,
        Self::DailySmall,
        Self::Snacks,
        Self::Utilities,
        Self::Phone,
        Self::Fuel,
        Self::Transport,
        Self::Sadaqa,
        Self::Children,
        Self::Cafe,
        Self::Other,
    ];

    /// Bazada saqlanadigan kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Rent => "RENT",
            Self::Credit => "CREDIT",
            Self::Groceries => "GROCERIES",
            Self::DailySmall => "DAILY_SMALL",
            Self::Snacks => "SNACKS",
            Self::Utilities => "UTILITIES",
            Self::Phone => "PHONE",
            Self::Fuel => "FUEL",
            Self::Transport => "TRANSPORT",
            Self::Sadaqa => "SADAQA",
            Self::Children => "CHILDREN",
            Self::Cafe => "CAFE",
            Self::Other => "OTHER",
        }
    }

    /// Koddan kalit; noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|key| key.code() == code)
    }

    /// Standart nom (o'zbekcha). Foydalanuvchi bu nomni o'zgartirishi mumkin, kalit o'zgarmaydi.
    pub const fn default_name(self) -> &'static str {
        match self {
            Self::Rent => "Ijara",
            Self::Credit => "Kredit",
            Self::Groceries => "Oziq-ovqat",
            Self::DailySmall => "Mayda kundalik",
            Self::Snacks => "Gazak va ichimlik",
            Self::Utilities => "Kommunal",
            Self::Phone => "Telefon",
            Self::Fuel => "Yoqilgʻi",
            Self::Transport => "Yoʻlkira",
            Self::Sadaqa => "Sadaqa",
            Self::Children => "Bolalar",
            Self::Cafe => "Kafe",
            Self::Other => "Boshqa",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn kod_qaytarilib_oqiladi() {
        for key in CategoryKey::ALL {
            assert_eq!(CategoryKey::from_code(key.code()), Some(key));
        }
        assert_eq!(CategoryKey::from_code("NOMA_LUM"), None);
    }
}
