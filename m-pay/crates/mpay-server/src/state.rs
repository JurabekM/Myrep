//! Ilova holati va komponentlarni konfiguratsiyadan yig'ish (port'larni ulash — ADR-0002).

use std::path::Path;
use std::sync::Arc;

use mpay_common::clock::{Clock, SystemClock};
use mpay_common::ports::{IdvDecider, RiskScorer};
use mpay_crypto::keystore::{ensure_standard_keys, KeyLabel, KeyStore, MemoryKeyStore};
use mpay_crypto::scheme::{CryptogramScheme, MpayAes128CmacV1};
use mpay_issuer::Issuer;
use mpay_pqlink::attestation::{AttestationPolicy, TrustAnchors};
use mpay_pqlink::{KeyStoreServerSigner, MlDsaSeedBlob, PqLinkServer, ServerConfig};
use mpay_shield::model::{MlScorer, TractScorer};
use mpay_shield::rules::RuleSet;
use mpay_shield::{Shield, StubShield};
use mpay_vault::{Vault, VaultDetokenizer};
use thiserror::Error;
use zeroize::Zeroizing;

use crate::auth::Authenticator;
use crate::config::{Config, KeyStoreBackend};

#[derive(Debug, Error)]
pub enum BootError {
    #[error("konfiguratsiya: {0}")]
    Config(String),
    #[error("fayl {path}: {msg}")]
    File { path: String, msg: String },
    #[error("KeyStore: {0}")]
    KeyStore(String),
    #[error("PQ Link: {0}")]
    PqLink(#[from] mpay_pqlink::PqLinkError),
    #[error("Vault: {0}")]
    Vault(#[from] mpay_vault::VaultError),
    #[error("Issuer: {0}")]
    Issuer(#[from] mpay_issuer::IssuerError),
    #[error("server migratsiyasi: {0}")]
    Migrate(#[from] sqlx::migrate::MigrateError),
}

fn read(path: &Path) -> Result<Vec<u8>, BootError> {
    std::fs::read(path).map_err(|e| BootError::File {
        path: path.display().to_string(),
        msg: e.to_string(),
    })
}

/// E'lon qilingan keyingi server identifikatori.
#[derive(Debug, Clone)]
pub struct NextIdentity {
    pub identity: mpay_pqlink::ServerIdentity,
    pub sig_ed25519: [u8; 64],
    pub sig_mldsa65: Vec<u8>,
}

/// Ilova holati.
pub struct AppState {
    pub vault: Arc<Vault>,
    pub issuer: Arc<Issuer>,
    pub pqlink: Arc<PqLinkServer>,
    pub keystore: Arc<dyn KeyStore>,
    pub scheme: Arc<dyn CryptogramScheme>,
    pub clock: Arc<dyn Clock>,
    pub auth: Authenticator,
    pub limits: crate::ratelimit::RateLimits,
    pub require_mtls: bool,
    pub trusted_proxies: Vec<crate::clientip::Cidr>,
    /// OTP yetkazish kanali.
    pub otp: crate::otp::OtpChannel,
    /// Davriy qayta attestatsiya muddati (soniya); 0 — o'chiq.
    pub reattest_after_secs: i64,
    /// Kalit almashtirish: keyingi identifikator va joriy kalitlar tasdig'i (boot paytida hisoblanadi).
    pub next_identity: Option<NextIdentity>,
    /// Bekor qilingan identifikatorlar ro'yxati (tarqatish uchun).
    pub revocations: Option<mpay_common::api::RevocationsDto>,
    /// Qurilmani ro'yxatdan o'tkazish (P1.7); `None` — `enrollment = off`.
    pub enrollment: Option<Arc<crate::enroll::Enrollment>>,
    pub sandbox: bool,
    pub expose_otp: bool,
}

impl std::fmt::Debug for AppState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("AppState")
            .field("keystore", &self.keystore.backend_name())
            .field("sandbox", &self.sandbox)
            .finish_non_exhaustive()
    }
}

impl AppState {
    /// Qurilma attestatsiyasi eskirganmi (ADR-0015). Attestatsiya vaqti handshake'da reyestrdan
    /// olinib sessiyaga yozilgan — har muhrlangan so'rovda DB'ga murojaat yo'q (yagona SQLite
    /// ulanishida navbat bo'lmasin) va DB xatosi so'rovni o'tkazib yubormaydi (handshake rad etiladi).
    pub fn reattest_due(&self, info: &mpay_pqlink::SessionInfo) -> bool {
        self.reattest_after_secs > 0
            && info
                .attested_at
                .is_some_and(|at| self.clock.unix() - at > self.reattest_after_secs)
    }

    /// IP chegaralari uchun mijoz manzili (ishonchli proksi ortida — `X-Forwarded-For`).
    pub fn client_ip(
        &self,
        peer: std::net::SocketAddr,
        headers: &axum::http::HeaderMap,
    ) -> std::net::IpAddr {
        let xff: Vec<&str> = headers
            .get_all("x-forwarded-for")
            .iter()
            .filter_map(|v| v.to_str().ok())
            .collect();
        crate::clientip::client_ip(peer.ip(), &xff, &self.trusted_proxies)
    }

    /// API kalitini tekshiradi (rol) va kalit bo'yicha so'rovlar chegarasini qo'llaydi.
    pub fn caller(
        &self,
        headers: &axum::http::HeaderMap,
        mtls: &crate::auth::Mtls,
        role: crate::config::Role,
    ) -> Result<crate::auth::Caller, crate::error::ApiError> {
        let c = self.auth.authorize(headers, role)?;
        // mTLS: Bearer kalitning o'zi yetarli emas — sertifikat CN'i kalit ID'siga teng bo'lishi shart.
        if self.require_mtls && mtls.0.as_deref() != Some(c.id.as_str()) {
            tracing::warn!(key = %c.id, cert = ?mtls.0, "mTLS: sertifikat yo'q yoki kalitga mos emas");
            return Err(crate::error::ApiError::new(
                axum::http::StatusCode::FORBIDDEN,
                "MTLS_REQUIRED",
                "mijoz sertifikati kerak (CN = API kaliti ID)",
            ));
        }
        self.limits.api_key(&c.id).map_err(|l| {
            tracing::warn!(key = %c.id, "rate-limit: API kaliti");
            crate::error::ApiError::rate_limited(l, false)
        })?;
        Ok(c)
    }
}

/// Dev-urug'ni o'qiydi: `MPAY_DEV_MASTER_SEED` yoki `keystore.seed_file`.
fn dev_seed(cfg: &Config) -> Result<Zeroizing<[u8; 32]>, BootError> {
    let text = match std::env::var("MPAY_DEV_MASTER_SEED") {
        Ok(v) => Zeroizing::new(v),
        Err(_) => {
            let p = cfg.keystore.seed_file.as_ref().ok_or_else(|| {
                BootError::KeyStore("MPAY_DEV_MASTER_SEED yoki keystore.seed_file kerak".into())
            })?;
            let raw = Zeroizing::new(read(&cfg.resolve(p))?);
            Zeroizing::new(String::from_utf8_lossy(&raw).trim().to_owned())
        }
    };
    let mut seed = Zeroizing::new([0u8; 32]);
    hex::decode_to_slice(text.trim(), &mut seed[..])
        .map_err(|_| BootError::KeyStore("dev-urug' 64 hex belgi bo'lishi kerak".into()))?;
    Ok(seed)
}

/// KeyStore'ni ochadi.
pub fn open_keystore(cfg: &Config) -> Result<Arc<dyn KeyStore>, BootError> {
    let ks: Arc<dyn KeyStore> = match cfg.keystore.backend {
        KeyStoreBackend::Memory => {
            if !cfg.sandbox {
                return Err(BootError::Config(
                    "memory KeyStore faqat sandbox rejimida".into(),
                ));
            }
            tracing::warn!("KeyStore: memory (dev-urug') — FAQAT SANDBOX");
            Arc::new(MemoryKeyStore::from_seed(*dev_seed(cfg)?))
        }
        KeyStoreBackend::Pkcs11 => open_pkcs11()?,
    };
    ensure_standard_keys(ks.as_ref()).map_err(|e| BootError::KeyStore(e.to_string()))?;
    Ok(ks)
}

#[cfg(feature = "pkcs11")]
fn open_pkcs11() -> Result<Arc<dyn KeyStore>, BootError> {
    use mpay_crypto::keystore::{Pkcs11Config, Pkcs11KeyStore};
    let c = Pkcs11Config::from_env().map_err(|e| BootError::KeyStore(e.to_string()))?;
    Ok(Arc::new(
        Pkcs11KeyStore::open(&c).map_err(|e| BootError::KeyStore(e.to_string()))?,
    ))
}

#[cfg(not(feature = "pkcs11"))]
fn open_pkcs11() -> Result<Arc<dyn KeyStore>, BootError> {
    Err(BootError::KeyStore(
        "mpay-server `pkcs11` feature'siz yig'ilgan".into(),
    ))
}

/// Ishonchli attestatsiya ildizlarini o'qiydi (PEM yoki DER).
pub fn load_anchors(cfg: &Config) -> Result<TrustAnchors, BootError> {
    let mut ders = Vec::new();
    for p in &cfg.pqlink.attestation_roots {
        let path = cfg.resolve(p);
        let raw = read(&path)?;
        // PEM (boshida izoh qatorlari bo'lishi mumkin) yoki DER.
        if raw.windows(11).any(|w| w == b"-----BEGIN ") {
            let certs = pem_to_der(&String::from_utf8_lossy(&raw));
            if certs.is_empty() {
                return Err(BootError::Config(format!(
                    "{} da sertifikat yo'q",
                    path.display()
                )));
            }
            ders.extend(certs);
        } else {
            ders.push(raw);
        }
    }
    Ok(TrustAnchors::from_der(&ders)?)
}

fn pem_to_der(pem: &str) -> Vec<Vec<u8>> {
    use base64::Engine;
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut inside = false;
    for line in pem.lines() {
        let l = line.trim();
        if l.starts_with("-----BEGIN CERTIFICATE") {
            inside = true;
            cur.clear();
        } else if l.starts_with("-----END CERTIFICATE") {
            inside = false;
            if let Ok(d) = base64::engine::general_purpose::STANDARD.decode(&cur) {
                out.push(d);
            }
        } else if inside {
            cur.push_str(l);
        }
    }
    out
}

/// Shield port'lari: `(ID&V, risk)`.
pub type ShieldPorts = (Arc<dyn IdvDecider>, Arc<dyn RiskScorer>);

/// Shield port'lari (ID&V va risk) — konfiguratsiya bo'yicha dvigatel yoki stub.
pub fn build_shield(cfg: &Config) -> Result<ShieldPorts, BootError> {
    use crate::config::ShieldEngine;
    let sc = &cfg.shield;
    match sc.engine {
        ShieldEngine::Stub => {
            tracing::warn!("Shield: deterministik STUB (faqat testlar)");
            let s = Arc::new(StubShield::new(cfg.shield_stub.clone()));
            Ok((s.clone(), s))
        }
        ShieldEngine::Engine => {
            let rules = match &sc.rules_file {
                Some(p) => RuleSet::parse(&String::from_utf8_lossy(&read(&cfg.resolve(p))?)),
                None => RuleSet::default_rules(),
            }
            .map_err(BootError::Config)?;
            let ml: Option<Arc<dyn MlScorer>> = if sc.disable_ml {
                None
            } else {
                let m = match (&sc.model_file, &sc.model_meta_file) {
                    (Some(m), Some(j)) => TractScorer::load(
                        &read(&cfg.resolve(m))?,
                        &String::from_utf8_lossy(&read(&cfg.resolve(j))?),
                    ),
                    (None, None) => TractScorer::default_model(),
                    _ => {
                        return Err(BootError::Config(
                            "shield.model_file va model_meta_file birga".into(),
                        ))
                    }
                }
                .map_err(BootError::Config)?;
                tracing::info!(
                    model = m.meta().version,
                    "Shield: ONNX model yuklandi (tract)"
                );
                Some(Arc::new(m))
            };
            tracing::info!(rules = %rules.version, txn_rules = rules.txn_rule.len(), idv_rules = rules.idv_rule.len(), "Shield: dvigatel");
            let s = Arc::new(Shield::new(rules, ml));
            Ok((s.clone(), s))
        }
    }
}

/// Bekor qilish ro'yxatini o'qiydi; joriy yoki keyingi identifikator ro'yxatda bo'lsa — ishga tushmaydi.
fn load_revocations(
    cfg: &Config,
    signer: &KeyStoreServerSigner,
    next: Option<&NextIdentity>,
) -> Result<Option<mpay_common::api::RevocationsDto>, BootError> {
    let Some(p) = &cfg.pqlink.revocations else {
        return Ok(None);
    };
    let raw = read(&cfg.resolve(p))?;
    let dto: mpay_common::api::RevocationsDto = serde_json::from_slice(&raw)
        .map_err(|e| BootError::Config(format!("pqlink.revocations: {e}")))?;
    let signed = crate::revocations::from_dto(&dto).map_err(BootError::Config)?;
    if let Some(rf) = &cfg.pqlink.root_fingerprint {
        let mut fp = [0u8; 32];
        hex::decode_to_slice(rf, &mut fp)
            .map_err(|_| BootError::Config("pqlink.root_fingerprint 64 hex".into()))?;
        signed
            .verify(&fp)
            .map_err(|e| BootError::Config(format!("bekor qilish ro'yxati imzosi: {e}")))?;
    }
    let own = mpay_pqlink::ServerSigner::identity(signer).fingerprint();
    if signed.is_revoked(&own) {
        return Err(BootError::Config(
            "joriy PQ Link identifikatori bekor qilingan — kalitni almashtiring".into(),
        ));
    }
    if next.is_some_and(|n| signed.is_revoked(&n.identity.fingerprint())) {
        return Err(BootError::Config(
            "pqlink.next identifikatori bekor qilingan".into(),
        ));
    }
    tracing::info!(
        version = signed.version,
        count = signed.revoked.len(),
        "PQ Link: bekor qilish ro'yxati"
    );
    Ok(Some(dto))
}

/// CLI buyruqlari (`identity`, `audit-verify`, …) uchun: tarmoqqa chiqmaydigan komponentlar —
/// OTP kanali `sandbox` (SMS shlyuzi tokeni talab qilinmaydi).
pub async fn build_offline(cfg: &Config) -> Result<AppState, BootError> {
    let mut cfg = cfg.clone();
    cfg.otp = crate::otp::OtpConfig::default();
    build(&cfg).await
}

/// Barcha komponentlarni yig'adi.
pub async fn build(cfg: &Config) -> Result<AppState, BootError> {
    let clock: Arc<dyn Clock> = Arc::new(SystemClock);
    let ks = open_keystore(cfg)?;
    let scheme: Arc<dyn CryptogramScheme> = Arc::new(MpayAes128CmacV1);

    let blob = MlDsaSeedBlob::from_bytes(&read(&cfg.resolve(&cfg.pqlink.mldsa_blob))?)?;
    // Joriy yorliq standart bo'lmasligi mumkin (kalit almashtirishdan keyin) — kalit tayyor bo'lsin.
    let ed_label = KeyLabel::new(cfg.pqlink.ed25519_label.as_str());
    ks.ensure_key(&ed_label, mpay_crypto::keystore::KeyKind::Ed25519)
        .map_err(|e| BootError::KeyStore(e.to_string()))?;
    let signer = Arc::new(KeyStoreServerSigner::new(ks.clone(), ed_label, blob)?);
    let next_identity = match &cfg.pqlink.next {
        Some(n) => {
            let label = KeyLabel::new(n.ed25519_label.as_str());
            ks.ensure_key(&label, mpay_crypto::keystore::KeyKind::Ed25519)
                .map_err(|e| BootError::KeyStore(e.to_string()))?;
            let nb = MlDsaSeedBlob::from_bytes(&read(&cfg.resolve(&n.mldsa_blob))?)?;
            let next = KeyStoreServerSigner::new(ks.clone(), label, nb)?;
            let id = mpay_pqlink::ServerSigner::identity(&next).clone();
            let (sig_ed25519, sig_mldsa65) =
                mpay_pqlink::ServerSigner::endorse(signer.as_ref(), &id.fingerprint())?;
            tracing::info!(next_fp = %hex::encode(id.fingerprint()), "PQ Link: keyingi identifikator e'lon qilingan");
            Some(NextIdentity {
                identity: id,
                sig_ed25519,
                sig_mldsa65,
            })
        }
        None => None,
    };
    let revocations = load_revocations(cfg, signer.as_ref(), next_identity.as_ref())?;
    let anchors = load_anchors(cfg)?;
    let pq_cfg = ServerConfig {
        session_ttl_secs: cfg.pqlink.session_ttl_secs,
        attestation: AttestationPolicy {
            min_security_level: cfg.pqlink.min_security_level,
            require_verified_boot: cfg.pqlink.require_verified_boot,
        },
        ..ServerConfig::default()
    };
    let url = cfg
        .database
        .connect_url(|p| cfg.resolve(p))
        .map_err(BootError::Config)?;
    let db = mpay_vault::db::Db::open(&url, cfg.database.synchronous, cfg.database.max_connections)
        .await
        .map_err(|e| BootError::Config(format!("ma'lumotlar bazasi: {e}")))?;
    tracing::info!(dialect = ?db.dialect(), "ma'lumotlar bazasi");
    crate::dedup::migrate(&db).await?;
    let pool = db.pool().clone();
    let enrollment = match cfg.pqlink.enrollment {
        crate::config::EnrollmentMode::Required => Some(Arc::new(
            crate::enroll::Enrollment::new(
                pool.clone(),
                ks.clone(),
                clock.clone(),
                cfg.pqlink.enrollment_nonce_ttl_secs,
            )
            .map_err(|e| BootError::KeyStore(e.to_string()))?,
        )),
        crate::config::EnrollmentMode::Off => {
            tracing::warn!("PQ Link: qurilmani ro'yxatdan o'tkazish o'chiq — FAQAT SANDBOX");
            None
        }
    };
    let mut pq = PqLinkServer::new(signer, anchors, pq_cfg, clock.clone());
    let shared_sessions = match cfg.pqlink.session_store {
        crate::config::SessionStoreKind::Auto => db.dialect() == mpay_vault::db::Dialect::Postgres,
        crate::config::SessionStoreKind::Memory => false,
        crate::config::SessionStoreKind::Database => true,
    };
    if shared_sessions {
        // Ko'p instansiya: sessiyalar DB'da (kalitlar KEK bilan shifrlangan).
        pq = pq.with_store(Arc::new(crate::sessions::DbSessionStore::new(
            pool.clone(),
            ks.clone(),
            clock.clone(),
        )));
    }
    tracing::info!(shared = shared_sessions, "PQ Link sessiyalari ombori");
    if let Some(e) = &enrollment {
        pq = pq.with_enrollment(e.clone());
    }
    let pqlink = Arc::new(pq);
    let (idv, risk) = build_shield(cfg)?;
    let vault = Arc::new(
        Vault::open(
            db.clone(),
            ks.clone(),
            scheme.clone(),
            idv,
            clock.clone(),
            cfg.vault.clone(),
        )
        .await?,
    );
    // Detokenizatsiya porti faqat emitentga beriladi (ADR-0002).
    let detok = Arc::new(VaultDetokenizer::new(vault.clone(), "issuer"));
    let issuer = Arc::new(
        Issuer::open(
            db,
            ks.clone(),
            scheme.clone(),
            detok,
            risk,
            clock.clone(),
            cfg.issuer.clone(),
        )
        .await?,
    );

    tracing::info!(
        keystore = ks.backend_name(),
        server_fp = %hex::encode(pqlink.identity().fingerprint()),
        "mpay-server komponentlari tayyor"
    );
    Ok(AppState {
        vault,
        issuer,
        pqlink,
        keystore: ks,
        scheme,
        clock,
        auth: Authenticator::new(&cfg.auth.keys),
        limits: crate::ratelimit::RateLimits::new(&cfg.rate_limit),
        require_mtls: cfg.auth.require_mtls,
        trusted_proxies: cfg.http.trusted_proxies.clone(),
        otp: crate::otp::OtpChannel::from_config(&cfg.otp, |p| cfg.resolve(p))
            .map_err(BootError::Config)?,
        reattest_after_secs: i64::from(cfg.pqlink.reattest_after_days) * 86_400,
        next_identity,
        revocations,
        enrollment,
        sandbox: cfg.sandbox,
        expose_otp: cfg.sandbox && cfg.sandbox_api.expose_otp,
    })
}
