//! liboqs (mustaqil C implementatsiyasi) yaratgan ML-DSA-65 imzosini tasdiqlash.
//! Vektor `scripts/interop_liboqs.py` bilan yaratiladi.

use std::path::PathBuf;

use ml_dsa::{EncodedSignature, EncodedVerifyingKey, MlDsa65, Signature, VerifyingKey};
use serde_json::Value;
use tamga_core::b64;

fn hex(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}

#[test]
fn liboqs_signature_verifies_in_rust() {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../spec/test-vectors/interop-liboqs.json");
    let v: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    let s = |k: &str| v[k].as_str().unwrap();

    let pk = b64::decode(s("public_key")).unwrap();
    let sig = b64::decode(s("signature")).unwrap();
    let msg = hex(s("message_hex"));
    let ctx = s("context").as_bytes();

    let vk = VerifyingKey::<MlDsa65>::decode(
        &EncodedVerifyingKey::<MlDsa65>::try_from(pk.as_slice()).unwrap(),
    );
    let sig = Signature::<MlDsa65>::decode(
        &EncodedSignature::<MlDsa65>::try_from(sig.as_slice()).unwrap(),
    )
    .unwrap();

    assert!(
        vk.verify_with_context(&msg, ctx, &sig),
        "liboqs imzosi Rust'da tasdiqlanmadi"
    );
    assert!(!vk.verify_with_context(&msg, b"boshqa", &sig));
    let mut tampered = msg.clone();
    tampered[0] ^= 1;
    assert!(!vk.verify_with_context(&tampered, ctx, &sig));
}
