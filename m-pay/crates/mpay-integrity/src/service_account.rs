//! Google xizmat akkaunti → OAuth2 access token (JWT bearer, RFC 7523) — `decodeIntegrityToken` uchun.
//!
//! Xizmat akkaunti JSON kaliti (`type = "service_account"`, `client_email`, `private_key` — PKCS#8
//! PEM RSA, `token_uri`) dan RS256 bilan imzolangan JWT (`iss`, `scope`, `aud = token_uri`, `iat`,
//! `exp`) tuziladi va `token_uri` ga `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer` bilan
//! almashtiriladi. Access token xotirada keshlanadi va muddati tugashidan 60 s oldin yangilanadi.
//!
//! Imzo — `ring` (doimiy vaqtli RSA; `rsa` crate'idagi Marvin vaqt yon kanali ta'sir qilmaydi).
//! Kalit, JWT va access token logga yozilmaydi.
//! `TODO(spec):` haqiqiy Google bilan sinalmagan — testlar protokol shaklidagi emulyatorga qarshi;
//! production'da kalit faylisiz Workload Identity / metadata server afzal (bank infratuzilmasiga ko'ra).

use std::time::{Duration, Instant};

use base64::engine::general_purpose::{STANDARD, URL_SAFE_NO_PAD as B64};
use base64::Engine as _;
use ring::rand::SystemRandom;
use ring::signature::{RsaKeyPair, RSA_PKCS1_SHA256};
use serde::Deserialize;
use zeroize::Zeroizing;

use crate::IntegrityError;

/// Play Integrity API scope'i.
pub const SCOPE: &str = "https://www.googleapis.com/auth/playintegrity";
const GRANT: &str = "urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer";
/// JWT umri (Google ruxsat bergan eng ko'pi — 1 soat).
const JWT_TTL: u64 = 3600;
/// Muddatidan shuncha oldin yangilanadi.
const REFRESH_MARGIN: Duration = Duration::from_secs(60);

#[derive(Deserialize)]
struct KeyFile {
    #[serde(rename = "type")]
    kind: String,
    client_email: String,
    private_key: Zeroizing<String>,
    token_uri: String,
}

#[derive(Deserialize)]
struct TokenResponse {
    access_token: Zeroizing<String>,
    #[serde(default)]
    expires_in: u64,
}

/// Xizmat akkaunti va keshlangan access token.
pub struct ServiceAccount {
    client_email: String,
    token_uri: String,
    key: RsaKeyPair,
    rng: SystemRandom,
    cache: tokio::sync::Mutex<Option<(Zeroizing<String>, Instant)>>,
}

impl std::fmt::Debug for ServiceAccount {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ServiceAccount")
            .field("client_email", &self.client_email)
            .field("token_uri", &self.token_uri)
            .finish_non_exhaustive()
    }
}

impl ServiceAccount {
    /// Google kalit fayli (JSON) mazmunidan. `token_uri` https bo'lishi shart (loopback `http` —
    /// faqat sinov).
    pub fn from_json(json: &str) -> Result<Self, String> {
        let k: KeyFile =
            serde_json::from_str(json).map_err(|_| "xizmat akkaunti JSON formati".to_owned())?;
        if k.kind != "service_account" {
            return Err("type = service_account kutilgan".into());
        }
        let loopback = k.token_uri.starts_with("http://127.0.0.1:")
            || k.token_uri.starts_with("http://localhost:");
        if !k.token_uri.starts_with("https://") && !loopback {
            return Err("token_uri https:// bo'lishi kerak".into());
        }
        let der = Zeroizing::new(pem_pkcs8(&k.private_key)?);
        let key = RsaKeyPair::from_pkcs8(&der)
            .map_err(|_| "private_key: PKCS#8 RSA (≥ 2048 bit) kutilgan".to_owned())?;
        Ok(Self {
            client_email: k.client_email,
            token_uri: k.token_uri,
            key,
            rng: SystemRandom::new(),
            cache: tokio::sync::Mutex::new(None),
        })
    }

    /// Imzolangan JWT (`now` — unix soniya).
    pub fn assertion(&self, now: u64) -> Result<Zeroizing<String>, IntegrityError> {
        let header = B64.encode(br#"{"alg":"RS256","typ":"JWT"}"#);
        let claims = serde_json::json!({
            "iss": self.client_email,
            "scope": SCOPE,
            "aud": self.token_uri,
            "iat": now,
            "exp": now + JWT_TTL,
        });
        let input = format!("{header}.{}", B64.encode(claims.to_string()));
        let mut sig = vec![0u8; self.key.public().modulus_len()];
        self.key
            .sign(&RSA_PKCS1_SHA256, &self.rng, input.as_bytes(), &mut sig)
            .map_err(|_| IntegrityError::Unavailable("JWT imzolanmadi".into()))?;
        Ok(Zeroizing::new(format!("{input}.{}", B64.encode(sig))))
    }

    /// Amaldagi access token (keshdan yoki `token_uri` dan yangisi).
    pub async fn token(&self, http: &reqwest::Client) -> Result<Zeroizing<String>, IntegrityError> {
        // Bitta qulf: muddati tugaganda bir vaqtda ko'p so'rov bitta almashuvga aylanadi.
        let mut cache = self.cache.lock().await;
        if let Some((t, until)) = cache.as_ref() {
            if Instant::now() < *until {
                return Ok(t.clone());
            }
        }
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        let jwt = self.assertion(now)?;
        let body = Zeroizing::new(format!("grant_type={GRANT}&assertion={}", jwt.as_str()));
        let resp = http
            .post(&self.token_uri)
            .header(
                reqwest::header::CONTENT_TYPE,
                "application/x-www-form-urlencoded",
            )
            .body(body.as_str().to_owned())
            .send()
            .await
            .map_err(|e| IntegrityError::Unavailable(e.without_url().to_string()))?;
        if !resp.status().is_success() {
            // Javob tanasi (xato sababi) logga ham, xabarga ham qo'yilmaydi.
            return Err(IntegrityError::Unavailable(format!(
                "OAuth token: HTTP {}",
                resp.status()
            )));
        }
        let t: TokenResponse = resp
            .json()
            .await
            .map_err(|_| IntegrityError::Unavailable("OAuth token javobi".into()))?;
        let ttl = Duration::from_secs(t.expires_in.max(60));
        let until = Instant::now() + ttl.saturating_sub(REFRESH_MARGIN);
        *cache = Some((t.access_token.clone(), until));
        Ok(t.access_token)
    }
}

/// `-----BEGIN PRIVATE KEY-----` PEM → DER.
fn pem_pkcs8(pem: &str) -> Result<Vec<u8>, String> {
    let body: String = pem
        .lines()
        .map(str::trim)
        .skip_while(|l| *l != "-----BEGIN PRIVATE KEY-----")
        .skip(1)
        .take_while(|l| *l != "-----END PRIVATE KEY-----")
        .collect();
    if body.is_empty() {
        return Err("private_key: PKCS#8 PEM kutilgan".into());
    }
    STANDARD
        .decode(body)
        .map_err(|_| "private_key: base64".to_owned())
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use rsa::pkcs1::EncodeRsaPublicKey;
    use rsa::pkcs8::EncodePrivateKey;

    /// Sinov kaliti (har ishga tushishda yangi, repoga tushmaydi): (PKCS#8 PEM, RSAPublicKey DER).
    pub(crate) fn test_key() -> (String, Vec<u8>) {
        let mut rng = rand_core06::OsRng;
        let k = rsa::RsaPrivateKey::new(&mut rng, 2048).unwrap();
        let pem = k
            .to_pkcs8_pem(rsa::pkcs8::LineEnding::LF)
            .unwrap()
            .to_string();
        let public = k
            .to_public_key()
            .to_pkcs1_der()
            .unwrap()
            .as_bytes()
            .to_vec();
        (pem, public)
    }

    pub(crate) fn key_json(pem: &str, token_uri: &str) -> String {
        serde_json::json!({
            "type": "service_account",
            "client_email": "mpay-integrity@sandbox.iam.gserviceaccount.com",
            "private_key": pem,
            "token_uri": token_uri,
        })
        .to_string()
    }

    #[test]
    fn jwt_is_signed_rs256_with_claims() {
        let (pem, public) = test_key();
        let sa =
            ServiceAccount::from_json(&key_json(&pem, "https://oauth2.example/token")).unwrap();
        let jwt = sa.assertion(1_800_000_000).unwrap();
        let parts: Vec<&str> = jwt.split('.').collect();
        assert_eq!(parts.len(), 3);
        let pk = ring::signature::UnparsedPublicKey::new(
            &ring::signature::RSA_PKCS1_2048_8192_SHA256,
            &public,
        );
        pk.verify(
            format!("{}.{}", parts[0], parts[1]).as_bytes(),
            &B64.decode(parts[2]).unwrap(),
        )
        .expect("RS256 imzo");
        let c: serde_json::Value = serde_json::from_slice(&B64.decode(parts[1]).unwrap()).unwrap();
        assert_eq!(c["scope"], SCOPE);
        assert_eq!(c["aud"], "https://oauth2.example/token");
        assert_eq!(c["exp"], 1_800_000_000u64 + 3600);
        // Debug'da kalit yo'q.
        assert!(!format!("{sa:?}").contains("PRIVATE"));
    }

    #[test]
    fn rejects_bad_files() {
        let (pem, _) = test_key();
        assert!(ServiceAccount::from_json(&key_json(&pem, "http://evil.example/token")).is_err());
        assert!(ServiceAccount::from_json(&key_json("yo'q", "https://o/token")).is_err());
        assert!(ServiceAccount::from_json(r#"{"type":"authorized_user"}"#).is_err());
        let mut v: serde_json::Value =
            serde_json::from_str(&key_json(&pem, "https://o/token")).unwrap();
        v["type"] = "user".into();
        assert!(ServiceAccount::from_json(&v.to_string()).is_err());
    }
}
