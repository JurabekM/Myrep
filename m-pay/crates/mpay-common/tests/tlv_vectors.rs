//! `testvectors/tlv-vectors.json` — Kotlin (`android/mpay-core`) bilan umumiy BER-TLV vektorlari.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::tlv::{self, Tlv, Value};
use serde_json::Value as J;

fn load() -> J {
    let p = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../testvectors/tlv-vectors.json"
    );
    serde_json::from_str(&std::fs::read_to_string(p).unwrap()).unwrap()
}

fn h(s: &str) -> Vec<u8> {
    hex::decode(s).unwrap()
}

fn node(j: &J) -> Tlv {
    let tag = u32::from_str_radix(j["tag"].as_str().unwrap(), 16).unwrap();
    match j.get("children") {
        Some(c) => Tlv::constructed(tag, c.as_array().unwrap().iter().map(node).collect()),
        None => Tlv::primitive(tag, h(j["value"].as_str().unwrap())),
    }
}

fn repeat(j: &J, prefix: &str) -> Vec<u8> {
    let mut v = h(prefix);
    let b = h(j["byte"].as_str().unwrap())[0];
    v.extend(std::iter::repeat_n(
        b,
        j["count"].as_u64().unwrap() as usize,
    ));
    v
}

#[test]
fn shared_tlv_vectors() {
    let d = load();
    for c in d["valid"].as_array().unwrap() {
        let name = c["name"].as_str().unwrap();
        let (bytes, want): (Vec<u8>, Vec<Tlv>) = if let Some(r) = c.get("hex_repeat") {
            let t = &c["tree_repeat"];
            let tag = u32::from_str_radix(t["tag"].as_str().unwrap(), 16).unwrap();
            (
                repeat(r, r["prefix"].as_str().unwrap()),
                vec![Tlv::primitive(tag, repeat(t, ""))],
            )
        } else {
            (
                h(c["hex"].as_str().unwrap()),
                c["tree"].as_array().unwrap().iter().map(node).collect(),
            )
        };
        let got = tlv::parse_all(&bytes).unwrap_or_else(|e| panic!("{name}: {e}"));
        assert_eq!(got, want, "{name}");
        let canonical = c
            .get("canonical")
            .and_then(J::as_str)
            .map(h)
            .unwrap_or(bytes);
        assert_eq!(tlv::encode_all(&got), canonical, "{name} qayta kodlash");
        // Konstruktiv/primitiv belgisi tegdan kelib chiqadi.
        for t in &got {
            assert_eq!(
                matches!(t.value, Value::Constructed(_)),
                t.tag.is_constructed(),
                "{name}"
            );
        }
    }
    for c in d["invalid"].as_array().unwrap() {
        let name = c["name"].as_str().unwrap();
        assert!(
            tlv::parse_all(&h(c["hex"].as_str().unwrap())).is_err(),
            "{name} rad etilishi kerak"
        );
    }
    for c in d["dol"].as_array().unwrap() {
        let e = tlv::parse_dol(&h(c["hex"].as_str().unwrap())).unwrap();
        let want: Vec<(u32, usize)> = c["entries"]
            .as_array()
            .unwrap()
            .iter()
            .map(|x| {
                (
                    u32::from_str_radix(x[0].as_str().unwrap(), 16).unwrap(),
                    x[1].as_u64().unwrap() as usize,
                )
            })
            .collect();
        assert_eq!(e.iter().map(|x| (x.tag.0, x.len)).collect::<Vec<_>>(), want);
    }
}
