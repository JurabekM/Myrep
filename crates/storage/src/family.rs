//! D6 repo'lari: a'zo PIN'i (urinishlar hisobi bilan), havas chegarasi va rozilik, «Juma shirinligi».
//!
//! Sanalar — `YYYY-MM-DD`, vaqtlar RFC 3339 UTC, pul — minor birlikda. PIN verifier bazada `members`
//! jadvalida turadi; PIN o'zi hech qachon saqlanmaydi.

use domain::treat::{weekday_from_index, weekday_index};
use domain::{HavasLimit, LimitConsent, ScheduledTreat};
use money::{Currency, Money};
use rusqlite::{Connection, OptionalExtension, Row, params};
use time::OffsetDateTime;

use crate::StorageError;
use crate::finance::RawMeta;
use crate::repo::{format_ts, parse_ts};

/// A'zoning PIN holati: verifier (bo'lsa), noto'g'ri urinishlar soni va oxirgi noto'g'ri urinish vaqti.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PinState {
    /// Verifier (`create_member_verifier` natijasi); PIN o'rnatilmagan bo'lsa — `None`.
    pub verifier: Option<Vec<u8>>,
    /// Ketma-ket noto'g'ri urinishlar.
    pub failed_attempts: u32,
    /// Oxirgi noto'g'ri urinish vaqti (UTC).
    pub failed_at: Option<OffsetDateTime>,
}

/// A'zo PIN'i: o'rnatish va urinishlar hisobi.
pub struct PinRepo<'a> {
    conn: &'a Connection,
}

impl<'a> PinRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// A'zoning PIN holati. A'zo yo'q bo'lsa — `None`.
    pub fn find(&self, member_id: &str) -> Result<Option<PinState>, StorageError> {
        let raw = self
            .conn
            .query_row(
                "SELECT pin_verifier, pin_failed_attempts, pin_failed_at FROM members \
                 WHERE id = ?1 AND deleted_at IS NULL",
                [member_id],
                |row| {
                    Ok((
                        row.get::<_, Option<Vec<u8>>>(0)?,
                        row.get::<_, i64>(1)?,
                        row.get::<_, Option<String>>(2)?,
                    ))
                },
            )
            .optional()?;
        let Some((verifier, attempts, failed_at)) = raw else {
            return Ok(None);
        };
        Ok(Some(PinState {
            verifier,
            failed_attempts: u32::try_from(attempts)
                .map_err(|_| StorageError::InvalidData("urinishlar".to_owned()))?,
            failed_at: failed_at.as_deref().map(parse_ts).transpose()?,
        }))
    }

    /// Verifier'ni o'rnatadi (yoki almashtiradi) va urinishlar hisobini nolga tushiradi.
    pub fn set_verifier(&self, member_id: &str, verifier: &[u8]) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE members SET pin_verifier = ?2, pin_failed_attempts = 0, pin_failed_at = NULL \
             WHERE id = ?1 AND deleted_at IS NULL",
            params![member_id, verifier],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Noto'g'ri urinishni qayd etadi; yangi hisobni qaytaradi.
    pub fn record_failure(
        &self,
        member_id: &str,
        now: OffsetDateTime,
    ) -> Result<u32, StorageError> {
        let changed = self.conn.execute(
            "UPDATE members SET pin_failed_attempts = pin_failed_attempts + 1, pin_failed_at = ?2 \
             WHERE id = ?1 AND deleted_at IS NULL",
            params![member_id, format_ts(now)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        let attempts: i64 = self.conn.query_row(
            "SELECT pin_failed_attempts FROM members WHERE id = ?1",
            [member_id],
            |row| row.get(0),
        )?;
        u32::try_from(attempts).map_err(|_| StorageError::InvalidData("urinishlar".to_owned()))
    }

    /// To'g'ri PIN kiritilgach urinishlar hisobini nolga tushiradi.
    pub fn reset_failures(&self, member_id: &str) -> Result<(), StorageError> {
        self.conn.execute(
            "UPDATE members SET pin_failed_attempts = 0, pin_failed_at = NULL WHERE id = ?1",
            [member_id],
        )?;
        Ok(())
    }
}

fn money_of(minor: i64, currency: &str) -> Result<Money, StorageError> {
    let currency = Currency::from_iso(currency)
        .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?;
    Ok(Money::new(minor, currency))
}

/// Havas chegaralari va rozilik yozuvlari.
pub struct LimitRepo<'a> {
    conn: &'a Connection,
}

impl<'a> LimitRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi chegara qo'shadi.
    pub fn insert_limit(&self, limit: &HavasLimit) -> Result<(), StorageError> {
        let meta = &limit.meta;
        self.conn.execute(
            "INSERT INTO havas_limits (id, household_id, monthly_minor, currency, created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
            params![
                limit.id,
                limit.household_id,
                limit.monthly.minor(),
                limit.monthly.currency().iso_code(),
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Xonadonning eng so'nggi faol chegarasi.
    pub fn latest(&self, household_id: &str) -> Result<Option<HavasLimit>, StorageError> {
        let raw = self
            .conn
            .query_row(
                "SELECT id, household_id, monthly_minor, currency, created_at, updated_at, deleted_at, version, origin_device_id \
                 FROM havas_limits WHERE household_id = ?1 AND deleted_at IS NULL \
                 ORDER BY created_at DESC, id DESC LIMIT 1",
                [household_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, i64>(2)?,
                        row.get::<_, String>(3)?,
                        RawMeta::read(row, 4)?,
                    ))
                },
            )
            .optional()?;
        let Some((id, household_id, minor, currency, meta)) = raw else {
            return Ok(None);
        };
        Ok(Some(HavasLimit {
            id,
            household_id,
            monthly: money_of(minor, &currency)?,
            meta: meta.into_meta()?,
        }))
    }

    /// Rozilik yozuvini qo'shadi. Bir kattaning bir chegaraga ikki marta roziligi `UNIQUE` bilan rad etiladi.
    pub fn insert_consent(&self, consent: &LimitConsent) -> Result<(), StorageError> {
        let meta = &consent.meta;
        self.conn.execute(
            "INSERT INTO limit_consents (id, household_id, limit_id, member_id, created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
            params![
                consent.id,
                consent.household_id,
                consent.limit_id,
                consent.member_id,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Chegaraga rozilik bergan a'zolar identifikatorlari.
    pub fn consented_members(&self, limit_id: &str) -> Result<Vec<String>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT member_id FROM limit_consents WHERE limit_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([limit_id], |row| row.get::<_, String>(0))?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        Ok(out)
    }
}

/// «Juma shirinligi» ritualari.
pub struct TreatRepo<'a> {
    conn: &'a Connection,
}

impl<'a> TreatRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi ritual qo'shadi.
    pub fn insert_treat(&self, treat: &ScheduledTreat) -> Result<(), StorageError> {
        let meta = &treat.meta;
        self.conn.execute(
            "INSERT INTO scheduled_treats (id, household_id, name, amount_minor, currency, weekday, created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                treat.id,
                treat.household_id,
                treat.name,
                treat.amount.minor(),
                treat.amount.currency().iso_code(),
                i64::from(weekday_index(treat.weekday)),
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Xonadonning faol ritualari, yaratilish tartibida.
    pub fn list_treats(&self, household_id: &str) -> Result<Vec<ScheduledTreat>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, name, amount_minor, currency, weekday, created_at, updated_at, deleted_at, version, origin_device_id \
             FROM scheduled_treats WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([household_id], |row: &Row<'_>| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, i64>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, i64>(5)?,
                RawMeta::read(row, 6)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (id, household_id, name, minor, currency, weekday, meta) = row?;
            let weekday = u8::try_from(weekday)
                .ok()
                .and_then(weekday_from_index)
                .ok_or_else(|| StorageError::InvalidData("hafta kuni".to_owned()))?;
            out.push(ScheduledTreat {
                id,
                household_id,
                name,
                amount: money_of(minor, &currency)?,
                weekday,
                meta: meta.into_meta()?,
            });
        }
        Ok(out)
    }
}
