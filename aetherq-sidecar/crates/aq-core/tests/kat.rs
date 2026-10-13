//! Python referens (aether_q_v3) vektorlariga qarshi tekshiruv.
//! Vektorlar: kat/aq51_wire_kat.json (generator: kat/gen_wire_kat.py).

use aq_core::handshake::{derive_hs, derive_master, derive_rms, fin_keys, finished_mac, server_id_hash};
use aq_core::identity::from_hex;
use aq_core::kdf::{hkdf_expand, hkdf_extract, kmac256, sha3_256};
use aq_core::kem::{self, mlkem_decaps, mlkem_from_seed, PROFILE_HYBRID, PROFILE_MINIMAL};
use aq_core::sig;
use aq_core::transport::{Role, Session};
use aq_core::wire::{self, ClientHello};
use serde_json::Value;

fn kat() -> Value {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../kat/aq51_wire_kat.json");
    let text = std::fs::read_to_string(path).expect("KAT fayl topilmadi (kat/gen_wire_kat.py)");
    serde_json::from_str(&text).expect("KAT JSON")
}

fn hx(v: &Value, key: &str) -> Vec<u8> {
    from_hex(v[key].as_str().unwrap_or_else(|| panic!("KAT maydon yo'q: {key}"))).expect("hex")
}

fn arr<const N: usize>(v: &Value, key: &str) -> [u8; N] {
    let b = hx(v, key);
    assert_eq!(b.len(), N, "uzunlik: {key}");
    let mut out = [0u8; N];
    out.copy_from_slice(&b);
    out
}

#[test]
fn hkdf_matches_python() {
    let k = kat();
    let v = &k["vectors"]["hkdf"];
    let ikm = hx(v, "ikm");
    let salt = hx(v, "salt");
    let prk = hkdf_extract(&salt, &ikm);
    assert_eq!(prk.to_vec(), hx(v, "prk"));
    assert_eq!(hkdf_expand(&prk, &hx(v, "info"), 64), hx(v, "okm_64"));
    assert_eq!(hkdf_extract(b"", &ikm).to_vec(), hx(v, "empty_salt_prk"));
}

#[test]
fn kmac256_matches_python() {
    let k = kat();
    let v = &k["vectors"]["kmac256"];
    let key = hx(v, "key");
    let data = hx(v, "data");
    let custom = hx(v, "custom");
    assert_eq!(kmac256(&key, &data, 32, &custom), hx(v, "out_32"));
    assert_eq!(kmac256(&key, &data, 16, b""), hx(v, "out_16_nocustom"));
}

#[test]
fn combiner_matches_python() {
    let k = kat();
    let c = &k["vectors"]["combiner"];
    let p1 = &c["profile_01"];
    let ss = kem::combine(
        PROFILE_HYBRID,
        &hx(p1, "label"),
        &hx(p1, "ss_m"),
        &hx(p1, "ct_m"),
        &hx(p1, "ss_x"),
        &hx(p1, "ct_x"),
        &hx(p1, "pk_x"),
    );
    assert_eq!(ss.to_vec(), hx(p1, "ss"), "profil 0x01");
    let p3 = &c["profile_03"];
    let ss3 = kem::combine(PROFILE_MINIMAL, &hx(p3, "label"), &hx(p3, "ss_m"), &hx(p3, "ct_m"), &[], &[], &[]);
    assert_eq!(ss3.to_vec(), hx(p3, "ss"), "profil 0x03");
}

#[test]
fn implicit_reject_key_matches_python() {
    let k = kat();
    let v = &k["vectors"]["reject_0x01"];
    let seed: [u8; 64] = arr(v, "dk_m");
    let got = kem::reject_key(PROFILE_HYBRID, &seed, &hx(v, "ss_m"), &hx(v, "ct_m"), &hx(v, "ct_x"));
    assert_eq!(got.to_vec(), hx(v, "key"), "F1 implicit rejection: Python ↔ Rust");
}

#[test]
fn mlkem768_interops_with_python() {
    let k = kat();
    let v = &k["vectors"]["mlkem768"];
    let seed: [u8; 64] = arr(v, "seed");
    let (dk, ek) = mlkem_from_seed(&seed);
    assert_eq!(ek, hx(v, "ek"), "ML-KEM ochiq kalit (seed → ek)");
    let ss = mlkem_decaps(&dk, &hx(v, "ct")).expect("decaps");
    assert_eq!(ss.to_vec(), hx(v, "ss"), "Python encaps → Rust decaps");
}

#[test]
fn mldsa65_verifies_python_signature() {
    let k = kat();
    let v = &k["vectors"]["mldsa65"];
    let seed: [u8; 32] = arr(v, "seed");
    let (_sk, pk) = sig::keypair_from_seed(&seed);
    assert_eq!(pk, hx(v, "pk"), "ML-DSA ochiq kalit (seed → pk)");
    let msg = hx(v, "msg");
    let s = hx(v, "sig");
    assert!(sig::verify(&pk, &msg, &s), "Python imzosi Rust'da tekshiriladi");
    let mut bad = msg.clone();
    bad[0] ^= 1;
    assert!(!sig::verify(&pk, &bad, &s));
}

#[test]
fn x25519_matches_rfc_and_python() {
    use x25519_dalek::{PublicKey, StaticSecret};
    let k = kat();
    let v = &k["vectors"]["x25519"];
    let sk_a = StaticSecret::from(arr::<32>(v, "sk_a"));
    assert_eq!(PublicKey::from(&sk_a).to_bytes().to_vec(), hx(v, "pk_a"));
    let pk_b = PublicKey::from(arr::<32>(v, "pk_b"));
    assert_eq!(sk_a.diffie_hellman(&pk_b).as_bytes().to_vec(), hx(v, "shared"));
}

#[test]
fn handshake_full_key_schedule_matches_python() {
    let k = kat();
    let v = &k["vectors"]["handshake_full"];
    let ss = hx(v, "ss");
    let transcript = hx(v, "transcript");
    let hs = derive_hs(&ss, &[], &[]);
    assert_eq!(hs.to_vec(), hx(v, "hs"));
    let (c_fin, s_fin) = fin_keys(&hs);
    assert_eq!(c_fin.to_vec(), hx(v, "c_fin"));
    assert_eq!(s_fin.to_vec(), hx(v, "s_fin"));
    let th = sha3_256(&transcript);
    assert_eq!(finished_mac(&c_fin, &th, b"CF").to_vec(), hx(v, "cf"));
    assert_eq!(finished_mac(&s_fin, &th, b"SF").to_vec(), hx(v, "sf"));
    assert_eq!(derive_master(&hs, &transcript).to_vec(), hx(v, "master"));
    assert_eq!(derive_rms(&hs, &transcript).to_vec(), hx(v, "rms"));
}

#[test]
fn handshake_resumed_hs_matches_python() {
    let k = kat();
    let v = &k["vectors"]["handshake_resumed"];
    let sid = server_id_hash(&hx(v, "server_pub"));
    assert_eq!(sid, hx(v, "server_id"));
    let hs = derive_hs(&hx(v, "ss"), &hx(v, "rms"), &sid);
    assert_eq!(hs.to_vec(), hx(v, "hs"));
}

#[test]
fn transport_records_match_python() {
    let k = kat();
    let v = &k["vectors"]["transport"];
    let master = hx(v, "master");
    let mut cli = Session::from_master(&master, 1, Role::Client);
    let mut srv = Session::from_master(&master, 1, Role::Server);
    for r in v["records_client_send"].as_array().unwrap() {
        let pt = from_hex(r["pt"].as_str().unwrap()).unwrap();
        let rec = from_hex(r["rec"].as_str().unwrap()).unwrap();
        assert_eq!(cli.seal(&pt).unwrap(), rec, "record baytlari");
        assert_eq!(srv.open(&rec).unwrap(), (0x17, pt));
    }
    cli.rekey();
    srv.rekey();
    let rk = hx(v, "after_rekey_rec");
    assert_eq!(cli.seal(&hx(v, "after_rekey_pt")).unwrap(), rk, "rekey'dan keyin record");
    assert_eq!(srv.open(&rk).unwrap().1, hx(v, "after_rekey_pt"));
}

#[test]
fn frame_encodings_match_python() {
    let k = kat();
    let f = &k["vectors"]["frames"];
    let ch = wire::enc_client_hello(&ClientHello {
        versions: vec![0x0501],
        profiles: vec![1, 3],
        client_random: (0u8..32).collect::<Vec<_>>().try_into().unwrap(),
        flags: 0,
        ticket: vec![],
    });
    assert_eq!(ch, hx(f, "ch"), "CH");
    let srand: [u8; 32] = (0x50u8..0x70).collect::<Vec<_>>().try_into().unwrap();
    let ek: Vec<u8> = (0..256).map(|i| i as u8).collect::<Vec<u8>>().repeat(5);
    let core = wire::sh_core(0x0501, 1, &srand, &ek, 0x01);
    assert_eq!(core, hx(f, "sh_core_flags1"), "SH yadrosi");
    assert_eq!(wire::enc_server_hello(&wire::sh_core(0x0501, 1, &srand, &ek, 1), &[]), hx(f, "sh_no_sig"), "SH");
    assert_eq!(wire::enc_client_kex(&(0u8..200).collect::<Vec<_>>()), hx(f, "ckx"), "CKX");
    let mac: [u8; 32] = (0u8..32).collect::<Vec<_>>().try_into().unwrap();
    assert_eq!(wire::enc_finished(&mac), hx(f, "fin"), "FINISHED");
    assert_eq!(
        wire::enc_client_auth(&(0u8..16).collect::<Vec<_>>(), &(0u8..40).collect::<Vec<_>>()),
        hx(f, "client_auth"),
        "CLIENT_AUTH"
    );
    assert_eq!(wire::alert_frame(0x2A), hx(f, "alert_bad_finished"), "ALERT");
}
