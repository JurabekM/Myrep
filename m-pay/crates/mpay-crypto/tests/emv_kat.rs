//! M-Pay Test Scheme KAT: `testvectors/emv-kat.json` (mustaqil Python implementatsiyasi
//! `scripts/gen_emv_kat.py` generatsiya qilgan) bilan har bir oraliq qiymatni solishtiradi.

#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_common::emv::{cdol_data, EmvDate, Iad, TerminalData, AIP};
use mpay_common::Pan;
use mpay_crypto::keystore::{KeyKind, KeyLabel, KeyStore, MemoryKeyStore};
use mpay_crypto::scheme::{CryptogramScheme, MpayAes128CmacV1};
use serde_json::Value;

fn hexv(v: &Value) -> Vec<u8> {
    hex::decode(v.as_str().unwrap()).unwrap()
}

#[test]
fn emv_kat_vectors() {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../testvectors/emv-kat.json"
    );
    let doc: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    assert_eq!(doc["scheme"], "MPAY-AES128-CMAC-V1");
    let scheme = MpayAes128CmacV1;
    let cases = doc["cases"].as_array().unwrap();
    assert!(cases.len() >= 3);

    for c in cases {
        let name = c["name"].as_str().unwrap();
        let ks = MemoryKeyStore::random();
        let imk = KeyLabel::new(KeyLabel::IMK_AC);
        ks.import_secret(&imk, KeyKind::Aes128, &hexv(&c["imk"]))
            .unwrap();

        let dpan = Pan::parse(c["dpan"].as_str().unwrap()).unwrap();
        let psn = c["psn"].as_u64().unwrap() as u8;
        assert_eq!(
            MpayAes128CmacV1::mk_context(&dpan, psn),
            hexv(&c["mk_context"]),
            "{name}"
        );

        let mk = scheme.token_master_key(&ks, &imk, &dpan, psn).unwrap();
        assert_eq!(
            mk.expose().to_vec(),
            hexv(&c["token_master_key"]),
            "{name} MK"
        );

        let seq = c["luk_seq"].as_u64().unwrap() as u32;
        let luk = scheme.luk(&mk, seq);
        assert_eq!(luk.expose().to_vec(), hexv(&c["luk"]), "{name} LUK");

        let atc = c["atc"].as_u64().unwrap() as u16;
        let sk = scheme.session_key(&luk, atc);
        assert_eq!(sk.expose().to_vec(), hexv(&c["session_key"]), "{name} SK");

        let t = &c["terminal"];
        let date = hexv(&t["date_yymmdd"]);
        let td = TerminalData {
            amount_minor: t["amount_minor"].as_u64().unwrap(),
            other_amount_minor: t["other_amount_minor"].as_u64().unwrap(),
            country: t["country"].as_u64().unwrap() as u16,
            tvr: hexv(&t["tvr"]).try_into().unwrap(),
            currency: t["currency"].as_u64().unwrap() as u16,
            date: EmvDate::from_bcd(date.try_into().unwrap()).unwrap(),
            txn_type: t["txn_type"].as_u64().unwrap() as u8,
            unpredictable_number: hexv(&t["un"]).try_into().unwrap(),
        };
        let pdol = td.to_pdol_data().unwrap();
        assert_eq!(pdol.to_vec(), hexv(&c["pdol_data"]), "{name} PDOL");

        let iad = Iad::from_bytes(&hexv(&c["iad"])).unwrap();
        assert_eq!(iad.luk_seq, seq);
        assert_eq!(iad.scheme_id, scheme.scheme_id());
        let cdol = cdol_data(&pdol, AIP, atc, &iad);
        assert_eq!(cdol.to_vec(), hexv(&c["cdol"]), "{name} CDOL");

        let arqc = scheme.arqc(&sk, &cdol);
        assert_eq!(arqc.to_vec(), hexv(&c["arqc"]), "{name} ARQC");
        assert!(scheme.verify_arqc(&sk, &cdol, &arqc));

        let arc: [u8; 2] = c["arc"].as_str().unwrap().as_bytes().try_into().unwrap();
        assert_eq!(
            scheme.arpc(&sk, &arqc, arc).to_vec(),
            hexv(&c["arpc"]),
            "{name} ARPC"
        );
    }
}
