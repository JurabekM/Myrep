//! Verifikatsiya xato kodlari (spec §8).

use std::fmt;

/// Spec §8 dagi xato kodlari. Satr ko'rinishi spec bilan aynan bir xil.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ErrorCode {
    Parse,
    NonCanonical,
    Version,
    Field,
    Log,
    Seq,
    Hash,
    Prev,
    CkptFormat,
    CkptSig,
    CkptSize,
    CkptRoot,
}

impl ErrorCode {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Parse => "E_PARSE",
            Self::NonCanonical => "E_NONCANONICAL",
            Self::Version => "E_VERSION",
            Self::Field => "E_FIELD",
            Self::Log => "E_LOG",
            Self::Seq => "E_SEQ",
            Self::Hash => "E_HASH",
            Self::Prev => "E_PREV",
            Self::CkptFormat => "E_CKPT_FORMAT",
            Self::CkptSig => "E_CKPT_SIG",
            Self::CkptSize => "E_CKPT_SIZE",
            Self::CkptRoot => "E_CKPT_ROOT",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        ALL.iter().copied().find(|c| c.as_str() == s)
    }
}

const ALL: [ErrorCode; 12] = [
    ErrorCode::Parse,
    ErrorCode::NonCanonical,
    ErrorCode::Version,
    ErrorCode::Field,
    ErrorCode::Log,
    ErrorCode::Seq,
    ErrorCode::Hash,
    ErrorCode::Prev,
    ErrorCode::CkptFormat,
    ErrorCode::CkptSig,
    ErrorCode::CkptSize,
    ErrorCode::CkptRoot,
];

impl fmt::Display for ErrorCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Birinchi topilgan xato: kod, qator indeksi (jurnal yoki checkpoint fayli ichida) va izoh.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{code} at index {index}: {detail}")]
pub struct VerifyError {
    pub code: ErrorCode,
    pub index: u64,
    pub detail: String,
}

impl VerifyError {
    pub fn new(code: ErrorCode, index: u64, detail: impl Into<String>) -> Self {
        Self {
            code,
            index,
            detail: detail.into(),
        }
    }
}
