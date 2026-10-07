#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum SecurityError {
    #[error("PIN aniq 6 ta raqamdan iborat bo'lishi kerak")]
    InvalidPin,
    #[error("seyf allaqachon sozlangan")]
    AlreadyInitialized,
    #[error("seyf hali sozlanmagan")]
    NotInitialized,
    #[error("PIN noto'g'ri")]
    WrongPin,
    #[error("juda ko'p urinish: {retry_after_secs} soniyadan keyin urinib ko'ring")]
    Locked { retry_after_secs: u64 },
    #[error("OS keyring'da qurilma siri topilmadi")]
    KeyringMissing,
    #[error("keyring xatosi: {0}")]
    Keyring(String),
    #[error("fayl xatosi: {0}")]
    Io(String),
    #[error("seyf fayli buzilgan: {0}")]
    Corrupt(String),
    #[error("kriptografiya xatosi")]
    Crypto,
}
