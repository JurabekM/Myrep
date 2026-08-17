//! X25519 (RFC 7748) — klassik ECDH, "DH-as-KEM" transformatsiyasi orqali
//! `Kem` interfeysiga moslashtirilgan: ephemeral public key `ct_X` sifatida
//! uzatiladi, shared secret esa DH natijasidir.

use crate::{Bytes, Kem, PrimitiveError, Secret};
use x25519_dalek::{EphemeralSecret, PublicKey, StaticSecret};
use zeroize::Zeroizing;

pub struct X25519Kem;

impl Kem for X25519Kem {
    const NAME: &'static str = "X25519";

    fn keypair() -> (Bytes, Secret) {
        let sk = StaticSecret::random();
        let pk = PublicKey::from(&sk);
        (pk.as_bytes().to_vec(), Zeroizing::new(sk.to_bytes().to_vec()))
    }

    fn encapsulate(pk: &[u8]) -> Result<(Bytes, Secret), PrimitiveError> {
        let pk_arr: [u8; 32] = pk.try_into().map_err(|_| PrimitiveError::InvalidEncoding)?;
        let recipient_pk = PublicKey::from(pk_arr);
        let eph_sk = EphemeralSecret::random();
        let eph_pk = PublicKey::from(&eph_sk);
        let shared = eph_sk.diffie_hellman(&recipient_pk);
        Ok((
            eph_pk.as_bytes().to_vec(),
            Zeroizing::new(shared.as_bytes().to_vec()),
        ))
    }

    fn decapsulate(sk: &[u8], ct: &[u8]) -> Result<Secret, PrimitiveError> {
        let sk_arr: [u8; 32] = sk.try_into().map_err(|_| PrimitiveError::InvalidEncoding)?;
        let ct_arr: [u8; 32] = ct.try_into().map_err(|_| PrimitiveError::InvalidEncoding)?;
        let static_sk = StaticSecret::from(sk_arr);
        let eph_pk = PublicKey::from(ct_arr);
        let shared = static_sk.diffie_hellman(&eph_pk);
        Ok(Zeroizing::new(shared.as_bytes().to_vec()))
    }
}
