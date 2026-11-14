//! Kalit ajratish va XOF — Python `aether_q_v51/kdf.py` bilan bayt-mos.
//!
//! - SHA3-256 (FIPS 202)
//! - HKDF-SHA3-256 (RFC 5869, HMAC-SHA3-256 bilan); bo'sh salt → 32 nol bayt
//! - KMAC256 (SP 800-185) = cSHAKE256(bytepad(enc_str(K)) ‖ X ‖ right_encode(L·8), "KMAC", S)

use hmac::{Hmac, Mac};
use sha3::digest::{ExtendableOutput, XofReader};
use sha3::{Digest, Sha3_256, Shake256};
use subtle::ConstantTimeEq;

type HmacSha3 = Hmac<Sha3_256>;

pub fn sha3_256(data: &[u8]) -> [u8; 32] {
    Sha3_256::digest(data).into()
}

/// PRK = HMAC-SHA3-256(salt, ikm). Bo'sh salt → 32 nol bayt.
pub fn hkdf_extract(salt: &[u8], ikm: &[u8]) -> [u8; 32] {
    let zeros = [0u8; 32];
    let key: &[u8] = if salt.is_empty() { &zeros } else { salt };
    let mut mac = <HmacSha3 as Mac>::new_from_slice(key).expect("HMAC: istalgan uzunlik");
    mac.update(ikm);
    mac.finalize().into_bytes().into()
}

/// RFC 5869 Expand, SHA3-256 bilan. `length` ≤ 255·32.
pub fn hkdf_expand(prk: &[u8], info: &[u8], length: usize) -> Vec<u8> {
    assert!(length <= 255 * 32, "HKDF-Expand: length juda katta");
    let mut okm = Vec::with_capacity(length + 32);
    let mut t: Vec<u8> = Vec::new();
    let mut counter: u8 = 1;
    while okm.len() < length {
        let mut mac = <HmacSha3 as Mac>::new_from_slice(prk).expect("HMAC: istalgan uzunlik");
        mac.update(&t);
        mac.update(info);
        mac.update(&[counter]);
        t = mac.finalize().into_bytes().to_vec();
        okm.extend_from_slice(&t);
        counter = counter.wrapping_add(1);
    }
    okm.truncate(length);
    okm
}

/// `hkdf_expand` ning 32 baytli varianti.
pub fn hkdf_expand32(prk: &[u8], info: &[u8]) -> [u8; 32] {
    let v = hkdf_expand(prk, info, 32);
    let mut out = [0u8; 32];
    out.copy_from_slice(&v);
    out
}

/// SP 800-185 left_encode.
fn left_encode(x: u64) -> Vec<u8> {
    let bytes = x.to_be_bytes();
    let first = bytes.iter().position(|&b| b != 0).unwrap_or(7);
    let s = &bytes[first..];
    let s = if s.is_empty() { &bytes[7..] } else { s };
    let mut out = Vec::with_capacity(s.len() + 1);
    out.push(s.len() as u8);
    out.extend_from_slice(s);
    out
}

/// SP 800-185 right_encode.
fn right_encode(x: u64) -> Vec<u8> {
    let bytes = x.to_be_bytes();
    let first = bytes.iter().position(|&b| b != 0).unwrap_or(7);
    let s = &bytes[first..];
    let s = if s.is_empty() { &bytes[7..] } else { s };
    let mut out = s.to_vec();
    out.push(s.len() as u8);
    out
}

/// enc_str(s) = left_encode(len(s)·8) ‖ s
fn encode_string(s: &[u8]) -> Vec<u8> {
    let mut out = left_encode((s.len() as u64) * 8);
    out.extend_from_slice(s);
    out
}

/// bytepad(x, w) = left_encode(w) ‖ x ‖ nollar (w ning karraligiga)
fn bytepad(x: &[u8], w: usize) -> Vec<u8> {
    let mut out = left_encode(w as u64);
    out.extend_from_slice(x);
    while out.len() % w != 0 {
        out.push(0);
    }
    out
}

/// KMAC256(K, X, L, S) — `custom` = S.
///
/// ⚠ Python referens (`aether_q_v51/kdf.py` `cshake_256`) SP 800-185 cSHAKE256 emas:
/// u `SHAKE256(bytepad(enc_str("KMAC") ‖ enc_str(S), 136) ‖ X)` ni hisoblaydi (0x1F padding,
/// 0x04 emas). Bu "KNOWN_LIMITATIONS" C1. Rust bayt-mos bo'lishi uchun shuni takrorlaydi.
pub fn kmac256(key: &[u8], data: &[u8], out_len: usize, custom: &[u8]) -> Vec<u8> {
    let mut newx = bytepad(&encode_string(key), 136);
    newx.extend_from_slice(data);
    newx.extend_from_slice(&right_encode((out_len as u64) * 8));
    let mut name_custom = encode_string(b"KMAC");
    name_custom.extend_from_slice(&encode_string(custom));
    let mut input = bytepad(&name_custom, 136);
    input.extend_from_slice(&newx);
    let mut h = Shake256::default();
    sha3::digest::Update::update(&mut h, &input);
    let mut out = vec![0u8; out_len];
    h.finalize_xof().read(&mut out);
    out
}

/// Konstant-vaqt tenglik (uzunliklar teng bo'lishi shart emas — teng bo'lmasa `false`).
pub fn ct_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    bool::from(a.ct_eq(b))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn left_right_encode_match_sp800_185() {
        assert_eq!(left_encode(0), vec![1, 0]);
        assert_eq!(left_encode(256), vec![2, 1, 0]);
        assert_eq!(right_encode(0), vec![0, 1]);
        assert_eq!(right_encode(256), vec![1, 0, 2]);
    }

    #[test]
    fn empty_salt_is_zero_key() {
        assert_eq!(hkdf_extract(b"", b"x"), hkdf_extract(&[0u8; 32], b"x"));
    }

    #[test]
    fn ct_eq_length_mismatch_is_false() {
        assert!(!ct_eq(b"ab", b"abc"));
        assert!(ct_eq(b"abc", b"abc"));
    }
}
