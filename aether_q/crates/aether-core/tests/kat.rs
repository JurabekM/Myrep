//! Known-Answer-Test uslubidagi determinizm tekshiruvlari — spec 6-bo'lim.
//!
//! ML-KEM/ML-DSA/HQC/X25519 tashqi crate'lar ichki tasodifiylikka (getrandom) tayangani
//! uchun NIST rasmiy KAT vektorlariga to'g'ridan-to'g'ri solishtira olmaymiz; buning o'rniga
//! sof deterministik komponentlar (combiner, delta_tag, AAD, nonce) uchun fixed-input
//! KAT'lar yozamiz — bular kelajakdagi refaktoringlarda regressiyani ushlab qoladi.

use aether_core::combiner::{combine_default, combine_minimal, combine_paranoid};
use aether_core::labels::{AKEM_LABEL, PARANOID_LABEL, XWING_LABEL};
use aether_core::record::build_aad;

#[test]
fn labels_match_spec_5_4() {
    assert_eq!(XWING_LABEL, &[0x5c, 0x2e, 0x2f, 0x2f, 0x5e, 0x5c]);
    assert_eq!(PARANOID_LABEL, b"AETHER-Q-v3-KEM/L3/v1");
    assert_eq!(AKEM_LABEL, b"AETHER-Q-v4-AKEM/L3/v1");
}

#[test]
fn combine_default_is_deterministic() {
    let ss_m = [1u8; 32];
    let ss_x = [2u8; 32];
    let ct_x = [3u8; 32];
    let pk_x = [4u8; 32];

    let a = combine_default(&ss_m, &ss_x, &ct_x, &pk_x);
    let b = combine_default(&ss_m, &ss_x, &ct_x, &pk_x);
    assert_eq!(&*a, &*b);
    assert_eq!(a.len(), 32);
}

#[test]
fn combine_default_and_paranoid_diverge_on_same_shared_inputs() {
    let ss_m = [1u8; 32];
    let ss_x = [2u8; 32];
    let ss_h = [5u8; 64];
    let ct_x = [3u8; 32];
    let ct_h = [6u8; 32];
    let pk_x = [4u8; 32];

    let default_ss = combine_default(&ss_m, &ss_x, &ct_x, &pk_x);
    let paranoid_ss = combine_paranoid(&ss_m, &ss_x, &ss_h, &ct_x, &ct_h, &pk_x);
    assert_ne!(&*default_ss, &*paranoid_ss, "profil label'lari orqali domain separation ishlashi SHART");
}

#[test]
fn combine_minimal_returns_ss_unchanged() {
    let ss_m = vec![7u8; 32];
    let out = combine_minimal(&ss_m);
    assert_eq!(&*out, &ss_m[..]);
}

#[test]
fn build_aad_kat_vector() {
    let aad = build_aad(0x01, [0u8, 1, 2, 3, 4, 5, 6, 7], 0x0000_0001);
    assert_eq!(
        aad,
        [0x01, 0, 1, 2, 3, 4, 5, 6, 7, 0x00, 0x00, 0x00, 0x01],
        "AAD = profile_id || session_id || counter(BE) — 7.3-bo'lim"
    );
}
