#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! `spec/interchange/vectors.json` (mustaqil Python oracle) bilan bayt-bayt moslik:
//! konteyner, kanonik xesh, birlashtirish qarorlari.

use baraka_interchange::canon::{canonical, row_hash, Row};
use baraka_interchange::container::{open, seal_with, Kdf};
use baraka_interchange::merge::{decide, Decision};
use baraka_interchange::model::{decode, encode, Meta, Mode, RowRecord};
use baraka_interchange::InterchangeError;
use serde_json::Value;
use sha2::{Digest, Sha256};

fn vectors() -> Value {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../spec/interchange/vectors.json");
    serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap()
}

fn s(v: &Value, k: &str) -> String {
    v[k].as_str().unwrap().to_string()
}

fn meta(v: &Value) -> Meta {
    Meta {
        format_version: 1,
        schema_version: v["schemaVersion"].as_i64().unwrap(),
        household_id: s(v, "householdId"),
        source_device_id: s(v, "sourceDeviceId"),
        source_device_name: s(v, "sourceDeviceName"),
        export_id: s(v, "exportId"),
        ack_export_id: v["ackExportId"].as_str().map(str::to_string),
        mode: match v["mode"].as_str().unwrap() {
            "FULL" => Mode::Full,
            "INCREMENTAL" => Mode::Incremental,
            _ => Mode::Pairing,
        },
        exported_at: s(v, "exportedAt"),
        row_count: 0,
        audience: None,
    }
}

#[test]
fn container_matches_oracle() {
    let all = vectors();
    let mut n = 0;
    for c in all["cases"].as_array().unwrap() {
        if c["kind"] != "container" {
            continue;
        }
        n += 1;
        let rows: Vec<RowRecord> = c["rows"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| RowRecord {
                table: s(r, "table"),
                data: r["data"].as_object().unwrap().clone(),
            })
            .collect();
        let plain = encode(&meta(&c["meta"]), &rows).unwrap();
        assert_eq!(
            hex::encode(Sha256::digest(&plain)),
            s(c, "plaintextSha256"),
            "{}",
            c["id"]
        );
        let k = &c["kdf"];
        let kdf = Kdf::argon2id(
            k["mKib"].as_u64().unwrap() as u32,
            k["tCost"].as_u64().unwrap() as u32,
            k["pCost"].as_u64().unwrap() as u32,
        );
        let salt: [u8; 16] = hex::decode(s(c, "salt")).unwrap().try_into().unwrap();
        let nonce: [u8; 24] = hex::decode(s(c, "nonce")).unwrap().try_into().unwrap();
        let password = s(c, "password");
        let sealed = seal_with(&plain, &password, kdf, salt, nonce).unwrap();
        assert_eq!(hex::encode(&sealed), s(c, "sealedHex"), "{}", c["id"]);
        let (_, back) = open(&sealed, &password).unwrap();
        let (m, decoded) = decode(&back).unwrap();
        assert_eq!((m.row_count, decoded), (2, rows));
        assert_eq!(
            open(&sealed, "noto'g'ri-parol").err(),
            Some(InterchangeError::BadPassword)
        );
    }
    assert_eq!(n, 2);
}

#[test]
fn row_hash_and_merge_match_oracle() {
    let all = vectors();
    let (mut hashes, mut merges) = (0, 0);
    for c in all["cases"].as_array().unwrap() {
        match c["kind"].as_str().unwrap() {
            "rowHash" => {
                hashes += 1;
                let row: Row = c["row"].as_object().unwrap().clone();
                let table = s(c, "table");
                let mut wrapped = serde_json::Map::new();
                wrapped.insert("t".into(), Value::String(table.clone()));
                wrapped.insert("r".into(), Value::Object(row.clone()));
                assert_eq!(
                    canonical(&Value::Object(wrapped)).unwrap(),
                    s(c, "canonical")
                );
                assert_eq!(
                    row_hash(&table, &row).unwrap(),
                    s(c, "expected"),
                    "{}",
                    c["id"]
                );
            }
            "merge" => {
                merges += 1;
                let got = decide(
                    c["local"].as_str(),
                    c["base"].as_str(),
                    c["remote"].as_str().unwrap(),
                    c["appendOnly"].as_bool().unwrap(),
                );
                let want = match c["expected"].as_str().unwrap() {
                    "INSERT" => Decision::Insert,
                    "UPDATE" => Decision::Update,
                    "SAME" => Decision::Same,
                    "KEEP_LOCAL" => Decision::KeepLocal,
                    "CONFLICT" => Decision::Conflict,
                    _ => Decision::Protected,
                };
                assert_eq!(got, want, "{}", c["id"]);
            }
            _ => {}
        }
    }
    assert_eq!((hashes, merges), (4, 9));
}
