//! KEM qatlami: ML-KEM-768 (FIPS 203), X25519, va profil combiner'lari
//! (0x01 gibrid, 0x03 faqat ML-KEM). Python `aether_q_v51/hybrid.py` va `kem.py` bilan bayt-mos.

use ml_kem::kem::{Decapsulate, FromSeed, KeyExport, TryKeyInit};
use ml_kem::{DecapsulationKey, EncapsulationKey, MlKem768, Seed};
use x25519_dalek::{PublicKey as XPublicKey, StaticSecret};

use crate::error::{AqError, Result};
use crate::kdf::{hkdf_expand32, hkdf_extract, sha3_256};

pub const PROFILE_HYBRID: u8 = 0x01;
pub const PROFILE_MINIMAL: u8 = 0x03;

pub const DEFAULT_LABEL: &[u8] = b"AETHER-Q-v5.1-XWING/L3/v1";
pub const MINIMAL_LABEL: &[u8] = b"AETHER-Q-v5.1-MINIMAL/L3/v1";
/// Implicit rejection domeni (F1 / S4). Python tomoni hali o'zgartirilmagan — KAT da bu yo'l yo'q.
pub const REJECT_LABEL: &[u8] = b"AETHER-Q-v5.1-XREJECT/L3/v1";

pub const MLKEM_EK_LEN: usize = 1184;
pub const MLKEM_CT_LEN: usize = 1088;
pub const X_LEN: usize = 32;
pub const SS_LEN: usize = 32;

/// Python `_combine`: transcript = H(profile ‖ LABEL ‖ ct_M ‖ ct_X ‖ pk_X),
/// PRK = Extract(transcript, ss_M ‖ ss_X ‖ LABEL), SS = Expand(PRK, profile ‖ "/ss", 32).
pub fn combine(profile: u8, label: &[u8], ss_m: &[u8], ct_m: &[u8], ss_x: &[u8], ct_x: &[u8], pk_x: &[u8]) -> [u8; 32] {
    let mut t = vec![profile];
    t.extend_from_slice(label);
    t.extend_from_slice(ct_m);
    t.extend_from_slice(ct_x);
    t.extend_from_slice(pk_x);
    let transcript = sha3_256(&t);
    let mut ikm = Vec::with_capacity(ss_m.len() + ss_x.len() + label.len());
    ikm.extend_from_slice(ss_m);
    ikm.extend_from_slice(ss_x);
    ikm.extend_from_slice(label);
    let prk = hkdf_extract(&transcript, &ikm);
    let mut info = vec![profile];
    info.extend_from_slice(b"/ss");
    hkdf_expand32(&prk, &info)
}

/// Profil privat kaliti: ML-KEM dekapsulyatsiya kaliti (seed bilan birga) va (0x01 uchun) X25519.
pub struct KemPriv {
    pub profile: u8,
    pub dk: DecapsulationKey<MlKem768>,
    /// ML-KEM 64 baytli seed (d ‖ z). Implicit rejection kaliti shu seed'dan olinadi.
    pub dk_seed: [u8; 64],
    /// 0x01 uchun: (statik X25519 maxfiy kalit, pk_x).
    pub x: Option<(StaticSecret, [u8; 32])>,
}

fn random_bytes<const N: usize>() -> Result<[u8; N]> {
    let mut b = [0u8; N];
    getrandom::getrandom(&mut b).map_err(|_| AqError::Crypto("getrandom"))?;
    Ok(b)
}

/// ML-KEM-768 kalit juftligi seed'dan (FIPS 203). Qaytaradi: (dk, ek bayt).
pub fn mlkem_from_seed(seed: &[u8; 64]) -> (DecapsulationKey<MlKem768>, Vec<u8>) {
    let s: Seed = (*seed).into();
    let (dk, ek) = MlKem768::from_seed(&s);
    let ek_bytes = ek.to_bytes();
    (dk, ek_bytes.as_slice().to_vec())
}

/// Profil uchun kalit juftligi. Qaytaradi: (ochiq bundle, maxfiy kalit).
/// 0x01 → ek_m(1184) ‖ pk_x(32) = 1216 bayt; 0x03 → ek_m(1184).
pub fn keygen(profile: u8) -> Result<(Vec<u8>, KemPriv)> {
    let dk_seed = random_bytes::<64>()?;
    let (dk, ek) = mlkem_from_seed(&dk_seed);
    match profile {
        PROFILE_HYBRID => {
            let x_seed = random_bytes::<32>()?;
            let x = StaticSecret::from(x_seed);
            let pk_x = XPublicKey::from(&x).to_bytes();
            let mut bundle = ek;
            bundle.extend_from_slice(&pk_x);
            Ok((bundle, KemPriv { profile, dk, dk_seed, x: Some((x, pk_x)) }))
        }
        PROFILE_MINIMAL => Ok((ek, KemPriv { profile, dk, dk_seed, x: None })),
        _ => Err(AqError::Crypto("noma'lum KEM profili")),
    }
}

/// Encaps. Qaytaradi: (ct bundle, shared secret). Nol (low-order) X25519 ochiq kaliti
/// bo'lsa `Crypto` xatosi (klient tomonida alert bilan uziladi).
pub fn encaps(profile: u8, pk: &[u8]) -> Result<(Vec<u8>, [u8; 32])> {
    match profile {
        PROFILE_HYBRID => {
            if pk.len() != MLKEM_EK_LEN + X_LEN {
                return Err(AqError::Crypto("0x01: public bundle uzunligi"));
            }
            let (ek_m, pk_x) = pk.split_at(MLKEM_EK_LEN);
            let (ct_m, ss_m) = mlkem_encaps(ek_m)?;
            let eph_seed = random_bytes::<32>()?;
            let eph = StaticSecret::from(eph_seed);
            let ct_x = XPublicKey::from(&eph).to_bytes();
            let shared = eph.diffie_hellman(&XPublicKey::from(<[u8; 32]>::try_from(pk_x).unwrap()));
            if !shared.was_contributory() {
                return Err(AqError::Crypto("low-order X25519 ochiq kaliti"));
            }
            let ss = combine(PROFILE_HYBRID, DEFAULT_LABEL, &ss_m, &ct_m, shared.as_bytes(), &ct_x, pk_x);
            let mut ct = ct_m;
            ct.extend_from_slice(&ct_x);
            Ok((ct, ss))
        }
        PROFILE_MINIMAL => {
            if pk.len() != MLKEM_EK_LEN {
                return Err(AqError::Crypto("0x03: public key uzunligi"));
            }
            let (ct_m, ss_m) = mlkem_encaps(pk)?;
            let ss = combine(PROFILE_MINIMAL, MINIMAL_LABEL, &ss_m, &ct_m, &[], &[], &[]);
            Ok((ct_m, ss))
        }
        _ => Err(AqError::Crypto("noma'lum KEM profili")),
    }
}

/// Decaps. Protokol xatosi (noto'g'ri uzunlik) `Crypto`; kriptografik muvaffaqiyatsizlik
/// (nol X25519 nuqta) exception emas — implicit rejection kaliti qaytariladi.
pub fn decaps(priv_: &KemPriv, ct: &[u8]) -> Result<[u8; 32]> {
    match priv_.profile {
        PROFILE_HYBRID => {
            if ct.len() != MLKEM_CT_LEN + X_LEN {
                return Err(AqError::Crypto("0x01: ciphertext uzunligi"));
            }
            let (ct_m, ct_x) = ct.split_at(MLKEM_CT_LEN);
            let ss_m = mlkem_decaps(&priv_.dk, ct_m)?;
            let (x, pk_x) = priv_.x.as_ref().ok_or(AqError::Crypto("0x01: X25519 kaliti yo'q"))?;
            let shared = x.diffie_hellman(&XPublicKey::from(<[u8; 32]>::try_from(ct_x).unwrap()));
            if !shared.was_contributory() {
                return Ok(reject_key(priv_.profile, &priv_.dk_seed, &ss_m, ct_m, ct_x));
            }
            Ok(combine(PROFILE_HYBRID, DEFAULT_LABEL, &ss_m, ct_m, shared.as_bytes(), ct_x, pk_x))
        }
        PROFILE_MINIMAL => {
            if ct.len() != MLKEM_CT_LEN {
                return Err(AqError::Crypto("0x03: ciphertext uzunligi"));
            }
            let ss_m = mlkem_decaps(&priv_.dk, ct)?;
            Ok(combine(PROFILE_MINIMAL, MINIMAL_LABEL, &ss_m, ct, &[], &[], &[]))
        }
        _ => Err(AqError::Crypto("noma'lum KEM profili")),
    }
}

/// Implicit rejection kaliti (F1 / S4): maxfiy `dk_seed` va `ss_m` dan, hujumchi hisoblay olmaydi.
pub fn reject_key(profile: u8, dk_seed: &[u8; 64], ss_m: &[u8], ct_m: &[u8], ct_x: &[u8]) -> [u8; 32] {
    let mut ikm = dk_seed.to_vec();
    ikm.extend_from_slice(ss_m);
    let prk = hkdf_extract(REJECT_LABEL, &ikm);
    let mut info = vec![profile];
    info.extend_from_slice(b"/reject");
    info.extend_from_slice(ct_m);
    info.extend_from_slice(ct_x);
    hkdf_expand32(&prk, &info)
}

fn mlkem_encaps(ek_bytes: &[u8]) -> Result<(Vec<u8>, [u8; 32])> {
    let ek = EncapsulationKey::<MlKem768>::new_from_slice(ek_bytes)
        .map_err(|_| AqError::Crypto("ML-KEM ochiq kalit yaroqsiz"))?;
    // FIPS 203 Encaps: tasodifiy m (32 bayt) — deterministik variant bilan.
    let m = random_bytes::<32>()?;
    let (ct, ss) = ek.encapsulate_deterministic(&m.into());
    let mut out = [0u8; 32];
    out.copy_from_slice(ss.as_slice());
    Ok((ct.as_slice().to_vec(), out))
}

/// ML-KEM-768 dekapsulyatsiya (implicit rejection FIPS 203 ichida).
pub fn mlkem_decaps(dk: &DecapsulationKey<MlKem768>, ct: &[u8]) -> Result<[u8; 32]> {
    let ss = dk.decapsulate_slice(ct).map_err(|_| AqError::Crypto("ML-KEM ciphertext uzunligi"))?;
    let mut out = [0u8; 32];
    out.copy_from_slice(ss.as_slice());
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bundle_sizes() {
        let (pk1, _) = keygen(PROFILE_HYBRID).unwrap();
        assert_eq!(pk1.len(), 1216);
        let (pk3, _) = keygen(PROFILE_MINIMAL).unwrap();
        assert_eq!(pk3.len(), 1184);
    }

    #[test]
    fn roundtrip_both_profiles() {
        for p in [PROFILE_HYBRID, PROFILE_MINIMAL] {
            let (pk, priv_) = keygen(p).unwrap();
            let (ct, ss_a) = encaps(p, &pk).unwrap();
            let ss_b = decaps(&priv_, &ct).unwrap();
            assert_eq!(ss_a, ss_b, "profil {p:#x}");
        }
    }
}
