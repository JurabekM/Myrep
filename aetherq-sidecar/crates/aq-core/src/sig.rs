//! ML-DSA-65 (FIPS 204) — server va klient identity'si. Python `aether_q_v51/sig.py` bilan bayt-mos.
//! Kontekst (ctx) bo'sh; xabar — protokol transcript digest'i (SHA3-256).

use ml_dsa::{EncodedSignature, EncodedVerifyingKey, Keypair, MlDsa65, Signature, SigningKey, VerifyingKey};

use crate::error::{AqError, Result};

pub const PK_LEN: usize = 1952;
pub const SIG_LEN: usize = 3309;

/// 32 baytli seed'dan imzolash kaliti va ochiq kalit (bayt).
pub fn keypair_from_seed(seed: &[u8; 32]) -> (SigningKey<MlDsa65>, Vec<u8>) {
    let sk = SigningKey::<MlDsa65>::from_seed(&(*seed).into());
    let pk = sk.verifying_key().encode().as_slice().to_vec();
    (sk, pk)
}

/// Deterministik ML-DSA imzo (ctx = bo'sh).
pub fn sign(sk: &SigningKey<MlDsa65>, msg: &[u8]) -> Result<Vec<u8>> {
    let sig = sk
        .expanded_key()
        .sign_deterministic(msg, b"")
        .map_err(|_| AqError::Crypto("ML-DSA imzo"))?;
    Ok(sig.encode().as_slice().to_vec())
}

/// Imzoni tekshirish. Noto'g'ri uzunlik yoki noto'g'ri imzo → `false` (istisno emas).
pub fn verify(pk: &[u8], msg: &[u8], sig: &[u8]) -> bool {
    let Ok(enc_pk) = EncodedVerifyingKey::<MlDsa65>::try_from(pk) else {
        return false;
    };
    let vk = VerifyingKey::<MlDsa65>::decode(&enc_pk);
    let Ok(enc_sig) = EncodedSignature::<MlDsa65>::try_from(sig) else {
        return false;
    };
    let Some(s) = Signature::<MlDsa65>::decode(&enc_sig) else {
        return false;
    };
    vk.verify_with_context(msg, b"", &s)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sign_verify_roundtrip() {
        let (sk, pk) = keypair_from_seed(&[7u8; 32]);
        assert_eq!(pk.len(), PK_LEN);
        let sig = sign(&sk, b"hello").unwrap();
        assert_eq!(sig.len(), SIG_LEN);
        assert!(verify(&pk, b"hello", &sig));
        assert!(!verify(&pk, b"hellO", &sig));
    }
}
