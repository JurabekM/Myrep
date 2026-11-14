//! MemoryKeyStore: ochiq standart KAT vektorlari.

#![allow(clippy::unwrap_used, clippy::expect_used)]

use mpay_crypto::keystore::{conformance::check_conformance, MemoryKeyStore};

#[test]
fn memory_keystore_conformance() {
    check_conformance(&MemoryKeyStore::random(), "kat").unwrap();
    check_conformance(&MemoryKeyStore::from_seed([5; 32]), "kat").unwrap();
}
