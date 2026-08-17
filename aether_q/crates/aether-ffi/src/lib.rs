//! UniFFI orqali Python/Kotlin/Swift'ga eksport qilinadigan yagona FFI interfeysi.
//!
//! Qamrov: DEFAULT (0x01) profil handshake'i, AUTH-AKEM (0x05) va Compress-KEM (0x04)
//! ratchet, hamda umumiy record layer (7-bo'lim). PARANOID/MINIMAL profillar hozircha
//! FFI'ga eksport qilinmagan (`aether-core`da mavjud va test qilingan).

uniffi::setup_scaffolding!();

use aether_core::combiner::combine_default;
use aether_core::ratchet::{CompressRecipient, CompressSender};
use aether_core::record;
use aether_primitives::aead::AeadAlgorithm;
use aether_primitives::kem_mlkem768::MlKem768Kem;
use aether_primitives::kem_x25519::X25519Kem;
use aether_primitives::sig_ed25519::Ed25519Signer;
use aether_primitives::{Kem, Signer};
use std::sync::{Arc, Mutex};

#[derive(uniffi::Error, Debug, thiserror::Error)]
pub enum AetherError {
    /// S2/7.4: barcha kripto-operatsiya xatolari uchun yagona umumiy xato turi.
    #[error("AETHER_DECRYPT_FAILURE")]
    OperationFailed,
}

#[derive(uniffi::Record)]
pub struct KeyPair {
    pub public_key: Vec<u8>,
    pub secret_key: Vec<u8>,
}

#[derive(uniffi::Record)]
pub struct DefaultEncapsulation {
    pub ct_mlkem: Vec<u8>,
    pub ct_x25519: Vec<u8>,
    pub shared_secret: Vec<u8>,
}

#[derive(uniffi::Record)]
pub struct AkemEncapsulation {
    pub ct_mlkem: Vec<u8>,
    pub ct_x25519: Vec<u8>,
    pub signature: Vec<u8>,
    pub shared_secret: Vec<u8>,
}

#[derive(uniffi::Record)]
pub struct CompressFrameResult {
    pub frame: Vec<u8>,
    pub shared_secret: Vec<u8>,
}

#[uniffi::export]
pub fn generate_x25519_keypair() -> KeyPair {
    let (pk, sk) = X25519Kem::keypair();
    KeyPair {
        public_key: pk,
        secret_key: sk.to_vec(),
    }
}

#[uniffi::export]
pub fn generate_mlkem768_keypair() -> KeyPair {
    let (pk, sk) = MlKem768Kem::keypair();
    KeyPair {
        public_key: pk,
        secret_key: sk.to_vec(),
    }
}

/// Identity imzo kaliti (AUTH-AKEM transcript'ini imzolash uchun).
#[uniffi::export]
pub fn generate_ed25519_keypair() -> KeyPair {
    let (pk, sk) = Ed25519Signer::keypair();
    KeyPair {
        public_key: pk,
        secret_key: sk.to_vec(),
    }
}

/// `len` baytlik kriptografik tasodifiy buferi (masalan `z_recip` uchun).
#[uniffi::export]
pub fn generate_random_bytes(len: u32) -> Vec<u8> {
    aether_primitives::rng::random_bytes(len as usize)
}

/// `SHAKE-256(input || label)` — ilova darajasida bir xil `shared_secret`dan
/// deterministik hosila qiymatlar (masalan Compress-KEM `base_seed`/`session_id`)
/// olish uchun, qo'shimcha xabar almashishga hojatsiz.
#[uniffi::export]
pub fn derive_bytes(input: Vec<u8>, label: Vec<u8>, len: u32) -> Vec<u8> {
    aether_primitives::hash::shake256_concat(&[&input, &label], len as usize)
}

/// DEFAULT (0x01) profil bo'yicha sender tomonida encapsulate qiladi.
#[uniffi::export]
pub fn default_encapsulate(pk_mlkem: Vec<u8>, pk_x25519: Vec<u8>) -> Result<DefaultEncapsulation, AetherError> {
    let (ct_mlkem, ss_mlkem) =
        MlKem768Kem::encapsulate(&pk_mlkem).map_err(|_| AetherError::OperationFailed)?;
    let (ct_x25519, ss_x25519) =
        X25519Kem::encapsulate(&pk_x25519).map_err(|_| AetherError::OperationFailed)?;
    let ss = combine_default(&ss_mlkem, &ss_x25519, &ct_x25519, &pk_x25519);
    Ok(DefaultEncapsulation {
        ct_mlkem,
        ct_x25519,
        shared_secret: ss.to_vec(),
    })
}

/// DEFAULT (0x01) profil bo'yicha recipient tomonida decapsulate qiladi.
#[uniffi::export]
pub fn default_decapsulate(
    sk_mlkem: Vec<u8>,
    sk_x25519: Vec<u8>,
    pk_x25519: Vec<u8>,
    ct_mlkem: Vec<u8>,
    ct_x25519: Vec<u8>,
) -> Result<Vec<u8>, AetherError> {
    let ss_mlkem =
        MlKem768Kem::decapsulate(&sk_mlkem, &ct_mlkem).map_err(|_| AetherError::OperationFailed)?;
    let ss_x25519 =
        X25519Kem::decapsulate(&sk_x25519, &ct_x25519).map_err(|_| AetherError::OperationFailed)?;
    let ss = combine_default(&ss_mlkem, &ss_x25519, &ct_x25519, &pk_x25519);
    Ok(ss.to_vec())
}

/// AUTH-AKEM (0x05) — sender tomoni: encapsulate + transcript sign + combine.
#[uniffi::export]
pub fn akem_encapsulate(
    pk_recip_mlkem: Vec<u8>,
    pk_recip_x25519_static: Vec<u8>,
    sk_sender_sign: Vec<u8>,
    pk_sender_sign: Vec<u8>,
    pk_recip_sign: Vec<u8>,
) -> Result<AkemEncapsulation, AetherError> {
    let (ct_mlkem, ct_x25519, signature, shared_secret) =
        aether_core::akem::encapsulate::<MlKem768Kem, X25519Kem, Ed25519Signer>(
            &pk_recip_mlkem,
            &pk_recip_x25519_static,
            &sk_sender_sign,
            &pk_sender_sign,
            &pk_recip_sign,
        )
        .map_err(|_| AetherError::OperationFailed)?;
    Ok(AkemEncapsulation {
        ct_mlkem,
        ct_x25519,
        signature,
        shared_secret: shared_secret.to_vec(),
    })
}

/// AUTH-AKEM (0x05) — recipient tomoni: transcript qayta hisoblanadi, imzo tekshiriladi.
/// Imzo yaroqsiz bo'lsa ham xato qaytarilmaydi — Implicit Rejection natijasi qaytariladi
/// (S1/S2: constant-time, oracle'ga qarshi himoya — `aether_core::akem` qarang).
#[uniffi::export]
#[allow(clippy::too_many_arguments)]
pub fn akem_decapsulate(
    sk_recip_mlkem: Vec<u8>,
    sk_recip_x25519_static: Vec<u8>,
    pk_recip_x25519_static: Vec<u8>,
    z_recip: Vec<u8>,
    pk_sender_sign: Vec<u8>,
    pk_recip_sign: Vec<u8>,
    ct_mlkem: Vec<u8>,
    ct_x25519: Vec<u8>,
    signature: Vec<u8>,
) -> Vec<u8> {
    aether_core::akem::decapsulate::<MlKem768Kem, X25519Kem, Ed25519Signer>(
        &sk_recip_mlkem,
        &sk_recip_x25519_static,
        &pk_recip_x25519_static,
        &z_recip,
        &pk_sender_sign,
        &pk_recip_sign,
        &ct_mlkem,
        &ct_x25519,
        &signature,
    )
    .to_vec()
}

/// Compress-KEM (0x04) — bitta yo'nalishdagi yuboruvchi ratchet holati.
#[derive(uniffi::Object)]
pub struct CompressSenderHandle {
    inner: Mutex<CompressSender>,
}

#[uniffi::export]
impl CompressSenderHandle {
    #[uniffi::constructor]
    pub fn new(session_id: Vec<u8>, base_seed: Vec<u8>) -> Result<Arc<Self>, AetherError> {
        let sid: [u8; 8] = session_id.try_into().map_err(|_| AetherError::OperationFailed)?;
        Ok(Arc::new(Self {
            inner: Mutex::new(CompressSender::new(sid, base_seed)),
        }))
    }

    /// Yangi ratchet qadami: yangi ephemeral X25519 juftlik + 77-baytli frame.
    pub fn next_frame(&self, recipient_pk_x25519: Vec<u8>) -> Result<CompressFrameResult, AetherError> {
        let mut sender = self.inner.lock().map_err(|_| AetherError::OperationFailed)?;
        let (frame, shared_secret) = sender
            .next_frame::<X25519Kem>(&recipient_pk_x25519)
            .map_err(|_| AetherError::OperationFailed)?;
        Ok(CompressFrameResult {
            frame: frame.to_vec(),
            shared_secret: shared_secret.to_vec(),
        })
    }

    pub fn needs_rekey(&self) -> bool {
        self.inner
            .lock()
            .map(|s| s.needs_rekey())
            .unwrap_or(true)
    }
}

/// Compress-KEM (0x04) — bitta yo'nalishdagi qabul qiluvchi ratchet holati
/// (delta_tag tekshiruvi + replay-himoya bitmap).
#[derive(uniffi::Object)]
pub struct CompressRecipientHandle {
    inner: Mutex<CompressRecipient>,
}

#[uniffi::export]
impl CompressRecipientHandle {
    #[uniffi::constructor]
    pub fn new(session_id: Vec<u8>, base_seed: Vec<u8>) -> Result<Arc<Self>, AetherError> {
        let sid: [u8; 8] = session_id.try_into().map_err(|_| AetherError::OperationFailed)?;
        Ok(Arc::new(Self {
            inner: Mutex::new(CompressRecipient::new(sid, base_seed)),
        }))
    }

    pub fn accept_frame(&self, frame: Vec<u8>, sk_x25519: Vec<u8>) -> Result<Vec<u8>, AetherError> {
        let mut recipient = self.inner.lock().map_err(|_| AetherError::OperationFailed)?;
        recipient
            .accept_frame::<X25519Kem>(&frame, &sk_x25519)
            .map(|s| s.to_vec())
            .map_err(|_| AetherError::OperationFailed)
    }
}

/// Handshake yoki ratchet qadamidan olingan `shared_secret` orqali bitta record'ni
/// muhrlaydi (ChaCha20-Poly1305). `profile_id` faqat AAD'ga yozilgan meta-belgi.
#[uniffi::export]
pub fn seal_record(
    profile_id: u8,
    shared_secret: Vec<u8>,
    session_id: Vec<u8>,
    is_client_to_server: bool,
    counter: u32,
    plaintext: Vec<u8>,
) -> Result<Vec<u8>, AetherError> {
    let keys = record::derive_record_keys(&shared_secret);
    let dir = if is_client_to_server { &keys.c2s } else { &keys.s2c };
    let sid: [u8; 8] = session_id
        .try_into()
        .map_err(|_| AetherError::OperationFailed)?;
    record::seal_record(AeadAlgorithm::ChaCha20Poly1305, dir, profile_id, sid, counter, &plaintext)
        .map_err(|_| AetherError::OperationFailed)
}

/// `seal_record` bilan yaratilgan record'ni ochadi va plaintext'ni qaytaradi.
#[uniffi::export]
pub fn open_record(
    profile_id: u8,
    shared_secret: Vec<u8>,
    session_id: Vec<u8>,
    is_client_to_server: bool,
    frame: Vec<u8>,
) -> Result<Vec<u8>, AetherError> {
    let keys = record::derive_record_keys(&shared_secret);
    let dir = if is_client_to_server { &keys.c2s } else { &keys.s2c };
    let sid: [u8; 8] = session_id
        .try_into()
        .map_err(|_| AetherError::OperationFailed)?;
    let (_counter, plaintext) =
        record::open_record(AeadAlgorithm::ChaCha20Poly1305, dir, profile_id, sid, &frame)
            .map_err(|_| AetherError::OperationFailed)?;
    Ok(plaintext)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ffi_default_profile_and_record_roundtrip() {
        let mlkem_kp = generate_mlkem768_keypair();
        let x_kp = generate_x25519_keypair();

        let encaps = default_encapsulate(mlkem_kp.public_key.clone(), x_kp.public_key.clone()).unwrap();
        let ss_recv = default_decapsulate(
            mlkem_kp.secret_key,
            x_kp.secret_key,
            x_kp.public_key,
            encaps.ct_mlkem,
            encaps.ct_x25519,
        )
        .unwrap();
        assert_eq!(encaps.shared_secret, ss_recv);

        let session_id = vec![1u8, 2, 3, 4, 5, 6, 7, 8];
        let frame = seal_record(0x01, ss_recv.clone(), session_id.clone(), true, 1, b"ffi smoke test".to_vec())
            .unwrap();
        let plaintext = open_record(0x01, ss_recv, session_id, true, frame).unwrap();
        assert_eq!(plaintext, b"ffi smoke test");
    }

    #[test]
    fn ffi_akem_handshake_roundtrip() {
        let mlkem_kp = generate_mlkem768_keypair();
        let x_kp = generate_x25519_keypair();
        let sender_sign_kp = generate_ed25519_keypair();
        let recip_sign_kp = generate_ed25519_keypair();
        let z_recip = generate_random_bytes(32);

        let encaps = akem_encapsulate(
            mlkem_kp.public_key.clone(),
            x_kp.public_key.clone(),
            sender_sign_kp.secret_key.clone(),
            sender_sign_kp.public_key.clone(),
            recip_sign_kp.public_key.clone(),
        )
        .unwrap();

        let ss_recv = akem_decapsulate(
            mlkem_kp.secret_key,
            x_kp.secret_key,
            x_kp.public_key,
            z_recip,
            sender_sign_kp.public_key,
            recip_sign_kp.public_key,
            encaps.ct_mlkem,
            encaps.ct_x25519,
            encaps.signature,
        );

        assert_eq!(encaps.shared_secret, ss_recv);
    }

    #[test]
    fn ffi_compress_ratchet_roundtrip() {
        let x_kp = generate_x25519_keypair();
        let session_id = generate_random_bytes(8);
        let base_seed = generate_random_bytes(32);

        let sender = CompressSenderHandle::new(session_id.clone(), base_seed.clone()).unwrap();
        let recipient = CompressRecipientHandle::new(session_id, base_seed).unwrap();

        let step1 = sender.next_frame(x_kp.public_key.clone()).unwrap();
        assert_eq!(step1.frame.len(), 77);
        let ss1_recv = recipient.accept_frame(step1.frame, x_kp.secret_key.clone()).unwrap();
        assert_eq!(step1.shared_secret, ss1_recv);

        let step2 = sender.next_frame(x_kp.public_key.clone()).unwrap();
        let ss2_recv = recipient.accept_frame(step2.frame, x_kp.secret_key).unwrap();
        assert_eq!(step2.shared_secret, ss2_recv);
        assert_ne!(step1.shared_secret, step2.shared_secret);
    }
}
