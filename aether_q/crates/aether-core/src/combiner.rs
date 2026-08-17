//! KEM combiner formulalari — DEFAULT/PARANOID/MINIMAL profillar uchun.
//! AUTH-AKEM (0x05) combiner `akem.rs`da, spec 4.1-bo'limga muvofiq.

use crate::labels::{PARANOID_LABEL, XWING_LABEL};
use crate::Secret;
use aether_primitives::hash::sha3_256_concat;
use zeroize::Zeroizing;

/// DEFAULT (0x01) — X-Wing uslubidagi combiner:
/// `SHA3-256(ss_M || ss_X || ct_X || pk_X || XWING_LABEL)`
pub fn combine_default(ss_mlkem: &[u8], ss_x25519: &[u8], ct_x25519: &[u8], pk_x25519: &[u8]) -> Secret {
    let digest = sha3_256_concat(&[ss_mlkem, ss_x25519, ct_x25519, pk_x25519, XWING_LABEL]);
    Zeroizing::new(digest.to_vec())
}

/// PARANOID (0x02) — Triple-Hybrid combiner:
/// `SHA3-256(ss_M || ss_X || ss_H || ct_X || ct_H || pk_X || PARANOID_LABEL)`
pub fn combine_paranoid(
    ss_mlkem: &[u8],
    ss_x25519: &[u8],
    ss_hqc: &[u8],
    ct_x25519: &[u8],
    ct_hqc: &[u8],
    pk_x25519: &[u8],
) -> Secret {
    let digest = sha3_256_concat(&[
        ss_mlkem,
        ss_x25519,
        ss_hqc,
        ct_x25519,
        ct_hqc,
        pk_x25519,
        PARANOID_LABEL,
    ]);
    Zeroizing::new(digest.to_vec())
}

/// MINIMAL (0x03) — ML-KEM-768 standalone: combiner shart emas, `ss_M` bevosita ishlatiladi.
pub fn combine_minimal(ss_mlkem: &[u8]) -> Secret {
    Zeroizing::new(ss_mlkem.to_vec())
}
