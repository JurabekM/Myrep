use std::fmt;

/// Barqaror xato kodlari (UI `error.<CODE>` bilan tarjima qiladi).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum InterchangeError {
    /// Fayl `.baraka` emas (sehrli satr yo'q).
    NotBaraka,
    /// Format versiyasi qo'llab-quvvatlanmaydi.
    VersionUnsupported,
    /// Sarlavha yoki tarkib buzilgan.
    Corrupt,
    /// Parol noto'g'ri (yoki fayl o'zgartirilgan — AEAD ikkalasini ajratmaydi).
    BadPassword,
    /// Parol juda qisqa.
    WeakPassword,
    /// Sarlavhadagi KDF parametrlari ruxsat etilgan chegaradan tashqarida.
    KdfParams,
    Random,
    Crypto,
}

impl InterchangeError {
    pub const fn code(self) -> &'static str {
        match self {
            Self::NotBaraka => "INTERCHANGE_NOT_BARAKA",
            Self::VersionUnsupported => "INTERCHANGE_VERSION_UNSUPPORTED",
            Self::Corrupt => "INTERCHANGE_CORRUPT",
            Self::BadPassword => "INTERCHANGE_BAD_PASSWORD",
            Self::WeakPassword => "INTERCHANGE_WEAK_PASSWORD",
            Self::KdfParams => "INTERCHANGE_KDF_PARAMS",
            Self::Random => "RANDOM_UNAVAILABLE",
            Self::Crypto => "CRYPTO_FAILURE",
        }
    }
}

impl fmt::Display for InterchangeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for InterchangeError {}
