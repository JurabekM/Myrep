#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use security::{
    KdfParams, KeyStore, KeyringStore, MemoryStore, SecretKey, SecurityError, UnixClock, Vault,
    VaultStatus,
};

struct FakeClock(Cell<i64>);
impl UnixClock for FakeClock {
    fn unix_now(&self) -> i64 {
        self.0.get()
    }
}

fn clock() -> FakeClock {
    FakeClock(Cell::new(1_800_000_000))
}

fn vault<'a>(
    dir: &tempfile::TempDir,
    store: &'a MemoryStore,
    clock: &'a FakeClock,
) -> Vault<&'a MemoryStore, &'a FakeClock> {
    Vault::with_clock(
        dir.path().join("vault.json"),
        store,
        KdfParams::fast_for_tests(),
        clock,
    )
}

#[test]
fn setup_then_unlock_returns_same_key() {
    let (dir, store, clk) = (tempfile::tempdir().unwrap(), MemoryStore::new(), clock());
    let v = vault(&dir, &store, &clk);
    assert_eq!(v.status().unwrap(), VaultStatus::Uninitialized);

    let created = v.setup("123456").unwrap();
    assert_eq!(
        v.status().unwrap(),
        VaultStatus::Locked {
            retry_after_secs: 0
        }
    );
    let opened = v.unlock("123456").unwrap();
    assert_eq!(created.as_bytes(), opened.as_bytes());

    // Kalit diskda ochiq holda yo'q.
    let on_disk = std::fs::read_to_string(dir.path().join("vault.json")).unwrap();
    let key_hex: String = created
        .as_bytes()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    assert!(!on_disk.contains(&key_hex));
}

#[test]
fn rejects_malformed_pin_and_double_setup() {
    let (dir, store, clk) = (tempfile::tempdir().unwrap(), MemoryStore::new(), clock());
    let v = vault(&dir, &store, &clk);
    for bad in ["", "12345", "1234567", "12345a", "١٢٣٤٥٦"] {
        assert_eq!(
            v.setup(bad).unwrap_err(),
            SecurityError::InvalidPin,
            "{bad}"
        );
    }
    v.setup("123456").unwrap();
    assert_eq!(
        v.setup("654321").unwrap_err(),
        SecurityError::AlreadyInitialized
    );
    assert_eq!(
        vault(&tempfile::tempdir().unwrap(), &MemoryStore::new(), &clk)
            .unlock("123456")
            .unwrap_err(),
        SecurityError::NotInitialized
    );
}

#[test]
fn wrong_pin_is_rejected() {
    let (dir, store, clk) = (tempfile::tempdir().unwrap(), MemoryStore::new(), clock());
    let v = vault(&dir, &store, &clk);
    v.setup("123456").unwrap();
    assert_eq!(v.unlock("654321").unwrap_err(), SecurityError::WrongPin);
    assert_eq!(v.unlock("12").unwrap_err(), SecurityError::WrongPin);
}

/// Qabul mezoni: keyring yozuvi o'chirilsa, faqat PIN bilan ochib bo'lmaydi;
/// PIN + keyring bilan ochiladi; keyring (boshqa sir) + to'g'ri PIN ham ochmaydi.
#[test]
fn needs_both_pin_and_keyring_secret() {
    let (dir, store, clk) = (tempfile::tempdir().unwrap(), MemoryStore::new(), clock());
    let v = vault(&dir, &store, &clk);
    let key = v.setup("123456").unwrap();

    assert_eq!(v.unlock("123456").unwrap().as_bytes(), key.as_bytes());

    store.delete().unwrap();
    assert_eq!(
        v.unlock("123456").unwrap_err(),
        SecurityError::KeyringMissing
    );

    store.set(&[0xAB; 32]).unwrap(); // boshqa sir
    assert_eq!(v.unlock("123456").unwrap_err(), SecurityError::WrongPin);
}

#[test]
fn keyring_missing_does_not_count_as_failed_attempt() {
    let (dir, store, clk) = (tempfile::tempdir().unwrap(), MemoryStore::new(), clock());
    let v = vault(&dir, &store, &clk);
    v.setup("123456").unwrap();
    let secret = store.get().unwrap().unwrap();
    store.delete().unwrap();
    for _ in 0..5 {
        assert_eq!(
            v.unlock("123456").unwrap_err(),
            SecurityError::KeyringMissing
        );
    }
    store.set(&secret).unwrap();
    assert!(v.unlock("123456").is_ok());
}

#[test]
fn lockout_escalates_blocks_even_correct_pin_and_expires() {
    let (dir, store, clk) = (tempfile::tempdir().unwrap(), MemoryStore::new(), clock());
    let v = vault(&dir, &store, &clk);
    v.setup("123456").unwrap();

    for _ in 0..3 {
        assert_eq!(v.unlock("000000").unwrap_err(), SecurityError::WrongPin);
    }
    // 3-xatodan keyin 30 s.
    assert_eq!(
        v.status().unwrap(),
        VaultStatus::Locked {
            retry_after_secs: 30
        }
    );
    assert_eq!(
        v.unlock("123456").unwrap_err(),
        SecurityError::Locked {
            retry_after_secs: 30
        }
    );

    clk.0.set(clk.0.get() + 10);
    assert_eq!(
        v.unlock("123456").unwrap_err(),
        SecurityError::Locked {
            retry_after_secs: 20
        }
    );

    clk.0.set(clk.0.get() + 20);
    assert_eq!(v.unlock("000000").unwrap_err(), SecurityError::WrongPin); // 4-xato → 60 s
    assert_eq!(
        v.status().unwrap(),
        VaultStatus::Locked {
            retry_after_secs: 60
        }
    );

    clk.0.set(clk.0.get() + 60);
    assert!(v.unlock("123456").is_ok());
    // Muvaffaqiyatdan keyin hisoblagich nolga tushadi.
    assert_eq!(
        v.status().unwrap(),
        VaultStatus::Locked {
            retry_after_secs: 0
        }
    );
    assert_eq!(v.unlock("000000").unwrap_err(), SecurityError::WrongPin);
    assert_eq!(
        v.status().unwrap(),
        VaultStatus::Locked {
            retry_after_secs: 0
        }
    );
}

#[test]
fn lockout_survives_restart() {
    let (dir, store, clk) = (tempfile::tempdir().unwrap(), MemoryStore::new(), clock());
    vault(&dir, &store, &clk).setup("123456").unwrap();
    for _ in 0..3 {
        let _ = vault(&dir, &store, &clk).unlock("000000");
    }
    // Yangi `Vault` (ilova qayta ishga tushdi) ham kutishni ko'radi.
    assert_eq!(
        vault(&dir, &store, &clk).unlock("123456").unwrap_err(),
        SecurityError::Locked {
            retry_after_secs: 30
        }
    );
}

#[test]
fn corrupt_or_tampered_file_is_an_error_not_a_panic() {
    let (dir, store, clk) = (tempfile::tempdir().unwrap(), MemoryStore::new(), clock());
    let v = vault(&dir, &store, &clk);
    v.setup("123456").unwrap();
    let path = dir.path().join("vault.json");
    let good = std::fs::read_to_string(&path).unwrap();

    std::fs::write(&path, "{not json").unwrap();
    assert!(matches!(v.unlock("123456"), Err(SecurityError::Corrupt(_))));

    // KDF parametrlari DoS uchun cheklanadi.
    std::fs::write(&path, good.replace("\"m_kib\":8", "\"m_kib\":4000000000")).unwrap();
    assert!(matches!(v.unlock("123456"), Err(SecurityError::Corrupt(_))));

    // Wrapped blob o'zgartirilsa AEAD rad etadi.
    let tampered = {
        let mut f: serde_json::Value = serde_json::from_str(&good).unwrap();
        let w = f["wrapped"].as_str().unwrap().to_owned();
        let (head, rest) = w.split_at(1);
        let flipped = format!("{}{rest}", if head == "0" { "1" } else { "0" });
        f["wrapped"] = flipped.into();
        f.to_string()
    };
    std::fs::write(&path, tampered).unwrap();
    assert_eq!(v.unlock("123456").unwrap_err(), SecurityError::WrongPin);
}

#[test]
fn secret_key_debug_does_not_leak() {
    let k = SecretKey::from_bytes([0x42; 32]);
    let s = format!("{k:?}");
    assert!(!s.contains("42") && s.contains("***"));
}

/// Butun zanjir: seyf kaliti → shifrlangan baza. Keyring yo'qolsa baza ochilmaydi.
#[test]
fn vault_key_opens_database_and_database_stays_closed_without_it() {
    use domain::*;
    use money::Currency;
    use storage::{repo, Database};

    let (dir, store, clk) = (tempfile::tempdir().unwrap(), MemoryStore::new(), clock());
    let v = vault(&dir, &store, &clk);
    let db_path = dir.path().join("baraka.db");

    let key = v.setup("123456").unwrap();
    let h = {
        struct C;
        impl Clock for C {
            fn now(&self) -> OffsetDateTime {
                OffsetDateTime::UNIX_EPOCH
            }
        }
        let mut meta = Meta::new(&UuidV7Gen, &C, "", "dev");
        meta.household_id = meta.id.clone();
        Household {
            meta,
            name: "Oila".into(),
            base_currency: Currency::Uzs,
        }
    };
    {
        let db = Database::open(&db_path, key.as_bytes()).unwrap();
        repo::insert(db.conn(), &h).unwrap();
    }

    // To'g'ri PIN + keyring → baza ochiladi.
    let reopened = v.unlock("123456").unwrap();
    let db = Database::open(&db_path, reopened.as_bytes()).unwrap();
    assert_eq!(
        repo::get::<Household>(db.conn(), &h.meta.id)
            .unwrap()
            .unwrap(),
        h
    );
    drop(db);

    // Keyring yo'q → kalit olinmaydi, shuning uchun baza ochilmaydi.
    store.delete().unwrap();
    assert!(v.unlock("123456").is_err());
    assert!(Database::open(&db_path, &[0u8; 32]).is_err());
}

/// Haqiqiy OS keyring (Windows Credential Manager / Keychain / Secret Service).
/// CI'da Windows/macOS'da `cargo test -p security -- --ignored` bilan ishga tushiriladi.
#[test]
#[ignore = "haqiqiy OS keyring talab qiladi"]
fn real_os_keyring_roundtrip() {
    let store = KeyringStore::new("uz.baraka.daftari.desktop.test", "roundtrip").unwrap();
    store.delete().unwrap();
    assert!(store.get().unwrap().is_none());
    store.set(&[1, 2, 3, 4]).unwrap();
    assert_eq!(store.get().unwrap().unwrap().as_slice(), &[1, 2, 3, 4]);
    store.delete().unwrap();
    assert!(store.get().unwrap().is_none());
}
