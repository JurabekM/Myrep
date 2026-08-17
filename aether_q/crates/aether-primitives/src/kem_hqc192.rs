//! HQC-192 (NIST Round 4, PARANOID profil) — `pqcrypto-hqc` (PQClean) ustidan wrapper'i.

use crate::{Bytes, Kem, PrimitiveError, Secret};
use pqcrypto_hqc::hqc192::{
    ciphertext_bytes, decapsulate, encapsulate, keypair, public_key_bytes, secret_key_bytes,
    Ciphertext, PublicKey as Hqc192PublicKey, SecretKey as Hqc192SecretKey,
};
use pqcrypto_traits::kem::{Ciphertext as _, PublicKey as _, SecretKey as _, SharedSecret as _};
use zeroize::Zeroizing;

pub struct Hqc192Kem;

impl Kem for Hqc192Kem {
    const NAME: &'static str = "HQC-192";

    fn keypair() -> (Bytes, Secret) {
        let (pk, sk) = keypair();
        (pk.as_bytes().to_vec(), Zeroizing::new(sk.as_bytes().to_vec()))
    }

    fn encapsulate(pk: &[u8]) -> Result<(Bytes, Secret), PrimitiveError> {
        let pk = Hqc192PublicKey::from_bytes(pk).map_err(|_| PrimitiveError::InvalidEncoding)?;
        let (ss, ct) = encapsulate(&pk);
        Ok((ct.as_bytes().to_vec(), Zeroizing::new(ss.as_bytes().to_vec())))
    }

    fn decapsulate(sk: &[u8], ct: &[u8]) -> Result<Secret, PrimitiveError> {
        let sk = Hqc192SecretKey::from_bytes(sk).map_err(|_| PrimitiveError::InvalidEncoding)?;
        let ct = Ciphertext::from_bytes(ct).map_err(|_| PrimitiveError::InvalidEncoding)?;
        let ss = decapsulate(&ct, &sk);
        Ok(Zeroizing::new(ss.as_bytes().to_vec()))
    }
}

#[allow(dead_code)]
fn _size_check() {
    let _ = public_key_bytes();
    let _ = secret_key_bytes();
    let _ = ciphertext_bytes();
}
