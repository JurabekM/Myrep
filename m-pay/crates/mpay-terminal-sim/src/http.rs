//! `mpay-server` uchun HTTP client (rustls + ring, ixtiyoriy sandbox TLS ildizi bilan).

use std::sync::Arc;

use mpay_common::api::{ErrorResponse, ServerIdentityDto};
use mpay_pqlink::ServerIdentity;
use reqwest::header::{HeaderValue, AUTHORIZATION, CONTENT_TYPE};
use reqwest::StatusCode;
use serde::de::DeserializeOwned;
use serde::Serialize;

use crate::WalletError;

/// PQ Link tanalari uchun Content-Type.
pub const PQLINK_CONTENT_TYPE: &str = "application/x-mpay-pqlink";

/// Server javobi.
#[derive(Debug)]
pub struct RawResponse {
    pub status: StatusCode,
    pub sealed: bool,
    pub body: Vec<u8>,
}

/// HTTP client.
#[derive(Clone)]
pub struct ServerClient {
    http: reqwest::Client,
    base: String,
}

impl std::fmt::Debug for ServerClient {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "ServerClient({})", self.base)
    }
}

impl ServerClient {
    /// `base` — masalan `http://127.0.0.1:8080`; `tls_root_pem` — sandbox o'z-o'zini imzolagan sertifikati.
    pub fn new(base: &str, tls_root_pem: Option<&[u8]>) -> Result<Self, WalletError> {
        Self::with_identity(base, tls_root_pem, None)
    }

    /// mTLS: `identity` — mijoz sertifikati va kaliti (PEM), operator/terminal uchun.
    pub fn with_identity(
        base: &str,
        tls_root_pem: Option<&[u8]>,
        identity: Option<(&[u8], &[u8])>,
    ) -> Result<Self, WalletError> {
        use rustls::pki_types::pem::PemObject;
        use rustls::pki_types::CertificateDer;
        let mut roots = rustls::RootCertStore::empty();
        if let Some(pem) = tls_root_pem {
            for c in CertificateDer::pem_slice_iter(pem) {
                let c = c.map_err(|e| WalletError::Config(format!("TLS ildizi: {e}")))?;
                roots
                    .add(c)
                    .map_err(|e| WalletError::Config(format!("TLS ildizi: {e}")))?;
            }
        }
        let provider = Arc::new(rustls::crypto::ring::default_provider());
        let tls = rustls::ClientConfig::builder_with_provider(provider)
            .with_safe_default_protocol_versions()
            .map_err(|e| WalletError::Config(e.to_string()))?
            .with_root_certificates(roots);
        let tls = match identity {
            Some((cert_pem, key_pem)) => {
                use rustls::pki_types::PrivateKeyDer;
                let certs = CertificateDer::pem_slice_iter(cert_pem)
                    .collect::<Result<Vec<_>, _>>()
                    .map_err(|e| WalletError::Config(format!("mijoz sertifikati: {e}")))?;
                let key = PrivateKeyDer::from_pem_slice(key_pem)
                    .map_err(|e| WalletError::Config(format!("mijoz kaliti: {e}")))?;
                tls.with_client_auth_cert(certs, key)
                    .map_err(|e| WalletError::Config(format!("mTLS: {e}")))?
            }
            None => tls.with_no_client_auth(),
        };
        let http = reqwest::Client::builder()
            .use_preconfigured_tls(tls)
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .map_err(|e| WalletError::Http(e.to_string()))?;
        Ok(Self {
            http,
            base: base.trim_end_matches('/').to_owned(),
        })
    }

    pub fn base(&self) -> &str {
        &self.base
    }

    /// Server identifikatori. Sandbox'da TOFU; production'da qurilmaga oldindan pinlanadi.
    pub async fn identity(&self) -> Result<(ServerIdentity, String), WalletError> {
        let dto: ServerIdentityDto = self.get_json("/v1/pqlink/identity", None).await?;
        let ed: [u8; 32] = hex::decode(&dto.ed25519)
            .ok()
            .and_then(|v| v.try_into().ok())
            .ok_or(WalletError::Decode("ed25519"))?;
        let ml = hex::decode(&dto.mldsa65).map_err(|_| WalletError::Decode("mldsa65"))?;
        let id = ServerIdentity::new(ed, ml)?;
        if hex::encode(id.fingerprint()) != dto.fingerprint {
            return Err(WalletError::Decode("fingerprint mos emas"));
        }
        Ok((id, dto.fingerprint))
    }

    /// PQ Link tanasini yuboradi.
    pub async fn post_pqlink(&self, path: &str, body: Vec<u8>) -> Result<RawResponse, WalletError> {
        let r = self
            .http
            .post(format!("{}{path}", self.base))
            .header(CONTENT_TYPE, PQLINK_CONTENT_TYPE)
            .body(body)
            .send()
            .await
            .map_err(|e| WalletError::Http(e.to_string()))?;
        let status = r.status();
        let sealed = r
            .headers()
            .get(CONTENT_TYPE)
            .and_then(|v| v.to_str().ok())
            .is_some_and(|v| v.starts_with(PQLINK_CONTENT_TYPE));
        let body = r
            .bytes()
            .await
            .map_err(|e| WalletError::Http(e.to_string()))?
            .to_vec();
        Ok(RawResponse {
            status,
            sealed,
            body,
        })
    }

    fn auth(key: Option<&str>) -> Result<Option<HeaderValue>, WalletError> {
        key.map(|k| {
            HeaderValue::from_str(&format!("Bearer {k}"))
                .map_err(|_| WalletError::Config("API kalit".into()))
        })
        .transpose()
    }

    async fn json_response<T: DeserializeOwned>(r: reqwest::Response) -> Result<T, WalletError> {
        let status = r.status();
        let bytes = r
            .bytes()
            .await
            .map_err(|e| WalletError::Http(e.to_string()))?;
        if status.is_success() {
            return serde_json::from_slice(&bytes).map_err(|_| WalletError::Decode("JSON javob"));
        }
        let err: ErrorResponse =
            serde_json::from_slice(&bytes).map_err(|_| WalletError::Decode("xato JSON"))?;
        Err(WalletError::Api {
            status: status.as_u16(),
            code: err.error.code,
            message: err.error.message,
        })
    }

    /// Ochiq JSON GET (operator/terminal kaliti bilan yoki kalitsiz).
    pub async fn get_json<T: DeserializeOwned>(
        &self,
        path: &str,
        key: Option<&str>,
    ) -> Result<T, WalletError> {
        let mut rb = self.http.get(format!("{}{path}", self.base));
        if let Some(h) = Self::auth(key)? {
            rb = rb.header(AUTHORIZATION, h);
        }
        Self::json_response(
            rb.send()
                .await
                .map_err(|e| WalletError::Http(e.to_string()))?,
        )
        .await
    }

    /// Ochiq JSON POST.
    pub async fn post_json<B: Serialize, T: DeserializeOwned>(
        &self,
        path: &str,
        key: Option<&str>,
        body: &B,
    ) -> Result<T, WalletError> {
        let mut rb = self.http.post(format!("{}{path}", self.base)).json(body);
        if let Some(h) = Self::auth(key)? {
            rb = rb.header(AUTHORIZATION, h);
        }
        Self::json_response(
            rb.send()
                .await
                .map_err(|e| WalletError::Http(e.to_string()))?,
        )
        .await
    }

    /// Ochiq DELETE.
    pub async fn delete_json<T: DeserializeOwned>(
        &self,
        path: &str,
        key: Option<&str>,
    ) -> Result<T, WalletError> {
        let mut rb = self.http.delete(format!("{}{path}", self.base));
        if let Some(h) = Self::auth(key)? {
            rb = rb.header(AUTHORIZATION, h);
        }
        Self::json_response(
            rb.send()
                .await
                .map_err(|e| WalletError::Http(e.to_string()))?,
        )
        .await
    }
}
