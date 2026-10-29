//! Vault ma'lumot tiplari va konfiguratsiya.

use mpay_common::config::LukPolicy;
use mpay_common::ports::{IdvAssessment, SecurityLevel, TokenState};
use mpay_common::{CardExpiry, DeviceId, Pan, TokenId};
use mpay_crypto::SecretKey16;
use serde::{Deserialize, Serialize};

/// Vault sozlamalari.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct VaultConfig {
    /// DPAN BIN (`990050`–`990099` oralig'ida).
    pub token_bin: String,
    /// Token amal qilish muddati (oy), karta muddatidan oshmaydi.
    pub token_validity_months: u32,
    /// Bitta qurilmadagi o'chirilmagan tokenlar chegarasi.
    pub max_tokens_per_device: u32,
    /// Bitta karta tokenlashtirilishi mumkin bo'lgan qurilmalar soni (2-faza P2.7, ADR-0022);
    /// 0 — cheklanmagan. `TODO(spec):` bank mahsulot siyosati.
    pub max_devices_per_card: u32,
    pub luk: LukPolicy,
    /// OTP challenge umri (sekund).
    pub otp_ttl_secs: i64,
    /// OTP urinishlari chegarasi.
    pub otp_max_attempts: i64,
    /// Token muddati tugashiga shuncha kun qolganda (yoki o'tgach) uzaytirish mumkin (ADR-0022).
    pub token_renew_before_days: u32,
}

impl Default for VaultConfig {
    fn default() -> Self {
        Self {
            token_bin: "990077".into(),
            token_validity_months: 36,
            max_tokens_per_device: 10,
            max_devices_per_card: 3,
            luk: LukPolicy::default(),
            otp_ttl_secs: 300,
            otp_max_attempts: 3,
            token_renew_before_days: 30,
        }
    }
}

/// Provisioning so'rovi (PQ Link ichida keladi).
#[derive(Debug, Clone)]
pub struct ProvisionRequest {
    pub fpan: Pan,
    pub expiry: CardExpiry,
    /// Tekshirilgan yaxlitlik belgilari (P2.6, ADR-0021) — Shield'ga uzatiladi.
    pub integrity: Option<mpay_common::ports::IntegritySignals>,
}

/// PQ Link sessiyasi tasdiqlagan qurilma.
#[derive(Debug, Clone, Copy)]
pub struct DeviceContext {
    pub device_id: DeviceId,
    pub security_level: SecurityLevel,
}

/// Qurilmaga beriladigan LUK. Serializatsiya qilinmaydi — server uni faqat PQ Link muhrlangan
/// javobi uchun `mpay_common::api::LukDto` ga aylantiradi.
#[derive(Clone)]
pub struct LukGrant {
    pub seq: u32,
    pub key: SecretKey16,
    pub issued_at: i64,
    pub expires_at: i64,
    pub max_uses: u32,
}

impl std::fmt::Debug for LukGrant {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "LukGrant(seq={}, <maxfiy>)", self.seq)
    }
}

/// Qurilmaga beriladigan token profili (serializatsiya qilinmaydi, `LukGrant` ga qarang).
#[derive(Clone)]
pub struct TokenProfile {
    pub token_id: TokenId,
    pub dpan: Pan,
    pub dpan_expiry: String,
    pub psn: u8,
    pub aid: String,
    pub scheme: String,
    pub luks: Vec<LukGrant>,
    /// Shu lahzadan uzaytirish mumkin; `None` — karta muddati tugaydi (uzaytirib bo'lmaydi).
    pub renew_after: Option<i64>,
}

impl std::fmt::Debug for TokenProfile {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TokenProfile")
            .field("token_id", &self.token_id)
            .field("dpan", &self.dpan)
            .field("luks", &self.luks.len())
            .finish()
    }
}

/// Provisioning natijasi.
#[derive(Debug, Clone)]
pub enum ProvisionOutcome {
    Active {
        profile: TokenProfile,
        idv: IdvAssessment,
    },
    PendingIdv {
        token_id: TokenId,
        challenge_id: String,
        otp_expires_at: i64,
        idv: IdvAssessment,
    },
    Declined {
        idv: IdvAssessment,
    },
}

/// Operator uchun token ko'rinishi (maskalangan).
#[derive(Debug, Clone, Serialize)]
pub struct TokenSummary {
    pub token_id: TokenId,
    pub state: TokenState,
    pub dpan_masked: String,
    pub fpan_masked: String,
    pub dpan_expiry: String,
    pub device_id: String,
    pub idv_decision: String,
    pub luks_active: i64,
    pub luks_issued: i64,
    pub last_atc: Option<i64>,
    pub created_at: i64,
    pub updated_at: i64,
    /// `SUSPENDED` bo'lsa kim to'xtatgan: `DEVICE` (foydalanuvchi) yoki `BANK`.
    pub suspended_by: Option<String>,
}
