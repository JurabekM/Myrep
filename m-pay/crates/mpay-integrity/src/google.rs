//! Google Play Integrity — server tomonida dekodlash (`decodeIntegrityToken`).
//!
//! `POST {base}/v1/{paket}:decodeIntegrityToken`, tana `{"integrityToken": "…"}`, javob
//! `{"tokenPayloadExternal": {…}}`; `Authorization: Bearer <OAuth2 access token>`
//! (`https://www.googleapis.com/auth/playintegrity` scope'i bilan xizmat akkaunti).
//!
//! `TODO(spec):` access token olish (xizmat akkaunti JWT → token almashuvi) bu crate'da yo'q —
//! token tashqaridan beriladi ([`AccessToken`]: muhit o'zgaruvchisi yoki fayl, masalan
//! sidecar/workload identity yangilab turadi). Haqiqiy Google bilan sinalmagan; testlar shu
//! protokol shaklidagi emulyatorga qarshi.

use std::path::PathBuf;

use async_trait::async_trait;
use serde::Deserialize;
use zeroize::Zeroizing;

use crate::{IntegrityError, IntegrityVerifier, TokenPayload};

/// Standart manzil.
pub const DEFAULT_BASE: &str = "https://playintegrity.googleapis.com";

/// OAuth2 access token manbai (har so'rovda o'qiladi — tashqi jarayon yangilashi mumkin).
#[derive(Debug, Clone)]
pub enum AccessToken {
    Env(String),
    File(PathBuf),
}

impl AccessToken {
    fn read(&self) -> Result<Zeroizing<String>, IntegrityError> {
        let v = match self {
            Self::Env(var) => std::env::var(var)
                .map_err(|_| IntegrityError::Unavailable(format!("{var} yo'q")))?,
            Self::File(p) => std::fs::read_to_string(p)
                .map_err(|e| IntegrityError::Unavailable(format!("{}: {e}", p.display())))?,
        };
        Ok(Zeroizing::new(v.trim().to_owned()))
    }
}

/// Google dekodlash mijozi.
pub struct GoogleDecoder {
    http: reqwest::Client,
    url: String,
    token: AccessToken,
}

impl std::fmt::Debug for GoogleDecoder {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("GoogleDecoder")
            .field("url", &self.url)
            .finish_non_exhaustive()
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct DecodeResponse {
    token_payload_external: TokenPayload,
}

impl GoogleDecoder {
    /// `http` — TLS sozlangan mijoz (timeout bilan); `base` — odatda [`DEFAULT_BASE`].
    pub fn new(http: reqwest::Client, base: &str, package: &str, token: AccessToken) -> Self {
        Self {
            http,
            url: format!(
                "{}/v1/{package}:decodeIntegrityToken",
                base.trim_end_matches('/')
            ),
            token,
        }
    }
}

#[async_trait]
impl IntegrityVerifier for GoogleDecoder {
    fn name(&self) -> &'static str {
        "google"
    }

    async fn decode(&self, token: &str) -> Result<TokenPayload, IntegrityError> {
        let bearer = self.token.read()?;
        let resp = self
            .http
            .post(&self.url)
            .bearer_auth(bearer.as_str())
            .json(&serde_json::json!({ "integrityToken": token }))
            .send()
            .await
            .map_err(|e| IntegrityError::Unavailable(e.without_url().to_string()))?;
        let status = resp.status();
        if status.is_client_error() && status != reqwest::StatusCode::TOO_MANY_REQUESTS {
            // 400 — token yaroqsiz (shifr/imzo); 401/403 — bizning hisob ma'lumotlarimiz.
            if status == reqwest::StatusCode::BAD_REQUEST {
                return Err(IntegrityError::BadSignature);
            }
            return Err(IntegrityError::Unavailable(format!(
                "Google: HTTP {status}"
            )));
        }
        if !status.is_success() {
            return Err(IntegrityError::Unavailable(format!(
                "Google: HTTP {status}"
            )));
        }
        resp.json::<DecodeResponse>()
            .await
            .map(|r| r.token_payload_external)
            .map_err(|_| IntegrityError::Malformed("decodeIntegrityToken javobi"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::extract::Path;
    use axum::http::{HeaderMap, StatusCode};
    use axum::routing::post;
    use axum::Json;

    fn client() -> reqwest::Client {
        let provider = std::sync::Arc::new(rustls::crypto::ring::default_provider());
        let tls = rustls::ClientConfig::builder_with_provider(provider)
            .with_safe_default_protocol_versions()
            .unwrap()
            .with_root_certificates(rustls::RootCertStore::empty())
            .with_no_client_auth();
        reqwest::Client::builder()
            .use_preconfigured_tls(tls)
            .build()
            .unwrap()
    }

    /// Google `decodeIntegrityToken` emulyatori: `good` → verdict, `bad` → 400.
    async fn emulator() -> String {
        let app = axum::Router::new().route(
            "/v1/{call}",
            post(
                |Path(call): Path<String>, h: HeaderMap, Json(b): Json<serde_json::Value>| async move {
                    if h.get("authorization").and_then(|v| v.to_str().ok())
                        != Some("Bearer at-123")
                    {
                        return (StatusCode::UNAUTHORIZED, Json(serde_json::json!({})));
                    }
                    assert_eq!(call, "uz.mpay.walletdemo:decodeIntegrityToken");
                    if b["integrityToken"] != "good" {
                        return (StatusCode::BAD_REQUEST, Json(serde_json::json!({})));
                    }
                    let p = crate::mock::Preset::Device.payload("uz.mpay.walletdemo", "C", "H", 5);
                    (
                        StatusCode::OK,
                        Json(serde_json::json!({ "tokenPayloadExternal": p })),
                    )
                },
            ),
        );
        let l = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let a = l.local_addr().unwrap();
        tokio::spawn(async move { axum::serve(l, app).await.unwrap() });
        format!("http://{a}")
    }

    #[tokio::test]
    async fn decode_via_emulator() {
        let base = emulator().await;
        std::env::set_var("MPAY_TEST_PI_TOKEN", "at-123");
        let d = GoogleDecoder::new(
            client(),
            &base,
            "uz.mpay.walletdemo",
            AccessToken::Env("MPAY_TEST_PI_TOKEN".into()),
        );
        let p = d.decode("good").await.unwrap();
        assert_eq!(
            p.device_integrity.device_recognition_verdict,
            ["MEETS_BASIC_INTEGRITY", "MEETS_DEVICE_INTEGRITY"]
        );
        assert_eq!(d.decode("bad").await, Err(IntegrityError::BadSignature));
        let wrong = GoogleDecoder::new(
            client(),
            &base,
            "uz.mpay.walletdemo",
            AccessToken::Env("MPAY_TEST_PI_NO_SUCH".into()),
        );
        assert!(matches!(
            wrong.decode("good").await,
            Err(IntegrityError::Unavailable(_))
        ));
    }
}
