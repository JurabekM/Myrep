//! 7-qonun repo: taklif tekshiruvlari (`offer_checks`, sxema v18) — javoblar, natija, summa, va'da, maslahatchi va
//! qaror (`DECLINED | POSTPONED | ACCEPTED`). Tekshiruv yozuvi o'zgarmaydi; faqat qaror bir marta yoziladi.

use money::{Currency, Money};
use rusqlite::{Connection, OptionalExtension, Row, params};
use time::OffsetDateTime;

use crate::StorageError;
use crate::repo::{format_ts, parse_ts};

/// Taklif tekshiruvi yozuvi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OfferCheckRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Taklif nomi (kim, nima), ixtiyoriy.
    pub title: Option<String>,
    /// Javoblar JSON (`{"guaranteed":"YES",...}`) — xizmat tahlil qiladi.
    pub answers_json: String,
    /// Baho: `GREEN | YELLOW | RED`.
    pub verdict: String,
    /// Daraja: `NONE | CAUTION | FLEE`.
    pub level: String,
    /// Belgilar JSON massivi (`["URGENCY", ...]`).
    pub signs_json: String,
    /// Toifalar JSON massivi (`["RIBO", ...]`).
    pub categories_json: String,
    /// Taxminiy summa (bo'lmasligi mumkin).
    pub amount: Option<Money>,
    /// Va'da qilingan oylik foyda, bp.
    pub promised_monthly_bp: Option<u32>,
    /// Maslahatlashilgan odam.
    pub advisor: Option<String>,
    /// Qaror: `DECLINED | POSTPONED | ACCEPTED` yoki hali yo'q.
    pub decision: Option<String>,
    /// Tekshirilgan vaqt.
    pub checked_at: OffsetDateTime,
    /// Qaror vaqti.
    pub decided_at: Option<OffsetDateTime>,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Taklif tekshiruvlari.
pub struct OfferCheckRepo<'a> {
    conn: &'a Connection,
}

const SELECT: &str = "SELECT id, household_id, title, answers, verdict, level, signs, categories, amount_minor, currency, \
    promised_monthly_bp, advisor, decision, checked_at, decided_at, origin_device_id FROM offer_checks";

impl<'a> OfferCheckRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi tekshiruv.
    pub fn insert(&self, row: &OfferCheckRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO offer_checks (id, household_id, title, answers, verdict, level, signs, categories, amount_minor, \
             currency, promised_monthly_bp, advisor, decision, checked_at, decided_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16)",
            params![
                row.id,
                row.household_id,
                row.title,
                row.answers_json,
                row.verdict,
                row.level,
                row.signs_json,
                row.categories_json,
                row.amount.map(|m| m.minor()),
                row.amount.map(|m| m.currency().iso_code().to_owned()),
                row.promised_monthly_bp,
                row.advisor,
                row.decision,
                format_ts(row.checked_at)?,
                row.decided_at.map(format_ts).transpose()?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Qaror va maslahatchi (bir marta; qaror bor yozuv o'zgarmaydi).
    pub fn set_decision(
        &self,
        id: &str,
        decision: &str,
        advisor: Option<&str>,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE offer_checks SET decision = ?2, advisor = COALESCE(?3, advisor), decided_at = ?4 \
             WHERE id = ?1 AND decision IS NULL",
            params![id, decision, advisor, format_ts(now)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Maslahatchini yozadi (qaror oldidan ham).
    pub fn set_advisor(&self, id: &str, advisor: &str) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE offer_checks SET advisor = ?2 WHERE id = ?1",
            params![id, advisor],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Bitta tekshiruv.
    pub fn find(&self, id: &str) -> Result<Option<OfferCheckRow>, StorageError> {
        self.conn
            .query_row(&format!("{SELECT} WHERE id = ?1"), [id], read_row)
            .optional()?
            .map(Raw::into_row)
            .transpose()
    }

    /// Xonadon tekshiruvlari, eng yangisi avval.
    pub fn list(&self, household_id: &str) -> Result<Vec<OfferCheckRow>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{SELECT} WHERE household_id = ?1 ORDER BY checked_at DESC, id DESC"
        ))?;
        let rows = statement.query_map([household_id], read_row)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?.into_row()?);
        }
        Ok(out)
    }
}

struct Raw {
    id: String,
    household_id: String,
    title: Option<String>,
    answers_json: String,
    verdict: String,
    level: String,
    signs_json: String,
    categories_json: String,
    amount_minor: Option<i64>,
    currency: Option<String>,
    promised_monthly_bp: Option<i64>,
    advisor: Option<String>,
    decision: Option<String>,
    checked_at: String,
    decided_at: Option<String>,
    origin_device_id: String,
}

fn read_row(row: &Row<'_>) -> rusqlite::Result<Raw> {
    Ok(Raw {
        id: row.get(0)?,
        household_id: row.get(1)?,
        title: row.get(2)?,
        answers_json: row.get(3)?,
        verdict: row.get(4)?,
        level: row.get(5)?,
        signs_json: row.get(6)?,
        categories_json: row.get(7)?,
        amount_minor: row.get(8)?,
        currency: row.get(9)?,
        promised_monthly_bp: row.get(10)?,
        advisor: row.get(11)?,
        decision: row.get(12)?,
        checked_at: row.get(13)?,
        decided_at: row.get(14)?,
        origin_device_id: row.get(15)?,
    })
}

impl Raw {
    fn into_row(self) -> Result<OfferCheckRow, StorageError> {
        let amount = match (self.amount_minor, self.currency.as_deref()) {
            (Some(minor), Some(iso)) => Some(Money::new(
                minor,
                Currency::from_iso(iso)
                    .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?,
            )),
            _ => None,
        };
        Ok(OfferCheckRow {
            id: self.id,
            household_id: self.household_id,
            title: self.title,
            answers_json: self.answers_json,
            verdict: self.verdict,
            level: self.level,
            signs_json: self.signs_json,
            categories_json: self.categories_json,
            amount,
            promised_monthly_bp: self
                .promised_monthly_bp
                .map(|bp| u32::try_from(bp).map_err(|_| StorageError::InvalidData("bp".to_owned())))
                .transpose()?,
            advisor: self.advisor,
            decision: self.decision,
            checked_at: parse_ts(&self.checked_at)?,
            decided_at: self.decided_at.as_deref().map(parse_ts).transpose()?,
            origin_device_id: self.origin_device_id,
        })
    }
}
