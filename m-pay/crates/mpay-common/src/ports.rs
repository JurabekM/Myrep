//! Modullararo port trait'lari (ADR-0002).
//!
//! Modul crate'lari bir-biriga emas, shu trait'larga bog'liq. `mpay-server` ularni
//! haqiqiy implementatsiyalarga (`Arc<dyn ...>`) ulaydi.

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use time::OffsetDateTime;

use crate::ids::{DeviceId, PanFingerprint, TokenId};
use crate::pan::{CardExpiry, Pan};

/// Port xatolari (tashqi modul ishlamayapti yoki ichki xato).
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum PortError {
    #[error("xizmat mavjud emas: {0}")]
    Unavailable(String),
    #[error("ichki xato: {0}")]
    Internal(String),
}

// ---------------------------------------------------------------- ID&V (provisioning)

/// ID&V qarori.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum IdvDecision {
    /// Token darhol yaratiladi.
    Green,
    /// Qo'shimcha tasdiq (OTP) kerak.
    Yellow,
    /// Rad.
    Red,
}

/// Qurilma attestatsiya xavfsizlik darajasi (Android KeyMint `SecurityLevel`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SecurityLevel {
    Software = 0,
    TrustedEnvironment = 1,
    StrongBox = 2,
}

impl SecurityLevel {
    /// ASN.1 ENUMERATED qiymatidan.
    pub fn from_raw(v: u8) -> Option<Self> {
        match v {
            0 => Some(Self::Software),
            1 => Some(Self::TrustedEnvironment),
            2 => Some(Self::StrongBox),
            _ => None,
        }
    }
}

/// Ilova/qurilma yaxlitligi belgilari (2-faza P2.6, ADR-0021) — Play Integrity verdict'idan
/// (yoki sandbox mock'idan) olingan, tekshirilgan va soddalashtirilgan. Shield qoidalari shularga
/// qaraydi; ochiq token va verdict JSON'i saqlanmaydi.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct IntegritySignals {
    /// Ilova: 0 — baholanmagan, 1 — tanilmagan (o'zgartirilgan / Play'dan emas), 2 — tanilgan.
    pub app: u8,
    /// Qurilma: 0 — hech biri, 1 — basic (yoki virtual), 2 — device, 3 — strong.
    pub device: u8,
    /// Litsenziya: 0 — baholanmagan, 1 — litsenziyasiz, 2 — litsenziyali.
    pub licensed: u8,
    /// Muhit xavfi: 0 — yo'q / ma'lumot yo'q, 1 — mumkin, 2 — o'rta, 3 — yuqori
    /// (Play Protect xavfi yoki ekranni noma'lum ilova boshqaradi/yozadi).
    pub env_risk: u8,
}

/// Provisioning paytidagi ID&V so'rovi.
#[derive(Debug, Clone)]
pub struct IdvRequest {
    pub fpan: Pan,
    pub pan_fingerprint: PanFingerprint,
    pub device_id: DeviceId,
    pub attestation_level: SecurityLevel,
    /// Shu karta uchun allaqachon mavjud (o'chirilmagan) tokenlar soni.
    pub existing_tokens_for_pan: u32,
    /// Shu qurilmadagi (o'chirilmagan) tokenlar soni.
    pub existing_tokens_for_device: u32,
    /// Yaxlitlik belgilari (`[integrity] mode = "off"` bo'lsa yoki token berilmasa — `None`).
    pub integrity: Option<IntegritySignals>,
    pub at: OffsetDateTime,
}

/// ID&V natijasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IdvAssessment {
    pub decision: IdvDecision,
    /// 0–1000, katta = xavfliroq.
    pub score: u16,
    pub reasons: Vec<String>,
}

/// ID&V qaror qabul qiluvchi (Shield).
#[async_trait]
pub trait IdvDecider: Send + Sync {
    async fn decide(&self, req: &IdvRequest) -> Result<IdvAssessment, PortError>;

    /// Qurilma kaliti almashtirildi (ADR-0015): `new` — `old` ning davomi (o'sha hamyon, attestatsiya
    /// va eski kalit imzosi bilan tasdiqlangan). Shield yangi ID'ni eski qurilma tuguniga bog'laydi —
    /// kartalar, qurilma yoshi va tarixi (yomoni ham) saqlanadi. Standart — hech narsa qilmaydi.
    async fn device_rekeyed(
        &self,
        _old: &DeviceId,
        _new: &DeviceId,
        _at: OffsetDateTime,
    ) -> Result<(), PortError> {
        Ok(())
    }
}

// ---------------------------------------------------------------- risk (avtorizatsiya)

/// Tranzaksiya risk qarori.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum RiskDecision {
    Approve,
    Review,
    Decline,
}

/// Avtorizatsiya paytidagi risk so'rovi.
#[derive(Debug, Clone)]
pub struct RiskRequest {
    pub token_id: TokenId,
    pub device_id: DeviceId,
    pub pan_fingerprint: PanFingerprint,
    pub amount_minor: u64,
    pub currency: u16,
    pub merchant_id: String,
    pub terminal_id: String,
    pub country: u16,
    pub atc: u16,
    pub cdcvm_performed: bool,
    pub at: OffsetDateTime,
}

/// Risk natijasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RiskAssessment {
    /// 0–1000, katta = xavfliroq.
    pub score: u16,
    pub decision: RiskDecision,
    pub reasons: Vec<String>,
}

/// Real-time risk skorlovchi (Shield).
#[async_trait]
pub trait RiskScorer: Send + Sync {
    async fn score(&self, req: &RiskRequest) -> Result<RiskAssessment, PortError>;
}

// ---------------------------------------------------------------- detokenizatsiya

/// Token hayot sikli holati.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum TokenState {
    /// ID&V (OTP) kutilmoqda.
    PendingIdv,
    Active,
    Suspended,
    Deleted,
}

impl TokenState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::PendingIdv => "PENDING_IDV",
            Self::Active => "ACTIVE",
            Self::Suspended => "SUSPENDED",
            Self::Deleted => "DELETED",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        Some(match s {
            "PENDING_IDV" => Self::PendingIdv,
            "ACTIVE" => Self::Active,
            "SUSPENDED" => Self::Suspended,
            "DELETED" => Self::Deleted,
            _ => return None,
        })
    }
}

/// So'ralgan LUK holati.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LukStatus {
    Valid { remaining_uses: u32 },
    Expired,
    Exhausted,
    Unknown,
}

/// Issuer uchun token ko'rinishi (FPAN ochiq — faqat xotirada).
#[derive(Debug, Clone)]
pub struct TokenView {
    pub token_id: TokenId,
    pub state: TokenState,
    pub fpan: Pan,
    pub fpan_expiry: CardExpiry,
    pub dpan_expiry: CardExpiry,
    pub psn: u8,
    pub device_id: DeviceId,
    pub pan_fingerprint: PanFingerprint,
    pub last_atc: Option<u16>,
    pub luk: LukStatus,
}

/// LUK foydalanishini qayd etish natijasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConsumeOutcome {
    Consumed,
    TokenNotActive,
    LukUnknown,
    LukExpired,
    LukExhausted,
    AtcReplay,
}

/// Detokenizatsiya porti. Faqat `mpay-issuer` ga beriladi; HTTP orqali ochilmaydi.
#[async_trait]
pub trait Detokenizer: Send + Sync {
    /// DPAN bo'yicha token va LUK holatini qaytaradi (hech narsani o'zgartirmaydi).
    async fn lookup(&self, dpan: &Pan, luk_seq: u32) -> Result<Option<TokenView>, PortError>;

    /// ARQC muvaffaqiyatli tekshirilgandan keyin: LUK foydalanishini va ATC'ni atomar qayd etadi.
    async fn consume(
        &self,
        token_id: &TokenId,
        luk_seq: u32,
        atc: u16,
    ) -> Result<ConsumeOutcome, PortError>;
}
