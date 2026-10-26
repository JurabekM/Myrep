//! Real dunyo attestatsiya zanjirlari: RSA va ECDSA P-384 imzolovchilar, Google ildizlari.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::ports::SecurityLevel;
use mpay_pqlink::attestation::{verify_chain, AttestationPolicy, TrustAnchors};
use p256::ecdsa::signature::Signer;
use p256::ecdsa::{DerSignature, SigningKey};
use p256::pkcs8::DecodePrivateKey;
use serde_json::Value;

fn fixture() -> Value {
    serde_json::from_str(include_str!("data/attest_rsa_p384.json")).unwrap()
}

fn hexs(v: &Value) -> Vec<u8> {
    hex::decode(v.as_str().unwrap()).unwrap()
}

const NOW: i64 = 1_800_000_000;

#[test]
fn rsa_root_p384_intermediate_chain_verifies() {
    let f = fixture();
    let chain: Vec<Vec<u8>> = f["chain"].as_array().unwrap().iter().map(hexs).collect();
    let anchors = TrustAnchors::from_der(&[hexs(&f["root"])]).unwrap();
    let v = verify_chain(&chain, &anchors, &AttestationPolicy::default(), NOW).unwrap();
    assert_eq!(v.security_level, SecurityLevel::StrongBox);
    assert_eq!(v.attestation_challenge, b"fixture");

    // Ildizsiz zanjir (leaf + oraliq) ham RSA ildizga bog'lanadi.
    assert!(verify_chain(&chain[..2], &anchors, &AttestationPolicy::default(), NOW).is_ok());

    // Leaf kaliti bilan qurilma imzosi.
    let sk = SigningKey::from_pkcs8_der(&hexs(&f["leaf_pkcs8"])).unwrap();
    let sig: DerSignature = sk.sign(b"th2");
    v.verify_signature(b"th2", sig.as_bytes()).unwrap();
}

#[test]
fn tampered_rsa_or_p384_signature_rejected() {
    let f = fixture();
    let anchors = TrustAnchors::from_der(&[hexs(&f["root"])]).unwrap();
    for idx in [0usize, 1] {
        let mut chain: Vec<Vec<u8>> = f["chain"].as_array().unwrap().iter().map(hexs).collect();
        let n = chain[idx].len();
        chain[idx][n - 5] ^= 0x01;
        assert!(
            verify_chain(&chain, &anchors, &AttestationPolicy::default(), NOW).is_err(),
            "idx {idx}"
        );
    }
}

#[test]
fn google_roots_load_and_reject_foreign_chain() {
    let pem = include_str!("../../../config/google-attestation-roots.pem");
    let google = TrustAnchors::from_pem(pem).unwrap();
    assert_eq!(google.len(), 2);
    let f = fixture();
    let chain: Vec<Vec<u8>> = f["chain"].as_array().unwrap().iter().map(hexs).collect();
    assert!(verify_chain(&chain, &google, &AttestationPolicy::default(), NOW).is_err());
}
