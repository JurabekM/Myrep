//! Sandbox yaxlitlik tokenlari (Play Integrity mock'i). **Faqat sandbox.**
//!
//! Token — kompakt JWS (ES256, P-256), mazmuni Play Integrity verdict tuzilmasida
//! ([`TokenPayload`]). Kalit `mpay-server init` da yaratiladi (`sandbox-integrity-mock.key.pem`),
//! server ochiq kalit bilan tekshiradi; tokenni soft-hamyon (shu kalit bilan) yoki emulyatordagi
//! demo ilova (`POST /v1/sandbox/integrity-token`) oladi. Haqiqiy Google tokeni bilan
//! almashtirib bo'lmaydi va aksincha.

use async_trait::async_trait;
use base64::engine::general_purpose::URL_SAFE_NO_PAD as B64;
use base64::Engine as _;
use p256::ecdsa::signature::{Signer, Verifier};
use p256::ecdsa::{Signature, SigningKey, VerifyingKey};
use p256::pkcs8::DecodePrivateKey;
use serde::{Deserialize, Serialize};

use crate::{
    AccountDetails, AppAccessRisk, AppIntegrity, DeviceIntegrity, EnvironmentDetails,
    IntegrityError, IntegrityVerifier, RequestDetails, TokenPayload,
};

/// JWS sarlavhasidagi `kid`.
pub const KID: &str = "mpay-sandbox-integrity-v1";

#[derive(Serialize, Deserialize)]
struct Header {
    alg: String,
    #[serde(default)]
    kid: String,
}

/// Tayyor verdict'lar (sinov stsenariylari).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Preset {
    /// Tanilgan ilova, strong + device + basic, litsenziyali, muhit toza.
    Strong,
    /// Device + basic.
    Device,
    /// Faqat basic (sertifikatlanmagan qurilma).
    Basic,
    /// Hech qanday qurilma yaxlitligi yo'q (root); ilova baholanmagan.
    NoIntegrity,
    /// Ilova tanilmagan (o'zgartirilgan versiya).
    Unrecognized,
    /// Play Protect o'rta xavf.
    PlayProtectRisk,
    /// Ekranni noma'lum ilova boshqaradi.
    RemoteControl,
}

impl Preset {
    pub fn parse(s: &str) -> Option<Self> {
        serde_json::from_value(serde_json::Value::String(s.to_owned())).ok()
    }

    /// Shu stsenariy uchun verdict.
    pub fn payload(self, package: &str, cert: &str, hash: &str, now_ms: i64) -> TokenPayload {
        let device: &[&str] = match self {
            Self::Strong | Self::PlayProtectRisk | Self::RemoteControl => &[
                "MEETS_BASIC_INTEGRITY",
                "MEETS_DEVICE_INTEGRITY",
                "MEETS_STRONG_INTEGRITY",
            ],
            Self::Device | Self::Unrecognized => {
                &["MEETS_BASIC_INTEGRITY", "MEETS_DEVICE_INTEGRITY"]
            }
            Self::Basic => &["MEETS_BASIC_INTEGRITY"],
            Self::NoIntegrity => &[],
        };
        let app = match self {
            Self::Unrecognized => "UNRECOGNIZED_VERSION",
            Self::NoIntegrity => "UNEVALUATED",
            _ => "PLAY_RECOGNIZED",
        };
        let evaluated = app != "UNEVALUATED";
        TokenPayload {
            request_details: RequestDetails {
                request_package_name: package.to_owned(),
                request_hash: Some(hash.to_owned()),
                nonce: None,
                timestamp_millis: now_ms.to_string(),
            },
            app_integrity: AppIntegrity {
                app_recognition_verdict: app.to_owned(),
                package_name: evaluated.then(|| package.to_owned()),
                certificate_sha256_digest: if evaluated {
                    vec![cert.to_owned()]
                } else {
                    Vec::new()
                },
                version_code: evaluated.then(|| "1".to_owned()),
            },
            device_integrity: DeviceIntegrity {
                device_recognition_verdict: device.iter().map(|s| (*s).to_owned()).collect(),
            },
            account_details: AccountDetails {
                app_licensing_verdict: Some(
                    if evaluated { "LICENSED" } else { "UNEVALUATED" }.to_owned(),
                ),
            },
            environment_details: Some(EnvironmentDetails {
                play_protect_verdict: Some(
                    if self == Self::PlayProtectRisk {
                        "MEDIUM_RISK"
                    } else {
                        "NO_ISSUES"
                    }
                    .to_owned(),
                ),
                app_access_risk_verdict: Some(AppAccessRisk {
                    apps_detected: if self == Self::RemoteControl {
                        vec!["KNOWN_INSTALLED".into(), "UNKNOWN_CONTROLLING".into()]
                    } else {
                        vec!["KNOWN_INSTALLED".into()]
                    },
                }),
            }),
        }
    }
}

/// Mock token chiqaruvchi (maxfiy kalit — sandbox holati papkasida).
pub struct MockIssuer {
    sk: SigningKey,
}

impl std::fmt::Debug for MockIssuer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("MockIssuer(..)")
    }
}

impl MockIssuer {
    /// PKCS#8 PEM (`-----BEGIN PRIVATE KEY-----`).
    pub fn from_pkcs8_pem(pem: &str) -> Result<Self, String> {
        SigningKey::from_pkcs8_pem(pem)
            .map(|sk| Self { sk })
            .map_err(|e| format!("integrity mock kaliti: {e}"))
    }

    pub fn verifier(&self) -> MockVerifier {
        MockVerifier {
            vk: *self.sk.verifying_key(),
        }
    }

    /// Ixtiyoriy mazmun uchun token.
    pub fn issue(&self, payload: &TokenPayload) -> String {
        let header = serde_json::to_vec(&Header {
            alg: "ES256".into(),
            kid: KID.into(),
        })
        .unwrap_or_default();
        let body = serde_json::to_vec(payload).unwrap_or_default();
        let signing_input = format!("{}.{}", B64.encode(header), B64.encode(body));
        let sig: Signature = self.sk.sign(signing_input.as_bytes());
        format!("{signing_input}.{}", B64.encode(sig.to_bytes()))
    }

    /// Stsenariy bo'yicha token.
    pub fn issue_preset(
        &self,
        preset: Preset,
        package: &str,
        cert: &str,
        hash: &str,
        now_ms: i64,
    ) -> String {
        self.issue(&preset.payload(package, cert, hash, now_ms))
    }
}

/// Mock token tekshiruvchi (ochiq kalit).
#[derive(Debug, Clone)]
pub struct MockVerifier {
    vk: VerifyingKey,
}

#[async_trait]
impl IntegrityVerifier for MockVerifier {
    fn name(&self) -> &'static str {
        "mock"
    }

    async fn decode(&self, token: &str) -> Result<TokenPayload, IntegrityError> {
        let mut parts = token.split('.');
        let (Some(h), Some(b), Some(s), None) =
            (parts.next(), parts.next(), parts.next(), parts.next())
        else {
            return Err(IntegrityError::Malformed("JWS 3 qismdan iborat emas"));
        };
        let header: Header = B64
            .decode(h)
            .ok()
            .and_then(|v| serde_json::from_slice(&v).ok())
            .ok_or(IntegrityError::Malformed("JWS sarlavhasi"))?;
        // Algoritm qat'iy: `none` yoki boshqa algoritmga tushirish mumkin emas.
        if header.alg != "ES256" || header.kid != KID {
            return Err(IntegrityError::Malformed("JWS algoritmi yoki kid"));
        }
        let sig = B64
            .decode(s)
            .ok()
            .and_then(|v| Signature::from_slice(&v).ok())
            .ok_or(IntegrityError::Malformed("JWS imzosi"))?;
        let signing_input = &token[..h.len() + 1 + b.len()];
        self.vk
            .verify(signing_input.as_bytes(), &sig)
            .map_err(|_| IntegrityError::BadSignature)?;
        let body = B64
            .decode(b)
            .map_err(|_| IntegrityError::Malformed("JWS mazmuni"))?;
        serde_json::from_slice(&body).map_err(|_| IntegrityError::Malformed("verdict JSON"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    pub(crate) fn issuer() -> MockIssuer {
        let kp = rcgen::KeyPair::generate().unwrap();
        MockIssuer::from_pkcs8_pem(&kp.serialize_pem()).unwrap()
    }

    #[tokio::test]
    async fn roundtrip_and_tamper() {
        let i = issuer();
        let v = i.verifier();
        let t = i.issue_preset(Preset::Strong, "uz.mpay.walletdemo", "C", "H", 1);
        let p = v.decode(&t).await.unwrap();
        assert_eq!(p.request_details.request_hash.as_deref(), Some("H"));

        // Mazmun almashtirilsa imzo buziladi.
        let mut parts: Vec<String> = t.split('.').map(str::to_owned).collect();
        let other = i.issue_preset(Preset::Strong, "uz.mpay.walletdemo", "C", "H2", 1);
        parts[1] = other.split('.').nth(1).unwrap().to_owned();
        assert_eq!(
            v.decode(&parts.join(".")).await,
            Err(IntegrityError::BadSignature)
        );
        // Boshqa kalit bilan imzolangan.
        let foreign = issuer().issue_preset(Preset::Strong, "uz.mpay.walletdemo", "C", "H", 1);
        assert_eq!(v.decode(&foreign).await, Err(IntegrityError::BadSignature));
        // alg = none.
        let none = format!(
            "{}.{}.",
            B64.encode(br#"{"alg":"none","kid":"mpay-sandbox-integrity-v1"}"#),
            parts[1]
        );
        assert!(matches!(
            v.decode(&none).await,
            Err(IntegrityError::Malformed(_))
        ));
        assert!(v.decode("a.b").await.is_err());
        assert_eq!(Preset::parse("remote_control"), Some(Preset::RemoteControl));
        assert_eq!(Preset::parse("x"), None);
    }
}
