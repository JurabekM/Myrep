//! Python referens vektorlari: resumption ticket, PoW cookie/nonce, 0-RTT, yangi frame'lar.
//! Vektorlar: kat/aq51_wire_kat.json (generator: kat/gen_wire_kat.py).

use aq_core::dos::{verify_pow, PuzzleAuthority};
use aq_core::early::{derive_early_key, open_early};
use aq_core::identity::from_hex;
use aq_core::ticket::TicketAuthority;
use aq_core::wire;
use serde_json::Value;

fn kat() -> Value {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../kat/aq51_wire_kat.json");
    serde_json::from_str(&std::fs::read_to_string(path).expect("KAT")).expect("JSON")
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
fn ticket_opens_python_ticket() {
    let k = kat();
    let v = &k["vectors"]["ticket"];
    let t = TicketAuthority::new(arr::<32>(v, "key"), 3600);
    let got = t.open(&hx(v, "ticket"), v["now"].as_u64().unwrap(), &hx(v, "context"));
    let (rms, profile) = got.expect("Python ticket Rust'da ochilishi kerak");
    assert_eq!(rms.to_vec(), hx(v, "rms"));
    assert_eq!(profile as u64, v["profile"].as_u64().unwrap());
}

#[test]
fn puzzle_cookie_and_python_pow_nonce_match() {
    let k = kat();
    let v = &k["vectors"]["puzzle"];
    let p = PuzzleAuthority::new(arr::<32>(v, "secret"), v["difficulty"].as_u64().unwrap() as u8, 30);
    let ch = hx(v, "ch");
    let now = v["now"].as_u64().unwrap();
    assert_eq!(p.issue(&ch, now), hx(v, "cookie"), "cookie: Python ↔ Rust");
    let nonce = v["pow_nonce"].as_u64().unwrap();
    assert!(verify_pow(&hx(v, "cookie"), nonce, 8), "Python PoW yechimi Rust'da tasdiqlanishi kerak");
    assert!(p.verify(&ch, &hx(v, "cookie"), nonce, now));
}

#[test]
fn early_key_and_python_blob_match() {
    let k = kat();
    let v = &k["vectors"]["early"];
    let rms = hx(v, "rms");
    let ch = hx(v, "ch");
    assert_eq!(derive_early_key(&rms, &ch).to_vec(), hx(v, "key"), "K_early: Python ↔ Rust");
    let got = open_early(&rms, &ch, &hx(v, "blob")).expect("Python early blob ochilishi kerak");
    assert_eq!(got, hx(v, "data"));
}

#[test]
fn new_frames_match_python_encoding() {
    let k = kat();
    let f = &k["vectors"]["frames2"];
    let v = &k["vectors"]["puzzle"];
    let cookie = hx(v, "cookie");
    assert_eq!(wire::enc_hello_retry(&cookie, 8), hx(f, "hello_retry"), "HELLO_RETRY");
    assert_eq!(
        wire::enc_client_hello_retry(&cookie, v["pow_nonce"].as_u64().unwrap(), &hx(v, "ch")),
        hx(f, "ch_retry"),
        "CH_RETRY"
    );
    let t = &k["vectors"]["ticket"];
    assert_eq!(wire::enc_nst(&hx(t, "ticket"), 3600), hx(f, "nst"), "NST");
    let e = &k["vectors"]["early"];
    assert_eq!(wire::enc_early_data(&hx(e, "blob")), hx(f, "early_data"), "EARLY_DATA");
    // Dekoderlar ham Python freymini o'qiy oladi
    let (c, n, ch) = wire::dec_client_hello_retry(wire::parse_frame(&hx(f, "ch_retry")).unwrap().1).unwrap();
    assert_eq!(c, cookie);
    assert_eq!(n, v["pow_nonce"].as_u64().unwrap());
    assert_eq!(ch, hx(v, "ch"));
}
