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
    #[error("pauza tugamagan: {remaining_secs} soniya qoldi")]
    Cooling { remaining_secs: i64 },
}
