//! Ed25519 (RFC 8032) — yengil klassik imzo, Opsional (spec 2-bo'lim).

use crate::{Bytes, PrimitiveError, Secret, Signer};
use ed25519_dalek::{Signature, Signer as _, SigningKey, Verifier as _, VerifyingKey};
use getrandom::rand_core::UnwrapErr;
use getrandom::SysRng;
use zeroize::Zeroizing;

pub struct Ed25519Signer;

impl Signer for Ed25519Signer {
    const NAME: &'static str = "Ed25519";

    fn keypair() -> (Bytes, Secret) {
        let signing_key = SigningKey::generate(&mut UnwrapErr(SysRng));
        let verifying_key = signing_key.verifying_key();
        (
            verifying_key.to_bytes().to_vec(),
            Zeroizing::new(signing_key.to_bytes().to_vec()),
        )
    }

    fn sign(sk: &[u8], msg: &[u8]) -> Result<Bytes, PrimitiveError> {
        let sk_arr: [u8; 32] = sk.try_into().map_err(|_| PrimitiveError::InvalidEncoding)?;
        let signing_key = SigningKey::from_bytes(&sk_arr);
        let sig = signing_key.sign(msg);
        Ok(sig.to_bytes().to_vec())
    }

    fn verify(pk: &[u8], msg: &[u8], sig: &[u8]) -> Result<(), PrimitiveError> {
        let pk_arr: [u8; 32] = pk.try_into().map_err(|_| PrimitiveError::InvalidEncoding)?;
        let sig_arr: [u8; 64] = sig.try_into().map_err(|_| PrimitiveError::InvalidEncoding)?;
        let verifying_key =
            VerifyingKey::from_bytes(&pk_arr).map_err(|_| PrimitiveError::InvalidEncoding)?;
        let signature = Signature::from_bytes(&sig_arr);
        verifying_key
            .verify(msg, &signature)
            .map_err(|_| PrimitiveError::OperationFailed)
    }
}
