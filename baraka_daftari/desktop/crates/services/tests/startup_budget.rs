//! Sovuq startning Rust qismi: bazani ochish + 11 migratsiya + xonadon seed'i. To'liq «sovuq start < 1,5 s»
//! (oyna + WebView2) faqat Windows'da o'lchanadi (RELEASE_CHECKLIST); bu test faqat regressiya signali.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::{cell::Cell, time::Instant};

use domain::{Clock, IdGen, OffsetDateTime};
use services::{setup, Env};
use storage::Database;

struct TestClock;
impl Clock for TestClock {
    fn now(&self) -> OffsetDateTime {
        time::macros::datetime!(2026-10-11 05:00 UTC)
    }
}

struct Seq(Cell<u64>);
impl IdGen for Seq {
    fn new_id(&self) -> String {
        let n = self.0.get();
        self.0.set(n + 1);
        format!("00000000-0000-7000-8000-{n:012}")
    }
}

#[test]
fn database_open_migrate_and_seed_is_fast() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("baraka.db");
    let t = Instant::now();
    let mut db = Database::open(&path, &[7; 32]).unwrap();
    let ids = Seq(Cell::new(1));
    setup::ensure_household(
        &mut db,
        &Env {
            clock: &TestClock,
            ids: &ids,
            device_id: "dev",
        },
    )
    .unwrap();
    let first = t.elapsed();
    drop(db);

    // Keyingi ishga tushirish (migratsiyalar allaqachon qo'llangan).
    let t = Instant::now();
    let mut db = Database::open(&path, &[7; 32]).unwrap();
    setup::ensure_household(
        &mut db,
        &Env {
            clock: &TestClock,
            ids: &ids,
            device_id: "dev",
        },
    )
    .unwrap();
    let again = t.elapsed();
    eprintln!("birinchi ishga tushirish: {first:?}, keyingisi: {again:?}");
    // Debug build uchun keng chegara; reliz build'da bir necha o'n millisekund.
    assert!(first.as_millis() < 1_500, "{first:?}");
    assert!(again.as_millis() < 1_500, "{again:?}");
}
