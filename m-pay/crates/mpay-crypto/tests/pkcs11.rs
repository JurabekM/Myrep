//! SoftHSM2 / PKCS#11 integratsion testi.
//!
//! `#[ignore]` — faqat `MPAY_PKCS11_LIB`, `MPAY_PKCS11_TOKEN_LABEL`, `MPAY_PKCS11_PIN`
//! o'rnatilgan muhitda ishga tushiriladi (CI: Ubuntu + softhsm2; lokal: `scripts/softhsm-test.sh`):
//!
//! ```text
//! cargo test -p mpay-crypto --features pkcs11 -- --include-ignored pkcs11
//! ```
#![allow(clippy::unwrap_used, clippy::expect_used)]
#![cfg(feature = "pkcs11")]

use mpay_common::Pan;
use mpay_crypto::envelope::Dek;
use mpay_crypto::keystore::conformance::check_conformance;
use mpay_crypto::keystore::{
    ensure_standard_keys, KeyKind, KeyLabel, KeyStore, MemoryKeyStore, Pkcs11Config, Pkcs11KeyStore,
};
use mpay_crypto::scheme::{CryptogramScheme, MpayAes128CmacV1};

/// SoftHSM2 bir nechta sessiyadan bir vaqtda token obyektlari yaratilganda ba'zan
/// `CKR_GENERAL_ERROR` qaytaradi (2026-10-23 da kuzatilgan). Server bitta sessiyani `Mutex`
/// ostida ishlatadi, shuning uchun testlar ham ketma-ket bajariladi.
static SERIAL: std::sync::Mutex<()> = std::sync::Mutex::new(());

fn serial() -> std::sync::MutexGuard<'static, ()> {
    SERIAL
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

fn open() -> Pkcs11KeyStore {
    Pkcs11KeyStore::open(&Pkcs11Config::from_env().expect("MPAY_PKCS11_* muhit o'zgaruvchilari"))
        .unwrap()
}

fn unique() -> String {
    format!("t{}", hex::encode(mpay_crypto::rng::array::<6>().unwrap()))
}

#[test]
#[ignore = "SoftHSM2 kerak"]
fn pkcs11_conformance_kat() {
    let _g = serial();
    let ks = open();
    check_conformance(&ks, &unique()).unwrap();
}

#[test]
#[ignore = "SoftHSM2 kerak"]
fn pkcs11_keys_are_non_extractable_and_persist() {
    let _g = serial();
    let ks = open();
    let p = unique();
    let imk = KeyLabel::new(format!("{p}.imk"));
    ks.ensure_key(&imk, KeyKind::Aes128).unwrap();
    let m1 = ks.aes_cmac(&imk, b"persist").unwrap();
    drop(ks);
    // Qayta ochilganda shu kalit (CKA_TOKEN=true) topiladi.
    let ks = open();
    assert_eq!(ks.key_kind(&imk).unwrap(), Some(KeyKind::Aes128));
    assert_eq!(ks.aes_cmac(&imk, b"persist").unwrap(), m1);
}

#[test]
#[ignore = "SoftHSM2 kerak"]
fn pkcs11_matches_memory_for_emv_chain_and_envelope() {
    let _g = serial();
    let ks = open();
    let p = unique();
    let imk_bytes = [0x2Bu8; 16];
    let imk = KeyLabel::new(format!("{p}.imk-ac"));
    ks.import_secret(&imk, KeyKind::Aes128, &imk_bytes).unwrap();
    let mem = MemoryKeyStore::random();
    mem.import_secret(&imk, KeyKind::Aes128, &imk_bytes)
        .unwrap();

    let s = MpayAes128CmacV1;
    let dpan = Pan::from_prefix("990077000000123").unwrap();
    assert_eq!(
        s.luk_from_imk(&ks, &imk, &dpan, 0, 3).unwrap(),
        s.luk_from_imk(&mem, &imk, &dpan, 0, 3).unwrap()
    );

    let kek = KeyLabel::new(format!("{p}.kek"));
    ks.ensure_key(&kek, KeyKind::Aes256).unwrap();
    let dek = Dek::generate("dek-hsm").unwrap();
    let wrapped = dek.wrap(&ks, &kek).unwrap();
    let back = Dek::unwrap(&ks, &wrapped).unwrap();
    let sealed = dek.seal(b"ctx", b"payload").unwrap();
    assert_eq!(&back.open(b"ctx", &sealed).unwrap()[..], b"payload");
}

#[test]
#[ignore = "SoftHSM2 kerak"]
fn pkcs11_standard_keys() {
    let _g = serial();
    let ks = open();
    ensure_standard_keys(&ks).unwrap();
    ensure_standard_keys(&ks).unwrap();
    let pk = ks
        .ed25519_public_key(&KeyLabel::new(KeyLabel::SERVER_ED25519))
        .unwrap();
    assert_ne!(pk, [0u8; 32]);
}

/// 2-faza P2.2: sessiyalar pool'i — parallel operatsiyalar to'g'ri va bir xil natija beradi;
/// 1 va 4 sessiya o'tkazuvchanligi chop etiladi (`--nocapture`).
#[test]
#[ignore = "SoftHSM2 kerak"]
fn pkcs11_session_pool_parallel_ops() {
    let _g = serial();
    let imk = KeyLabel::new(format!("{}.pool", unique()));
    for sessions in [1, 4] {
        let mut cfg = Pkcs11Config::from_env().unwrap();
        cfg.sessions = sessions;
        let ks = std::sync::Arc::new(Pkcs11KeyStore::open(&cfg).unwrap());
        assert_eq!(ks.session_count(), sessions);
        ks.ensure_key(&imk, KeyKind::Aes128).unwrap();
        let want = ks.aes_cmac(&imk, b"pool").unwrap();
        let t0 = std::time::Instant::now();
        let handles: Vec<_> = (0..8)
            .map(|_| {
                let ks = ks.clone();
                let imk = imk.clone();
                std::thread::spawn(move || {
                    for _ in 0..500 {
                        assert_eq!(ks.aes_cmac(&imk, b"pool").unwrap(), want);
                    }
                })
            })
            .collect();
        for h in handles {
            h.join().unwrap();
        }
        let dt = t0.elapsed().as_secs_f64();
        println!(
            "pkcs11 pool: {sessions} sessiya, 8 oqim, 4000 CMAC: {:.0} op/s",
            4000.0 / dt
        );
    }
}

/// 2-faza P2.2: login tushib qolsa (HSM qayta ishga tushishi) sessiya qayta ochiladi va operatsiya
/// muvaffaqiyatli takrorlanadi — server qayta ishga tushirilmaydi.
#[test]
#[ignore = "SoftHSM2 kerak"]
fn pkcs11_recovers_after_logout() {
    let _g = serial();
    let mut cfg = Pkcs11Config::from_env().unwrap();
    cfg.sessions = 1;
    let ks = Pkcs11KeyStore::open(&cfg).unwrap();
    let imk = KeyLabel::new(format!("{}.relogin", unique()));
    ks.ensure_key(&imk, KeyKind::Aes128).unwrap();
    let before = ks.aes_cmac(&imk, b"relogin").unwrap();
    ks.simulate_logout().unwrap();
    assert_eq!(ks.aes_cmac(&imk, b"relogin").unwrap(), before);
    // Ikkinchi marta ham (yangi sessiya bilan) ishlaydi.
    ks.simulate_logout().unwrap();
    assert_eq!(ks.key_kind(&imk).unwrap(), Some(KeyKind::Aes128));
}
