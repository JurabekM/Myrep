//! Tuzlangan payload majburiyati (spec §5).
//!
//! Jurnalga buyruq matni yoki fayl mazmuni emas, faqat `H("TAMGA-PAYLOAD-v1" || 0x00 || salt || payload)`
//! yoziladi. Tuz va payload shifrlangan vault'da turadi; vault yozuvi o'chirilsa payload qaytarib
//! bo'lmaydi, jurnal esa baribir tekshiriladi.

use serde_json::{Value, json};

use crate::digest::Digest;

pub const DOMAIN: &[u8] = b"TAMGA-PAYLOAD-v1\0";
pub const SALT_LEN: usize = 32;

pub fn commit(salt: &[u8; SALT_LEN], payload: &[u8]) -> Digest {
    Digest::of(&[DOMAIN, salt, payload])
}

/// Yozuvga qo'yiladigan payload-ref obyekti.
pub fn reference(salt: &[u8; SALT_LEN], payload: &[u8], vault: Option<&str>) -> Value {
    let mut v = json!({
        "digest": commit(salt, payload).to_string(),
        "size": payload.len() as u64,
    });
    if let Some(id) = vault {
        v["vault"] = Value::String(id.to_owned());
    }
    v
}

/// Vault'dan tiklangan tuz va payload jurnaldagi majburiyatga mosligini tekshiradi.
pub fn opens(reference: &Value, salt: &[u8; SALT_LEN], payload: &[u8]) -> bool {
    let digest_ok = reference
        .get("digest")
        .and_then(Value::as_str)
        .and_then(Digest::parse)
        .is_some_and(|d| d == commit(salt, payload));
    let size_ok = reference.get("size").and_then(Value::as_u64) == Some(payload.len() as u64);
    digest_ok && size_ok
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn salt_hides_and_binds() {
        let a = [1u8; 32];
        let b = [2u8; 32];
        assert_ne!(
            commit(&a, b"rm -rf /"),
            commit(&b, b"rm -rf /"),
            "tuz natijani o'zgartiradi"
        );
        let r = reference(&a, b"rm -rf /", Some("v1"));
        assert!(opens(&r, &a, b"rm -rf /"));
        assert!(!opens(&r, &a, b"rm -rf ."));
        assert!(!opens(&r, &b, b"rm -rf /"));
        assert_eq!(r["size"], 8);
    }
}
