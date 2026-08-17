//! Record Layer va AEAD Framing — spec 7-bo'lim.

use crate::labels::{RECORD_C2S_KEY_LABEL, RECORD_C2S_NIV_LABEL, RECORD_S2C_KEY_LABEL, RECORD_S2C_NIV_LABEL};
use crate::CoreError;
use aether_primitives::aead::{self, AeadAlgorithm};
use aether_primitives::hash::shake256_concat;

pub struct DirectionalKeys {
    pub key: [u8; 32],
    pub base_niv: [u8; 12],
}

pub struct RecordKeys {
    pub c2s: DirectionalKeys,
    pub s2c: DirectionalKeys,
}

/// 7.1: `SharedSecret`dan HKDF-Expand (SHAKE-256 asosida) orqali yo'nalishga xos
/// kalit va boshlang'ich nonce ("niv") juftliklarini hosil qiladi.
pub fn derive_record_keys(shared_secret: &[u8]) -> RecordKeys {
    let c2s_key = shake256_concat(&[shared_secret, RECORD_C2S_KEY_LABEL], 32);
    let s2c_key = shake256_concat(&[shared_secret, RECORD_S2C_KEY_LABEL], 32);
    let c2s_niv = shake256_concat(&[shared_secret, RECORD_C2S_NIV_LABEL], 12);
    let s2c_niv = shake256_concat(&[shared_secret, RECORD_S2C_NIV_LABEL], 12);

    RecordKeys {
        c2s: DirectionalKeys {
            key: c2s_key.try_into().expect("shake256 32B output"),
            base_niv: c2s_niv.try_into().expect("shake256 12B output"),
        },
        s2c: DirectionalKeys {
            key: s2c_key.try_into().expect("shake256 32B output"),
            base_niv: s2c_niv.try_into().expect("shake256 12B output"),
        },
    }
}

/// 7.2: `Nonce = N_base XOR LE64(counter)` — counter faqat pastki 8 baytga ta'sir qiladi,
/// yuqori 4 bayt `N_base`dan o'zgarishsiz qoladi.
fn compute_nonce(base_niv: &[u8; 12], counter: u32) -> [u8; 12] {
    let mut nonce = *base_niv;
    let counter_le = (counter as u64).to_le_bytes();
    for i in 0..8 {
        nonce[4 + i] ^= counter_le[i];
    }
    nonce
}

/// 7.3: `AAD = profile_id(1B) || session_id(8B) || counter(4B)`
pub fn build_aad(profile_id: u8, session_id: [u8; 8], counter: u32) -> [u8; 13] {
    let mut aad = [0u8; 13];
    aad[0] = profile_id;
    aad[1..9].copy_from_slice(&session_id);
    aad[9..13].copy_from_slice(&counter.to_be_bytes());
    aad
}

/// Counter 32-bit chegaraga yetganda majburiy rekey zarurligini bildiradi (7.2).
pub fn needs_rekey(counter: u32) -> bool {
    counter == u32::MAX
}

/// `RecordFrame = AAD || AEAD_Encrypt(K_dir, Nonce, plaintext, AAD)`
pub fn seal_record(
    alg: AeadAlgorithm,
    dir_keys: &DirectionalKeys,
    profile_id: u8,
    session_id: [u8; 8],
    counter: u32,
    plaintext: &[u8],
) -> Result<Vec<u8>, CoreError> {
    let aad = build_aad(profile_id, session_id, counter);
    let nonce = compute_nonce(&dir_keys.base_niv, counter);
    let ciphertext = aead::seal(alg, &dir_keys.key, &nonce, &aad, plaintext)
        .map_err(|_| CoreError::DecryptFailure)?;

    let mut frame = Vec::with_capacity(aad.len() + ciphertext.len());
    frame.extend_from_slice(&aad);
    frame.extend_from_slice(&ciphertext);
    Ok(frame)
}

/// 7.4: buzuq tag yoki boshqa dekriptsiya xatosi — yagona `CoreError::DecryptFailure`
/// qaytariladi (oracle hujumlariga qarshi himoya, qisman deshifrlangan ma'lumot chiqmaydi).
pub fn open_record(
    alg: AeadAlgorithm,
    dir_keys: &DirectionalKeys,
    profile_id: u8,
    session_id: [u8; 8],
    frame: &[u8],
) -> Result<(u32, Vec<u8>), CoreError> {
    if frame.len() < 13 {
        return Err(CoreError::DecryptFailure);
    }
    let (aad, ciphertext) = frame.split_at(13);
    if aad[0] != profile_id || aad[1..9] != session_id {
        return Err(CoreError::DecryptFailure);
    }
    let counter = u32::from_be_bytes(aad[9..13].try_into().unwrap());
    let nonce = compute_nonce(&dir_keys.base_niv, counter);

    let plaintext =
        aead::open(alg, &dir_keys.key, &nonce, aad, ciphertext).map_err(|_| CoreError::DecryptFailure)?;
    Ok((counter, plaintext))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_and_aad_binding() {
        let shared_secret = [0x55u8; 32];
        let keys = derive_record_keys(&shared_secret);
        assert_ne!(keys.c2s.key, keys.s2c.key, "yo'nalish kalitlari farqli bo'lishi SHART");

        let session_id = [3u8; 8];
        let frame = seal_record(
            AeadAlgorithm::ChaCha20Poly1305,
            &keys.c2s,
            0x01,
            session_id,
            1,
            b"hello record layer",
        )
        .unwrap();

        let (counter, plaintext) =
            open_record(AeadAlgorithm::ChaCha20Poly1305, &keys.c2s, 0x01, session_id, &frame).unwrap();
        assert_eq!(counter, 1);
        assert_eq!(plaintext, b"hello record layer");

        // AAD (profile_id) o'zgartirilsa autentifikatsiya buzilishi SHART.
        let err = open_record(AeadAlgorithm::ChaCha20Poly1305, &keys.c2s, 0x02, session_id, &frame);
        assert!(err.is_err());
    }

    #[test]
    fn nonce_differs_across_counters() {
        let base_niv = [0u8; 12];
        let n1 = compute_nonce(&base_niv, 1);
        let n2 = compute_nonce(&base_niv, 2);
        assert_ne!(n1, n2);
    }
}
