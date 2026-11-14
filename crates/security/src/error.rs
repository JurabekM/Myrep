use thiserror::Error;

/// Xavfsizlik qatlamining xatolari. Xabarlarda hech qachon kalit yoki PIN bo'lmaydi.
#[derive(Debug, Error)]
pub enum SecurityError {
    /// PIN aniq 6 ta raqamdan iborat emas.
    #[error("PIN aniq 6 ta raqamdan iborat bo'lishi kerak")]
    InvalidPin,
    /// PIN noto'g'ri.
    #[error("PIN noto'g'ri")]
    WrongPin,
    /// Juda ko'p noto'g'ri urinish: kutish davom etmoqda.
    #[error("juda ko'p noto'g'ri urinish: {retry_after_secs} soniyadan keyin urinib ko'ring")]
    LockedOut {
        /// Qolgan kutish vaqti (soniyalarda).
        retry_after_secs: u64,
    },
    /// Kalit OS keyring'ida topilmadi.
    #[error("kalit OS keyring'ida topilmadi")]
    KeyUnavailable,
    /// Keyring'dagi kalit bu bazaga mos kelmaydi.
    #[error("keyring'dagi kalit bu bazaga mos emas")]
    KeyringMismatch,
    /// Kalit fayli buzilgan yoki noto'g'ri formatda.
    #[error("kalit fayli buzilgan yoki noto'g'ri formatda")]
    CorruptKeyFile,
    /// Kalit fayli yo'q: avval sozlash kerak.
    #[error("kalit fayli topilmadi: avval PIN o'rnatilishi kerak")]
    NotSetUp,
    /// Kalit allaqachon sozlangan.
    #[error("kalit allaqachon sozlangan")]
    AlreadySetUp,
    /// OS keyring xatosi.
    #[error("OS keyring xatosi: {0}")]
    Keyring(String),
    /// Tasodifiy sonlar manbai ishlamadi.
    #[error("tasodifiy sonlar manbai ishlamadi: {0}")]
    Rng(String),
    /// Kalitni hosil qilish (Argon2id) xatosi.
    #[error("kalitni hosil qilish xatosi")]
    Kdf,
    /// Shifrlash yoki ochish xatosi.
    #[error("shifrlash xatosi")]
    Crypto,
    /// Almashish fayli paroli noto'g'ri.
    #[error("parol noto'g'ri")]
    WrongPassword,
    /// Almashish fayli buzilgan yoki `.baraka` emas.
    #[error("almashish fayli buzilgan yoki noto'g'ri formatda")]
    CorruptContainer,
    /// Parol juda qisqa (kamida 8 belgi).
    #[error("parol kamida 8 belgi bo'lishi kerak")]
    WeakPassword,
    /// Kalit faylini o'qish yoki yozish xatosi.
    #[error("kalit faylini o'qish/yozish xatosi: {0}")]
    Io(#[from] std::io::Error),
}
