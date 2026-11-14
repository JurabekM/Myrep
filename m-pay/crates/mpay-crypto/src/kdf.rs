//! NIST SP 800-108r1 counter rejimidagi KDF, PRF = AES-128-CMAC, L = 128 bit.
//!
//! ```text
//! KDF(K, Label, Context) = AES-CMAC(K, 0x01 ‖ Label ‖ 0x00 ‖ Context ‖ 0x0080)
//! ```
//! (`docs/specs/emv-profile.md` §5). Ota kalit HSM ichida bo'lsa — [`derive_with_keystore`].

use crate::keystore::{soft, KeyLabel, KeyStore};
use crate::{CryptoError, SecretKey16};

/// KDF kirish bloki (fixed input data counter bilan).
pub fn kdf_input(label: &[u8], context: &[u8]) -> Vec<u8> {
    let mut v = Vec::with_capacity(4 + label.len() + context.len());
    v.push(0x01); // [i]_8
    v.extend_from_slice(label);
    v.push(0x00);
    v.extend_from_slice(context);
    v.extend_from_slice(&128u16.to_be_bytes()); // [L]_16
    v
}

/// Dasturiy ota kalitdan hosil qilish.
pub fn derive(parent: &SecretKey16, label: &[u8], context: &[u8]) -> SecretKey16 {
    SecretKey16::from_bytes(soft::cmac_aes128(
        parent.expose(),
        &kdf_input(label, context),
    ))
}

/// HSM ichidagi ota kalitdan hosil qilish (natija dastur xotirasiga chiqadi — ADR-0004).
pub fn derive_with_keystore(
    ks: &dyn KeyStore,
    parent: &KeyLabel,
    label: &[u8],
    context: &[u8],
) -> Result<SecretKey16, CryptoError> {
    Ok(SecretKey16::from_bytes(
        ks.aes_cmac(parent, &kdf_input(label, context))?,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::keystore::{KeyKind, MemoryKeyStore};

    #[test]
    fn input_layout() {
        assert_eq!(
            kdf_input(b"AB", &[7, 8]),
            vec![1, b'A', b'B', 0, 7, 8, 0x00, 0x80]
        );
    }

    #[test]
    fn keystore_and_software_agree() {
        let k = [0x11u8; 16];
        let ks = MemoryKeyStore::random();
        let l = KeyLabel::new("p");
        ks.import_secret(&l, KeyKind::Aes128, &k).unwrap();
        let a = derive(&SecretKey16::from_bytes(k), b"L", b"C");
        let b = derive_with_keystore(&ks, &l, b"L", b"C").unwrap();
        assert_eq!(a, b);
        assert_ne!(a, derive(&SecretKey16::from_bytes(k), b"L", b"D"));
    }
}
