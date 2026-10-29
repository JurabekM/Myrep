//! Emitent: to'g'ridan-to'g'ri ISO 8583 xabarlari bilan format va nomuvofiqlik holatlari.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::sync::Arc;

use mpay_common::clock::{Clock, ManualClock};
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
    env_with(
        IssuerConfig::default(),
        Arc::new(ManualClock::new(time::OffsetDateTime::now_utc())),
    )
    .await
}

/// `cfg` — emitent siyosati (hisoblar qo'shiladi), `clock` — vault va emitent uchun umumiy soat.
async fn env_with(cfg: IssuerConfig, clock: Arc<ManualClock>) -> Env {
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
            clock.clone(),
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
        clock,
        IssuerConfig {
            accounts: vec![TestAccount {
                pan: fpan.expose_digits().into(),
                balance_minor: 1_000_000_000,
                label: "t".into(),
                phone: None,
            }],
            ..cfg
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
    valid_0100_with(e, atc, amount, 0, "SHOP0000000001 ")
}

/// `cvr` — IAD ichidagi CVR (CDCVM bitlari, ARQC bilan himoyalangan), `merchant` — 15 belgi.
fn valid_0100_with(e: &Env, atc: u16, amount: u64, cvr: u8, merchant: &str) -> IsoMessage {
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
        cvr,
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
    m.set_str(42, merchant).unwrap();
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

/// 2-faza P2.7 (ADR-0022): CVM chegarasi emitentda — o'zgartirilgan hamyon biometriyasiz katta summa
/// o'tkazolmaydi; Shield REVIEW + `step_up`; muddati o'tgan token — `54`.
#[tokio::test]
async fn product_policies() {
    let clock = Arc::new(ManualClock::new(time::OffsetDateTime::now_utc()));
    let e = env_with(
        IssuerConfig {
            cvm_limit_minor: 50_000,
            ..IssuerConfig::default()
        },
        clock.clone(),
    )
    .await;
    let cdcvm = emv::cvr::CDCVM_PERFORMED;
    let shop = "SHOP0000000001 ";
    assert_eq!(
        code(&e, &valid_0100_with(&e, 1, 50_000, 0, shop)).await,
        ("00".into(), "APPROVED".into()),
        "chegarada — CDCVM shart emas"
    );
    assert_eq!(
        code(&e, &valid_0100_with(&e, 2, 50_001, 0, shop)).await,
        ("Q2".into(), "CVM_REQUIRED".into())
    );
    assert_eq!(
        code(&e, &valid_0100_with(&e, 3, 50_001, cdcvm, shop)).await,
        ("00".into(), "APPROVED".into())
    );
    // Stub Shield: `REVIEW…` savdo nuqtasi — REVIEW; standart siyosat `step_up`.
    let review = "REVIEW000000001";
    assert_eq!(
        code(&e, &valid_0100_with(&e, 4, 1_000, 0, review)).await,
        ("Q2".into(), "REVIEW_STEP_UP".into())
    );
    assert_eq!(
        code(&e, &valid_0100_with(&e, 5, 1_000, cdcvm, review)).await,
        ("00".into(), "APPROVED_AFTER_REVIEW".into())
    );

    // Token muddati (karta 2031-12, token ≤ 36 oy) o'tgach — `54`, LUK holatidan oldin.
    clock.set(
        time::OffsetDateTime::from_unix_timestamp(
            CardExpiry::new(2031, 12).unwrap().end_unix() + 1,
        )
        .unwrap(),
    );
    assert!(clock.now().year() >= 2029);
    assert_eq!(
        code(&e, &valid_0100_with(&e, 6, 1_000, cdcvm, shop)).await,
        ("54".into(), "TOKEN_EXPIRED".into())
    );

    // `approve` va `decline` siyosatlari.
    for (action, want) in [
        (
            mpay_issuer::ReviewAction::Approve,
            ("00", "APPROVED_AFTER_REVIEW"),
        ),
        (mpay_issuer::ReviewAction::Decline, ("05", "RISK_REVIEW")),
    ] {
        let e = env_with(
            IssuerConfig {
                review_action: action,
                ..IssuerConfig::default()
            },
            Arc::new(ManualClock::new(time::OffsetDateTime::now_utc())),
        )
        .await;
        let (c, r) = code(&e, &valid_0100_with(&e, 1, 1_000, 0, review)).await;
        assert_eq!((c.as_str(), r.as_str()), want, "{action:?}");
    }
}

/// Asl `0100` uchun reversal (ADR-0024): maydonlar asldan, maydon 90 — asl MTI, STAN, vaqt.
fn reversal_for(m: &IsoMessage, mti: Mti) -> IsoMessage {
    let mut r = IsoMessage::new(mti);
    for f in [3u8, 4, 7, 11, 37, 41, 42, 49] {
        r.set(f, m.get(f).unwrap().to_vec()).unwrap();
    }
    let orig = format!(
        "0100{}{}{:011}{:011}",
        m.require_str(11).unwrap(),
        m.require_str(7).unwrap(),
        0,
        0
    );
    r.set_str(90, &orig).unwrap();
    r
}

async fn reverse(e: &Env, m: &IsoMessage) -> (String, String) {
    let (resp, out) = e.issuer.process_reversal_bytes(&m.pack()).await.unwrap();
    let r = IsoMessage::unpack(&resp).unwrap();
    assert_eq!(r.mti, Mti::REVERSAL_RESPONSE);
    assert_eq!(r.get(37), m.get(37), "RRN aks ettirilishi kerak");
    assert_eq!(r.require_str(39).unwrap(), out.code());
    (out.code().to_owned(), out.reason.as_str().to_owned())
}

async fn balance(e: &Env) -> i64 {
    e.issuer.accounts().await.unwrap()[0].balance_minor
}

#[tokio::test]
async fn reversal_returns_funds_exactly_once() {
    let e = env().await;
    let start = balance(&e).await;
    let m = valid_0100(&e, 1, 5_000);
    assert_eq!(code(&e, &m).await.0, "00");
    assert_eq!(balance(&e).await, start - 5_000);

    // Emitent ko'rmagan so'rov — 25 (acquirer uchun yakuniy).
    let unseen = reversal_for(&valid_0100(&e, 9, 5_000), Mti::REVERSAL_REQUEST);
    assert_eq!(
        reverse(&e, &unseen).await,
        ("25".into(), "ORIGINAL_NOT_FOUND".into())
    );
    // Summa mos emas — 13, pul qaytmaydi.
    let mut bad = reversal_for(&m, Mti::REVERSAL_REQUEST);
    bad.set_num(4, 4_999).unwrap();
    assert_eq!(
        reverse(&e, &bad).await,
        ("13".into(), "AMOUNT_MISMATCH".into())
    );
    // Maydon 90 boshqa STAN'ni ko'rsatadi yoki yo'q — 30.
    let mut bad = reversal_for(&m, Mti::REVERSAL_REQUEST);
    bad.set_str(90, &format!("0100000002{}{:022}", "1023120000", 0))
        .unwrap();
    assert_eq!(
        reverse(&e, &bad).await,
        ("30".into(), "FORMAT_ERROR".into())
    );
    let mut bad = reversal_for(&m, Mti::REVERSAL_REQUEST);
    bad.remove(90);
    assert_eq!(
        reverse(&e, &bad).await,
        ("30".into(), "FORMAT_ERROR".into())
    );
    assert_eq!(balance(&e).await, start - 5_000);

    // To'g'ri reversal — pul qaytadi; takror (0401) — ikkinchi marta qaytmaydi.
    let rev = reversal_for(&m, Mti::REVERSAL_REQUEST);
    assert_eq!(reverse(&e, &rev).await, ("00".into(), "REVERSED".into()));
    assert_eq!(balance(&e).await, start);
    let rep = reversal_for(&m, Mti::REVERSAL_REPEAT);
    assert_eq!(
        reverse(&e, &rep).await,
        ("00".into(), "ALREADY_REVERSED".into())
    );
    assert_eq!(balance(&e).await, start);

    // Rad etilgan asl (CVM chegarasi, Q2) — qaytariladigan pul yo'q.
    let declined = valid_0100(&e, 2, 200_000_000);
    assert_eq!(code(&e, &declined).await.0, "Q2");
    assert_eq!(
        reverse(&e, &reversal_for(&declined, Mti::REVERSAL_REQUEST)).await,
        ("00".into(), "NOTHING_TO_REVERSE".into())
    );

    // Hisobot: tasdiqlangani qaytarilgan deb belgilangan; har reversal xabari qayd etilgan.
    let report = e.issuer.report(0, i64::MAX).await.unwrap();
    let orig = report.iter().find(|r| r.stan == "000001").unwrap();
    assert_eq!(orig.response_code, "00");
    assert!(orig.reversed_at.is_some());
    assert_eq!(orig.terminal_id, "TERM0001");
    assert!(orig.dpan_masked.as_deref().unwrap().contains("******"));
    let n: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM issuer_reversals")
        .fetch_one(&e.pool)
        .await
        .unwrap();
    assert_eq!(n, 7);

    // Avtorizatsiya MTI'si reversal yo'lida — xato.
    assert!(e.issuer.process_reversal_bytes(&m.pack()).await.is_err());
}

#[tokio::test]
async fn concurrent_reversals_credit_once() {
    let e = env().await;
    let start = balance(&e).await;
    let m = valid_0100(&e, 1, 7_000);
    assert_eq!(code(&e, &m).await.0, "00");
    let a = reversal_for(&m, Mti::REVERSAL_REQUEST);
    let b = reversal_for(&m, Mti::REVERSAL_REPEAT);
    let (ra, rb) = tokio::join!(reverse(&e, &a), reverse(&e, &b));
    let mut reasons = [ra.1, rb.1];
    reasons.sort();
    assert_eq!(reasons, ["ALREADY_REVERSED", "REVERSED"]);
    assert_eq!(balance(&e).await, start);
}

fn clearing_rec(seq: u32, stan: u32, amount: u64) -> mpay_common::clearing::ClearingRecord {
    mpay_common::clearing::ClearingRecord {
        seq,
        terminal_id: "TERM0001".into(),
        merchant_id: "SHOP0000000001".into(),
        stan,
        rrn: "629612000001".into(),
        amount_minor: amount,
        currency: 860,
        txn_at: 1_793_050_000,
        dpan_masked: "990077******0001".into(),
    }
}

#[tokio::test]
async fn clearing_matches_each_record_once() {
    use mpay_common::clearing::{ClearingAck, ClearingFile};
    let e = env().await;
    for (atc, amount) in [(1u16, 1_000u64), (2, 2_000), (3, 3_000)] {
        assert_eq!(code(&e, &valid_0100(&e, atc, amount)).await.0, "00");
    }
    assert_eq!(code(&e, &valid_0100(&e, 4, 200_000_000)).await.0, "Q2");
    let rev = reversal_for(&valid_0100(&e, 2, 2_000), Mti::REVERSAL_REQUEST);
    assert_eq!(reverse(&e, &rev).await.1, "REVERSED");
    let before = balance(&e).await;

    let file = ClearingFile {
        batch_id: "MPAY20261027".into(),
        business_date: "20261027".into(),
        created_at: 1_793_128_000,
        records: vec![
            clearing_rec(1, 1, 1_000),
            clearing_rec(2, 2, 2_000),
            clearing_rec(3, 3, 3_001),
            clearing_rec(4, 4, 200_000_000),
            clearing_rec(5, 9, 500),
        ],
    };
    let bytes = file.encode().unwrap();
    let (ack_bytes, ack) = e.issuer.process_clearing(&bytes).await.unwrap();
    let got: Vec<(&str, &str)> = ack
        .records
        .iter()
        .map(|r| (r.code.as_str(), r.reason.as_str()))
        .collect();
    assert_eq!(
        got,
        [
            ("00", "ACCEPTED"),
            ("12", "REVERSED"),
            ("13", "AMOUNT_MISMATCH"),
            ("12", "NOT_APPROVED"),
            ("25", "ORIGINAL_NOT_FOUND"),
        ]
    );
    assert_eq!(ClearingAck::parse(&ack_bytes).unwrap(), ack);
    // Kliring balansni o'zgartirmaydi (emulyator avtorizatsiyada yechgan).
    assert_eq!(balance(&e).await, before);

    // O'sha paket qayta — o'sha tasdiq; o'sha ID boshqa mazmun bilan — xato.
    let (again, _) = e.issuer.process_clearing(&bytes).await.unwrap();
    assert_eq!(again, ack_bytes);
    let mut other = file.clone();
    other.records.truncate(1);
    assert!(e
        .issuer
        .process_clearing(&other.encode().unwrap())
        .await
        .is_err());

    // Boshqa paketda o'sha tranzaksiya — 94.
    let second = ClearingFile {
        batch_id: "MPAY20261028".into(),
        business_date: "20261028".into(),
        records: vec![clearing_rec(1, 1, 1_000)],
        ..file
    };
    let (_, ack2) = e
        .issuer
        .process_clearing(&second.encode().unwrap())
        .await
        .unwrap();
    assert_eq!(ack2.records[0].reason, "ALREADY_CLEARED");

    // Kliringdan o'tgan tranzaksiyani reversal bilan qaytarib bo'lmaydi.
    let late = reversal_for(&valid_0100(&e, 1, 1_000), Mti::REVERSAL_REQUEST);
    assert_eq!(
        reverse(&e, &late).await,
        ("12".into(), "ALREADY_CLEARED".into())
    );
    assert_eq!(balance(&e).await, before);

    // Buzilgan fayl — butun paket rad.
    let mut broken = bytes.clone();
    let n = broken.len();
    broken[n - 2] ^= 1;
    assert!(e.issuer.process_clearing(&broken).await.is_err());
}
