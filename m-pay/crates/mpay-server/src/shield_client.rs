//! Shield roliga murojaat (2-faza P2.4, ADR-0019): ko'p instansiyada belgilar ombori yagona Shield
//! instansiyasida — hamma API instansiyalari bir xil tezlik/grafik belgilarini ko'radi.
//!
//! Shield javob bermasa (tarmoq, timeout, 5xx) — shu instansiyaning mahalliy dvigateli (zaxira):
//! qaror chiqadi, lekin belgilar faqat shu instansiya hodisalaridan, sababga `SHIELD_DEGRADED`
//! qo'shiladi va ogohlantirish logga yoziladi. Ochiq PAN yuborilmaydi (`mpay_shield::remote`).
//!
//! Bir nechta Shield instansiyasi (`standby_urls`, ADR-0026): so'rov avval oxirgi javob bergan
//! instansiyaga, xato yoki `503 SHIELD_STANDBY` bo'lsa — navbatdagisiga; hammasi javob bermasa —
//! mahalliy zaxira.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

use async_trait::async_trait;
use mpay_common::ports::{
    IdvAssessment, IdvDecider, IdvRequest, PortError, RiskAssessment, RiskRequest, RiskScorer,
};
use mpay_shield::remote::{IdvEventDto, RekeyEventDto, RekeyResult, TxnEventDto};
use mpay_shield::Shield;
use zeroize::Zeroizing;

use crate::config::ShieldRemoteConfig;

/// Zaxira rejimidagi qaror sababi.
pub const DEGRADED: &str = "SHIELD_DEGRADED";

/// Masofaviy Shield + mahalliy zaxira.
pub struct RemoteShield {
    http: reqwest::Client,
    /// Asosiy va zaxira instansiyalar.
    bases: Vec<String>,
    /// Oxirgi javob bergan instansiya.
    preferred: AtomicUsize,
    key: Option<Zeroizing<String>>,
    local: Arc<Shield>,
}

impl std::fmt::Debug for RemoteShield {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "RemoteShield({:?})", self.bases)
    }
}

impl RemoteShield {
    pub fn new(
        rc: &ShieldRemoteConfig,
        resolve: impl Fn(&Path) -> PathBuf,
        local: Arc<Shield>,
    ) -> Result<Self, String> {
        let bases: Vec<String> = std::iter::once(&rc.url)
            .chain(&rc.standby_urls)
            .map(|u| u.trim_end_matches('/').to_owned())
            .collect();
        if let Some(bad) = bases
            .iter()
            .find(|b| !(b.starts_with("https://") || crate::otp::is_loopback_http(b)))
        {
            return Err(format!(
                "shield.remote: {bad} — https:// (http:// faqat loopback)"
            ));
        }
        let any_https = bases.iter().any(|b| b.starts_with("https://"));
        let key = match (&rc.key, &rc.key_env) {
            (Some(k), _) => Some(Zeroizing::new(k.clone())),
            (None, Some(var)) => {
                Some(Zeroizing::new(std::env::var(var).map_err(|_| {
                    format!("shield.remote: {var} muhit o'zgaruvchisi yo'q")
                })?))
            }
            (None, None) => None,
        };
        let mut b = reqwest::Client::builder()
            .timeout(Duration::from_millis(rc.timeout_ms.max(10)))
            .connect_timeout(Duration::from_millis((rc.timeout_ms / 2).clamp(10, 1000)))
            .pool_max_idle_per_host(64);
        // reqwest `rustls-no-provider`: TLS konfiguratsiyasi har doim aniq beriladi; loopback `http://`
        // da ildizlarsiz (hech qanday TLS ulanishga ishonmaydi).
        b = b.use_preconfigured_tls(if any_https {
            tls_config(rc, &resolve)?
        } else {
            rustls::ClientConfig::builder_with_provider(Arc::new(
                rustls::crypto::ring::default_provider(),
            ))
            .with_safe_default_protocol_versions()
            .map_err(|e| e.to_string())?
            .with_root_certificates(rustls::RootCertStore::empty())
            .with_no_client_auth()
        });
        Ok(Self {
            http: b.build().map_err(|e| e.to_string())?,
            bases,
            preferred: AtomicUsize::new(0),
            key,
            local,
        })
    }

    async fn post_one<B: serde::Serialize, T: serde::de::DeserializeOwned>(
        &self,
        base: &str,
        path: &str,
        body: &B,
    ) -> Result<T, String> {
        let mut rb = self.http.post(format!("{base}{path}")).json(body);
        if let Some(k) = &self.key {
            rb = rb.bearer_auth(k.as_str());
        }
        let r = rb.send().await.map_err(|e| e.without_url().to_string())?;
        if !r.status().is_success() {
            return Err(format!("Shield: {}", r.status()));
        }
        r.json::<T>().await.map_err(|e| e.without_url().to_string())
    }

    /// Instansiyalarni oxirgi muvaffaqiyatlisidan boshlab navbat bilan sinaydi.
    async fn post<B: serde::Serialize, T: serde::de::DeserializeOwned>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T, String> {
        let n = self.bases.len();
        let start = self.preferred.load(Ordering::Relaxed) % n;
        let mut errors = Vec::new();
        for i in 0..n {
            let idx = (start + i) % n;
            match self.post_one(&self.bases[idx], path, body).await {
                Ok(v) => {
                    if idx != start {
                        self.preferred.store(idx, Ordering::Relaxed);
                        tracing::warn!(shield = %self.bases[idx], "Shield: boshqa instansiyaga o'tildi");
                    }
                    return Ok(v);
                }
                Err(e) => errors.push(format!("{}: {e}", self.bases[idx])),
            }
        }
        Err(errors.join("; "))
    }
}

/// Ichki CA'ga pinlangan TLS (tizim ildizlari ishlatilmaydi) va ixtiyoriy mTLS identifikatori.
fn tls_config(
    rc: &ShieldRemoteConfig,
    resolve: &impl Fn(&Path) -> PathBuf,
) -> Result<rustls::ClientConfig, String> {
    use rustls::pki_types::pem::PemObject;
    use rustls::pki_types::{CertificateDer, PrivateKeyDer};
    let ca = rc
        .ca_file
        .as_ref()
        .ok_or("shield.remote: https uchun ca_file kerak (ichki CA)")?;
    let p = resolve(ca);
    let mut roots = rustls::RootCertStore::empty();
    for c in CertificateDer::pem_file_iter(&p).map_err(|e| format!("{}: {e}", p.display()))? {
        roots
            .add(c.map_err(|e| format!("{}: {e}", p.display()))?)
            .map_err(|e| format!("{}: {e}", p.display()))?;
    }
    let provider = Arc::new(rustls::crypto::ring::default_provider());
    let builder = rustls::ClientConfig::builder_with_provider(provider)
        .with_safe_default_protocol_versions()
        .map_err(|e| e.to_string())?
        .with_root_certificates(roots);
    match (&rc.client_cert, &rc.client_key) {
        (Some(c), Some(k)) => {
            let (c, k) = (resolve(c), resolve(k));
            let chain = CertificateDer::pem_file_iter(&c)
                .map_err(|e| format!("{}: {e}", c.display()))?
                .collect::<Result<Vec<_>, _>>()
                .map_err(|e| format!("{}: {e}", c.display()))?;
            let key =
                PrivateKeyDer::from_pem_file(&k).map_err(|e| format!("{}: {e}", k.display()))?;
            builder
                .with_client_auth_cert(chain, key)
                .map_err(|e| e.to_string())
        }
        (None, None) => Ok(builder.with_no_client_auth()),
        _ => Err("shield.remote: client_cert va client_key birga".into()),
    }
}

#[async_trait]
impl IdvDecider for RemoteShield {
    async fn decide(&self, req: &IdvRequest) -> Result<IdvAssessment, PortError> {
        match self
            .post::<_, IdvAssessment>("/internal/shield/idv", &IdvEventDto::from_request(req))
            .await
        {
            Ok(a) => Ok(a),
            Err(e) => {
                tracing::warn!(error = %e, "Shield roli javob bermadi — ID&V mahalliy zaxirada");
                let mut a = self.local.decide(req).await?;
                a.reasons.push(DEGRADED.into());
                crate::metrics::shield_degraded();
                Ok(a)
            }
        }
    }

    async fn device_rekeyed(
        &self,
        old: &mpay_common::DeviceId,
        new: &mpay_common::DeviceId,
        at: time::OffsetDateTime,
    ) -> Result<(), PortError> {
        // Mahalliy zaxira ombori ham bog'lanadi — Shield roli yiqilganda ham izchil.
        self.local.link_rekeyed_device(old.0, new.0);
        let dto = RekeyEventDto {
            at: at.unix_timestamp(),
            old: old.to_hex(),
            new: new.to_hex(),
        };
        match self
            .post::<_, RekeyResult>("/internal/shield/rekey", &dto)
            .await
        {
            Ok(r) => {
                tracing::info!(old = %old, new = %new, linked = r.linked, "Shield: qurilma kaliti almashtirildi");
                Ok(())
            }
            Err(e) => {
                // Hodisa yo'qolsa xavfsiz tomonga: yangi qurilma "yosh" ko'rinadi (ortiqcha step-up).
                tracing::warn!(error = %e, "Shield roli javob bermadi — rekey hodisasi yetkazilmadi");
                crate::metrics::shield_degraded();
                Err(PortError::Unavailable(e))
            }
        }
    }
}

#[async_trait]
impl RiskScorer for RemoteShield {
    async fn score(&self, req: &RiskRequest) -> Result<RiskAssessment, PortError> {
        match self
            .post::<_, RiskAssessment>("/internal/shield/txn", &TxnEventDto::from_request(req))
            .await
        {
            Ok(a) => Ok(a),
            Err(e) => {
                tracing::warn!(error = %e, "Shield roli javob bermadi — risk mahalliy zaxirada");
                let mut a = self.local.score(req).await?;
                a.reasons.push(DEGRADED.into());
                crate::metrics::shield_degraded();
                Ok(a)
            }
        }
    }
}
