//! D8 saqlash oqimi: sxema v6 → v7 (eski «Kelajagim» yozuvi QOROVUL bo'ladi, balans yo'qolmaydi).
#![allow(clippy::expect_used, clippy::unwrap_used)]

use rusqlite::{Connection, params};
use rusqlite_migration::{M, Migrations};
use storage::schema::{self, SCHEMA_V1, SCHEMA_V2, SCHEMA_V3, SCHEMA_V4, SCHEMA_V5, SCHEMA_V6};

const HOUSEHOLD: &str = "0192f100-0000-7000-8000-0000000000a1";
const ASSET: &str = "0192f100-0000-7000-8000-0000000000b1";
const ENTRY_1: &str = "0192f100-0000-7000-8000-0000000000c1";
const ENTRY_2: &str = "0192f100-0000-7000-8000-0000000000c2";

#[test]
fn v6_dan_joriy_versiyaga_otganda_qorovul_turi_tiklanadi_va_balans_saqlanadi() {
    let mut conn = Connection::open_in_memory().expect("xotira");
    Migrations::new(vec![
        M::up(SCHEMA_V1),
        M::up(SCHEMA_V2),
        M::up(SCHEMA_V3),
        M::up(SCHEMA_V4),
        M::up(SCHEMA_V5),
        M::up(SCHEMA_V6),
    ])
    .to_latest(&mut conn)
    .expect("v6 gacha");

    let created = "2026-10-15T01:00:00Z";
    conn.execute(
        "INSERT INTO households (id, name, created_at, updated_at, version, origin_device_id) VALUES (?1, 'Oila', ?2, ?2, 1, 'device-1')",
        params![HOUSEHOLD, created],
    )
    .expect("xonadon");
    conn.execute(
        "INSERT INTO assets (id, household_id, type, name, quantity, unit, currency, acquired_at, created_at, updated_at, version, origin_device_id) \
         VALUES (?1, ?2, 'VAULT', 'Kelajagim', 0, 'so''m', 'UZS', '2026-10-01', ?3, ?3, 1, 'device-1')",
        params![ASSET, HOUSEHOLD, created],
    )
    .expect("aktiv");
    // Eski (v6 gacha) yozuvlar: pul turi yo'q.
    for (id, kind, amount) in [
        (ENTRY_1, "INITIAL", 50_000_000_i64),
        (ENTRY_2, "DEPOSIT", 12_000_000_i64),
    ] {
        conn.execute(
            "INSERT INTO vault_transactions (id, household_id, asset_id, vault_type, kind, amount_minor, currency, occurred_on, created_at, updated_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, NULL, ?4, ?5, 'UZS', '2026-10-01', ?6, ?6, 1, 'device-1')",
            params![id, HOUSEHOLD, ASSET, kind, amount, created],
        )
        .expect("yozuv");
    }
    let balance_before: i64 = conn
        .query_row(
            "SELECT SUM(amount_minor) FROM vault_transactions",
            [],
            |row| row.get(0),
        )
        .expect("balans");

    schema::migrations()
        .to_latest(&mut conn)
        .expect("joriy versiya gacha");

    let types: Vec<Option<String>> = conn
        .prepare("SELECT vault_type FROM vault_transactions ORDER BY id")
        .expect("so'rov")
        .query_map([], |row| row.get(0))
        .expect("qatorlar")
        .map(|row| row.expect("qator"))
        .collect();
    assert_eq!(
        types,
        vec![Some("QOROVUL".to_owned()), Some("QOROVUL".to_owned())]
    );

    let balance_after: i64 = conn
        .query_row(
            "SELECT SUM(amount_minor) FROM vault_transactions",
            [],
            |row| row.get(0),
        )
        .expect("balans");
    assert_eq!(balance_before, balance_after);

    let version: i64 = conn
        .query_row("PRAGMA user_version", [], |row| row.get(0))
        .expect("versiya");
    assert_eq!(version, 9);
}
