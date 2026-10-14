//! Kalit to'plamining oqimlari: yaratish, ochish, lockout va keyring nosozliklari.
//! Testlar haqiqiy fayl tizimida ishlaydi, lekin keyring o'rniga xotiradagi saqlash ishlatiladi.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use std::path::PathBuf;

use security::{
    KdfParams, KeyFile, MemorySecretStore, SecretKey, SecretStore, SecurityError, create_vault,
    open_vault,
};

const PIN: &str = "135790";
const WRONG_PIN: &str = "000000";
const NOW: i64 = 1_800_000_000;

/// Har test uchun alohida vaqtinchalik papka.
fn fresh_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "baraka-security-{name}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|elapsed| elapsed.as_nanos())
            .unwrap_or(0)
    ));
    std::fs::create_dir_all(&dir).expect("vaqtinchalik papka");
    dir
}

fn failed_attempts(path: &PathBuf) -> u32 {
    KeyFile::from_bytes(&std::fs::read(path).expect("fayl"))
        .expect("to'g'ri fayl")
        .failed_attempts
}

#[test]
fn yaratish_va_ochish_bir_xil_kalit_beradi() {
    let dir = fresh_dir("roundtrip");
    let path = dir.join("keys.bin");
    let store = MemorySecretStore::new();

    let created = create_vault(&path, PIN, &store, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");
    let opened = open_vault(&path, PIN, &store, NOW).expect("ochilsin");
    assert_eq!(created.as_bytes(), opened.as_bytes());
}

#[test]
fn keyring_yozuvi_yoq_bolsa_faqat_pin_bilan_ochilmaydi() {
    // D3 qabul mezoni: keyring'dagi yozuvni o'chirib, faqat PIN bilan ochib bo'lmasligi.
    let dir = fresh_dir("no-keyring");
    let path = dir.join("keys.bin");
    let store = MemorySecretStore::new();
    create_vault(&path, PIN, &store, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");

    let saved = store.read().expect("o'qilsin").expect("kalit bor");
    store.delete().expect("o'chirilsin");

    let result = open_vault(&path, PIN, &store, NOW);
    assert!(matches!(result, Err(SecurityError::KeyUnavailable)));
    // Tizim xatosi foydalanuvchi urinishi sifatida hisoblanmaydi.
    assert_eq!(failed_attempts(&path), 0);

    // Keyring tiklansa, PIN + keyring bilan yana ochiladi.
    store.write(&saved).expect("tiklansin");
    open_vault(&path, PIN, &store, NOW).expect("PIN + keyring bilan ochilsin");
}

#[test]
fn keyring_bor_bolsa_notogri_pin_ochmaydi() {
    let dir = fresh_dir("wrong-pin");
    let path = dir.join("keys.bin");
    let store = MemorySecretStore::new();
    create_vault(&path, PIN, &store, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");

    assert!(matches!(
        open_vault(&path, WRONG_PIN, &store, NOW),
        Err(SecurityError::WrongPin)
    ));
    assert_eq!(failed_attempts(&path), 1);
}

#[test]
fn uchinchi_xato_qulflaydi_va_kutish_otgach_ochiladi() {
    let dir = fresh_dir("lockout");
    let path = dir.join("keys.bin");
    let store = MemorySecretStore::new();
    create_vault(&path, PIN, &store, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");

    assert!(matches!(
        open_vault(&path, WRONG_PIN, &store, NOW),
        Err(SecurityError::WrongPin)
    ));
    assert!(matches!(
        open_vault(&path, WRONG_PIN, &store, NOW),
        Err(SecurityError::WrongPin)
    ));
    // Uchinchi xato — 30 soniyalik kutish.
    assert!(matches!(
        open_vault(&path, WRONG_PIN, &store, NOW),
        Err(SecurityError::LockedOut {
            retry_after_secs: 30
        })
    ));
    // Kutish davomida to'g'ri PIN ham qabul qilinmaydi.
    assert!(matches!(
        open_vault(&path, PIN, &store, NOW + 10),
        Err(SecurityError::LockedOut {
            retry_after_secs: 20
        })
    ));
    // Kutish tugagach to'g'ri PIN ochadi va hisoblagich nolga tushadi.
    open_vault(&path, PIN, &store, NOW + 30).expect("kutishdan keyin ochilsin");
    assert_eq!(failed_attempts(&path), 0);
}

#[test]
fn ikkita_xato_qulflamaydi() {
    let dir = fresh_dir("two-errors");
    let path = dir.join("keys.bin");
    let store = MemorySecretStore::new();
    create_vault(&path, PIN, &store, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");

    for _ in 0..2 {
        assert!(matches!(
            open_vault(&path, WRONG_PIN, &store, NOW),
            Err(SecurityError::WrongPin)
        ));
    }
    open_vault(&path, PIN, &store, NOW).expect("to'g'ri PIN ochsin");
}

#[test]
fn ikki_marta_sozlash_rad_etiladi() {
    let dir = fresh_dir("twice");
    let path = dir.join("keys.bin");
    let store = MemorySecretStore::new();
    create_vault(&path, PIN, &store, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");

    assert!(matches!(
        create_vault(&path, PIN, &store, KdfParams::FAST_FOR_TESTS),
        Err(SecurityError::AlreadySetUp)
    ));
}

#[test]
fn format_xato_pin_hisoblanmaydi() {
    let dir = fresh_dir("format");
    let path = dir.join("keys.bin");
    let store = MemorySecretStore::new();
    create_vault(&path, PIN, &store, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");

    assert!(matches!(
        open_vault(&path, "12", &store, NOW),
        Err(SecurityError::InvalidPin)
    ));
    assert_eq!(failed_attempts(&path), 0);
}

#[test]
fn boshqa_qurilma_kaliti_mismatch_beradi() {
    let dir = fresh_dir("mismatch");
    let path = dir.join("keys.bin");
    let store = MemorySecretStore::new();
    create_vault(&path, PIN, &store, KdfParams::FAST_FOR_TESTS).expect("yaratilsin");

    store
        .write(&SecretKey::from_array([0x5A; 32]))
        .expect("almashtirilsin");
    assert!(matches!(
        open_vault(&path, PIN, &store, NOW),
        Err(SecurityError::KeyringMismatch)
    ));
}

#[test]
fn sozlanmagan_fayl_notsetup_beradi() {
    let dir = fresh_dir("not-set-up");
    let path = dir.join("keys.bin");
    let store = MemorySecretStore::new();
    assert!(matches!(
        open_vault(&path, PIN, &store, NOW),
        Err(SecurityError::NotSetUp)
    ));
}
