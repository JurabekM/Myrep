//! D12 repo: sheriklik yozuvlari (sxema v13) — `PARTNERSHIP` kelishuviga bog'langan tur, rol, buyout va
//! oilaviy rozilik. Shartnoma matni (9 savol) kelishuvning o'zida; bu yerda faqat sheriklikka xos maydonlar.

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

/// Sheriklik yozuvi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartnershipRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// `PARTNERSHIP` kelishuvi.
    pub agreement_id: String,
    /// `MUDARABA | MUSHARAKA`.
    pub kind: String,
    /// Mening rolim: `CAPITAL_PROVIDER | WORKER`.
    pub my_role: String,
    /// Buyout: sotib olinadigan ulush qiymati.
    pub buyout_total: Option<Money>,
    /// Buyout oylari.
    pub buyout_months: Option<u32>,
    /// Buyout boshlanish sanasi.
    pub buyout_start: Option<Date>,
    /// Oilaviy rozilik bergan a'zo.
    pub consent_member: Option<String>,
    /// Rozilik vaqti.
    pub consent_at: Option<OffsetDateTime>,
    /// Yaratilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Buyout to'lovi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BuyoutPaymentRow {
    /// UUIDv7.
    pub id: String,
    /// Sheriklik.
    pub partnership_id: String,
    /// Summa.
    pub amount: Money,
    /// Sana.
    pub paid_on: Date,
    /// Yozilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Sherikliklar.
pub struct PartnershipRepo<'a> {
    conn: &'a Connection,
}

impl<'a> PartnershipRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi yozuv.
    pub fn insert(&self, row: &PartnershipRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO partnerships (id, household_id, agreement_id, kind, my_role, buyout_total_minor, buyout_months, \
             buyout_start, currency, consent_member, consent_at, created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, NULL, 1, ?13)",
            params![
                row.id,
                row.household_id,
                row.agreement_id,
                row.kind,
                row.my_role,
                row.buyout_total.map(|m| m.minor()),
                row.buyout_months,
                row.buyout_start.map(format_date).transpose()?,
                row.buyout_total
                    .map_or(Currency::Uzs, |m| m.currency())
                    .iso_code(),
                row.consent_member,
                row.consent_at.map(format_ts).transpose()?,
                format_ts(row.created_at)?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Buyout shartlarini yozadi.
    pub fn set_buyout(
        &self,
        id: &str,
        total: Money,
        months: u32,
        start: Date,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE partnerships SET buyout_total_minor = ?2, buyout_months = ?3, buyout_start = ?4, currency = ?5, \
             updated_at = ?6, version = version + 1 WHERE id = ?1 AND deleted_at IS NULL",
            params![
                id,
                total.minor(),
                months,
                format_date(start)?,
                total.currency().iso_code(),
                format_ts(now)?
            ],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Oilaviy rozilikni yozadi.
    pub fn set_consent(
        &self,
        id: &str,
        member: &str,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE partnerships SET consent_member = ?2, consent_at = ?3, updated_at = ?3, version = version + 1 \
             WHERE id = ?1 AND deleted_at IS NULL",
            params![id, member, format_ts(now)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Buyout to'lovi.
    pub fn insert_payment(&self, payment: &BuyoutPaymentRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO partnership_buyout_payments (id, partnership_id, amount_minor, currency, paid_on, created_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                payment.id,
                payment.partnership_id,
                payment.amount.minor(),
                payment.amount.currency().iso_code(),
                format_date(payment.paid_on)?,
                format_ts(payment.created_at)?,
                payment.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// To'lovlar (sana bo'yicha).
    pub fn payments(&self, partnership_id: &str) -> Result<Vec<(Money, Date)>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT amount_minor, currency, paid_on FROM partnership_buyout_payments \
             WHERE partnership_id = ?1 ORDER BY paid_on, created_at",
        )?;
        let rows = statement.query_map([partnership_id], |row| {
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

    /// Bitta yozuv.
    pub fn find(&self, id: &str) -> Result<Option<PartnershipRow>, StorageError> {
        self.conn
            .query_row(
                &format!("{SELECT} WHERE p.id = ?1 AND p.deleted_at IS NULL"),
                [id],
                read_row,
            )
            .optional()?
            .map(Raw::into_row)
            .transpose()
    }

    /// Kelishuv bo'yicha yozuv.
    pub fn find_by_agreement(
        &self,
        agreement_id: &str,
    ) -> Result<Option<PartnershipRow>, StorageError> {
        self.conn
            .query_row(
                &format!("{SELECT} WHERE p.agreement_id = ?1 AND p.deleted_at IS NULL"),
                [agreement_id],
                read_row,
            )
            .optional()?
            .map(Raw::into_row)
            .transpose()
    }

    /// Xonadon sherikliklari, yaratilish tartibida.
    pub fn list(&self, household_id: &str) -> Result<Vec<PartnershipRow>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{SELECT} WHERE p.household_id = ?1 AND p.deleted_at IS NULL ORDER BY p.created_at, p.id"
        ))?;
        let rows = statement.query_map([household_id], read_row)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?.into_row()?);
        }
        Ok(out)
    }
}

const SELECT: &str = "SELECT p.id, p.household_id, p.agreement_id, p.kind, p.my_role, p.buyout_total_minor, p.buyout_months, \
    p.buyout_start, p.currency, p.consent_member, p.consent_at, p.created_at, p.updated_at, p.deleted_at, p.version, \
    p.origin_device_id FROM partnerships p";

struct Raw {
    id: String,
    household_id: String,
    agreement_id: String,
    kind: String,
    my_role: String,
    buyout_total_minor: Option<i64>,
    buyout_months: Option<i64>,
    buyout_start: Option<String>,
    currency: String,
    consent_member: Option<String>,
    consent_at: Option<String>,
    meta: RawMeta,
}

fn read_row(row: &Row<'_>) -> rusqlite::Result<Raw> {
    Ok(Raw {
        id: row.get(0)?,
        household_id: row.get(1)?,
        agreement_id: row.get(2)?,
        kind: row.get(3)?,
        my_role: row.get(4)?,
        buyout_total_minor: row.get(5)?,
        buyout_months: row.get(6)?,
        buyout_start: row.get(7)?,
        currency: row.get(8)?,
        consent_member: row.get(9)?,
        consent_at: row.get(10)?,
        meta: RawMeta::read(row, 11)?,
    })
}

impl Raw {
    fn into_row(self) -> Result<PartnershipRow, StorageError> {
        let meta = self.meta.into_meta()?;
        Ok(PartnershipRow {
            id: self.id,
            household_id: self.household_id,
            agreement_id: self.agreement_id,
            kind: self.kind,
            my_role: self.my_role,
            buyout_total: self
                .buyout_total_minor
                .map(|minor| money_of(minor, &self.currency))
                .transpose()?,
            buyout_months: self
                .buyout_months
                .map(|m| {
                    u32::try_from(m).map_err(|_| StorageError::InvalidData("oylar".to_owned()))
                })
                .transpose()?,
            buyout_start: self.buyout_start.as_deref().map(parse_date).transpose()?,
            consent_member: self.consent_member,
            consent_at: self
                .consent_at
                .as_deref()
                .map(crate::repo::parse_ts)
                .transpose()?,
            created_at: meta.created_at,
            origin_device_id: meta.origin_device_id,
        })
    }
}

/// Ongli chetlab o'tish yozuvi (darvoza qasddan ochildi): bitta amal, sabab, ADULT a'zo (PIN bilan tasdiqlangan).
pub struct GateOverrideRepo<'a> {
    conn: &'a Connection,
}

impl<'a> GateOverrideRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yozuv qo'shadi.
    #[allow(clippy::too_many_arguments)]
    pub fn insert(
        &self,
        id: &str,
        household_id: &str,
        action: &str,
        target_id: &str,
        reason: &str,
        member_id: &str,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO gate_overrides (id, household_id, action, target_id, reason, member_id, created_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![id, household_id, action, target_id, reason, member_id, format_ts(now)?, origin_device_id],
        )?;
        Ok(())
    }

    /// Nishon uchun sabab (bo'lsa).
    pub fn reason_for(&self, target_id: &str) -> Result<Option<String>, StorageError> {
        Ok(self
            .conn
            .query_row(
                "SELECT reason FROM gate_overrides WHERE target_id = ?1 ORDER BY created_at DESC LIMIT 1",
                [target_id],
                |row| row.get(0),
            )
            .optional()?)
    }
}
