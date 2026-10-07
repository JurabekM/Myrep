use money::MoneyError;
use storage::StorageError;

#[derive(Debug, thiserror::Error)]
pub enum ServiceError {
    #[error("baza xatosi")]
    Storage(#[from] StorageError),
    #[error("hisob xatosi: {0}")]
    Money(#[from] MoneyError),
    #[error("noto'g'ri kiritish: {0}")]
    Invalid(&'static str),
    #[error("topilmadi")]
    NotFound,
    #[error("boshlang'ich balans allaqachon kiritilgan")]
    OpeningBalanceExists,
    #[error("Kelajagimda mablag' yetarli emas")]
    InsufficientFunds,
    #[error("PIN noto'g'ri")]
    WrongPin,
    #[error("juda ko'p urinish: {retry_after_secs} soniyadan keyin")]
    PinLocked { retry_after_secs: u64 },
    #[error("a'zo uchun PIN o'rnatilmagan")]
    NoPin,
    #[error("pauza tugamagan: {remaining_secs} soniya qoldi")]
    Cooling { remaining_secs: i64 },
}

impl From<domain::GuardError> for ServiceError {
    fn from(e: domain::GuardError) -> Self {
        match e {
            domain::GuardError::NoWeights => Self::Invalid("savat og'irliklari yig'indisi 0"),
            domain::GuardError::InvalidPrice => Self::Invalid("narx noto'g'ri"),
            domain::GuardError::InvalidAmount => Self::Invalid("summa noto'g'ri"),
            domain::GuardError::Money(m) => Self::Money(m),
        }
    }
}
