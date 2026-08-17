//! Compress-KEM (`profile_id = 0x04`) — spec 4.2-bo'lim: Stateful Delta Compression Engine.

use crate::profile::AetherProfile;
use crate::replay::ReplayWindow;
use crate::{CoreError, Secret};
use aether_primitives::hash::sha3_256_concat;
use aether_primitives::Kem;
use subtle::ConstantTimeEq;
use zeroize::Zeroizing;

/// `profile_id(1B) || session_id(8B) || counter(4B) || ct_X(32B) || delta_tag(32B)`
pub const FRAME_LEN: usize = 77;

fn delta_tag(base_seed: &[u8], counter: u32, ct_x: &[u8]) -> [u8; 32] {
    sha3_256_concat(&[base_seed, &counter.to_be_bytes(), ct_x])
}

/// Yuboruvchi tomon session holati: har bir `next_frame` chaqiruvi bitta ratchet
/// qadamini (yangi X25519 ephemeral juftlik) bildiradi.
pub struct CompressSender {
    session_id: [u8; 8],
    base_seed: Secret,
    counter: u32,
}

impl CompressSender {
    pub fn new(session_id: [u8; 8], base_seed: Vec<u8>) -> Self {
        Self {
            session_id,
            base_seed: Zeroizing::new(base_seed),
            counter: 0,
        }
    }

    /// Yangi Compress-KEM frame generatsiya qiladi va shu qadamning shared secret'ini qaytaradi.
    pub fn next_frame<X: Kem>(&mut self, recipient_pk_x25519: &[u8]) -> Result<([u8; FRAME_LEN], Secret), CoreError> {
        let (ct_x, ss_x) = X::encapsulate(recipient_pk_x25519).map_err(|_| CoreError::DecryptFailure)?;
        self.counter = self.counter.checked_add(1).ok_or(CoreError::DecryptFailure)?;
        let tag = delta_tag(&self.base_seed, self.counter, &ct_x);

        let mut frame = [0u8; FRAME_LEN];
        frame[0] = AetherProfile::Compress.as_byte();
        frame[1..9].copy_from_slice(&self.session_id);
        frame[9..13].copy_from_slice(&self.counter.to_be_bytes());
        frame[13..45].copy_from_slice(&ct_x);
        frame[45..77].copy_from_slice(&tag);

        Ok((frame, ss_x))
    }

    /// Joriy counter 32-bit chegaraga yaqinlashganda majburiy to'liq handshake (rekey)
    /// zarurligini bildiradi.
    pub fn needs_rekey(&self) -> bool {
        self.counter == u32::MAX
    }
}

/// Qabul qiluvchi tomon session holati: `delta_tag` tekshiruvi va replay-himoya bilan.
pub struct CompressRecipient {
    session_id: [u8; 8],
    base_seed: Secret,
    replay: ReplayWindow,
}

impl CompressRecipient {
    pub fn new(session_id: [u8; 8], base_seed: Vec<u8>) -> Self {
        Self {
            session_id,
            base_seed: Zeroizing::new(base_seed),
            replay: ReplayWindow::new(),
        }
    }

    /// Kelgan frame'ni tekshiradi (profil, session_id, delta_tag, replay) va yaroqli
    /// bo'lsa shared secret'ni qaytaradi. Har qanday nomuvofiqlik yagona
    /// `CoreError::DecryptFailure` bilan qaytariladi (7.4 xato siyosati).
    pub fn accept_frame<X: Kem>(&mut self, frame: &[u8], sk_x25519: &[u8]) -> Result<Secret, CoreError> {
        if frame.len() != FRAME_LEN {
            return Err(CoreError::DecryptFailure);
        }
        if frame[0] != AetherProfile::Compress.as_byte() {
            return Err(CoreError::DecryptFailure);
        }
        if frame[1..9] != self.session_id {
            return Err(CoreError::DecryptFailure);
        }

        let counter = u32::from_be_bytes(frame[9..13].try_into().unwrap());
        let ct_x = &frame[13..45];
        let tag = &frame[45..77];

        let expected_tag = delta_tag(&self.base_seed, counter, ct_x);
        if expected_tag[..].ct_eq(tag).unwrap_u8() == 0 {
            return Err(CoreError::DecryptFailure);
        }

        if !self.replay.check_and_update(counter) {
            return Err(CoreError::DecryptFailure);
        }

        X::decapsulate(sk_x25519, ct_x).map_err(|_| CoreError::DecryptFailure)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aether_primitives::kem_x25519::X25519Kem;

    #[test]
    fn sender_recipient_agree_and_reject_replay() {
        let (recipient_pk, recipient_sk) = X25519Kem::keypair();
        let session_id = [7u8; 8];
        let base_seed = vec![9u8; 32];

        let mut sender = CompressSender::new(session_id, base_seed.clone());
        let mut recipient = CompressRecipient::new(session_id, base_seed);

        let (frame1, ss1) = sender.next_frame::<X25519Kem>(&recipient_pk).unwrap();
        let ss1_recv = recipient.accept_frame::<X25519Kem>(&frame1, &recipient_sk).unwrap();
        assert_eq!(&*ss1, &*ss1_recv);
        assert_eq!(frame1.len(), FRAME_LEN);

        // Replay of the same frame must be rejected.
        assert!(recipient.accept_frame::<X25519Kem>(&frame1, &recipient_sk).is_err());

        let (frame2, ss2) = sender.next_frame::<X25519Kem>(&recipient_pk).unwrap();
        let ss2_recv = recipient.accept_frame::<X25519Kem>(&frame2, &recipient_sk).unwrap();
        assert_eq!(&*ss2, &*ss2_recv);
    }

    #[test]
    fn tampered_delta_tag_is_rejected() {
        let (recipient_pk, recipient_sk) = X25519Kem::keypair();
        let session_id = [1u8; 8];
        let base_seed = vec![2u8; 32];

        let mut sender = CompressSender::new(session_id, base_seed.clone());
        let mut recipient = CompressRecipient::new(session_id, base_seed);

        let (mut frame, _ss) = sender.next_frame::<X25519Kem>(&recipient_pk).unwrap();
        frame[FRAME_LEN - 1] ^= 0xFF;
        assert!(recipient.accept_frame::<X25519Kem>(&frame, &recipient_sk).is_err());
    }
}
