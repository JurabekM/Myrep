//! `[integrity]` (2-faza P2.6, ADR-0021): provisioning'da Play Integrity tokenini tekshirish.
//!
//! * `mock` — sandbox kaliti bilan imzolangan tokenlar; emulyatordagi demo ilova ularni
//!   `POST /v1/sandbox/integrity-token` dan oladi, soft-hamyon — [`SandboxIssuer`] orqali.
//! * `google` — `decodeIntegrityToken` (`mpay_integrity::google`).
//!
//! Token haqiqiy emas yoki boshqa sessiya/ilovaga tegishli bo'lsa — 403 (`INTEGRITY_INVALID`),
//! dekodlash xizmati javob bermasa — 503 (`INTEGRITY_UNAVAILABLE`, mijoz qayta urinadi).
//! Verdict sifati (qurilma darajasi va h.k.) — Shield qoidalarida.

use std::sync::Arc;
use std::time::Duration;

use axum::http::StatusCode;
use mpay_integrity::mock::{MockIssuer, Preset};
use mpay_integrity::{Integrity, IntegrityError, Policy};

use crate::config::{Config, IntegrityMode};
use crate::error::ApiError;

/// Sandbox mock tokenlari chiqaruvchisi (paket va sertifikat konfiguratsiyadan).
#[derive(Debug)]
pub struct SandboxIssuer {
    issuer: MockIssuer,
    package: String,
    cert: String,
}

impl SandboxIssuer {
    /// Shu sessiya `requestHash` i uchun token.
    pub fn issue(&self, preset: Preset, request_hash: &str, now_ms: i64) -> String {
        self.issuer
            .issue_preset(preset, &self.package, &self.cert, request_hash, now_ms)
    }
}

/// `mock` rejimida: chiqaruvchi (soft-hamyon, yuk generatori, sandbox endpoint uchun).
pub fn sandbox_issuer(cfg: &Config) -> Result<Option<SandboxIssuer>, String> {
    let pi = &cfg.integrity;
    if pi.mode != IntegrityMode::Mock {
        return Ok(None);
    }
    let path = cfg.resolve(pi.mock_key.as_ref().ok_or("integrity.mock_key kerak")?);
    let pem = zeroize::Zeroizing::new(
        std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?,
    );
    Ok(Some(SandboxIssuer {
        issuer: MockIssuer::from_pkcs8_pem(&pem)?,
        package: pi.package_name.clone(),
        cert: pi
            .certificate_sha256
            .first()
            .cloned()
            .unwrap_or_else(|| "SANDBOX".into()),
    }))
}

/// [`build`] natijasi: tekshiruvchi va (mock bo'lsa) chiqaruvchi.
pub type Built = (Option<Arc<Integrity>>, Option<Arc<SandboxIssuer>>);

/// Tekshiruvchi va (mock bo'lsa) chiqaruvchi.
pub fn build(cfg: &Config) -> Result<Built, String> {
    let pi = &cfg.integrity;
    let policy = Policy {
        package_name: pi.package_name.clone(),
        certificate_sha256: pi.certificate_sha256.clone(),
        max_age_ms: pi.max_age_secs * 1000,
        max_skew_ms: 30_000,
    };
    match pi.mode {
        IntegrityMode::Off => Ok((None, None)),
        IntegrityMode::Mock => {
            let issuer = sandbox_issuer(cfg)?.ok_or("integrity mock")?;
            let verifier = Arc::new(issuer.issuer.verifier());
            tracing::warn!(package = %pi.package_name, "integrity: MOCK tokenlar (faqat sandbox)");
            Ok((
                Some(Arc::new(Integrity::new(verifier, policy, pi.required))),
                Some(Arc::new(issuer)),
            ))
        }
        IntegrityMode::Google => {
            use mpay_integrity::google::{AccessToken, GoogleDecoder};
            let g = pi.google.as_ref().ok_or("[integrity.google] kerak")?;
            let token = match (&g.access_token_env, &g.access_token_file) {
                (Some(v), _) => AccessToken::Env(v.clone()),
                (None, Some(f)) => AccessToken::File(cfg.resolve(f)),
                (None, None) => return Err("integrity.google: access token manbai kerak".into()),
            };
            let decoder = GoogleDecoder::new(
                http_client(g.timeout_ms)?,
                &g.base_url,
                &pi.package_name,
                token,
            );
            tracing::info!(package = %pi.package_name, "integrity: Google Play Integrity");
            Ok((
                Some(Arc::new(Integrity::new(
                    Arc::new(decoder),
                    policy,
                    pi.required,
                ))),
                None,
            ))
        }
    }
}

fn http_client(timeout_ms: u64) -> Result<reqwest::Client, String> {
    let mut roots = rustls::RootCertStore::empty();
    for c in rustls_native_certs::load_native_certs().certs {
        let _ = roots.add(c);
    }
    let provider = Arc::new(rustls::crypto::ring::default_provider());
    let tls = rustls::ClientConfig::builder_with_provider(provider)
        .with_safe_default_protocol_versions()
        .map_err(|e| e.to_string())?
        .with_root_certificates(roots)
        .with_no_client_auth();
    reqwest::Client::builder()
        .use_preconfigured_tls(tls)
        .timeout(Duration::from_millis(timeout_ms))
        .connect_timeout(Duration::from_millis((timeout_ms / 2).clamp(100, 2000)))
        .build()
        .map_err(|e| e.to_string())
}

/// Tekshiruv xatosi → HTTP javobi.
pub fn api_error(e: &IntegrityError) -> ApiError {
    match e {
        IntegrityError::Missing => ApiError::new(
            StatusCode::FORBIDDEN,
            "INTEGRITY_REQUIRED",
            "ilova yaxlitligi tokeni kerak (integrity_token)",
        ),
        IntegrityError::Unavailable(_) => {
            let mut err = ApiError::new(
                StatusCode::SERVICE_UNAVAILABLE,
                "INTEGRITY_UNAVAILABLE",
                "yaxlitlik tekshiruvi vaqtincha mavjud emas",
            );
            err.retry_after = Some(2);
            err
        }
        // Sabab mijozga aytilmaydi (hujumchiga yordam bermasin) — faqat logda.
        _ => ApiError::new(
            StatusCode::FORBIDDEN,
            "INTEGRITY_INVALID",
            "ilova yaxlitligi tokeni yaroqsiz",
        ),
    }
}
