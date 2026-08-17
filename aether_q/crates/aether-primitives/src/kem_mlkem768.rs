//! ML-KEM-768 (NIST FIPS 203) — RustCrypto `ml-kem` crate ustidan `Kem` wrapper'i.

use crate::{Bytes, Kem, PrimitiveError, Secret};
use ml_kem::kem::{
    Ciphertext, Decapsulate, Encapsulate, Kem as KemFamily, KeyExport, KeyInit, TryKeyInit,
};
use ml_kem::MlKem768;
use zeroize::Zeroizing;

type DecapsulationKey = <MlKem768 as KemFamily>::DecapsulationKey;
type EncapsulationKey = <MlKem768 as KemFamily>::EncapsulationKey;

pub struct MlKem768Kem;

impl Kem for MlKem768Kem {
    const NAME: &'static str = "ML-KEM-768";

    fn keypair() -> (Bytes, Secret) {
        let (dk, ek) = MlKem768::generate_keypair();
        (ek.to_bytes().to_vec(), Zeroizing::new(dk.to_bytes().to_vec()))
    }

    fn encapsulate(pk: &[u8]) -> Result<(Bytes, Secret), PrimitiveError> {
        let ek = EncapsulationKey::new_from_slice(pk).map_err(|_| PrimitiveError::InvalidEncoding)?;
        let (ct, ss) = ek.encapsulate();
        Ok((ct.to_vec(), Zeroizing::new(ss.to_vec())))
    }

    fn decapsulate(sk: &[u8], ct: &[u8]) -> Result<Secret, PrimitiveError> {
        let dk = DecapsulationKey::new_from_slice(sk).map_err(|_| PrimitiveError::InvalidEncoding)?;
        let ct_arr =
            Ciphertext::<MlKem768>::try_from(ct).map_err(|_| PrimitiveError::InvalidEncoding)?;
        let ss = dk.decapsulate(&ct_arr);
        Ok(Zeroizing::new(ss.to_vec()))
    }
}
