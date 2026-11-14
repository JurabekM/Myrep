//! NIST ACVP vektorlari (FIPS 203 ML-KEM-768, FIPS 204 ML-DSA-65) — biz ishlatadigan
//! `ml-kem` va `ml-dsa` crate versiyalari standartga mos ekanini tekshiradi.
//! Manba va qism ajratish: `scripts/trim_acvp.py`, `testvectors/acvp/`.
#![allow(clippy::unwrap_used, clippy::expect_used, deprecated)]

use ml_dsa::{
    EncodedSignature, EncodedVerifyingKey, ExpandedSigningKey, ExpandedSigningKeyBytes, Keypair,
    MlDsa65, Signature, SigningKey, VerifyingKey,
};
use ml_kem::kem::{Decapsulate, KeyExport};
use ml_kem::{DecapsulationKey768, EncapsulationKey768, ExpandedKeyEncoding};
use serde_json::Value;

fn load(name: &str) -> Value {
    let p = format!(
        "{}/../../testvectors/acvp/{name}.json",
        env!("CARGO_MANIFEST_DIR")
    );
    serde_json::from_str(&std::fs::read_to_string(p).unwrap()).unwrap()
}

fn h(v: &Value) -> Vec<u8> {
    hex::decode(v.as_str().unwrap()).unwrap()
}

fn groups(doc: &Value) -> impl Iterator<Item = &Value> {
    doc["testGroups"].as_array().unwrap().iter()
}

fn tests(g: &Value) -> impl Iterator<Item = &Value> {
    g["tests"].as_array().unwrap().iter()
}

#[test]
fn ml_kem_768_keygen() {
    let mut n = 0;
    for g in groups(&load("ml-kem-768-keygen")) {
        for t in tests(g) {
            let seed = [h(&t["d"]), h(&t["z"])].concat();
            let dk = DecapsulationKey768::from_seed(seed.as_slice().try_into().unwrap());
            assert_eq!(
                dk.encapsulation_key().to_bytes().to_vec(),
                h(&t["ek"]),
                "tcId {}",
                t["tcId"]
            );
            assert_eq!(
                dk.to_expanded_bytes().to_vec(),
                h(&t["dk"]),
                "tcId {}",
                t["tcId"]
            );
            n += 1;
        }
    }
    assert_eq!(n, 10);
}

#[test]
fn ml_kem_768_encap_decap_and_key_checks() {
    let mut counts = [0usize; 4];
    for g in groups(&load("ml-kem-768-encapdecap")) {
        let func = g["function"].as_str().unwrap();
        for t in tests(g) {
            let id = &t["tcId"];
            match func {
                "encapsulation" => {
                    let ek = EncapsulationKey768::new(h(&t["ek"]).as_slice().try_into().unwrap())
                        .unwrap();
                    let (c, k) =
                        ek.encapsulate_deterministic(h(&t["m"]).as_slice().try_into().unwrap());
                    assert_eq!(c.to_vec(), h(&t["c"]), "tcId {id}");
                    assert_eq!(k.to_vec(), h(&t["k"]), "tcId {id}");
                    counts[0] += 1;
                }
                "decapsulation" => {
                    let dk = DecapsulationKey768::from_expanded_bytes(
                        h(&t["dk"]).as_slice().try_into().unwrap(),
                    )
                    .unwrap();
                    let k = dk.decapsulate(h(&t["c"]).as_slice().try_into().unwrap());
                    assert_eq!(k.to_vec(), h(&t["k"]), "tcId {id}");
                    counts[1] += 1;
                }
                "encapsulationKeyCheck" => {
                    let ok = EncapsulationKey768::new(h(&t["ek"]).as_slice().try_into().unwrap())
                        .is_ok();
                    assert_eq!(ok, t["testPassed"].as_bool().unwrap(), "tcId {id}");
                    counts[2] += 1;
                }
                "decapsulationKeyCheck" => {
                    let ok = DecapsulationKey768::from_expanded_bytes(
                        h(&t["dk"]).as_slice().try_into().unwrap(),
                    )
                    .is_ok();
                    assert_eq!(ok, t["testPassed"].as_bool().unwrap(), "tcId {id}");
                    counts[3] += 1;
                }
                other => panic!("kutilmagan funksiya {other}"),
            }
        }
    }
    assert_eq!(counts, [10, 10, 10, 10]);
}

#[test]
fn ml_dsa_65_keygen() {
    let mut n = 0;
    for g in groups(&load("ml-dsa-65-keygen")) {
        for t in tests(g) {
            let seed: [u8; 32] = h(&t["seed"]).try_into().unwrap();
            let sk = SigningKey::<MlDsa65>::from_seed(&seed.into());
            assert_eq!(
                sk.verifying_key().encode().to_vec(),
                h(&t["pk"]),
                "tcId {}",
                t["tcId"]
            );
            assert_eq!(
                sk.expanded_key().to_expanded().to_vec(),
                h(&t["sk"]),
                "tcId {}",
                t["tcId"]
            );
            n += 1;
        }
    }
    assert_eq!(n, 10);
}

fn expanded(sk: &[u8]) -> ExpandedSigningKey<MlDsa65> {
    let b = ExpandedSigningKeyBytes::<MlDsa65>::try_from(sk).unwrap();
    ExpandedSigningKey::<MlDsa65>::from_expanded(&b)
}

#[test]
fn ml_dsa_65_siggen() {
    let mut seen = std::collections::BTreeSet::new();
    for g in groups(&load("ml-dsa-65-siggen")) {
        let external = g["signatureInterface"] == "external";
        let det = g["deterministic"].as_bool().unwrap();
        for t in tests(g) {
            let sk = expanded(&h(&t["sk"]));
            let msg = h(&t["message"]);
            let rnd: [u8; 32] = if det {
                [0; 32]
            } else {
                h(&t["rnd"]).try_into().unwrap()
            };
            let sig = if external {
                let ctx = h(&t["context"]);
                if det {
                    sk.sign_deterministic(&msg, &ctx).unwrap()
                } else {
                    // FIPS 204 Algorithm 2: M' = 0 ‖ |ctx| ‖ ctx ‖ M
                    sk.sign_internal(&[&[0u8, ctx.len() as u8], &ctx, &msg], &rnd.into())
                }
            } else {
                sk.sign_internal(&[&msg], &rnd.into())
            };
            assert_eq!(
                sig.encode().to_vec(),
                h(&t["signature"]),
                "tcId {}",
                t["tcId"]
            );
            seen.insert((external, det));
        }
    }
    // To'rtala kombinatsiya qamrab olingan.
    assert_eq!(seen.len(), 4);
}

#[test]
fn ml_dsa_65_sigver() {
    let (mut pass, mut fail) = (0, 0);
    for g in groups(&load("ml-dsa-65-sigver")) {
        let external = g["signatureInterface"] == "external";
        for t in tests(g) {
            let vk = VerifyingKey::<MlDsa65>::decode(
                &EncodedVerifyingKey::<MlDsa65>::try_from(h(&t["pk"]).as_slice()).unwrap(),
            );
            let sig_bytes = h(&t["signature"]);
            let ok = EncodedSignature::<MlDsa65>::try_from(sig_bytes.as_slice())
                .ok()
                .and_then(|e| Signature::<MlDsa65>::decode(&e))
                .is_some_and(|sig| {
                    let msg = h(&t["message"]);
                    if external {
                        vk.verify_with_context(&msg, &h(&t["context"]), &sig)
                    } else {
                        vk.verify_internal(&msg, &sig)
                    }
                });
            let want = t["testPassed"].as_bool().unwrap();
            assert_eq!(ok, want, "tcId {} ({})", t["tcId"], t["reason"]);
            if want {
                pass += 1
            } else {
                fail += 1
            }
        }
    }
    assert_eq!(pass + fail, 30);
    assert!(
        pass > 0 && fail > 0,
        "ham to'g'ri, ham noto'g'ri holatlar bo'lishi kerak"
    );
}
