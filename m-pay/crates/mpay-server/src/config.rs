//! `mpay-server` konfiguratsiyasi (TOML). Nisbiy yo'llar konfiguratsiya fayli joylashgan
//! papkaga nisbatan hal qilinadi. Sirlar faylda emas: dev-urug' alohida fayl/muhit
//! o'zgaruvchisida, API kalitlari faqat SHA-256 xesh ko'rinishida.

use std::net::SocketAddr;
use std::path::{Path, PathBuf};

use mpay_common::config::{load_toml, ConfigError};
use mpay_common::ports::SecurityLevel;
use mpay_shield::StubShieldConfig;
use mpay_vault::VaultConfig;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    /// Sandbox rejimi: `memory` KeyStore va sandbox endpointlariga ruxsat beradi.
    pub sandbox: bool,
    pub http: HttpConfig,
    pub database: DatabaseConfig,
    pub keystore: KeyStoreConfig,
    pub pqlink: PqLinkConfig,
    #[serde(default)]
    pub vault: VaultConfig,
    #[serde(default)]
    pub shield: ShieldConfig,
    #[serde(default)]
    pub shield_stub: StubShieldConfig,
    #[serde(default)]
    pub issuer: mpay_issuer::IssuerConfig,
    #[serde(default)]
    pub auth: AuthConfig,
    #[serde(default)]
    pub sandbox_api: SandboxApiConfig,
    #[serde(default)]
    pub rate_limit: crate::ratelimit::RateLimitConfig,
    /// OTP yetkazish kanali (2-faza P2.1).
    #[serde(default)]
    pub otp: crate::otp::OtpConfig,

    /// Konfiguratsiya fayli papkasi (yuklashda to'ldiriladi).
    #[serde(skip)]
    pub base_dir: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HttpConfig {
    pub listen: SocketAddr,
    /// TLS sertifikati (PEM). Berilmasa — oddiy HTTP (faqat sandbox).
    pub tls_cert: Option<PathBuf>,
    pub tls_key: Option<PathBuf>,
    /// mTLS: mijoz sertifikatlari CA'si (PEM). Berilsa, server mijoz sertifikatini so'raydi
    /// (majburiy emas — hamyonlar PQ Link bilan ulanadi); talab `[auth] require_mtls` da.
    #[serde(default)]
    pub client_ca: Option<PathBuf>,
    /// Teskari proksilar (CIDR): ulanish shulardan kelsa mijoz IP'si `X-Forwarded-For` dan olinadi.
    #[serde(default)]
    pub trusted_proxies: Vec<crate::clientip::Cidr>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DatabaseConfig {
    /// SQLite fayli.
    pub path: PathBuf,
    /// `full` (standart) yoki `normal` — `mpay_vault::db::Durability`.
    #[serde(default)]
    pub synchronous: mpay_vault::db::Durability,
    /// Ulanishlar hovuzi hajmi (standart 1 — `mpay_vault::db::DEFAULT_MAX_CONNECTIONS`).
    #[serde(default = "default_db_connections")]
    pub max_connections: u32,
}

fn default_db_connections() -> u32 {
    mpay_vault::db::DEFAULT_MAX_CONNECTIONS
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum KeyStoreBackend {
    Memory,
    Pkcs11,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct KeyStoreConfig {
    pub backend: KeyStoreBackend,
    /// `memory`: 64 hex belgili dev-urug' fayli (`MPAY_DEV_MASTER_SEED` ustunroq).
    pub seed_file: Option<PathBuf>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PqLinkConfig {
    /// KEK bilan o'ralgan ML-DSA-65 urug'i.
    pub mldsa_blob: PathBuf,
    /// Ed25519 server kaliti yorlig'i (KeyStore/HSM).
    #[serde(default = "default_ed_label")]
    pub ed25519_label: String,
    /// Kalit almashtirish (P1.6): e'lon qilingan keyingi identifikator (`mpay-server identity-next`).
    #[serde(default)]
    pub next: Option<NextIdentityConfig>,
    /// Oflayn ildiz imzolagan bekor qilingan identifikatorlar ro'yxati (`mpay-server revoke`, ADR-0014).
    #[serde(default)]
    pub revocations: Option<PathBuf>,
    /// Ildiz barmoq izi (hex): berilsa, ro'yxat imzosi ishga tushishda tekshiriladi.
    #[serde(default)]
    pub root_fingerprint: Option<String>,
    /// Ishonchli attestatsiya ildizlari (DER yoki PEM).
    pub attestation_roots: Vec<PathBuf>,
    #[serde(default = "default_level")]
    pub min_security_level: SecurityLevel,
    #[serde(default = "default_session_ttl")]
    pub session_ttl_secs: i64,
    /// Qurilmani ro'yxatdan o'tkazish (P1.7): `required` — yangi qurilma attestatsiyasi server
    /// nonce'i bilan bo'lishi shart; `off` — talab yo'q (faqat sandbox/test).
    #[serde(default)]
    pub enrollment: EnrollmentMode,
    #[serde(default = "default_nonce_ttl")]
    pub enrollment_nonce_ttl_secs: i64,
    /// Davriy qayta attestatsiya (ADR-0015): shuncha kundan keyin qurilma kalitni almashtirishi shart
    /// (muhrlangan so'rovlar `REATTEST_REQUIRED`); 0 — o'chiq.
    #[serde(default)]
    pub reattest_after_days: u32,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum EnrollmentMode {
    #[default]
    Required,
    Off,
}

fn default_nonce_ttl() -> i64 {
    300
}

/// `[pqlink.next]`.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NextIdentityConfig {
    pub mldsa_blob: PathBuf,
    pub ed25519_label: String,
}

fn default_ed_label() -> String {
    mpay_crypto::keystore::KeyLabel::SERVER_ED25519.to_owned()
}

fn default_level() -> SecurityLevel {
    SecurityLevel::StrongBox
}

fn default_session_ttl() -> i64 {
    900
}

/// Shield rejimi.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ShieldEngine {
    /// Qoidalar + graf/tezlik belgilari + ONNX ML (M5).
    #[default]
    Engine,
    /// Deterministik test stub (`docs/test-data.md` §2).
    Stub,
}

/// `[shield]` bo'limi.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ShieldConfig {
    #[serde(default)]
    pub engine: ShieldEngine,
    /// Qoidalar TOML (berilmasa — binarga joylangan standart).
    pub rules_file: Option<PathBuf>,
    /// ONNX model va metadata (berilmasa — joylangan `shield_v0`).
    pub model_file: Option<PathBuf>,
    pub model_meta_file: Option<PathBuf>,
    /// `true` — ML o'chiq, faqat qoidalar.
    #[serde(default)]
    pub disable_ml: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    Operator,
    Terminal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ApiKey {
    pub id: String,
    pub role: Role,
    /// `SHA-256(kalit)` hex.
    pub sha256: String,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AuthConfig {
    /// Operator va terminal endpointlari mTLS sertifikatini talab qiladi: CN = API kaliti `id`.
    #[serde(default)]
    pub require_mtls: bool,
    /// Bekor qilingan mTLS mijoz sertifikatlari: DER'ning SHA-256 (hex, `mpay-server cert-fingerprint`).
    /// Bunday sertifikat bilan ulanish sertifikatsiz hisoblanadi (`MTLS_REQUIRED`).
    #[serde(default)]
    pub revoked_client_certs: Vec<String>,
    #[serde(default)]
    pub keys: Vec<ApiKey>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SandboxApiConfig {
    /// `GET /v1/sandbox/otp/{id}` ni yoqadi (faqat `sandbox = true` bilan).
    #[serde(default)]
    pub expose_otp: bool,
}

impl Config {
    /// Faylni o'qiydi va tekshiradi.
    pub fn load(path: &Path) -> Result<Self, ConfigError> {
        let mut c: Config = load_toml(path)?;
        c.base_dir = path
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_else(|| PathBuf::from("."));
        c.validate()?;
        Ok(c)
    }

    /// Nisbiy yo'lni konfiguratsiya papkasiga nisbatan hal qiladi.
    pub fn resolve(&self, p: &Path) -> PathBuf {
        if p.is_absolute() {
            p.to_path_buf()
        } else {
            self.base_dir.join(p)
        }
    }

    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.keystore.backend == KeyStoreBackend::Memory && !self.sandbox {
            return Err(ConfigError::Invalid(
                "memory KeyStore faqat sandbox = true bilan ruxsat etiladi".into(),
            ));
        }
        if self.sandbox_api.expose_otp && !self.sandbox {
            return Err(ConfigError::Invalid(
                "sandbox_api.expose_otp faqat sandbox rejimida".into(),
            ));
        }
        if self.http.tls_cert.is_some() != self.http.tls_key.is_some() {
            return Err(ConfigError::Invalid(
                "http.tls_cert va http.tls_key birga berilishi kerak".into(),
            ));
        }
        if self.http.tls_cert.is_none() && !self.sandbox {
            return Err(ConfigError::Invalid(
                "production rejimida TLS majburiy".into(),
            ));
        }
        if self.auth.require_mtls && (self.http.tls_cert.is_none() || self.http.client_ca.is_none())
        {
            return Err(ConfigError::Invalid(
                "auth.require_mtls uchun http.tls_cert va http.client_ca kerak".into(),
            ));
        }
        if let Some(bad) = self
            .auth
            .revoked_client_certs
            .iter()
            .find(|f| f.len() != 64 || hex::decode(f).is_err())
        {
            return Err(ConfigError::Invalid(format!(
                "auth.revoked_client_certs: 64 hex kutilgan ({bad})"
            )));
        }
        if self.http.client_ca.is_some() && self.http.tls_cert.is_none() {
            return Err(ConfigError::Invalid(
                "http.client_ca faqat TLS bilan".into(),
            ));
        }
        for k in &self.auth.keys {
            if k.sha256.len() != 64 || hex::decode(&k.sha256).is_err() {
                return Err(ConfigError::Invalid(format!(
                    "auth.keys[{}].sha256 64 hex bo'lishi kerak",
                    k.id
                )));
            }
        }
        if self.pqlink.enrollment == EnrollmentMode::Off && !self.sandbox {
            return Err(ConfigError::Invalid(
                "pqlink.enrollment = off faqat sandbox rejimida".into(),
            ));
        }
        if let Some(n) = &self.pqlink.next {
            if n.ed25519_label == self.pqlink.ed25519_label
                || n.mldsa_blob == self.pqlink.mldsa_blob
            {
                return Err(ConfigError::Invalid(
                    "pqlink.next joriy identifikatordan farq qilishi kerak".into(),
                ));
            }
        }
        if self.pqlink.attestation_roots.is_empty() {
            return Err(ConfigError::Invalid(
                "pqlink.attestation_roots bo'sh".into(),
            ));
        }
        self.vault.luk.validate()?;
        Ok(())
    }
}
