//! Emitent: to'g'ridan-to'g'ri ISO 8583 xabarlari bilan format va nomuvofiqlik holatlari.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::sync::Arc;

use mpay_common::clock::SystemClock;
use mpay_common::emv::{self, tag, EmvDate, Iad, TerminalData, Track2};
use mpay_common::iso8583::{IsoMessage, Mti};
use mpay_common::ports::SecurityLevel;
use mpay_common::tlv::{self, Tlv};
use mpay_common::{CardExpiry, DeviceId, Pan};
use mpay_crypto::keystore::{ensure_standard_keys, KeyLabel, KeyStore, MemoryKeyStore};
use mpay_crypto::scheme::{CryptogramScheme, MpayAes128CmacV1};
use mpay_issuer::{Issuer, IssuerConfig, TestAccount};
use mpay_shield::StubShield;
use mpay_vault::{
    DeviceContext, ProvisionOutcome, ProvisionRequest, Vault, VaultConfig, VaultDetokenizer,
};
use proptest::prelude::*;

struct Env {
    issuer: Issuer,
    ks: Arc<dyn KeyStore>,
    dpan: Pan,
    _dir: tempfile::TempDir,
    pool: sqlx::AnyPool,
}

async fn env() -> Env {
    let dir = tempfile::tempdir().unwrap();
    let db = mpay_vault::db::Db::open_sqlite(&dir.path().join("i.db"))
        .await
        .unwrap();
    let pool = db.pool().clone();
    let ks: Arc<dyn KeyStore> = Arc::new(MemoryKeyStore::random());
    ensure_standard_keys(ks.as_ref()).unwrap();
    let scheme: Arc<dyn CryptogramScheme> = Arc::new(MpayAes128CmacV1);
    let shield = Arc::new(StubShield::default());
    let vault = Arc::new(
        Vault::open(
            db.clone(),
            ks.clone(),
            scheme.clone(),
            shield.clone(),
            Arc::new(SystemClock),
            VaultConfig::default(),
        )
        .await
        .unwrap(),
    );
    let fpan = Pan::from_prefix("990012100001234").unwrap();
    let ProvisionOutcome::Active { profile, .. } = vault
        .provision(
            ProvisionRequest {
                fpan: fpan.clone(),
                expiry: CardExpiry::new(2031, 12).unwrap(),
                integrity: None,
            },
            DeviceContext {
                device_id: DeviceId([1; 32]),
                security_level: SecurityLevel::StrongBox,
            },
        )
        .await
        .unwrap()
    else {
        panic!()
    };
    let issuer = Issuer::open(
        db,
        ks.clone(),
        scheme,
        Arc::new(VaultDetokenizer::new(vault, "issuer")),
        shield,
        Arc::new(SystemClock),
        IssuerConfig {
            accounts: vec![TestAccount {
                pan: fpan.expose_digits().into(),
                balance_minor: 1_000_000,
                label: "t".into(),
                phone: None,
            }],
            ..IssuerConfig::default()
        },
    )
    .await
    .unwrap();
    Env {
        issuer,
        ks,
        dpan: profile.dpan,
        _dir: dir,
        pool,
    }
}

/// To'g'ri `0100` (ARQC haqiqiy LUK bilan hisoblangan).
fn valid_0100(e: &Env, atc: u16, amount: u64) -> IsoMessage {
    let s = MpayAes128CmacV1;
    let luk = s
        .luk_from_imk(
            e.ks.as_ref(),
            &KeyLabel::new(KeyLabel::IMK_AC),
            &e.dpan,
            0,
            1,
        )
        .unwrap();
    let td = TerminalData {
        amount_minor: amount,
        other_amount_minor: 0,
        country: 860,
        tvr: [0; 5],
        currency: 860,
        date: EmvDate::new(2026, 10, 23).unwrap(),
        txn_type: 0,
        unpredictable_number: [1, 2, 3, 4],
    };
    let pdol = td.to_pdol_data().unwrap();
    let iad = Iad {
        scheme_id: 1,
        luk_seq: 1,
        cvr: 0,
    };
    let arqc = s.arqc(
        &s.session_key(&luk, atc),
        &emv::cdol_data(&pdol, emv::AIP, atc, &iad),
    );
    let mut icc = vec![
        Tlv::primitive(tag::ARQC, arqc.to_vec()),
        Tlv::primitive(tag::CID, vec![0x80]),
        Tlv::primitive(tag::IAD, iad.to_bytes().to_vec()),
        Tlv::primitive(tag::ATC, atc.to_be_bytes().to_vec()),
        Tlv::primitive(tag::AIP, emv::AIP.to_vec()),
    ];
    let mut pos = 0;
    for d in emv::PDOL {
        icc.push(Tlv::primitive(d.tag.0, pdol[pos..pos + d.len].to_vec()));
        pos += d.len;
    }
    let exp = CardExpiry::new(2029, 10).unwrap();
    let mut m = IsoMessage::new(Mti::AUTH_REQUEST);
    m.set_str(2, e.dpan.expose_digits()).unwrap();
    m.set_str(3, "000000").unwrap();
    m.set_num(4, amount).unwrap();
    m.set_str(7, "1023120000").unwrap();
    m.set_num(11, u64::from(atc)).unwrap();
    m.set_str(14, &exp.to_yymm()).unwrap();
    m.set_str(22, "071").unwrap();
    m.set_str(35, &Track2::new(e.dpan.clone(), exp).to_iso())
        .unwrap();
    m.set_str(37, "629612000001").unwrap();
    m.set_str(41, "TERM0001").unwrap();
    m.set_str(42, "SHOP0000000001 ").unwrap();
    m.set_num(49, 860).unwrap();
    m.set(55, tlv::encode_all(&icc)).unwrap();
    m
}

async fn code(e: &Env, m: &IsoMessage) -> (String, String) {
    let (resp, out) = e.issuer.process_bytes(&m.pack()).await.unwrap();
    let r = IsoMessage::unpack(&resp).unwrap();
    assert_eq!(r.mti, Mti::AUTH_RESPONSE);
    assert_eq!(r.get(11), m.get(11), "STAN aks ettirilishi kerak");
    (
        r.require_str(39).unwrap().to_owned(),
        out.reason.as_str().to_owned(),
    )
}

#[tokio::test]
async fn approve_then_field_and_format_errors() {
    let e = env().await;
    // DPAN'ning amal qilish muddati token profilidan farq qilishi mumkin — Track 2 va 14 o'zaro mos bo'lsa yetarli.
    assert_eq!(
        code(&e, &valid_0100(&e, 1, 1000)).await,
        ("00".into(), "APPROVED".into())
    );

    // Maydon 4 ≠ 9F02.
    let mut m = valid_0100(&e, 2, 1000);
    m.set_num(4, 999).unwrap();
    assert_eq!(code(&e, &m).await, ("Q1".into(), "FIELD_MISMATCH".into()));

    // Maydon 49 ≠ 5F2A.
    let mut m = valid_0100(&e, 3, 1000);
    m.set_num(49, 840).unwrap();
    assert_eq!(code(&e, &m).await, ("Q1".into(), "FIELD_MISMATCH".into()));

    // Track 2 PAN ≠ maydon 2.
    let mut m = valid_0100(&e, 4, 1000);
    let other = Pan::from_prefix("990077000000999").unwrap();
    m.set_str(
        35,
        &Track2::new(other, CardExpiry::new(2029, 10).unwrap()).to_iso(),
    )
    .unwrap();
    assert_eq!(code(&e, &m).await, ("Q1".into(), "FIELD_MISMATCH".into()));

    // Maydon 55 yo'q.
    let mut m = valid_0100(&e, 5, 1000);
    m.remove(55);
    assert_eq!(code(&e, &m).await, ("Q1".into(), "ICC_DATA_MISSING".into()));

    // Noma'lum sxema ID (IAD bayt 1).
    let mut m = valid_0100(&e, 6, 1000);
    let mut icc = tlv::parse_all(m.get(55).unwrap()).unwrap();
    for t in &mut icc {
        if t.tag.0 == tag::IAD {
            if let tlv::Value::Primitive(v) = &mut t.value {
                v[1] = 0x7F;
            }
        }
    }
    m.set(55, tlv::encode_all(&icc)).unwrap();
    assert_eq!(
        code(&e, &m).await,
        ("Q1".into(), "UNSUPPORTED_SCHEME".into())
    );

    // 0110 MTI bilan so'rov — xato (javob emas).
    let mut m = valid_0100(&e, 7, 1000);
    m.mti = Mti::AUTH_RESPONSE;
    assert!(e.issuer.process_bytes(&m.pack()).await.is_err());

    // Hisob qaydnomasida ochiq PAN yo'q.
    let rows: Vec<(String, Option<String>)> =
        sqlx::query_as("SELECT reason, dpan_masked FROM issuer_authorizations")
            .fetch_all(&e.pool)
            .await
            .unwrap();
    assert!(rows.len() >= 6);
    for (_, d) in rows {
        if let Some(d) = d {
            assert!(d.contains("******"));
            assert_ne!(d, e.dpan.expose_digits());
        }
    }
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(64))]
    #[test]
    fn random_iso_bytes_never_panic(data in proptest::collection::vec(any::<u8>(), 0..400)) {
        let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();
        rt.block_on(async {
            let e = env().await;
            let mut d = b"0100".to_vec();
            d.extend_from_slice(&data);
            let _ = e.issuer.process_bytes(&d).await;
        });
    }
}

/// 2-faza P2.1: telefon konfiguratsiyaga ergashadi — `None` bazadagi eski raqamni o'chiradi.
#[tokio::test]
async fn phone_follows_config_and_can_be_cleared() {
    let e = env().await;
    let fpan = Pan::from_prefix("990012100001234").unwrap();
    assert_eq!(e.issuer.contact_phone(&fpan).await.unwrap(), None);
    e.issuer
        .set_phone(&fpan, Some("+998000001234"))
        .await
        .unwrap();
    assert_eq!(
        e.issuer.contact_phone(&fpan).await.unwrap().as_deref(),
        Some("+998000001234")
    );
    assert!(e
        .issuer
        .set_phone(&fpan, Some("998000001234"))
        .await
        .is_err());
    e.issuer.set_phone(&fpan, None).await.unwrap();
    assert_eq!(e.issuer.contact_phone(&fpan).await.unwrap(), None);
}
