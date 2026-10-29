//! Ilova va qurilma yaxlitligi (2-faza P2.6, ADR-0021).
//!
//! Hamyon provisioning so'rovida yaxlitlik tokenini yuboradi. Server:
//! 1. tokenni **dekodlaydi va haqiqiyligini** tekshiradi ([`IntegrityVerifier`] — almashtiriladigan:
//!    [`mock::MockVerifier`] sandbox uchun, [`google::GoogleDecoder`] Google Play Integrity uchun);
//! 2. **bog'lanishni** tekshiradi ([`check`]): paket nomi, ilova imzo sertifikati, `requestHash` (PQ
//!    Link sessiyasiga bog'langan, [`request_hash`]) va yangilik — buzilsa so'rov rad etiladi;
//! 3. verdict sifatini [`IntegritySignals`] ga soddalashtiradi — qaror Shield qoidalarida.
//!
//! Verdict tuzilmasi Google Play Integrity API'ning ochiq hujjatidagi `tokenPayloadExternal`
//! maydonlariga mos (`requestDetails`, `appIntegrity`, `deviceIntegrity`, `accountDetails`,
//! `environmentDetails`). `TODO(spec):` integratsiya paytida Google'ning joriy hujjati bilan qayta
//! solishtirish (yangi maydonlar e'tiborsiz qoldiriladi, majburiylari yo'q bo'lsa — rad).
//!
//! `requestHash` ga PAN **kirmaydi**: u Google serverlariga yuboriladi, PAN esa xeshdan ham
//! tiklanadi (BIN ichida ~10⁹ variant).
#![forbid(unsafe_code)]

pub mod google;
pub mod mock;
pub mod service_account;

use std::sync::Arc;

use async_trait::async_trait;
use base64::Engine as _;
pub use mpay_common::ports::IntegritySignals;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

/// Token hajmi chegarasi (tahlildan oldin).
pub const MAX_TOKEN_LEN: usize = 16 * 1024;

/// `requestHash` domen ajratgichi.
const HASH_DOMAIN: &[u8] = b"MPAY-PI-V1";

/// Yaxlitlik tokeni qaysi amal uchun so'ralgan.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Purpose {
    Provision,
}

impl Purpose {
    fn as_bytes(self) -> &'static [u8] {
        match self {
            Self::Provision => b"provision",
        }
    }
}

/// `requestHash = base64url(SHA-256("MPAY-PI-V1" ‖ 0x00 ‖ amal ‖ 0x00 ‖ sessiya ID))`, paddingsiz.
/// Hamyon (Rust/Kotlin) va server bir xil hisoblaydi; token boshqa sessiyada qayta ishlatilmaydi.
pub fn request_hash(purpose: Purpose, session_id: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(HASH_DOMAIN);
    h.update([0]);
    h.update(purpose.as_bytes());
    h.update([0]);
    h.update(session_id);
    base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(h.finalize())
}

// ---------------------------------------------------------------- verdict (Play Integrity tuzilmasi)

/// Dekodlangan token mazmuni (`tokenPayloadExternal`).
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TokenPayload {
    #[serde(default)]
    pub request_details: RequestDetails,
    #[serde(default)]
    pub app_integrity: AppIntegrity,
    #[serde(default)]
    pub device_integrity: DeviceIntegrity,
    #[serde(default)]
    pub account_details: AccountDetails,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub environment_details: Option<EnvironmentDetails>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RequestDetails {
    #[serde(default)]
    pub request_package_name: String,
    /// Standart so'rov: ilova bergan `requestHash`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub request_hash: Option<String>,
    /// Klassik so'rov `nonce`'i — biz ishlatmaymiz (bo'lsa ham `requestHash` talab qilinadi).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub nonce: Option<String>,
    /// Millisekund (Google JSON'ida satr).
    #[serde(default)]
    pub timestamp_millis: String,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppIntegrity {
    /// `PLAY_RECOGNIZED`, `UNRECOGNIZED_VERSION`, `UNEVALUATED`.
    #[serde(default)]
    pub app_recognition_verdict: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub package_name: Option<String>,
    /// Ilova imzo sertifikatlari SHA-256, base64url.
    #[serde(default)]
    pub certificate_sha256_digest: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub version_code: Option<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DeviceIntegrity {
    /// `MEETS_BASIC_INTEGRITY`, `MEETS_DEVICE_INTEGRITY`, `MEETS_STRONG_INTEGRITY`,
    /// `MEETS_VIRTUAL_INTEGRITY`; bo'sh — hech biri.
    #[serde(default)]
    pub device_recognition_verdict: Vec<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AccountDetails {
    /// `LICENSED`, `UNLICENSED`, `UNEVALUATED`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub app_licensing_verdict: Option<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EnvironmentDetails {
    /// `NO_ISSUES`, `NO_DATA`, `POSSIBLE_RISK`, `MEDIUM_RISK`, `HIGH_RISK`, `UNEVALUATED`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub play_protect_verdict: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub app_access_risk_verdict: Option<AppAccessRisk>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppAccessRisk {
    /// Masalan `KNOWN_INSTALLED`, `UNKNOWN_CAPTURING`, `UNKNOWN_CONTROLLING`.
    #[serde(default)]
    pub apps_detected: Vec<String>,
}

// ---------------------------------------------------------------- tekshiruv

/// Tekshiruv xatolari. `Unavailable` dan boshqalari — token yaroqsiz (so'rov rad etiladi).
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum IntegrityError {
    #[error("yaxlitlik tokeni kerak")]
    Missing,
    #[error("token formati yaroqsiz: {0}")]
    Malformed(&'static str),
    #[error("token imzosi yaroqsiz")]
    BadSignature,
    #[error("paket nomi mos emas")]
    PackageMismatch,
    #[error("ilova imzo sertifikati ruxsat etilmagan")]
    CertificateMismatch,
    #[error("requestHash mos emas (boshqa sessiya yoki amal)")]
    RequestHashMismatch,
    #[error("token eskirgan")]
    Stale,
    #[error("token vaqti kelajakda")]
    FutureTimestamp,
    #[error("dekodlash xizmati javob bermadi: {0}")]
    Unavailable(String),
}

/// Bog'lanish siyosati.
#[derive(Debug, Clone)]
pub struct Policy {
    /// Hamyon ilovasi paketi.
    pub package_name: String,
    /// Ruxsat etilgan imzo sertifikatlari (SHA-256, base64url). Bo'sh — tekshirilmaydi (faqat sandbox).
    pub certificate_sha256: Vec<String>,
    /// Token yoshi chegarasi, millisekund.
    pub max_age_ms: i64,
    /// Soat farqi uchun ruxsat (token vaqti kelajakda), millisekund.
    pub max_skew_ms: i64,
}

/// Token bog'lanishini tekshiradi va verdict'ni belgilarga aylantiradi.
pub fn check(
    p: &TokenPayload,
    policy: &Policy,
    expected_hash: &str,
    now_ms: i64,
) -> Result<IntegritySignals, IntegrityError> {
    let rd = &p.request_details;
    if rd.request_package_name != policy.package_name
        || p.app_integrity
            .package_name
            .as_deref()
            .is_some_and(|n| n != policy.package_name)
    {
        return Err(IntegrityError::PackageMismatch);
    }
    // Doimiy vaqtli taqqoslash shart emas: xesh sir emas (mijoz o'zi hisoblaydi).
    if rd.request_hash.as_deref() != Some(expected_hash) {
        return Err(IntegrityError::RequestHashMismatch);
    }
    let ts: i64 = rd
        .timestamp_millis
        .parse()
        .map_err(|_| IntegrityError::Malformed("timestampMillis"))?;
    if ts > now_ms + policy.max_skew_ms {
        return Err(IntegrityError::FutureTimestamp);
    }
    if now_ms - ts > policy.max_age_ms {
        return Err(IntegrityError::Stale);
    }
    let app = match p.app_integrity.app_recognition_verdict.as_str() {
        "PLAY_RECOGNIZED" => 2,
        "UNRECOGNIZED_VERSION" => 1,
        _ => 0,
    };
    // Sertifikat faqat ilova baholangan bo'lsa keladi; berilgan bo'lsa — ruxsat ro'yxatida bo'lishi shart.
    if !policy.certificate_sha256.is_empty() && app > 0 {
        let ok = p
            .app_integrity
            .certificate_sha256_digest
            .iter()
            .any(|c| policy.certificate_sha256.contains(c));
        if !ok {
            return Err(IntegrityError::CertificateMismatch);
        }
    }
    let dv = &p.device_integrity.device_recognition_verdict;
    let has = |v: &str| dv.iter().any(|x| x == v);
    let device = if has("MEETS_STRONG_INTEGRITY") {
        3
    } else if has("MEETS_DEVICE_INTEGRITY") {
        2
    } else if has("MEETS_BASIC_INTEGRITY") || has("MEETS_VIRTUAL_INTEGRITY") {
        1
    } else {
        0
    };
    let licensed = match p.account_details.app_licensing_verdict.as_deref() {
        Some("LICENSED") => 2,
        Some("UNLICENSED") => 1,
        _ => 0,
    };
    let env = p.environment_details.as_ref();
    let protect = match env.and_then(|e| e.play_protect_verdict.as_deref()) {
        Some("HIGH_RISK") => 3,
        Some("MEDIUM_RISK") => 2,
        Some("POSSIBLE_RISK") => 1,
        _ => 0,
    };
    // Noma'lum ilova ekranni boshqaradi/yozadi — masofaviy kirish firibgarligining asosiy belgisi.
    let access = env
        .and_then(|e| e.app_access_risk_verdict.as_ref())
        .map_or(0, |a| {
            if a.apps_detected.iter().any(|x| x == "UNKNOWN_CONTROLLING") {
                3
            } else if a.apps_detected.iter().any(|x| x == "UNKNOWN_CAPTURING") {
                2
            } else {
                0
            }
        });
    Ok(IntegritySignals {
        app,
        device,
        licensed,
        env_risk: protect.max(access),
    })
}

/// Tokenni dekodlovchi va haqiqiyligini tekshiruvchi (almashtiriladigan).
#[async_trait]
pub trait IntegrityVerifier: Send + Sync {
    /// Nomi (log va `healthz` uchun): `mock`, `google`.
    fn name(&self) -> &'static str;
    /// Token → mazmun. Imzo/shifr (yoki Google dekodlashi) shu yerda tekshiriladi.
    async fn decode(&self, token: &str) -> Result<TokenPayload, IntegrityError>;
}

/// Server tomonidagi yaxlitlik tekshiruvi: verifier + siyosat.
#[derive(Clone)]
pub struct Integrity {
    verifier: Arc<dyn IntegrityVerifier>,
    policy: Policy,
    required: bool,
}

impl std::fmt::Debug for Integrity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Integrity")
            .field("verifier", &self.verifier.name())
            .field("package", &self.policy.package_name)
            .field("required", &self.required)
            .finish()
    }
}

impl Integrity {
    pub fn new(verifier: Arc<dyn IntegrityVerifier>, policy: Policy, required: bool) -> Self {
        Self {
            verifier,
            policy,
            required,
        }
    }

    pub fn verifier_name(&self) -> &'static str {
        self.verifier.name()
    }

    /// `None` token: `required` bo'lsa xato, aks holda belgisiz (`Ok(None)`).
    pub async fn verify(
        &self,
        token: Option<&str>,
        purpose: Purpose,
        session_id: &[u8],
        now_ms: i64,
    ) -> Result<Option<IntegritySignals>, IntegrityError> {
        let Some(token) = token.filter(|t| !t.is_empty()) else {
            return if self.required {
                Err(IntegrityError::Missing)
            } else {
                Ok(None)
            };
        };
        if token.len() > MAX_TOKEN_LEN {
            return Err(IntegrityError::Malformed("juda uzun"));
        }
        let payload = self.verifier.decode(token).await?;
        check(
            &payload,
            &self.policy,
            &request_hash(purpose, session_id),
            now_ms,
        )
        .map(Some)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn policy() -> Policy {
        Policy {
            package_name: "uz.mpay.walletdemo".into(),
            certificate_sha256: vec!["CERT".into()],
            max_age_ms: 120_000,
            max_skew_ms: 30_000,
        }
    }

    fn payload(hash: &str, ts: i64) -> TokenPayload {
        mock::Preset::Strong.payload("uz.mpay.walletdemo", "CERT", hash, ts)
    }

    #[test]
    fn request_hash_is_stable_and_bound() {
        let a = request_hash(Purpose::Provision, &[1; 16]);
        assert_eq!(a, request_hash(Purpose::Provision, &[1; 16]));
        assert_ne!(a, request_hash(Purpose::Provision, &[2; 16]));
        assert_eq!(a.len(), 43, "SHA-256 base64url paddingsiz");
        // Mustaqil hisob (Python hashlib) — Kotlin InteropTest ham shu vektorni tekshiradi.
        assert_eq!(
            request_hash(Purpose::Provision, &[0x11; 16]),
            "ibPmhjjxqmxmm7yGEh3rp1XGVsQiEPYcFNkCMz56DDw"
        );
    }

    #[test]
    fn binding_checks() {
        let h = request_hash(Purpose::Provision, &[7; 16]);
        let now = 1_800_000_000_000;
        let ok = check(&payload(&h, now - 1000), &policy(), &h, now).unwrap();
        assert_eq!(
            ok,
            IntegritySignals {
                app: 2,
                device: 3,
                licensed: 2,
                env_risk: 0
            }
        );
        let mut p = payload(&h, now);
        p.request_details.request_package_name = "evil.app".into();
        assert_eq!(
            check(&p, &policy(), &h, now),
            Err(IntegrityError::PackageMismatch)
        );
        let other = request_hash(Purpose::Provision, &[8; 16]);
        assert_eq!(
            check(&payload(&other, now), &policy(), &h, now),
            Err(IntegrityError::RequestHashMismatch)
        );
        assert_eq!(
            check(&payload(&h, now - 121_000), &policy(), &h, now),
            Err(IntegrityError::Stale)
        );
        assert_eq!(
            check(&payload(&h, now + 31_000), &policy(), &h, now),
            Err(IntegrityError::FutureTimestamp)
        );
        let mut p = payload(&h, now);
        p.app_integrity.certificate_sha256_digest = vec!["RESIGNED".into()];
        assert_eq!(
            check(&p, &policy(), &h, now),
            Err(IntegrityError::CertificateMismatch)
        );
    }

    #[test]
    fn verdict_mapping() {
        let h = request_hash(Purpose::Provision, &[7; 16]);
        let now = 1_800_000_000_000;
        let sig = |pr: mock::Preset| {
            check(
                &pr.payload("uz.mpay.walletdemo", "CERT", &h, now),
                &policy(),
                &h,
                now,
            )
            .unwrap()
        };
        assert_eq!(sig(mock::Preset::Device).device, 2);
        assert_eq!(sig(mock::Preset::Basic).device, 1);
        assert_eq!(sig(mock::Preset::NoIntegrity).device, 0);
        assert_eq!(sig(mock::Preset::Unrecognized).app, 1);
        assert_eq!(sig(mock::Preset::RemoteControl).env_risk, 3);
        assert_eq!(sig(mock::Preset::PlayProtectRisk).env_risk, 2);
    }
}
