//! SHA3-256 va SHAKE-256 wrapper'lari (spec 2-bo'lim).

use sha3::{Digest, Sha3_256};
use shake::{ExtendableOutput, Shake256, Update, XofReader};

/// SHA3-256(parts[0] || parts[1] || ... ) — domain-separated concat hash.
pub fn sha3_256_concat(parts: &[&[u8]]) -> [u8; 32] {
    let mut hasher = Sha3_256::new();
    for part in parts {
        Digest::update(&mut hasher, part);
    }
    let digest = hasher.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&digest);
    out
}

/// SHAKE-256(parts[0] || parts[1] || ...) -> `out_len` baytlik extensible-output.
pub fn shake256_concat(parts: &[&[u8]], out_len: usize) -> Vec<u8> {
    let mut hasher = Shake256::default();
    for part in parts {
        Update::update(&mut hasher, part);
    }
    let mut reader = hasher.finalize_xof();
    let mut out = vec![0u8; out_len];
    reader.read(&mut out);
    out
}
