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
    /// Prometheus metrikalari (2-faza P2.5).
    #[serde(default)]
    pub metrics: MetricsConfig,
    /// Ilova/qurilma yaxlitligi — Play Integrity (2-faza P2.6, ADR-0021).
    #[serde(default)]
    pub integrity: IntegrityConfig,
    /// Emitent bilan aloqa: timeout va reversal (ADR-0024).
    #[serde(default)]
    pub acquirer: AcquirerConfig,
    /// Kliring va hisob-kitob (ADR-0025).
    #[serde(default)]
    pub clearing: ClearingConfig,
    /// Shield roli: yetakchilik va snapshot'lar (ADR-0026; faqat `mpay-server shield`).
    #[serde(default)]
    pub shield_ha: ShieldHaConfig,

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
    /// PROXY protocol v1 (P2.5, ADR-0020): L4 load balancer (nginx `stream`) mijoz manzilini
    /// ulanish boshida yuboradi. Faqat `trusted_proxies` dan kelgan ulanishlarda o'qiladi.
    #[serde(default)]
    pub proxy_protocol: bool,
}

/// `[acquirer]`: emitentga yuborish va reversal ishchisi (ADR-0024).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct AcquirerConfig {
    /// Emitent `0110` ini kutish (ms). O'tsa — terminalga `96 ISSUER_TIMEOUT`, reversal navbatga.
    pub issuer_timeout_ms: u64,
    /// Reversal ishchisi tekshiruvi oralig'i (ms): qotgan `PENDING` lar va navbatdagi reversal'lar.
    pub reversal_interval_ms: u64,
    /// Birinchi `0400` dan oldin kutish (s) — kechikkan asl xabar emitentga reversal'dan oldin yetsin.
    pub reversal_delay_secs: i64,
    /// Emitentga yetib bo'lmasa qayta urinishlar orasidagi eng katta oraliq (s).
    pub reversal_max_backoff_secs: i64,
}

impl Default for AcquirerConfig {
    fn default() -> Self {
        Self {
            issuer_timeout_ms: 10_000,
            reversal_interval_ms: 5_000,
            reversal_delay_secs: 10,
            reversal_max_backoff_secs: 600,
        }
    }
}

/// `[shield_ha]`: Shield rolining yuqori mavjudligi (ADR-0026). Bir nechta Shield instansiyasi bitta
/// bazani ko'radi: bittasi yetakchi (DB ijarasi), qolganlari zaxira; yetakchi belgilar omborini
/// davriy saqlaydi, zaxira yetakchilikni olganda oxirgi snapshot'ni tiklaydi.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct ShieldHaConfig {
    pub enabled: bool,
    /// Instansiya nomi (log va ijara egasi); berilmasa — `HOSTNAME` yoki tasodifiy.
    pub instance_id: Option<String>,
    /// Ijara muddati (ms): yetakchi shuncha vaqt yangilamasa zaxira oladi.
    pub lease_ttl_ms: u64,
    /// Ijarani yangilash oralig'i (ms).
    pub renew_interval_ms: u64,
    /// Snapshot oralig'i (s) — yetakchi yiqilsa yo'qoladigan belgilar oynasi (RPO).
    pub snapshot_interval_secs: u64,
    /// Saqlanadigan snapshot'lar soni.
    pub snapshots_keep: u32,
}

impl Default for ShieldHaConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            instance_id: None,
            lease_ttl_ms: 6_000,
            renew_interval_ms: 1_000,
            snapshot_interval_secs: 30,
            snapshots_keep: 3,
        }
    }
}

/// `[clearing]`: kunlik kliring va hisob-kitob (ADR-0025). Tariflar — faraz, `TODO(spec):` bank va
/// sxema tariflari (savdo nuqtasi toifasi, karta turi bo'yicha).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct ClearingConfig {
    /// Savdo nuqtasidan olinadigan komissiya (MDR), bazis punkt (150 = 1,5 %).
    pub merchant_fee_bps: u32,
    /// Emitentga interchange, bazis punkt.
    pub interchange_bps: u32,
    /// Kun tugagach paket yaratishdan oldin kutish (s): javobi kutilayotgan avtorizatsiyalar yopilsin.
    pub cutoff_grace_secs: i64,
}

impl Default for ClearingConfig {
    fn default() -> Self {
        Self {
            merchant_fee_bps: 150,
            interchange_bps: 100,
            cutoff_grace_secs: 900,
        }
    }
}

/// `[metrics]`: Prometheus `/metrics` — alohida, ichki port (oddiy HTTP, kalitsiz). Berilmasa o'chiq.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MetricsConfig {
    #[serde(default)]
    pub listen: Option<SocketAddr>,
}

/// `[database]`: SQLite fayli (`path`, sandbox va bitta instansiya) **yoki** PostgreSQL (`url_env`,
/// 2-faza P2.3, ADR-0018). PostgreSQL URL'ida parol bor — u faylga yozilmaydi, faqat muhit
/// o'zgaruvchisida.
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DatabaseConfig {
    /// SQLite fayli.
    #[serde(default)]
    pub path: Option<PathBuf>,
    /// PostgreSQL URL'i (`postgres://foydalanuvchi:parol@host:5432/db`) turgan muhit o'zgaruvchisi.
    #[serde(default)]
    pub url_env: Option<String>,
    /// Dasturiy URL (testlar, embedding) — fayldan o'qilmaydi va yozilmaydi.
    #[serde(skip)]
    pub url: Option<String>,
    /// SQLite: `full` (standart) yoki `normal` — `mpay_vault::db::Durability`.
    #[serde(default)]
    pub synchronous: mpay_vault::db::Durability,
    /// Ulanishlar hovuzi hajmi (standart: SQLite 1, PostgreSQL 32).
    #[serde(default)]
    pub max_connections: Option<u32>,
}

impl std::fmt::Debug for DatabaseConfig {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("DatabaseConfig")
            .field("path", &self.path)
            .field("url_env", &self.url_env)
            .field("url", &self.url.as_ref().map(|_| "<maxfiy>"))
            .field("synchronous", &self.synchronous)
            .field("max_connections", &self.max_connections)
            .finish()
    }
}

impl DatabaseConfig {
    /// Ulanish URL'i: dasturiy `url` > `url_env` > `path` (SQLite). `base` — nisbiy yo'llar uchun.
    pub fn connect_url(&self, resolve: impl Fn(&Path) -> PathBuf) -> Result<String, String> {
        if let Some(u) = &self.url {
            return Ok(u.clone());
        }
        match (&self.url_env, &self.path) {
            (Some(var), None) => std::env::var(var)
                .map_err(|_| format!("database.url_env: {var} muhit o'zgaruvchisi yo'q")),
            (None, Some(p)) => Ok(mpay_vault::db::sqlite_url(&resolve(p))),
            (Some(_), Some(_)) => Err("database: `path` yoki `url_env` — faqat bittasi".into()),
            (None, None) => {
                Err("database: `path` (SQLite) yoki `url_env` (PostgreSQL) kerak".into())
            }
        }
    }
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
    /// Apparat `rootOfTrust` (Verified + deviceLocked) talab qilinadi. `false` — faqat emulyator sinovi.
    #[serde(default = "default_true")]
    pub require_verified_boot: bool,
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
    /// PQ Link sessiyalari ombori (2-faza P2.4): `auto` — PostgreSQL'da DB (ko'p instansiya),
    /// SQLite'da xotira; `memory` / `database` — majburiy.
    #[serde(default)]
    pub session_store: SessionStoreKind,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionStoreKind {
    #[default]
    Auto,
    Memory,
    Database,
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

fn default_true() -> bool {
    true
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

/// `[integrity]`: provisioning'da Play Integrity tokeni (ADR-0021).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct IntegrityConfig {
    /// `off` — tekshirilmaydi; `mock` — sandbox imzolagan tokenlar; `google` — `decodeIntegrityToken`.
    #[serde(default)]
    pub mode: IntegrityMode,
    /// `true` — tokensiz provisioning rad etiladi (`INTEGRITY_REQUIRED`).
    #[serde(default = "default_true")]
    pub required: bool,
    /// Hamyon ilovasi paketi (`requestPackageName`).
    #[serde(default)]
    pub package_name: String,
    /// Ruxsat etilgan ilova imzo sertifikatlari (SHA-256, base64url). Production'da majburiy.
    #[serde(default)]
    pub certificate_sha256: Vec<String>,
    /// Token yoshi chegarasi (soniya).
    #[serde(default = "default_integrity_max_age")]
    pub max_age_secs: i64,
    /// `mock`: maxfiy kalit (PKCS#8 PEM) — `mpay-server init` yaratadi. Faqat sandbox.
    #[serde(default)]
    pub mock_key: Option<PathBuf>,
    #[serde(default)]
    pub google: Option<GoogleIntegrityConfig>,
}

impl Default for IntegrityConfig {
    fn default() -> Self {
        Self {
            mode: IntegrityMode::Off,
            required: true,
            package_name: String::new(),
            certificate_sha256: Vec::new(),
            max_age_secs: default_integrity_max_age(),
            mock_key: None,
            google: None,
        }
    }
}

fn default_integrity_max_age() -> i64 {
    120
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum IntegrityMode {
    #[default]
    Off,
    Mock,
    Google,
}

/// `[integrity.google]`: server tomonida dekodlash. OAuth2 access token manbai — bittasi:
/// `service_account_file` (Google xizmat akkaunti JSON kaliti: JWT → token, kesh) yoki tashqaridan
/// yangilanadigan `access_token_env` / `access_token_file`.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GoogleIntegrityConfig {
    #[serde(default = "default_google_base")]
    pub base_url: String,
    #[serde(default)]
    pub access_token_env: Option<String>,
    #[serde(default)]
    pub access_token_file: Option<PathBuf>,
    /// Xizmat akkaunti kaliti (maxfiy; Docker secret sifatida).
    #[serde(default)]
    pub service_account_file: Option<PathBuf>,
    #[serde(default = "default_google_timeout")]
    pub timeout_ms: u64,
}

fn default_google_base() -> String {
    "https://playintegrity.googleapis.com".into()
}

fn default_google_timeout() -> u64 {
    2000
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
    /// 2-faza P2.4 (ADR-0019): `local` — dvigatel shu jarayonda (bitta instansiya); `remote` —
    /// belgilar ombori yagona Shield instansiyasida (`mpay-server shield`), bu yerda faqat zaxira.
    #[serde(default)]
    pub mode: ShieldMode,
    #[serde(default)]
    pub remote: Option<ShieldRemoteConfig>,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ShieldMode {
    #[default]
    Local,
    Remote,
}

/// `[shield.remote]`: Shield roli manzili va kirish ma'lumotlari.
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ShieldRemoteConfig {
    /// `https://shield.internal:8445` (`http://` — faqat loopback sinov).
    pub url: String,
    /// Zaxira Shield instansiyalari (ADR-0026): asosiysi javob bermasa yoki `503 SHIELD_STANDBY`
    /// qaytarsa navbatdagisi; oxirgi muvaffaqiyatlisi keyingi so'rovlarda birinchi.
    #[serde(default)]
    pub standby_urls: Vec<String>,
    /// `shield` rolidagi API kaliti turgan muhit o'zgaruvchisi.
    #[serde(default)]
    pub key_env: Option<String>,
    /// Dasturiy kalit (testlar) — fayldan o'qilmaydi.
    #[serde(skip)]
    pub key: Option<String>,
    /// Shield server sertifikatining ishonchli ildizi (PEM).
    #[serde(default)]
    pub ca_file: Option<PathBuf>,
    /// mTLS mijoz sertifikati va kaliti (PEM; CN = API kaliti ID).
    #[serde(default)]
    pub client_cert: Option<PathBuf>,
    #[serde(default)]
    pub client_key: Option<PathBuf>,
    /// So'rov vaqti chegarasi; oshsa — mahalliy zaxira dvigatel.
    #[serde(default = "default_shield_timeout")]
    pub timeout_ms: u64,
}

fn default_shield_timeout() -> u64 {
    300
}

impl std::fmt::Debug for ShieldRemoteConfig {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ShieldRemoteConfig")
            .field("url", &self.url)
            .field("standby_urls", &self.standby_urls)
            .field("key_env", &self.key_env)
            .field("key", &self.key.as_ref().map(|_| "<maxfiy>"))
            .field("timeout_ms", &self.timeout_ms)
            .finish_non_exhaustive()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    Operator,
    Terminal,
    /// Shield roliga murojaat qiluvchi API instansiyasi (ADR-0019).
    Shield,
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
        let a = &self.acquirer;
        // Timeout qotgan `PENDING` chegarasidan qisqa bo'lsin: aks holda ishlov tugamay turib ishchi
        // yozuvni "natija noma'lum" deb yopadi.
        if a.issuer_timeout_ms == 0
            || a.issuer_timeout_ms >= crate::dedup::STALE_PENDING_SECS as u64 * 1000 / 2
        {
            return Err(ConfigError::Invalid(format!(
                "acquirer.issuer_timeout_ms: 1 … {} ms",
                crate::dedup::STALE_PENDING_SECS * 1000 / 2 - 1
            )));
        }
        if a.reversal_interval_ms < 50
            || a.reversal_delay_secs < 0
            || a.reversal_max_backoff_secs < 1
        {
            return Err(ConfigError::Invalid(
                "acquirer: reversal_interval_ms ≥ 50, reversal_delay_secs ≥ 0, reversal_max_backoff_secs ≥ 1"
                    .into(),
            ));
        }
        let h = &self.shield_ha;
        if h.renew_interval_ms < 50
            || h.lease_ttl_ms < h.renew_interval_ms * 3
            || h.snapshot_interval_secs == 0
            || h.snapshots_keep == 0
            || h.instance_id.as_deref().is_some_and(|i| {
                i.is_empty() || i.len() > 64 || !i.bytes().all(|b| b.is_ascii_graphic())
            })
        {
            return Err(ConfigError::Invalid(
                "shield_ha: renew_interval_ms ≥ 50, lease_ttl_ms ≥ 3 × renew_interval_ms, \
                 snapshot_interval_secs ≥ 1, snapshots_keep ≥ 1, instance_id 1–64 belgi"
                    .into(),
            ));
        }
        if let Some(r) = &self.shield.remote {
            if r.standby_urls
                .iter()
                .any(|u| u.trim_end_matches('/') == r.url.trim_end_matches('/'))
            {
                return Err(ConfigError::Invalid(
                    "shield.remote.standby_urls asosiy url'ni takrorlamasin".into(),
                ));
            }
        }
        let c = &self.clearing;
        if c.merchant_fee_bps > 10_000 || c.interchange_bps > 10_000 || c.cutoff_grace_secs < 0 {
            return Err(ConfigError::Invalid(
                "clearing: *_bps 0 … 10000, cutoff_grace_secs ≥ 0".into(),
            ));
        }
        let pi = &self.integrity;
        if pi.mode != IntegrityMode::Off {
            if pi.package_name.is_empty() {
                return Err(ConfigError::Invalid("integrity.package_name kerak".into()));
            }
            if !(10..=3600).contains(&pi.max_age_secs) {
                return Err(ConfigError::Invalid(
                    "integrity.max_age_secs 10..3600 oralig'ida".into(),
                ));
            }
            if !self.sandbox && pi.certificate_sha256.is_empty() {
                return Err(ConfigError::Invalid(
                    "production'da integrity.certificate_sha256 (ilova imzo sertifikati) majburiy"
                        .into(),
                ));
            }
        }
        match pi.mode {
            IntegrityMode::Mock if !self.sandbox => {
                return Err(ConfigError::Invalid(
                    "integrity.mode = mock faqat sandbox = true bilan".into(),
                ))
            }
            IntegrityMode::Mock if pi.mock_key.is_none() => {
                return Err(ConfigError::Invalid(
                    "integrity.mode = mock uchun integrity.mock_key kerak".into(),
                ))
            }
            IntegrityMode::Google => {
                let g = pi.google.as_ref().ok_or_else(|| {
                    ConfigError::Invalid(
                        "integrity.mode = google uchun [integrity.google] kerak".into(),
                    )
                })?;
                let sources = [
                    g.access_token_env.is_some(),
                    g.access_token_file.is_some(),
                    g.service_account_file.is_some(),
                ];
                if sources.iter().filter(|s| **s).count() != 1 {
                    return Err(ConfigError::Invalid(
                        "integrity.google: service_account_file, access_token_env yoki access_token_file (bittasi)"
                            .into(),
                    ));
                }
                if !g.base_url.starts_with("https://") && !self.sandbox {
                    return Err(ConfigError::Invalid(
                        "integrity.google.base_url https:// bo'lishi kerak".into(),
                    ));
                }
            }
            _ => {}
        }
        if self.http.proxy_protocol && self.http.trusted_proxies.is_empty() {
            return Err(ConfigError::Invalid(
                "http.proxy_protocol uchun http.trusted_proxies kerak (sarlavha faqat proksidan)"
                    .into(),
            ));
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
