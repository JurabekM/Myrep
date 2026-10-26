//! Javob kodlari (ISO 8583 maydon 39) va ichki sabab kodlari (ADR-0007).

use serde::{Deserialize, Serialize};

/// Maydon 39 javob kodi.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ResponseCode {
    /// `00` — tasdiqlandi.
    Approved,
    /// `05` — rad (token holati, noma'lum token/hisob, REVIEW siyosati).
    DoNotHonor,
    /// `51` — mablag' yetarli emas.
    InsufficientFunds,
    /// `59` — fraud gumoni (Shield DECLINE).
    SuspectedFraud,
    /// `91` — emitent mavjud emas / ishlamayapti.
    IssuerUnavailable,
    /// `Q1` — kriptogramma/LUK/ATC tekshiruvi o'tmadi.
    CardAuthFailed,
    /// `54` — token muddati o'tgan (2-faza P2.7, ADR-0022).
    ExpiredCard,
    /// `Q2` — karta egasini qurilmada tasdiqlash (CDCVM) talab qilinadi: telefonda tasdiqlab qayta
    /// tap qilish kerak (M-Pay profili kodi, ADR-0022).
    CvmRequired,
}

impl ResponseCode {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Approved => "00",
            Self::DoNotHonor => "05",
            Self::InsufficientFunds => "51",
            Self::SuspectedFraud => "59",
            Self::IssuerUnavailable => "91",
            Self::CardAuthFailed => "Q1",
            Self::ExpiredCard => "54",
            Self::CvmRequired => "Q2",
        }
    }

    /// ARC baytlari (ARPC kirishi).
    pub fn arc(self) -> [u8; 2] {
        let b = self.as_str().as_bytes();
        [b[0], b[1]]
    }

    pub fn parse(s: &str) -> Option<Self> {
        Some(match s {
            "00" => Self::Approved,
            "05" => Self::DoNotHonor,
            "51" => Self::InsufficientFunds,
            "59" => Self::SuspectedFraud,
            "91" => Self::IssuerUnavailable,
            "Q1" => Self::CardAuthFailed,
            "54" => Self::ExpiredCard,
            "Q2" => Self::CvmRequired,
            _ => return None,
        })
    }
}

/// Ichki sabab (audit, log, terminal javobi). Maxfiy ma'lumotsiz.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Reason {
    Approved,
    ApprovedAfterReview,
    IccDataMissing,
    FieldMismatch,
    UnsupportedScheme,
    UnknownToken,
    LukUnknown,
    LukExpired,
    LukExhausted,
    ArqcMismatch,
    AtcReplay,
    TokenNotActive,
    IssuerOffline,
    RiskDecline,
    RiskReview,
    AccountNotFound,
    CurrencyMismatch,
    InsufficientFunds,
    /// Token (DPAN) muddati o'tgan.
    TokenExpired,
    /// Summa CVM chegarasidan yuqori va CDCVM bajarilmagan.
    CvmRequired,
    /// Shield REVIEW, siyosat `step_up`: CDCVM bajarilmagan.
    ReviewStepUp,
}

impl Reason {
    /// Sababga mos javob kodi.
    pub fn code(self) -> ResponseCode {
        use Reason::*;
        match self {
            Approved | ApprovedAfterReview => ResponseCode::Approved,
            IccDataMissing | FieldMismatch | UnsupportedScheme | LukUnknown | LukExpired
            | LukExhausted | ArqcMismatch | AtcReplay => ResponseCode::CardAuthFailed,
            UnknownToken | TokenNotActive | RiskReview | AccountNotFound | CurrencyMismatch => {
                ResponseCode::DoNotHonor
            }
            IssuerOffline => ResponseCode::IssuerUnavailable,
            RiskDecline => ResponseCode::SuspectedFraud,
            InsufficientFunds => ResponseCode::InsufficientFunds,
            TokenExpired => ResponseCode::ExpiredCard,
            CvmRequired | ReviewStepUp => ResponseCode::CvmRequired,
        }
    }

    pub fn as_str(self) -> &'static str {
        use Reason::*;
        match self {
            Approved => "APPROVED",
            ApprovedAfterReview => "APPROVED_AFTER_REVIEW",
            IccDataMissing => "ICC_DATA_MISSING",
            FieldMismatch => "FIELD_MISMATCH",
            UnsupportedScheme => "UNSUPPORTED_SCHEME",
            UnknownToken => "UNKNOWN_TOKEN",
            LukUnknown => "LUK_UNKNOWN",
            LukExpired => "LUK_EXPIRED",
            LukExhausted => "LUK_EXHAUSTED",
            ArqcMismatch => "ARQC_MISMATCH",
            AtcReplay => "ATC_REPLAY",
            TokenNotActive => "TOKEN_NOT_ACTIVE",
            IssuerOffline => "ISSUER_OFFLINE",
            RiskDecline => "RISK_DECLINE",
            RiskReview => "RISK_REVIEW",
            AccountNotFound => "ACCOUNT_NOT_FOUND",
            CurrencyMismatch => "CURRENCY_MISMATCH",
            InsufficientFunds => "INSUFFICIENT_FUNDS",
            TokenExpired => "TOKEN_EXPIRED",
            CvmRequired => "CVM_REQUIRED",
            ReviewStepUp => "REVIEW_STEP_UP",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn codes_match_adr_0007() {
        assert_eq!(Reason::ArqcMismatch.code().as_str(), "Q1");
        assert_eq!(Reason::LukExpired.code().as_str(), "Q1");
        assert_eq!(Reason::TokenNotActive.code().as_str(), "05");
        assert_eq!(Reason::RiskDecline.code().as_str(), "59");
        assert_eq!(Reason::IssuerOffline.code().as_str(), "91");
        assert_eq!(Reason::InsufficientFunds.code().as_str(), "51");
        assert_eq!(ResponseCode::Approved.arc(), *b"00");
        assert_eq!(Reason::TokenExpired.code().as_str(), "54");
        assert_eq!(Reason::CvmRequired.code().as_str(), "Q2");
        assert_eq!(Reason::ReviewStepUp.code().as_str(), "Q2");
        for c in ["00", "05", "51", "54", "59", "91", "Q1", "Q2"] {
            assert_eq!(ResponseCode::parse(c).unwrap().as_str(), c);
        }
        assert!(
            ResponseCode::parse("55").is_none(),
            "55 ishlatilmaydi (ADR-0007)"
        );
    }
}
