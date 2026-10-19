//! Musofir (M1): makon sozlamalari (ish valyutasi, o'z ulushi, qaytish maqsadi), kurslar va pul
//! harakatlari. Maosh va xarajat — `incomes` / `expenses` (makon bo'yicha).
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfSettingsRow {
    pub country: Option<String>,
    pub work_currency: String,
    pub share_bp: i64,
    pub target_minor: Option<i64>,
    pub target_currency: Option<String>,
    pub return_on: Option<String>,
}

pub fn settings(c: &Connection, s: &SpaceScope) -> Result<Option<MfSettingsRow>, StorageError> {
    Ok(c.query_row(
        "SELECT country, work_currency, share_bp, target_minor, target_currency, return_on FROM mf_settings
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(MfSettingsRow {
                country: r.get(0)?,
                work_currency: r.get(1)?,
                share_bp: r.get(2)?,
                target_minor: r.get(3)?,
                target_currency: r.get(4)?,
                return_on: r.get(5)?,
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
    row: &MfSettingsRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_settings (id, household_id, space_id, country, work_currency, share_bp, target_minor,
            target_currency, return_on, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?10, ?11, ?11)
         ON CONFLICT (space_id) DO UPDATE SET country = excluded.country,
            work_currency = excluded.work_currency, share_bp = excluded.share_bp,
            target_minor = excluded.target_minor, target_currency = excluded.target_currency,
            return_on = excluded.return_on, updated_at = excluded.updated_at,
            updated_by_device_id = excluded.updated_by_device_id, version = mf_settings.version + 1",
        params![id, s.household_id, s.space_id, row.country, row.work_currency, row.share_bp,
            row.target_minor, row.target_currency, row.return_on, m.now, m.device_id],
    )?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfRateRow {
    pub id: String,
    pub rate_on: String,
    pub from_currency: String,
    pub to_currency: String,
    pub rate_num: i64,
    pub rate_den: i64,
    pub source: Option<String>,
}

pub fn insert_rate(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &MfRateRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_rates (id, household_id, space_id, rate_on, from_currency, to_currency, rate_num,
            rate_den, source, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
        params![row.id, s.household_id, s.space_id, row.rate_on, row.from_currency, row.to_currency,
            row.rate_num, row.rate_den, row.source, m.now, m.device_id],
    )?;
    Ok(())
}

/// `on` sanasigacha (shu kun ham) amaldagi kurs: eng so'nggi sana, bir sanada — oxirgi kiritilgani.
pub fn rate_on(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
    on: &str,
) -> Result<Option<MfRateRow>, StorageError> {
    Ok(c.query_row(
        "SELECT id, rate_on, from_currency, to_currency, rate_num, rate_den, source FROM mf_rates
         WHERE household_id = ?1 AND space_id = ?2 AND from_currency = ?3 AND to_currency = ?4
            AND rate_on <= ?5
         ORDER BY rate_on DESC, created_at DESC, id DESC LIMIT 1",
        params![s.household_id, s.space_id, from, to, on],
        |r| {
            Ok(MfRateRow {
                id: r.get(0)?,
                rate_on: r.get(1)?,
                from_currency: r.get(2)?,
                to_currency: r.get(3)?,
                rate_num: r.get(4)?,
                rate_den: r.get(5)?,
                source: r.get(6)?,
            })
        },
    )
    .optional()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfMoveRow {
    pub id: String,
    pub kind: String,
    pub amount_minor: i64,
    pub currency: String,
    pub fee_minor: i64,
    pub received_minor: Option<i64>,
    pub received_currency: Option<String>,
    pub occurred_on: String,
    pub note: Option<String>,
}

const COLS: &str = "id, kind, amount_minor, currency, fee_minor, received_minor, received_currency,
    occurred_on, note";

fn map(r: &rusqlite::Row<'_>) -> rusqlite::Result<MfMoveRow> {
    Ok(MfMoveRow {
        id: r.get(0)?,
        kind: r.get(1)?,
        amount_minor: r.get(2)?,
        currency: r.get(3)?,
        fee_minor: r.get(4)?,
        received_minor: r.get(5)?,
        received_currency: r.get(6)?,
        occurred_on: r.get(7)?,
        note: r.get(8)?,
    })
}

pub fn insert_move(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &MfMoveRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_moves (id, household_id, space_id, kind, amount_minor, currency, fee_minor,
            received_minor, received_currency, occurred_on, note, created_at, updated_at, origin_device_id,
            updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)",
        params![row.id, s.household_id, s.space_id, row.kind, row.amount_minor, row.currency,
            row.fee_minor, row.received_minor, row.received_currency, row.occurred_on, row.note, m.now,
            m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi harakatlar (lokal sanalar).
pub fn moves_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<MfMoveRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM mf_moves WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Makonda istalgan yozuv bormi (maosh, xarajat yoki harakat).
pub fn has_records(c: &Connection, s: &SpaceScope) -> Result<bool, StorageError> {
    has_records_other_than(c, s, "")
}

/// Makonda boshqa valyutadagi yozuv bormi (ish valyutasini o'zgartirish taqiqi uchun).
pub fn has_records_other_than(
    c: &Connection,
    s: &SpaceScope,
    currency: &str,
) -> Result<bool, StorageError> {
    let n: i64 = c.query_row(
        "SELECT (SELECT COUNT(*) FROM incomes WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
                    AND currency <> ?3)
              + (SELECT COUNT(*) FROM expenses WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
                    AND currency <> ?3)
              + (SELECT COUNT(*) FROM mf_moves WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
                    AND currency <> ?3)
              + (SELECT COUNT(*) FROM mf_reserve_moves WHERE household_id = ?1 AND space_id = ?2
                    AND deleted_at IS NULL AND currency <> ?3)",
        params![s.household_id, s.space_id, currency],
        |r| r.get(0),
    )?;
    Ok(n > 0)
}

// ---- M2: «Ikki qirg'oq» ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfTermsRow {
    pub shares_json: String,
    pub receiver_member_id: Option<String>,
    pub agreement_id: Option<String>,
}

pub fn terms(c: &Connection, s: &SpaceScope) -> Result<Option<MfTermsRow>, StorageError> {
    Ok(c.query_row(
        "SELECT shares_json, receiver_member_id, agreement_id FROM mf_remittance_terms
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(MfTermsRow {
                shares_json: r.get(0)?,
                receiver_member_id: r.get(1)?,
                agreement_id: r.get(2)?,
            })
        },
    )
    .optional()?)
}

pub fn upsert_terms(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    row: &MfTermsRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_remittance_terms (id, household_id, space_id, shares_json, receiver_member_id,
            agreement_id, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?7, ?8, ?8)
         ON CONFLICT (space_id) DO UPDATE SET shares_json = excluded.shares_json,
            receiver_member_id = excluded.receiver_member_id, agreement_id = excluded.agreement_id,
            updated_at = excluded.updated_at, updated_by_device_id = excluded.updated_by_device_id,
            version = mf_remittance_terms.version + 1",
        params![id, s.household_id, s.space_id, row.shares_json, row.receiver_member_id,
            row.agreement_id, m.now, m.device_id],
    )?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfPartRow {
    pub id: String,
    pub move_id: String,
    pub purpose: String,
    pub share_bp: i64,
}

pub fn insert_part(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &MfPartRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_remittance_parts (id, household_id, space_id, move_id, purpose, share_bp, created_at,
            origin_device_id) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        params![row.id, s.household_id, s.space_id, row.move_id, row.purpose, row.share_bp, m.now,
            m.device_id],
    )?;
    Ok(())
}

pub fn parts(c: &Connection, s: &SpaceScope) -> Result<Vec<MfPartRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, move_id, purpose, share_bp FROM mf_remittance_parts
         WHERE household_id = ?1 AND space_id = ?2 ORDER BY move_id, purpose",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(MfPartRow {
            id: r.get(0)?,
            move_id: r.get(1)?,
            purpose: r.get(2)?,
            share_bp: r.get(3)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Uyga yuborilganlarning hammasi (eng yangisi birinchi).
pub fn sent_home(c: &Connection, s: &SpaceScope) -> Result<Vec<MfMoveRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM mf_moves WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND kind = 'SENT_HOME' ORDER BY occurred_on DESC, created_at DESC"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfReceiptRow {
    pub id: String,
    pub move_id: String,
    pub income_id: String,
    pub member_id: Option<String>,
    pub received_minor: i64,
    pub currency: String,
    pub received_on: String,
    pub note: Option<String>,
}

pub fn insert_receipt(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &MfReceiptRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_receipts (id, household_id, space_id, move_id, income_id, member_id, received_minor,
            currency, received_on, note, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
        params![row.id, s.household_id, s.space_id, row.move_id, row.income_id, row.member_id,
            row.received_minor, row.currency, row.received_on, row.note, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn receipts(c: &Connection, s: &SpaceScope) -> Result<Vec<MfReceiptRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, move_id, income_id, member_id, received_minor, currency, received_on, note FROM mf_receipts
         WHERE household_id = ?1 AND space_id = ?2 ORDER BY received_on, created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(MfReceiptRow {
            id: r.get(0)?,
            move_id: r.get(1)?,
            income_id: r.get(2)?,
            member_id: r.get(3)?,
            received_minor: r.get(4)?,
            currency: r.get(5)?,
            received_on: r.get(6)?,
            note: r.get(7)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn insert_spend(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    expense_id: &str,
    purpose: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_spends (id, household_id, space_id, expense_id, purpose, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![id, s.household_id, s.space_id, expense_id, purpose, m.now, m.device_id],
    )?;
    Ok(())
}

/// Maqsad bo'yicha xarajat: Uy makonidagi (o'chirilmagan) xarajat bilan.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfSpendRow {
    pub expense_id: String,
    pub purpose: String,
    pub amount_minor: i64,
    pub currency: String,
    pub category_id: String,
    pub occurred_on: String,
    pub note: Option<String>,
}

pub fn spends(c: &Connection, s: &SpaceScope) -> Result<Vec<MfSpendRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT e.id, sp.purpose, e.amount_minor, e.currency, e.category_id, e.occurred_on, e.note
         FROM mf_spends sp JOIN expenses e ON e.id = sp.expense_id AND e.household_id = sp.household_id
         WHERE sp.household_id = ?1 AND sp.space_id = ?2 AND e.deleted_at IS NULL
         ORDER BY e.occurred_on DESC, e.created_at DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(MfSpendRow {
            expense_id: r.get(0)?,
            purpose: r.get(1)?,
            amount_minor: r.get(2)?,
            currency: r.get(3)?,
            category_id: r.get(4)?,
            occurred_on: r.get(5)?,
            note: r.get(6)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// ---- M3: yo'l qarzi, qaytish, katta qarorlar ----

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct MfReturnRow {
    pub travel_debt_id: Option<String>,
    pub travel_target_months: Option<i64>,
    pub returned_on: Option<String>,
    pub brought_home_minor: Option<i64>,
    pub brought_home_currency: Option<String>,
}

pub fn return_info(c: &Connection, s: &SpaceScope) -> Result<MfReturnRow, StorageError> {
    Ok(c.query_row(
        "SELECT travel_debt_id, travel_target_months, returned_on, brought_home_minor, brought_home_currency
         FROM mf_settings WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(MfReturnRow {
                travel_debt_id: r.get(0)?,
                travel_target_months: r.get(1)?,
                returned_on: r.get(2)?,
                brought_home_minor: r.get(3)?,
                brought_home_currency: r.get(4)?,
            })
        },
    )
    .optional()?
    .unwrap_or_default())
}

pub fn set_travel_debt(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    debt_id: Option<&str>,
    target_months: Option<i64>,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE mf_settings SET travel_debt_id = ?3, travel_target_months = ?4, updated_at = ?5,
            updated_by_device_id = ?6, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![
            s.household_id,
            s.space_id,
            debt_id,
            target_months,
            m.now,
            m.device_id
        ],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

pub fn set_return(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    returned_on: Option<&str>,
    brought: Option<(i64, &str)>,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE mf_settings SET returned_on = ?3, brought_home_minor = ?4, brought_home_currency = ?5,
            updated_at = ?6, updated_by_device_id = ?7, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, returned_on, brought.map(|b| b.0), brought.map(|b| b.1),
            m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

pub fn insert_debt_payment(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    repayment_id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_debt_payments (id, household_id, space_id, repayment_id, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![id, s.household_id, s.space_id, repayment_id, m.now, m.device_id],
    )?;
    Ok(())
}

/// «Qarz to'lovi» maqsadidan qilingan to'lovlar (o'chirilmagan U8 to'lovlari, kreditor bilan).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfDebtPaymentRow {
    pub repayment_id: String,
    pub debt_id: String,
    pub creditor: String,
    pub amount_minor: i64,
    pub currency: String,
    pub paid_on: String,
    pub note: Option<String>,
}

pub fn debt_payments(
    c: &Connection,
    s: &SpaceScope,
) -> Result<Vec<MfDebtPaymentRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT r.id, r.owner_id, d.creditor, r.amount_minor, r.currency, r.paid_on, r.note
         FROM mf_debt_payments p
         JOIN repayments r ON r.id = p.repayment_id AND r.household_id = p.household_id
         JOIN debts d ON d.id = r.owner_id AND d.household_id = r.household_id
         WHERE p.household_id = ?1 AND p.space_id = ?2 AND r.deleted_at IS NULL AND r.owner_type = 'DEBT'
         ORDER BY r.paid_on DESC, r.created_at DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(MfDebtPaymentRow {
            repayment_id: r.get(0)?,
            debt_id: r.get(1)?,
            creditor: r.get(2)?,
            amount_minor: r.get(3)?,
            currency: r.get(4)?,
            paid_on: r.get(5)?,
            note: r.get(6)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfDecisionRow {
    pub id: String,
    pub decided_on: String,
    pub kind: String,
    pub title: String,
    pub amount_minor: i64,
    pub currency: String,
    pub answers_json: String,
    pub verdict: String,
    pub flags_json: String,
    pub in_cooling: bool,
    pub wait_until: Option<String>,
    pub choice: String,
    pub note: Option<String>,
}

pub fn insert_decision(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    d: &MfDecisionRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_decisions (id, household_id, space_id, decided_on, kind, title, amount_minor, currency,
            answers_json, verdict, flags_json, in_cooling, wait_until, choice, note, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17)",
        params![d.id, s.household_id, s.space_id, d.decided_on, d.kind, d.title, d.amount_minor, d.currency,
            d.answers_json, d.verdict, d.flags_json, d.in_cooling, d.wait_until, d.choice, d.note, m.now,
            m.device_id],
    )?;
    Ok(())
}

pub fn decisions(c: &Connection, s: &SpaceScope) -> Result<Vec<MfDecisionRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, decided_on, kind, title, amount_minor, currency, answers_json, verdict, flags_json,
            in_cooling, wait_until, choice, note FROM mf_decisions
         WHERE household_id = ?1 AND space_id = ?2 ORDER BY decided_on DESC, created_at DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(MfDecisionRow {
            id: r.get(0)?,
            decided_on: r.get(1)?,
            kind: r.get(2)?,
            title: r.get(3)?,
            amount_minor: r.get(4)?,
            currency: r.get(5)?,
            answers_json: r.get(6)?,
            verdict: r.get(7)?,
            flags_json: r.get(8)?,
            in_cooling: r.get(9)?,
            wait_until: r.get(10)?,
            choice: r.get(11)?,
            note: r.get(12)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// ---- M4: qorovul pul, ish boshlash summasi, qaror natijasi ----

/// Qorovul pul harakati — `MfMoveRow` shaklida (komissiya 0, uyda olingan yo'q).
pub fn insert_reserve_move(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &MfMoveRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_reserve_moves (id, household_id, space_id, kind, amount_minor, currency, occurred_on,
            note, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9, ?10, ?10)",
        params![row.id, s.household_id, s.space_id, row.kind, row.amount_minor, row.currency,
            row.occurred_on, row.note, m.now, m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi qorovul pul harakatlari.
pub fn reserve_moves_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<MfMoveRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, kind, amount_minor, currency, 0, NULL, NULL, occurred_on, note FROM mf_reserve_moves
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct MfPlanRow {
    pub reserve_months: Option<i64>,
    pub startup_minor: Option<i64>,
    pub startup_currency: Option<String>,
    pub startup_idea_id: Option<String>,
}

pub fn plan_info(c: &Connection, s: &SpaceScope) -> Result<MfPlanRow, StorageError> {
    Ok(c.query_row(
        "SELECT reserve_months, startup_minor, startup_currency, startup_idea_id FROM mf_settings
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(MfPlanRow {
                reserve_months: r.get(0)?,
                startup_minor: r.get(1)?,
                startup_currency: r.get(2)?,
                startup_idea_id: r.get(3)?,
            })
        },
    )
    .optional()?
    .unwrap_or_default())
}

pub fn set_plan(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    p: &MfPlanRow,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE mf_settings SET reserve_months = ?3, startup_minor = ?4, startup_currency = ?5,
            startup_idea_id = ?6, updated_at = ?7, updated_by_device_id = ?8, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![
            s.household_id,
            s.space_id,
            p.reserve_months,
            p.startup_minor,
            p.startup_currency,
            p.startup_idea_id,
            m.now,
            m.device_id
        ],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfOutcomeRow {
    pub id: String,
    pub decision_id: String,
    pub outcome: String,
    pub outcome_on: String,
    pub note: Option<String>,
}

pub fn insert_outcome(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    o: &MfOutcomeRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_decision_outcomes (id, household_id, space_id, decision_id, outcome, outcome_on, note,
            created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        params![o.id, s.household_id, s.space_id, o.decision_id, o.outcome, o.outcome_on, o.note, m.now,
            m.device_id],
    )?;
    Ok(())
}

pub fn outcomes(c: &Connection, s: &SpaceScope) -> Result<Vec<MfOutcomeRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, decision_id, outcome, outcome_on, note FROM mf_decision_outcomes
         WHERE household_id = ?1 AND space_id = ?2",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(MfOutcomeRow {
            id: r.get(0)?,
            decision_id: r.get(1)?,
            outcome: r.get(2)?,
            outcome_on: r.get(3)?,
            note: r.get(4)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}
