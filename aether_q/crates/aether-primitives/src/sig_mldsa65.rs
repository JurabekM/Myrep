//! ML-DSA-65 (NIST FIPS 204) — RustCrypto `ml-dsa` crate ustidan `Signer` wrapper'i.

use crate::{Bytes, PrimitiveError, Secret, Signer as AetherSigner};
use ml_dsa::signature::{Keypair, Signer as _, Verifier as _};
use ml_dsa::{EncodedSignature, Generate, KeyExport, KeyInit, MlDsa65, Signature, SigningKey, VerifyingKey};
use zeroize::Zeroizing;

pub struct MlDsa65Signer;

impl AetherSigner for MlDsa65Signer {
    const NAME: &'static str = "ML-DSA-65";

    fn keypair() -> (Bytes, Secret) {
        let sk = SigningKey::<MlDsa65>::generate();
        let vk = sk.verifying_key();
        (vk.to_bytes().to_vec(), Zeroizing::new(sk.to_bytes().to_vec()))
    }

    fn sign(sk: &[u8], msg: &[u8]) -> Result<Bytes, PrimitiveError> {
        let signing_key =
            SigningKey::<MlDsa65>::new_from_slice(sk).map_err(|_| PrimitiveError::InvalidEncoding)?;
        let sig = signing_key.sign(msg);
        Ok(sig.encode().to_vec())
    }

    fn verify(pk: &[u8], msg: &[u8], sig: &[u8]) -> Result<(), PrimitiveError> {
        let verifying_key = VerifyingKey::<MlDsa65>::new_from_slice(pk)
            .map_err(|_| PrimitiveError::InvalidEncoding)?;
        let encoded_sig =
            EncodedSignature::<MlDsa65>::try_from(sig).map_err(|_| PrimitiveError::InvalidEncoding)?;
        let signature =
            Signature::<MlDsa65>::decode(&encoded_sig).ok_or(PrimitiveError::InvalidEncoding)?;
        verifying_key
            .verify(msg, &signature)
            .map_err(|_| PrimitiveError::OperationFailed)
    }
}
