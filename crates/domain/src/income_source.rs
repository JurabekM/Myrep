//! Daromad manbasi turi (SPEC, `IncomeSourceType`): ixtiyoriy belgi. Kodlar: `TER | MOL | TAVAKKAL | RIBO`.
//!
//! Ma'nolari (ko'rsatiladigan nomlari) SPEC'da hali izohlanmagan — OPEN_QUESTIONS, 42-band.
//! Ilovada foiz stavkasi «muqobil daromad» sifatida ko'rsatilmaydi; `RIBO` faqat belgi.

/// Daromad manbasi turi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IncomeSourceType {
    /// `TER`.
    Ter,
    /// `MOL`.
    Mol,
    /// `TAVAKKAL`.
    Tavakkal,
    /// `RIBO`.
    Ribo,
}

impl IncomeSourceType {
    /// Bazadagi va bindingdagi kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Ter => "TER",
            Self::Mol => "MOL",
            Self::Tavakkal => "TAVAKKAL",
            Self::Ribo => "RIBO",
        }
    }

    /// Koddan tur. Noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "TER" => Some(Self::Ter),
            "MOL" => Some(Self::Mol),
            "TAVAKKAL" => Some(Self::Tavakkal),
            "RIBO" => Some(Self::Ribo),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn kodlar_qaytariladi_va_noma_lum_kod_rad_etiladi() {
        for source in [
            IncomeSourceType::Ter,
            IncomeSourceType::Mol,
            IncomeSourceType::Tavakkal,
            IncomeSourceType::Ribo,
        ] {
            assert_eq!(IncomeSourceType::from_code(source.code()), Some(source));
        }
        assert_eq!(IncomeSourceType::from_code("BOSHQA"), None);
    }
}
