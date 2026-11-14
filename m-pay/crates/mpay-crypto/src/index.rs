//! PAN HMAC indeksi: `HMAC-SHA256(PAN-IDX, "MPAY-PAN-IDX-V1" ‖ 0x00 ‖ PAN)`.
//!
//! Shifrlangan PAN bo'yicha qidirish uchun deterministik, kalitsiz qaytarib bo'lmaydigan indeks.

use mpay_common::{Pan, PanFingerprint};

use crate::keystore::{KeyLabel, KeyStore};
use crate::CryptoError;

const DOMAIN: &[u8] = b"MPAY-PAN-IDX-V1\x00";

/// PAN barmoq izi.
pub fn pan_fingerprint(
    ks: &dyn KeyStore,
    key: &KeyLabel,
    pan: &Pan,
) -> Result<PanFingerprint, CryptoError> {
    let input = zeroize::Zeroizing::new([DOMAIN, pan.expose_digits().as_bytes()].concat());
    Ok(PanFingerprint(ks.hmac_sha256(key, &input)?))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::keystore::{KeyKind, MemoryKeyStore};

    #[test]
    fn deterministic_and_keyed() {
        let ks = MemoryKeyStore::from_seed([3; 32]);
        let l = KeyLabel::new(KeyLabel::PAN_INDEX);
        ks.ensure_key(&l, KeyKind::HmacSha256).unwrap();
        let p = Pan::from_prefix("990012000000345").unwrap();
        let q = Pan::from_prefix("990012000000346").unwrap();
        assert_eq!(
            pan_fingerprint(&ks, &l, &p).unwrap(),
            pan_fingerprint(&ks, &l, &p).unwrap()
        );
        assert_ne!(
            pan_fingerprint(&ks, &l, &p).unwrap(),
            pan_fingerprint(&ks, &l, &q).unwrap()
        );
    }
}
