//! Bearer API kalitlari (operator, terminal). Konfiguratsiyada faqat `SHA-256(kalit)` saqlanadi;
//! solishtirish constant-time va barcha kalitlar bo'ylab (qaysi biri mos kelganini vaqt oshkor qilmaydi).

use axum::http::HeaderMap;
use mpay_crypto::ct_eq;
use sha2::{Digest, Sha256};

use crate::config::{ApiKey, Role};
use crate::error::ApiError;

/// Autentifikatsiyadan o'tgan chaqiruvchi.
#[derive(Debug, Clone)]
pub struct Caller {
    pub id: String,
    pub role: Role,
}

impl Caller {
    /// Audit uchun aktor nomi.
    pub fn actor(&self) -> String {
        let r = match self.role {
            Role::Operator => "operator",
            Role::Terminal => "terminal",
        };
        format!("{r}:{}", self.id)
    }
}

/// Kalitlar ro'yxati.
#[derive(Debug, Clone, Default)]
pub struct Authenticator {
    keys: Vec<(ApiKey, [u8; 32])>,
}

impl Authenticator {
    pub fn new(keys: &[ApiKey]) -> Self {
        let keys = keys
            .iter()
            .filter_map(|k| {
                let mut h = [0u8; 32];
                hex::decode_to_slice(&k.sha256, &mut h).ok()?;
                Some((k.clone(), h))
            })
            .collect();
        Self { keys }
    }

    /// `Authorization: Bearer ...` ni tekshiradi va talab qilingan rolni tasdiqlaydi.
    pub fn authorize(&self, headers: &HeaderMap, role: Role) -> Result<Caller, ApiError> {
        let token = headers
            .get(axum::http::header::AUTHORIZATION)
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.strip_prefix("Bearer "))
            .ok_or_else(ApiError::unauthorized)?;
        let digest: [u8; 32] = Sha256::digest(token.as_bytes()).into();
        let mut found: Option<&ApiKey> = None;
        for (k, h) in &self.keys {
            if ct_eq(h, &digest) {
                found = Some(k);
            }
        }
        let k = found.ok_or_else(ApiError::unauthorized)?;
        if k.role != role {
            return Err(ApiError::forbidden());
        }
        Ok(Caller {
            id: k.id.clone(),
            role: k.role,
        })
    }
}

/// Kalit uchun konfiguratsiyaga yoziladigan xesh.
pub fn hash_key(key: &str) -> String {
    hex::encode(Sha256::digest(key.as_bytes()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::HeaderValue;

    #[test]
    fn roles_enforced() {
        let a = Authenticator::new(&[
            ApiKey {
                id: "op".into(),
                role: Role::Operator,
                sha256: hash_key("secret-op"),
            },
            ApiKey {
                id: "t1".into(),
                role: Role::Terminal,
                sha256: hash_key("secret-t1"),
            },
        ]);
        let mut h = HeaderMap::new();
        assert!(a.authorize(&h, Role::Operator).is_err());
        h.insert(
            "authorization",
            HeaderValue::from_static("Bearer secret-op"),
        );
        assert_eq!(
            a.authorize(&h, Role::Operator).unwrap().actor(),
            "operator:op"
        );
        assert_eq!(
            a.authorize(&h, Role::Terminal).unwrap_err().code,
            "FORBIDDEN"
        );
        h.insert("authorization", HeaderValue::from_static("Bearer wrong"));
        assert_eq!(
            a.authorize(&h, Role::Operator).unwrap_err().code,
            "UNAUTHORIZED"
        );
    }
}
