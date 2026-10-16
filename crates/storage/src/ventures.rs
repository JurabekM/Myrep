//! D13 repo: sheriklik davrlari (sxema v14). Yopilgan davr o'zgarmaydi (DB triggerlari); davr yozuvlari
//! kelishuv jurnalida (D8A), bu yerda — davr yakuni, zanjir boshi va taqsimot (JSON).

use money::{Currency, Money};
use rusqlite::{Connection, OptionalExtension, Row, params};
use time::{Date, OffsetDateTime};

use crate::StorageError;
use crate::finance::{format_date, parse_date};
use crate::repo::{format_ts, parse_ts};

fn money_of(minor: i64, currency: &str) -> Result<Money, StorageError> {
    let currency = Currency::from_iso(currency)
        .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?;
    Ok(Money::new(minor, currency))
}

/// Yopilgan davr.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VenturePeriodRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Sheriklik.
    pub partnership_id: String,
    /// Davr boshi.
    pub start_on: Date,
    /// Davr oxiri (shu kun kiradi).
    pub end_on: Date,
    /// Kirim.
    pub income: Money,
    /// Xarajat (fors-major bilan).
    pub expense: Money,
    /// Sof natija (manfiy bo'lishi mumkin).
    pub net: Money,
    /// Yopilish paytidagi zanjir boshi.
    pub chain_head: String,
    /// Fors-major izohi.
    pub force_majeure_note: Option<String>,
    /// Taqsimot (JSON).
    pub distribution_json: String,
    /// Yopilgan vaqt.
    pub closed_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Davrlar.
pub struct VentureRepo<'a> {
    conn: &'a Connection,
}

impl<'a> VentureRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Davrni yozadi (faqat qo'shiladi).
    pub fn insert(&self, row: &VenturePeriodRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO venture_periods (id, household_id, partnership_id, start_on, end_on, income_minor, expense_minor, \
             net_minor, currency, chain_head, force_majeure_note, distribution_json, closed_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
            params![
                row.id,
                row.household_id,
                row.partnership_id,
                format_date(row.start_on)?,
                format_date(row.end_on)?,
                row.income.minor(),
                row.expense.minor(),
                row.net.minor(),
                row.net.currency().iso_code(),
                row.chain_head,
                row.force_majeure_note,
                row.distribution_json,
                format_ts(row.closed_at)?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Bitta davr.
    pub fn find(&self, id: &str) -> Result<Option<VenturePeriodRow>, StorageError> {
        self.conn
            .query_row(&format!("{SELECT} WHERE id = ?1"), [id], read_row)
            .optional()?
            .map(Raw::into_row)
            .transpose()
    }

    /// Sheriklik davrlari, oxiri bo'yicha.
    pub fn list(&self, partnership_id: &str) -> Result<Vec<VenturePeriodRow>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{SELECT} WHERE partnership_id = ?1 ORDER BY end_on, closed_at"
        ))?;
        let rows = statement.query_map([partnership_id], read_row)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?.into_row()?);
        }
        Ok(out)
    }

    /// Oxirgi yopilgan davr oxiri.
    pub fn last_end(&self, partnership_id: &str) -> Result<Option<Date>, StorageError> {
        let text: Option<String> = self.conn.query_row(
            "SELECT MAX(end_on) FROM venture_periods WHERE partnership_id = ?1",
            [partnership_id],
            |row| row.get(0),
        )?;
        text.as_deref().map(parse_date).transpose()
    }
}

const SELECT: &str = "SELECT id, household_id, partnership_id, start_on, end_on, income_minor, expense_minor, net_minor, \
    currency, chain_head, force_majeure_note, distribution_json, closed_at, origin_device_id FROM venture_periods";

struct Raw {
    id: String,
    household_id: String,
    partnership_id: String,
    start_on: String,
    end_on: String,
    income_minor: i64,
    expense_minor: i64,
    net_minor: i64,
    currency: String,
    chain_head: String,
    force_majeure_note: Option<String>,
    distribution_json: String,
    closed_at: String,
    origin_device_id: String,
}

fn read_row(row: &Row<'_>) -> rusqlite::Result<Raw> {
    Ok(Raw {
        id: row.get(0)?,
        household_id: row.get(1)?,
        partnership_id: row.get(2)?,
        start_on: row.get(3)?,
        end_on: row.get(4)?,
        income_minor: row.get(5)?,
        expense_minor: row.get(6)?,
        net_minor: row.get(7)?,
        currency: row.get(8)?,
        chain_head: row.get(9)?,
        force_majeure_note: row.get(10)?,
        distribution_json: row.get(11)?,
        closed_at: row.get(12)?,
        origin_device_id: row.get(13)?,
    })
}

impl Raw {
    fn into_row(self) -> Result<VenturePeriodRow, StorageError> {
        Ok(VenturePeriodRow {
            id: self.id,
            household_id: self.household_id,
            partnership_id: self.partnership_id,
            start_on: parse_date(&self.start_on)?,
            end_on: parse_date(&self.end_on)?,
            income: money_of(self.income_minor, &self.currency)?,
            expense: money_of(self.expense_minor, &self.currency)?,
            net: money_of(self.net_minor, &self.currency)?,
            chain_head: self.chain_head,
            force_majeure_note: self.force_majeure_note,
            distribution_json: self.distribution_json,
            closed_at: parse_ts(&self.closed_at)?,
            origin_device_id: self.origin_device_id,
        })
    }
}

/// Ledger yozuviga biriktirilgan chek rasmi (data URL matni; baza SQLCipher bilan shifrlangan).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AttachmentRow {
    /// UUIDv7.
    pub id: String,
    /// Jurnal yozuvi tartib raqami.
    pub seq: i64,
    /// Rasm (data URL).
    pub image: String,
}

/// Biriktirmalar.
pub struct AttachmentRepo<'a> {
    conn: &'a Connection,
}

impl<'a> AttachmentRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Biriktirma qo'shadi.
    #[allow(clippy::too_many_arguments)]
    pub fn insert(
        &self,
        id: &str,
        household_id: &str,
        agreement_id: &str,
        seq: i64,
        image: &str,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO venture_attachments (id, household_id, agreement_id, seq, image, created_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![id, household_id, agreement_id, seq, image, format_ts(now)?, origin_device_id],
        )?;
        Ok(())
    }

    /// Kelishuv biriktirmalari (seq bo'yicha).
    pub fn list(&self, agreement_id: &str) -> Result<Vec<AttachmentRow>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, seq, image FROM venture_attachments WHERE agreement_id = ?1 ORDER BY seq, created_at",
        )?;
        let rows = statement.query_map([agreement_id], |row| {
            Ok(AttachmentRow {
                id: row.get(0)?,
                seq: row.get(1)?,
                image: row.get(2)?,
            })
        })?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        Ok(out)
    }
}
