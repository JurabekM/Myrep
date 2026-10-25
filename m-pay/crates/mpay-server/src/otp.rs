//! OTP yetkazish kanali (2-faza P2.1, ADR-0016). YELLOW ID&V'da bir martalik kod karta egasining
//! **emitentdagi** telefoniga SMS bilan yuboriladi (qurilmaga emas — ATO'da telefon raqami hujumchiniki
//! bo'lmasligi kerak). Kanal: `sandbox` (yuborilmaydi; faqat operator endpointi) yoki `webhook`
//! (bankning SMS shlyuzi; sinovda — virtual shlyuz `mpay-smsgw`).
//!
//! OTP hech qachon logga yozilmaydi; telefon logda maskalanadi (`+998******12`).

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use zeroize::Zeroizing;

/// `[otp]`.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OtpConfig {
    #[serde(default)]
    pub channel: OtpChannelKind,
    #[serde(default)]
    pub webhook: Option<WebhookConfig>,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum OtpChannelKind {
    /// Yuborilmaydi (sandbox: `GET /v1/sandbox/otp/{id}` operator kaliti bilan).
    #[default]
    Sandbox,
    /// SMS shlyuziga HTTP POST.
    Webhook,
}

/// `[otp.webhook]`: `POST url` `{"to","text","reference"}`, `Authorization: Bearer <token_env qiymati>`.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WebhookConfig {
    pub url: String,
    /// Shlyuz tokeni saqlanadigan muhit o'zgaruvchisi (sir faylda emas).
    #[serde(default)]
    pub token_env: Option<String>,
    #[serde(default = "default_timeout")]
    pub timeout_ms: u64,
    /// Qo'shimcha ishonchli CA (PEM) — ichki shlyuz o'z CA'si bilan bo'lsa.
    #[serde(default)]
    pub ca_file: Option<PathBuf>,
}

fn default_timeout() -> u64 {
    5000
}

pub use mpay_common::phone::mask_phone;

/// SMS matni (o'zbekcha). Kod faqat shu yerda va HTTP tanasida.
fn sms_text(otp: &str, ttl_secs: i64) -> Zeroizing<String> {
    Zeroizing::new(format!(
        "M-Pay: karta qo'shish kodi {otp}. {} daqiqa amal qiladi. Kodni hech kimga aytmang.",
        (ttl_secs / 60).max(1)
    ))
}

/// Yetkazish kanali.
#[derive(Clone)]
pub enum OtpChannel {
    Sandbox,
    Webhook {
        http: reqwest::Client,
        url: String,
        token: Option<Arc<Zeroizing<String>>>,
    },
}

impl std::fmt::Debug for OtpChannel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Sandbox => f.write_str("OtpChannel::Sandbox"),
            Self::Webhook { url, .. } => write!(f, "OtpChannel::Webhook({url})"),
        }
    }
}

impl OtpChannel {
    pub fn from_config(
        cfg: &OtpConfig,
        resolve: impl Fn(&PathBuf) -> PathBuf,
    ) -> Result<Self, String> {
        match cfg.channel {
            OtpChannelKind::Sandbox => Ok(Self::Sandbox),
            OtpChannelKind::Webhook => {
                let w = cfg
                    .webhook
                    .as_ref()
                    .ok_or("otp.channel = webhook uchun [otp.webhook] kerak")?;
                if !(w.url.starts_with("https://") || w.url.starts_with("http://")) {
                    return Err("otp.webhook.url http(s):// bo'lishi kerak".into());
                }
                let token = match &w.token_env {
                    Some(var) => Some(Arc::new(Zeroizing::new(
                        std::env::var(var)
                            .map_err(|_| format!("otp.webhook: {var} muhit o'zgaruvchisi yo'q"))?,
                    ))),
                    None => None,
                };
                Ok(Self::Webhook {
                    http: http_client(w, resolve)?,
                    url: w.url.clone(),
                    token,
                })
            }
        }
    }

    /// Kanal SMS yuboradimi (`sandbox` — yo'q).
    pub fn sends(&self) -> bool {
        matches!(self, Self::Webhook { .. })
    }

    /// OTP'ni telefonga yuboradi. `reference` — challenge_id (shlyuz idempotentligi uchun).
    pub async fn deliver(
        &self,
        phone: &str,
        otp: &str,
        ttl_secs: i64,
        reference: &str,
    ) -> Result<(), String> {
        let Self::Webhook { http, url, token } = self else {
            return Ok(());
        };
        let text = sms_text(otp, ttl_secs);
        let body =
            serde_json::json!({ "to": phone, "text": text.as_str(), "reference": reference });
        let mut last = String::new();
        // Bitta qayta urinish (tarmoq uzilishi); 4xx — qayta urinilmaydi.
        for attempt in 0..2 {
            let mut rb = http.post(url).json(&body);
            if let Some(t) = token {
                rb = rb.bearer_auth(t.as_str());
            }
            match rb.send().await {
                Ok(r) if r.status().is_success() => {
                    tracing::info!(to = %mask_phone(phone), reference, "otp: SMS yuborildi");
                    return Ok(());
                }
                Ok(r) if r.status().is_client_error() => {
                    return Err(format!("SMS shlyuzi rad etdi: {}", r.status()));
                }
                Ok(r) => last = format!("SMS shlyuzi: {}", r.status()),
                Err(e) => last = format!("SMS shlyuzi: {}", e.without_url()),
            }
            if attempt == 0 {
                tokio::time::sleep(Duration::from_millis(300)).await;
            }
        }
        Err(last)
    }
}

fn http_client(
    w: &WebhookConfig,
    resolve: impl Fn(&PathBuf) -> PathBuf,
) -> Result<reqwest::Client, String> {
    use rustls::pki_types::pem::PemObject;
    use rustls::pki_types::CertificateDer;
    let mut roots = rustls::RootCertStore::empty();
    for c in rustls_native_certs::load_native_certs().certs {
        let _ = roots.add(c);
    }
    if let Some(ca) = &w.ca_file {
        let p = resolve(ca);
        for c in CertificateDer::pem_file_iter(&p).map_err(|e| format!("{}: {e}", p.display()))? {
            roots
                .add(c.map_err(|e| format!("{}: {e}", p.display()))?)
                .map_err(|e| format!("{}: {e}", p.display()))?;
        }
    }
    let provider = Arc::new(rustls::crypto::ring::default_provider());
    let tls = rustls::ClientConfig::builder_with_provider(provider)
        .with_safe_default_protocol_versions()
        .map_err(|e| e.to_string())?
        .with_root_certificates(roots)
        .with_no_client_auth();
    reqwest::Client::builder()
        .use_preconfigured_tls(tls)
        .timeout(Duration::from_millis(w.timeout_ms))
        .build()
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sms_text_has_code_and_minutes() {
        let t = sms_text("123456", 300);
        assert!(t.contains("123456") && t.contains("5 daqiqa"));
    }

    #[test]
    fn webhook_needs_config_and_token_env() {
        let cfg = OtpConfig {
            channel: OtpChannelKind::Webhook,
            webhook: None,
        };
        assert!(OtpChannel::from_config(&cfg, |p| p.clone()).is_err());
        let cfg = OtpConfig {
            channel: OtpChannelKind::Webhook,
            webhook: Some(WebhookConfig {
                url: "http://127.0.0.1:1/send".into(),
                token_env: Some("MPAY_TEST_SMS_TOKEN_YOQ".into()),
                timeout_ms: 100,
                ca_file: None,
            }),
        };
        assert!(OtpChannel::from_config(&cfg, |p| p.clone())
            .unwrap_err()
            .contains("MPAY_TEST_SMS_TOKEN_YOQ"));
    }
}
