//! Kasb-kor: egasi maoshi va o'z mehnati bahosi, egasi/hamyon harakatlari (K1), uskunalar va oilaviy
//! mehnat (K2). Tushum va chiqim — `incomes` / `expenses` (makon bo'yicha).
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkSettingsRow {
    pub owner_salary_minor: i64,
    pub owner_labor_minor: i64,
    pub currency: String,
}

pub fn settings(c: &Connection, s: &SpaceScope) -> Result<Option<KkSettingsRow>, StorageError> {
    Ok(c.query_row(
        "SELECT owner_salary_minor, owner_labor_minor, currency FROM kk_settings
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(KkSettingsRow {
                owner_salary_minor: r.get(0)?,
                owner_labor_minor: r.get(1)?,
                currency: r.get(2)?,
            })
        },
    )
    .optional()?)
}

/// Yangi makon uchun `id` bilan yaratadi, mavjud bo'lsa yangilaydi.
pub fn upsert_settings(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    row: &KkSettingsRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_settings (id, household_id, space_id, owner_salary_minor, owner_labor_minor, currency,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?8, ?5, ?6, ?6, ?7, ?7)
         ON CONFLICT (space_id) DO UPDATE SET owner_salary_minor = excluded.owner_salary_minor,
            owner_labor_minor = excluded.owner_labor_minor,
            currency = excluded.currency, updated_at = excluded.updated_at,
            updated_by_device_id = excluded.updated_by_device_id, version = kk_settings.version + 1",
        params![id, s.household_id, s.space_id, row.owner_salary_minor, row.currency, m.now, m.device_id,
            row.owner_labor_minor],
    )?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkMoveRow {
    pub id: String,
    pub kind: String,
    pub wallet: String,
    pub to_wallet: Option<String>,
    pub amount_minor: i64,
    pub currency: String,
    pub occurred_on: String,
    pub note: Option<String>,
    pub transfer_id: Option<String>,
}

const COLS: &str =
    "id, kind, wallet, to_wallet, amount_minor, currency, occurred_on, note, transfer_id";

fn map(r: &rusqlite::Row<'_>) -> rusqlite::Result<KkMoveRow> {
    Ok(KkMoveRow {
        id: r.get(0)?,
        kind: r.get(1)?,
        wallet: r.get(2)?,
        to_wallet: r.get(3)?,
        amount_minor: r.get(4)?,
        currency: r.get(5)?,
        occurred_on: r.get(6)?,
        note: r.get(7)?,
        transfer_id: r.get(8)?,
    })
}

pub fn insert_move(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &KkMoveRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_moves (id, household_id, space_id, kind, wallet, to_wallet, amount_minor, currency,
            occurred_on, note, transfer_id, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)",
        params![row.id, s.household_id, s.space_id, row.kind, row.wallet, row.to_wallet, row.amount_minor,
            row.currency, row.occurred_on, row.note, row.transfer_id, m.now, m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi harakatlar (lokal sanalar).
pub fn moves_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<KkMoveRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM kk_moves WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkEquipmentRow {
    pub id: String,
    pub name: String,
    pub cost_minor: i64,
    pub salvage_minor: i64,
    pub useful_months: i64,
    pub currency: String,
    pub acquired_on: String,
    pub wallet: Option<String>,
    pub disposed_on: Option<String>,
    pub disposal_proceeds_minor: Option<i64>,
    pub disposal_wallet: Option<String>,
}

const EQ_COLS: &str =
    "id, name, cost_minor, salvage_minor, useful_months, currency, acquired_on, wallet,
    disposed_on, disposal_proceeds_minor, disposal_wallet";

fn map_equipment(r: &rusqlite::Row<'_>) -> rusqlite::Result<KkEquipmentRow> {
    Ok(KkEquipmentRow {
        id: r.get(0)?,
        name: r.get(1)?,
        cost_minor: r.get(2)?,
        salvage_minor: r.get(3)?,
        useful_months: r.get(4)?,
        currency: r.get(5)?,
        acquired_on: r.get(6)?,
        wallet: r.get(7)?,
        disposed_on: r.get(8)?,
        disposal_proceeds_minor: r.get(9)?,
        disposal_wallet: r.get(10)?,
    })
}

pub fn insert_equipment(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &KkEquipmentRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_equipment (id, household_id, space_id, name, cost_minor, salvage_minor, useful_months,
            currency, acquired_on, wallet, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?11, ?12, ?12)",
        params![row.id, s.household_id, s.space_id, row.name, row.cost_minor, row.salvage_minor,
            row.useful_months, row.currency, row.acquired_on, row.wallet, m.now, m.device_id],
    )?;
    Ok(())
}

/// Makondagi barcha uskunalar (o'chirilmaganlari), xarid sanasi bo'yicha.
pub fn equipment(c: &Connection, s: &SpaceScope) -> Result<Vec<KkEquipmentRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {EQ_COLS} FROM kk_equipment WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY acquired_on, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_equipment)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Sotildi yoki yaroqsiz bo'ldi. Faqat hali chiqib ketmagan uskuna uchun.
pub fn dispose_equipment(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    disposed_on: &str,
    proceeds_minor: i64,
    wallet: Option<&str>,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE kk_equipment SET disposed_on = ?4, disposal_proceeds_minor = ?5, disposal_wallet = ?6,
            updated_at = ?7, updated_by_device_id = ?8, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL AND disposed_on IS NULL",
        params![s.household_id, s.space_id, id, disposed_on, proceeds_minor, wallet, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

pub fn delete_equipment(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    soft_delete(tx, "kk_equipment", s, id, m)
}

fn soft_delete(
    tx: &Transaction<'_>,
    table: &str,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        &format!(
            "UPDATE {table} SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5, version = version + 1
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkFamilyLaborRow {
    pub id: String,
    pub person: String,
    pub member_id: Option<String>,
    pub worked_on: String,
    pub hours100: i64,
    pub hourly_rate_minor: i64,
    pub currency: String,
    pub paid: bool,
    pub note: Option<String>,
}

pub fn insert_family_labor(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &KkFamilyLaborRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_family_labor (id, household_id, space_id, person, member_id, worked_on, hours100,
            hourly_rate_minor, currency, paid, note, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)",
        params![row.id, s.household_id, s.space_id, row.person, row.member_id, row.worked_on, row.hours100,
            row.hourly_rate_minor, row.currency, row.paid, row.note, m.now, m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi oilaviy mehnat yozuvlari.
pub fn family_labor_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<KkFamilyLaborRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, person, member_id, worked_on, hours100, hourly_rate_minor, currency, paid, note
         FROM kk_family_labor WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND worked_on >= ?3 AND worked_on < ?4 ORDER BY worked_on, created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], |r| {
        Ok(KkFamilyLaborRow {
            id: r.get(0)?,
            person: r.get(1)?,
            member_id: r.get(2)?,
            worked_on: r.get(3)?,
            hours100: r.get(4)?,
            hourly_rate_minor: r.get(5)?,
            currency: r.get(6)?,
            paid: r.get(7)?,
            note: r.get(8)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn delete_family_labor(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    soft_delete(tx, "kk_family_labor", s, id, m)
}

/// «Hisob kuni» qoidalari (K3): soliq zaxirasi va qolgan pul taqsimoti (bp).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkCloseRulesRow {
    pub tax_base: String,
    pub tax_bp: i64,
    pub tax_fixed_minor: i64,
    pub reserve_bp: i64,
    pub working_bp: i64,
    pub expansion_bp: i64,
    pub sadaqa_bp: i64,
}

impl Default for KkCloseRulesRow {
    /// Sxemadagi standart: soliqsiz, 30 / 50 / 20 / 0.
    fn default() -> Self {
        Self {
            tax_base: "NONE".into(),
            tax_bp: 0,
            tax_fixed_minor: 0,
            reserve_bp: 3000,
            working_bp: 5000,
            expansion_bp: 2000,
            sadaqa_bp: 0,
        }
    }
}

pub fn close_rules(
    c: &Connection,
    s: &SpaceScope,
) -> Result<Option<KkCloseRulesRow>, StorageError> {
    Ok(c.query_row(
        "SELECT tax_base, tax_bp, tax_fixed_minor, reserve_bp, working_bp, expansion_bp, sadaqa_bp
         FROM kk_settings WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(KkCloseRulesRow {
                tax_base: r.get(0)?,
                tax_bp: r.get(1)?,
                tax_fixed_minor: r.get(2)?,
                reserve_bp: r.get(3)?,
                working_bp: r.get(4)?,
                expansion_bp: r.get(5)?,
                sadaqa_bp: r.get(6)?,
            })
        },
    )
    .optional()?)
}

/// Faqat qoidalar ustunlarini yozadi (maosh va o'z mehnati bahosi saqlanib qoladi).
pub fn upsert_close_rules(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    currency: &str,
    row: &KkCloseRulesRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_settings (id, household_id, space_id, currency, tax_base, tax_bp, tax_fixed_minor,
            reserve_bp, working_bp, expansion_bp, sadaqa_bp, created_at, updated_at, origin_device_id,
            updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)
         ON CONFLICT (space_id) DO UPDATE SET tax_base = excluded.tax_base, tax_bp = excluded.tax_bp,
            tax_fixed_minor = excluded.tax_fixed_minor, reserve_bp = excluded.reserve_bp,
            working_bp = excluded.working_bp, expansion_bp = excluded.expansion_bp,
            sadaqa_bp = excluded.sadaqa_bp, updated_at = excluded.updated_at,
            updated_by_device_id = excluded.updated_by_device_id, version = kk_settings.version + 1",
        params![id, s.household_id, s.space_id, currency, row.tax_base, row.tax_bp, row.tax_fixed_minor,
            row.reserve_bp, row.working_bp, row.expansion_bp, row.sadaqa_bp, m.now, m.device_id],
    )?;
    Ok(())
}

/// «Hisob kuni» bayonnomasi (o'zgarmas).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkCloseRow {
    pub id: String,
    pub period_start: String,
    pub period_end: String,
    pub currency: String,
    pub remaining_minor: i64,
    pub carry_minor: i64,
    pub reserve_minor: i64,
    pub explanation: Option<String>,
    pub result_json: String,
    pub prev_hash: String,
    pub content_hash: String,
    pub closed_at: String,
}

pub fn insert_close(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &KkCloseRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_month_closes (id, household_id, space_id, period_start, period_end, currency,
            remaining_minor, carry_minor, reserve_minor, explanation, result_json, prev_hash, content_hash,
            closed_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)",
        params![row.id, s.household_id, s.space_id, row.period_start, row.period_end, row.currency,
            row.remaining_minor, row.carry_minor, row.reserve_minor, row.explanation, row.result_json,
            row.prev_hash, row.content_hash, row.closed_at, m.device_id],
    )?;
    Ok(())
}

/// Makondagi barcha bayonnomalar, yangisi birinchi.
pub fn closes(c: &Connection, s: &SpaceScope) -> Result<Vec<KkCloseRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, period_start, period_end, currency, remaining_minor, carry_minor, reserve_minor,
            explanation, result_json, prev_hash, content_hash, closed_at
         FROM kk_month_closes WHERE household_id = ?1 AND space_id = ?2 ORDER BY period_start DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkCloseRow {
            id: r.get(0)?,
            period_start: r.get(1)?,
            period_end: r.get(2)?,
            currency: r.get(3)?,
            remaining_minor: r.get(4)?,
            carry_minor: r.get(5)?,
            reserve_minor: r.get(6)?,
            explanation: r.get(7)?,
            result_json: r.get(8)?,
            prev_hash: r.get(9)?,
            content_hash: r.get(10)?,
            closed_at: r.get(11)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Eng oxirgi yopilgan davrning oxirgi kuni (yo'q bo'lsa `None`).
pub fn closed_until(c: &Connection, s: &SpaceScope) -> Result<Option<String>, StorageError> {
    Ok(c.query_row(
        "SELECT MAX(period_end) FROM kk_month_closes WHERE household_id = ?1 AND space_id = ?2",
        params![s.household_id, s.space_id],
        |r| r.get(0),
    )?)
}
