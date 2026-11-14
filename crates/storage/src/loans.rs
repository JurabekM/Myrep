//! D9 repo: qarzlar (olingan va bergan) — reja va to'lovlar bilan (sxema v11).
//!
//! Bitta jadval ikkala yo'nalish uchun (`direction`): bergan qarzda ham foiz maydoni yo'q — tuzilmaning o'zi
//! foizni ifodalay olmaydi (SPEC 2D.5). Reja qarz bilan birga bitta tranzaksiyada yoziladi.

use domain::loans::{Installment, RepaymentPlan};
use money::{Currency, Money};
use rusqlite::{Connection, OptionalExtension, Row, params};
use time::{Date, OffsetDateTime};

use crate::StorageError;
use crate::finance::{RawMeta, format_date, parse_date};
use crate::repo::format_ts;

fn money_of(minor: i64, currency: &str) -> Result<Money, StorageError> {
    let currency = Currency::from_iso(currency)
        .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?;
    Ok(Money::new(minor, currency))
}

/// Qarz yo'nalishi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LoanDirection {
    /// Olingan qarz.
    Taken,
    /// Bergan qarz.
    Given,
}

impl LoanDirection {
    /// Bazadagi kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Taken => "TAKEN",
            Self::Given => "GIVEN",
        }
    }

    fn from_code(code: &str) -> Option<Self> {
        match code {
            "TAKEN" => Some(Self::Taken),
            "GIVEN" => Some(Self::Given),
            _ => None,
        }
    }
}

/// Qarz yozuvi (reja bilan).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LoanRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Yo'nalish.
    pub direction: LoanDirection,
    /// Kimdan / kimga.
    pub counterparty: String,
    /// Turi: `BANK | SHOP | RELATIVE | FRIEND | OTHER`.
    pub counterparty_type: String,
    /// Sabab.
    pub reason: Option<String>,
    /// Asosiy summa.
    pub principal: Money,
    /// Foizli (mavjud) qarzni kuzatish belgisi.
    pub has_markup: bool,
    /// Olingan/berilgan sana.
    pub incurred_on: Date,
    /// Qarz oldidan tekshiruv natijasi.
    pub borrow_verdict: Option<String>,
    /// Friction: zaruratmi.
    pub friction_necessity: Option<bool>,
    /// Friction: foizsiz muqobil tekshirilganmi.
    pub friction_alternative: Option<bool>,
    /// Tilxat (kelishuv), bo'lsa.
    pub agreement_id: Option<String>,
    /// Reja.
    pub plan: RepaymentPlan,
    /// Yaratilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
}

/// To'lov yozuvi (kiritish).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PaymentRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Qarz.
    pub loan_id: String,
    /// Summa (musbat).
    pub amount: Money,
    /// To'lov sanasi.
    pub paid_on: Date,
    /// Yozilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
    /// Hissa qo'shgan oila a'zosi (`DebtContributor`), bo'lsa.
    pub contributor_member_id: Option<String>,
}

/// Qarzlar.
pub struct LoanRepo<'a> {
    conn: &'a Connection,
}

impl<'a> LoanRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Qarz va rejasini bitta tranzaksiyada yozadi.
    pub fn insert(&self, row: &LoanRow) -> Result<(), StorageError> {
        let tx = self.conn.unchecked_transaction()?;
        tx.execute(
            "INSERT INTO loans (id, household_id, direction, counterparty, counterparty_type, reason, principal_minor, currency, \
             has_markup, incurred_on, borrow_verdict, friction_necessity, friction_alternative, agreement_id, \
             created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?15, NULL, 1, ?16)",
            params![
                row.id,
                row.household_id,
                row.direction.code(),
                row.counterparty,
                row.counterparty_type,
                row.reason,
                row.principal.minor(),
                row.principal.currency().iso_code(),
                i32::from(row.has_markup),
                format_date(row.incurred_on)?,
                row.borrow_verdict,
                row.friction_necessity.map(i32::from),
                row.friction_alternative.map(i32::from),
                row.agreement_id,
                format_ts(row.created_at)?,
                row.origin_device_id,
            ],
        )?;
        for (index, installment) in row.plan.installments().iter().enumerate() {
            tx.execute(
                "INSERT INTO loan_installments (loan_id, seq, due_on, amount_minor) VALUES (?1, ?2, ?3, ?4)",
                params![
                    row.id,
                    i64::try_from(index + 1).unwrap_or(i64::MAX),
                    format_date(installment.due_on)?,
                    installment.amount.minor(),
                ],
            )?;
        }
        tx.commit()?;
        Ok(())
    }

    /// Tilxat (kelishuv) bog'laydi.
    pub fn set_agreement(
        &self,
        loan_id: &str,
        agreement_id: &str,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE loans SET agreement_id = ?2, updated_at = ?3 WHERE id = ?1 AND deleted_at IS NULL",
            params![loan_id, agreement_id, format_ts(now)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// To'lov qo'shadi.
    pub fn insert_payment(&self, payment: &PaymentRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO loan_payments (id, household_id, loan_id, amount_minor, currency, paid_on, created_at, origin_device_id, \
             contributor_member_id) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
            params![
                payment.id,
                payment.household_id,
                payment.loan_id,
                payment.amount.minor(),
                payment.amount.currency().iso_code(),
                format_date(payment.paid_on)?,
                format_ts(payment.created_at)?,
                payment.origin_device_id,
                payment.contributor_member_id,
            ],
        )?;
        Ok(())
    }

    /// A'zolar bo'yicha hissalar: (a'zo, jami minor). Hissa qo'shuvchisiz to'lovlar kirmaydi.
    pub fn contributions(&self, loan_id: &str) -> Result<Vec<(String, i64)>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT contributor_member_id, SUM(amount_minor) FROM loan_payments \
             WHERE loan_id = ?1 AND contributor_member_id IS NOT NULL GROUP BY contributor_member_id ORDER BY 2 DESC",
        )?;
        let rows = statement.query_map([loan_id], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?))
        })?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        Ok(out)
    }

    /// Qarzning to'lovlari (sana bo'yicha).
    pub fn payments(&self, loan_id: &str) -> Result<Vec<(Money, Date)>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT amount_minor, currency, paid_on FROM loan_payments WHERE loan_id = ?1 ORDER BY paid_on, created_at",
        )?;
        let rows = statement.query_map([loan_id], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (minor, currency, paid_on) = row?;
            out.push((money_of(minor, &currency)?, parse_date(&paid_on)?));
        }
        Ok(out)
    }

    /// Bitta qarz.
    pub fn find(&self, id: &str) -> Result<Option<LoanRow>, StorageError> {
        let raw = self
            .conn
            .query_row(
                &format!("{} WHERE l.id = ?1 AND l.deleted_at IS NULL", SELECT),
                [id],
                read_row,
            )
            .optional()?;
        raw.map(|raw| self.with_plan(raw)).transpose()
    }

    /// Xonadonning qarzlari (yo'nalish bo'yicha), yaratilish tartibida.
    pub fn list(
        &self,
        household_id: &str,
        direction: LoanDirection,
    ) -> Result<Vec<LoanRow>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{} WHERE l.household_id = ?1 AND l.direction = ?2 AND l.deleted_at IS NULL ORDER BY l.created_at, l.id",
            SELECT
        ))?;
        let rows = statement.query_map(params![household_id, direction.code()], read_row)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(self.with_plan(row?)?);
        }
        Ok(out)
    }

    fn with_plan(&self, raw: Raw) -> Result<LoanRow, StorageError> {
        let currency = Currency::from_iso(&raw.currency)
            .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?;
        let mut statement = self.conn.prepare(
            "SELECT due_on, amount_minor FROM loan_installments WHERE loan_id = ?1 ORDER BY seq",
        )?;
        let rows = statement.query_map([raw.id.as_str()], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?))
        })?;
        let mut installments = Vec::new();
        for row in rows {
            let (due_on, minor) = row?;
            installments.push(Installment {
                due_on: parse_date(&due_on)?,
                amount: Money::new(minor, currency),
            });
        }
        let plan = RepaymentPlan::new(installments)
            .map_err(|_| StorageError::InvalidData("to'lash rejasi".to_owned()))?;
        let meta = raw.meta.into_meta()?;
        Ok(LoanRow {
            id: raw.id,
            household_id: raw.household_id,
            direction: LoanDirection::from_code(&raw.direction)
                .ok_or_else(|| StorageError::InvalidData("qarz yo'nalishi".to_owned()))?,
            counterparty: raw.counterparty,
            counterparty_type: raw.counterparty_type,
            reason: raw.reason,
            principal: Money::new(raw.principal_minor, currency),
            has_markup: raw.has_markup != 0,
            incurred_on: parse_date(&raw.incurred_on)?,
            borrow_verdict: raw.borrow_verdict,
            friction_necessity: raw.friction_necessity.map(|v| v != 0),
            friction_alternative: raw.friction_alternative.map(|v| v != 0),
            agreement_id: raw.agreement_id,
            plan,
            created_at: meta.created_at,
            origin_device_id: meta.origin_device_id,
        })
    }
}

const SELECT: &str = "SELECT l.id, l.household_id, l.direction, l.counterparty, l.counterparty_type, l.reason, l.principal_minor, \
    l.currency, l.has_markup, l.incurred_on, l.borrow_verdict, l.friction_necessity, l.friction_alternative, l.agreement_id, \
    l.created_at, l.updated_at, l.deleted_at, l.version, l.origin_device_id FROM loans l";

struct Raw {
    id: String,
    household_id: String,
    direction: String,
    counterparty: String,
    counterparty_type: String,
    reason: Option<String>,
    principal_minor: i64,
    currency: String,
    has_markup: i64,
    incurred_on: String,
    borrow_verdict: Option<String>,
    friction_necessity: Option<i64>,
    friction_alternative: Option<i64>,
    agreement_id: Option<String>,
    meta: RawMeta,
}

fn read_row(row: &Row<'_>) -> rusqlite::Result<Raw> {
    Ok(Raw {
        id: row.get(0)?,
        household_id: row.get(1)?,
        direction: row.get(2)?,
        counterparty: row.get(3)?,
        counterparty_type: row.get(4)?,
        reason: row.get(5)?,
        principal_minor: row.get(6)?,
        currency: row.get(7)?,
        has_markup: row.get(8)?,
        incurred_on: row.get(9)?,
        borrow_verdict: row.get(10)?,
        friction_necessity: row.get(11)?,
        friction_alternative: row.get(12)?,
        agreement_id: row.get(13)?,
        meta: RawMeta::read(row, 14)?,
    })
}

/// Sotiladigan buyum (SPEC 2D.6: qarzdan chiqish uchun zaxira manba).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SellableRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Nomi.
    pub name: String,
    /// Taxminiy qiymati.
    pub estimate: Money,
    /// Izoh.
    pub note: Option<String>,
    /// Sotilgan vaqt.
    pub sold_at: Option<OffsetDateTime>,
    /// Yaratilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Sotiladigan buyumlar.
pub struct SellableRepo<'a> {
    conn: &'a Connection,
}

impl<'a> SellableRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi buyum.
    pub fn insert(&self, row: &SellableRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO sellable_items (id, household_id, name, estimate_minor, currency, note, sold_at, created_at, \
             updated_at, deleted_at, version, origin_device_id) VALUES (?1, ?2, ?3, ?4, ?5, ?6, NULL, ?7, ?7, NULL, 1, ?8)",
            params![
                row.id,
                row.household_id,
                row.name,
                row.estimate.minor(),
                row.estimate.currency().iso_code(),
                row.note,
                format_ts(row.created_at)?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Sotildi deb belgilaydi.
    pub fn mark_sold(&self, id: &str, now: OffsetDateTime) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE sellable_items SET sold_at = ?2, updated_at = ?2, version = version + 1 \
             WHERE id = ?1 AND deleted_at IS NULL AND sold_at IS NULL",
            params![id, format_ts(now)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Mantiqiy o'chirish.
    pub fn delete(&self, id: &str, now: OffsetDateTime) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE sellable_items SET deleted_at = ?2, updated_at = ?2, version = version + 1 \
             WHERE id = ?1 AND deleted_at IS NULL",
            params![id, format_ts(now)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Xonadon buyumlari (sotilmaganlar avval).
    pub fn list(&self, household_id: &str) -> Result<Vec<SellableRow>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, name, estimate_minor, currency, note, sold_at, created_at, origin_device_id \
             FROM sellable_items WHERE household_id = ?1 AND deleted_at IS NULL \
             ORDER BY sold_at IS NOT NULL, created_at, id",
        )?;
        let rows = statement.query_map([household_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, i64>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, Option<String>>(5)?,
                row.get::<_, Option<String>>(6)?,
                row.get::<_, String>(7)?,
                row.get::<_, String>(8)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (id, household_id, name, minor, currency, note, sold_at, created_at, origin) = row?;
            out.push(SellableRow {
                id,
                household_id,
                name,
                estimate: money_of(minor, &currency)?,
                note,
                sold_at: sold_at.as_deref().map(crate::repo::parse_ts).transpose()?,
                created_at: crate::repo::parse_ts(&created_at)?,
                origin_device_id: origin,
            });
        }
        Ok(out)
    }
}
