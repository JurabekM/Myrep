//! Trait qatlami: AETHER-Q v4 protokol mantig'i (`aether-core`) ushbu trait'lar
//! orqali kripto-primitivlarga murojaat qiladi, konkret crate'larga bevosita bog'lanmaydi.

pub mod aead;
pub mod hash;
pub mod kem_hqc192;
pub mod kem_mlkem768;
pub mod kem_x25519;
pub mod rng;
pub mod sig_ed25519;
pub mod sig_mldsa65;

use zeroize::Zeroizing;

#[derive(Debug, thiserror::Error)]
pub enum PrimitiveError {
    #[error("invalid key, ciphertext or signature encoding")]
    InvalidEncoding,
    #[error("cryptographic operation failed")]
    OperationFailed,
    #[error("AEAD authentication failed")]
    AeadAuthFailed,
}

/// Ochiq (public) baytlar — pk, ct, sig kabi maxfiy bo'lmagan qiymatlar uchun.
pub type Bytes = Vec<u8>;
/// Maxfiy baytlar — Drop bo'lganda avtomatik tozalanadi (S3 talabi).
pub type Secret = Zeroizing<Vec<u8>>;

/// Key Encapsulation Mechanism uchun umumiy, bayt-yo'naltirilgan interfeys.
pub trait Kem {
    const NAME: &'static str;

    fn keypair() -> (Bytes, Secret);
    fn encapsulate(pk: &[u8]) -> Result<(Bytes, Secret), PrimitiveError>;
    fn decapsulate(sk: &[u8], ct: &[u8]) -> Result<Secret, PrimitiveError>;
}

/// Raqamli imzo sxemasi uchun umumiy interfeys.
pub trait Signer {
    const NAME: &'static str;

    fn keypair() -> (Bytes, Secret);
    fn sign(sk: &[u8], msg: &[u8]) -> Result<Bytes, PrimitiveError>;
    fn verify(pk: &[u8], msg: &[u8], sig: &[u8]) -> Result<(), PrimitiveError>;
}

#[cfg(test)]
mod smoke_tests {
    use super::*;
    use crate::aead::{open, seal, AeadAlgorithm};
    use crate::kem_hqc192::Hqc192Kem;
    use crate::kem_mlkem768::MlKem768Kem;
    use crate::kem_x25519::X25519Kem;
    use crate::sig_ed25519::Ed25519Signer;
    use crate::sig_mldsa65::MlDsa65Signer;

    fn kem_roundtrip<K: Kem>() {
        let (pk, sk) = K::keypair();
        let (ct, ss_sender) = K::encapsulate(&pk).expect("encapsulate");
        let ss_receiver = K::decapsulate(&sk, &ct).expect("decapsulate");
        assert_eq!(&*ss_sender, &*ss_receiver, "{} shared secret mismatch", K::NAME);
    }

    fn signer_roundtrip<S: Signer>() {
        let (pk, sk) = S::keypair();
        let msg = b"AETHER-Q v4 smoke test";
        let sig = S::sign(&sk, msg).expect("sign");
        S::verify(&pk, msg, &sig).expect("verify should succeed");

        let mut bad_sig = sig.clone();
        let last = bad_sig.len() - 1;
        bad_sig[last] ^= 0xFF;
        assert!(S::verify(&pk, msg, &bad_sig).is_err(), "{} forged sig accepted", S::NAME);
    }

    #[test]
    fn x25519_roundtrip() {
        kem_roundtrip::<X25519Kem>();
    }

    #[test]
    fn mlkem768_roundtrip() {
        kem_roundtrip::<MlKem768Kem>();
    }

    #[test]
    fn hqc192_roundtrip() {
        kem_roundtrip::<Hqc192Kem>();
    }

    #[test]
    fn ed25519_roundtrip() {
        signer_roundtrip::<Ed25519Signer>();
    }

    #[test]
    fn mldsa65_roundtrip() {
        signer_roundtrip::<MlDsa65Signer>();
    }

    #[test]
    fn aead_roundtrip_and_tamper_detection() {
        let key = [0x42u8; 32];
        let nonce = [0x24u8; 12];
        let aad = b"profile_id+session_id+counter";
        let plaintext = b"AETHER-Q v4 record layer smoke test";

        let ct = seal(AeadAlgorithm::ChaCha20Poly1305, &key, &nonce, aad, plaintext)
            .expect("seal should succeed");
        let pt = open(AeadAlgorithm::ChaCha20Poly1305, &key, &nonce, aad, &ct)
            .expect("open should succeed");
        assert_eq!(pt, plaintext);

        let mut tampered_aad = aad.to_vec();
        tampered_aad[0] ^= 0xFF;
        assert!(
            open(AeadAlgorithm::ChaCha20Poly1305, &key, &nonce, &tampered_aad, &ct).is_err(),
            "AAD tampering must be detected"
        );
    }

    #[test]
    fn hash_functions_are_deterministic_and_correct() {
        // Streaming concatenation must match hashing the pre-joined bytes.
        let split = hash::sha3_256_concat(&[b"A", b"B"]);
        let joined = hash::sha3_256_concat(&[b"AB"]);
        assert_eq!(split, joined);

        // Distinct inputs must produce distinct digests.
        let other = hash::sha3_256_concat(&[b"C"]);
        assert_ne!(split, other);

        let x1 = hash::shake256_concat(&[b"seed"], 64);
        let x2 = hash::shake256_concat(&[b"seed"], 64);
        assert_eq!(x1, x2);
        assert_eq!(x1.len(), 64);
    }
}
