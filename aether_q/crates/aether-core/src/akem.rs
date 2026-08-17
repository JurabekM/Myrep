//! AUTH-AKEM (`profile_id = 0x05`) — spec 4.1-bo'lim: Single-Pass Authenticated KEM.
//!
//! Transcript -> Sign -> Combiner -> Implicit-Rejection zanjiri.

use crate::labels::{AKEM_LABEL, REJECT_LABEL};
use crate::Secret;
use aether_primitives::hash::sha3_256_concat;
use aether_primitives::{Kem, Signer};
use subtle::{Choice, ConditionallySelectable};
use zeroize::Zeroizing;

/// 1. Transcript = SHA3-256(AKEM_LABEL || pk_sender_sign || pk_recip_sign || ct_M || ct_X)
pub fn transcript(pk_sender_sign: &[u8], pk_recip_sign: &[u8], ct_mlkem: &[u8], ct_x25519: &[u8]) -> [u8; 32] {
    sha3_256_concat(&[AKEM_LABEL, pk_sender_sign, pk_recip_sign, ct_mlkem, ct_x25519])
}

/// 3. SharedSecret = SHA3-256(ss_M || ss_X || ct_X || pk_X || Sig || AKEM_LABEL)
pub fn combine(ss_mlkem: &[u8], ss_x25519: &[u8], ct_x25519: &[u8], pk_x25519: &[u8], sig: &[u8]) -> [u8; 32] {
    sha3_256_concat(&[ss_mlkem, ss_x25519, ct_x25519, pk_x25519, sig, AKEM_LABEL])
}

/// 4. SharedSecret_reject = SHA3-256("REJECT" || Sig || z_recip)
///
/// `z_recip` — `sk_recip_X` bilan birga saqlanadigan, faqat rejection uchun mo'ljallangan
/// alohida tasodifiy qiymat (FIPS 203 implicit-rejection dizayniga mos domain separation).
pub fn reject_secret(sig: &[u8], z_recip: &[u8]) -> [u8; 32] {
    sha3_256_concat(&[REJECT_LABEL, sig, z_recip])
}

/// `(ct_mlkem, ct_x25519, signature, shared_secret)` — birinchi uchtasi ochiq
/// (wire'ga chiqadigan) qiymatlar, oxirgisi maxfiy.
pub type EncapsulationOutput = (Vec<u8>, Vec<u8>, Vec<u8>, Secret);

/// Sender tomoni: ML-KEM va X25519 orqali encapsulate qiladi, transcript'ni imzolaydi
/// va SharedSecret'ni combine qiladi.
pub fn encapsulate<M: Kem, X: Kem, S: Signer>(
    pk_recip_mlkem: &[u8],
    pk_recip_x25519_static: &[u8],
    sk_sender_sign: &[u8],
    pk_sender_sign: &[u8],
    pk_recip_sign: &[u8],
) -> Result<EncapsulationOutput, aether_primitives::PrimitiveError> {
    let (ct_mlkem, ss_mlkem) = M::encapsulate(pk_recip_mlkem)?;
    let (ct_x25519, ss_x25519) = X::encapsulate(pk_recip_x25519_static)?;

    let tr = transcript(pk_sender_sign, pk_recip_sign, &ct_mlkem, &ct_x25519);
    let sig = S::sign(sk_sender_sign, &tr)?;

    let ss = combine(&ss_mlkem, &ss_x25519, &ct_x25519, pk_recip_x25519_static, &sig);
    Ok((ct_mlkem, ct_x25519, sig, Zeroizing::new(ss.to_vec())))
}

/// Qabul qiluvchi tomon: imzoni tekshiradi va SharedSecret'ni tiklaydi.
///
/// Imzo yaroqsiz bo'lsa ham funksiya xato qaytarmaydi — S1/S2 talablariga muvofiq,
/// haqiqiy va reject shared secret'lar har doim hisoblanadi va constant-time tanlanadi.
#[allow(clippy::too_many_arguments)]
pub fn decapsulate<M: Kem, X: Kem, S: Signer>(
    sk_recip_mlkem: &[u8],
    sk_recip_x25519_static: &[u8],
    pk_recip_x25519_static: &[u8],
    z_recip: &[u8],
    pk_sender_sign: &[u8],
    pk_recip_sign: &[u8],
    ct_mlkem: &[u8],
    ct_x25519: &[u8],
    sig: &[u8],
) -> Secret {
    let tr = transcript(pk_sender_sign, pk_recip_sign, ct_mlkem, ct_x25519);
    let sig_valid: Choice = Choice::from(S::verify(pk_sender_sign, &tr, sig).is_ok() as u8);

    // Har ikki yo'l — real va reject — har doim to'liq hisoblanadi (S1: constant-time).
    let ss_real = {
        let ss_mlkem = M::decapsulate(sk_recip_mlkem, ct_mlkem).unwrap_or_default();
        let ss_x25519 = X::decapsulate(sk_recip_x25519_static, ct_x25519).unwrap_or_default();
        combine(&ss_mlkem, &ss_x25519, ct_x25519, pk_recip_x25519_static, sig)
    };
    let ss_reject = reject_secret(sig, z_recip);

    let mut out = [0u8; 32];
    for i in 0..32 {
        out[i] = u8::conditional_select(&ss_reject[i], &ss_real[i], sig_valid);
    }
    Zeroizing::new(out.to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;
    use aether_primitives::kem_mlkem768::MlKem768Kem;
    use aether_primitives::kem_x25519::X25519Kem;
    use aether_primitives::sig_ed25519::Ed25519Signer;

    #[test]
    fn round_trip_succeeds_and_matches() {
        let (pk_recip_mlkem, sk_recip_mlkem) = MlKem768Kem::keypair();
        let (pk_recip_x, sk_recip_x) = X25519Kem::keypair();
        let (pk_sender_sign, sk_sender_sign) = Ed25519Signer::keypair();
        let (pk_recip_sign, _sk_recip_sign) = Ed25519Signer::keypair();
        let z_recip = vec![0x11u8; 32];

        let (ct_mlkem, ct_x, sig, ss_sender) =
            encapsulate::<MlKem768Kem, X25519Kem, Ed25519Signer>(
                &pk_recip_mlkem,
                &pk_recip_x,
                &sk_sender_sign,
                &pk_sender_sign,
                &pk_recip_sign,
            )
            .unwrap();

        let ss_recip = decapsulate::<MlKem768Kem, X25519Kem, Ed25519Signer>(
            &sk_recip_mlkem,
            &sk_recip_x,
            &pk_recip_x,
            &z_recip,
            &pk_sender_sign,
            &pk_recip_sign,
            &ct_mlkem,
            &ct_x,
            &sig,
        );

        assert_eq!(&*ss_sender, &*ss_recip);
    }

    #[test]
    fn forged_signature_triggers_deterministic_implicit_rejection() {
        let (pk_recip_mlkem, sk_recip_mlkem) = MlKem768Kem::keypair();
        let (pk_recip_x, sk_recip_x) = X25519Kem::keypair();
        let (pk_sender_sign, sk_sender_sign) = Ed25519Signer::keypair();
        let (pk_recip_sign, _) = Ed25519Signer::keypair();
        let z_recip = vec![0x22u8; 32];

        let (ct_mlkem, ct_x, sig, ss_sender) =
            encapsulate::<MlKem768Kem, X25519Kem, Ed25519Signer>(
                &pk_recip_mlkem,
                &pk_recip_x,
                &sk_sender_sign,
                &pk_sender_sign,
                &pk_recip_sign,
            )
            .unwrap();

        let mut forged_sig = sig.clone();
        let last = forged_sig.len() - 1;
        forged_sig[last] ^= 0xFF;

        let ss_reject_1 = decapsulate::<MlKem768Kem, X25519Kem, Ed25519Signer>(
            &sk_recip_mlkem,
            &sk_recip_x,
            &pk_recip_x,
            &z_recip,
            &pk_sender_sign,
            &pk_recip_sign,
            &ct_mlkem,
            &ct_x,
            &forged_sig,
        );
        let ss_reject_2 = decapsulate::<MlKem768Kem, X25519Kem, Ed25519Signer>(
            &sk_recip_mlkem,
            &sk_recip_x,
            &pk_recip_x,
            &z_recip,
            &pk_sender_sign,
            &pk_recip_sign,
            &ct_mlkem,
            &ct_x,
            &forged_sig,
        );

        // Reject path must be deterministic given identical inputs...
        assert_eq!(&*ss_reject_1, &*ss_reject_2);
        // ...and must never equal the legitimate shared secret.
        assert_ne!(&*ss_reject_1, &*ss_sender);
    }
}
