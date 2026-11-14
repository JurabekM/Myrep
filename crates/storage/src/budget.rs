//! D7 repo'lari: obunalar, konvertlar, «Qutqarilgan pul» yozuvlari va xonadon sozlamalari (sxema v6).
//!
//! Sanalar `YYYY-MM-DD`, vaqtlar RFC 3339 UTC, pul — minor birlikda. Mantiqiy o'chirish `deleted_at` orqali.

use domain::rescue::{RescueKind, SavingsRescue};
use domain::{Envelope, Subscription, VaultEntry};
use money::{Currency, Money};
use rusqlite::{Connection, OptionalExtension, Row, params};
use time::Date;

use crate::StorageError;
use crate::finance::{RawMeta, VaultRepo, format_date, parse_date};
use crate::repo::{format_ts, parse_ts};

fn money_of(minor: i64, currency: &str) -> Result<Money, StorageError> {
    let currency = Currency::from_iso(currency)
        .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?;
    Ok(Money::new(minor, currency))
}

fn optional_date(text: Option<String>) -> Result<Option<Date>, StorageError> {
    text.as_deref().map(parse_date).transpose()
}

/// Obunalar.
pub struct SubscriptionRepo<'a> {
    conn: &'a Connection,
}

impl<'a> SubscriptionRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi obuna qo'shadi.
    pub fn insert(&self, sub: &Subscription) -> Result<(), StorageError> {
        let meta = &sub.meta;
        self.conn.execute(
            "INSERT INTO subscriptions (id, household_id, name, monthly_minor, yearly_minor, currency, last_used_on, cancelled_on, \
             created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
            params![
                sub.id,
                sub.household_id,
                sub.name,
                sub.monthly.minor(),
                sub.yearly.map(|y| y.minor()),
                sub.monthly.currency().iso_code(),
                sub.last_used_on.map(format_date).transpose()?,
                sub.cancelled_on.map(format_date).transpose()?,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Obuna holatini (ishlatilgan sana, bekor qilish) yangilaydi.
    pub fn update(&self, sub: &Subscription) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE subscriptions SET last_used_on = ?2, cancelled_on = ?3, updated_at = ?4, version = ?5 WHERE id = ?1 AND deleted_at IS NULL",
            params![
                sub.id,
                sub.last_used_on.map(format_date).transpose()?,
                sub.cancelled_on.map(format_date).transpose()?,
                format_ts(sub.meta.updated_at)?,
                sub.meta.version,
            ],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Bitta obuna.
    pub fn find(&self, id: &str) -> Result<Option<Subscription>, StorageError> {
        let raw = self
            .conn
            .query_row(
                "SELECT id, household_id, name, monthly_minor, yearly_minor, currency, last_used_on, cancelled_on, \
                 created_at, updated_at, deleted_at, version, origin_device_id \
                 FROM subscriptions WHERE id = ?1 AND deleted_at IS NULL",
                [id],
                read_subscription_row,
            )
            .optional()?;
        raw.map(RawSubscription::into_subscription).transpose()
    }

    /// Xonadonning obunalari (bekor qilinganlari ham — tarix uchun), yaratilish tartibida.
    pub fn list(&self, household_id: &str) -> Result<Vec<Subscription>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, name, monthly_minor, yearly_minor, currency, last_used_on, cancelled_on, \
             created_at, updated_at, deleted_at, version, origin_device_id \
             FROM subscriptions WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([household_id], read_subscription_row)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?.into_subscription()?);
        }
        Ok(out)
    }
}

struct RawSubscription {
    id: String,
    household_id: String,
    name: String,
    monthly_minor: i64,
    yearly_minor: Option<i64>,
    currency: String,
    last_used_on: Option<String>,
    cancelled_on: Option<String>,
    meta: RawMeta,
}

fn read_subscription_row(row: &Row<'_>) -> rusqlite::Result<RawSubscription> {
    Ok(RawSubscription {
        id: row.get(0)?,
        household_id: row.get(1)?,
        name: row.get(2)?,
        monthly_minor: row.get(3)?,
        yearly_minor: row.get(4)?,
        currency: row.get(5)?,
        last_used_on: row.get(6)?,
        cancelled_on: row.get(7)?,
        meta: RawMeta::read(row, 8)?,
    })
}

impl RawSubscription {
    fn into_subscription(self) -> Result<Subscription, StorageError> {
        Ok(Subscription {
            id: self.id,
            household_id: self.household_id,
            name: self.name,
            monthly: money_of(self.monthly_minor, &self.currency)?,
            yearly: self
                .yearly_minor
                .map(|minor| money_of(minor, &self.currency))
                .transpose()?,
            last_used_on: optional_date(self.last_used_on)?,
            cancelled_on: optional_date(self.cancelled_on)?,
            meta: self.meta.into_meta()?,
        })
    }
}

/// Konvertlar.
pub struct EnvelopeRepo<'a> {
    conn: &'a Connection,
}

impl<'a> EnvelopeRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi konvert qo'shadi.
    pub fn insert(&self, envelope: &Envelope) -> Result<(), StorageError> {
        let meta = &envelope.meta;
        self.conn.execute(
            "INSERT INTO envelopes (id, household_id, name, weekly_limit_minor, currency, category_id, created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                envelope.id,
                envelope.household_id,
                envelope.name,
                envelope.weekly_limit.minor(),
                envelope.weekly_limit.currency().iso_code(),
                envelope.category_id,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Bitta konvert.
    pub fn find(&self, id: &str) -> Result<Option<Envelope>, StorageError> {
        let raw = self
            .conn
            .query_row(
                "SELECT id, household_id, name, weekly_limit_minor, currency, category_id, created_at, updated_at, deleted_at, version, origin_device_id \
                 FROM envelopes WHERE id = ?1 AND deleted_at IS NULL",
                [id],
                read_envelope_row,
            )
            .optional()?;
        raw.map(RawEnvelope::into_envelope).transpose()
    }

    /// Xonadonning faol konvertlari.
    pub fn list(&self, household_id: &str) -> Result<Vec<Envelope>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, name, weekly_limit_minor, currency, category_id, created_at, updated_at, deleted_at, version, origin_device_id \
             FROM envelopes WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([household_id], read_envelope_row)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?.into_envelope()?);
        }
        Ok(out)
    }
}

struct RawEnvelope {
    id: String,
    household_id: String,
    name: String,
    weekly_limit_minor: i64,
    currency: String,
    category_id: Option<String>,
    meta: RawMeta,
}

fn read_envelope_row(row: &Row<'_>) -> rusqlite::Result<RawEnvelope> {
    Ok(RawEnvelope {
        id: row.get(0)?,
        household_id: row.get(1)?,
        name: row.get(2)?,
        weekly_limit_minor: row.get(3)?,
        currency: row.get(4)?,
        category_id: row.get(5)?,
        meta: RawMeta::read(row, 6)?,
    })
}

impl RawEnvelope {
    fn into_envelope(self) -> Result<Envelope, StorageError> {
        Ok(Envelope {
            id: self.id,
            household_id: self.household_id,
            name: self.name,
            weekly_limit: money_of(self.weekly_limit_minor, &self.currency)?,
            category_id: self.category_id,
            meta: self.meta.into_meta()?,
        })
    }
}

/// «Qutqarilgan pul» yozuvlari va xonadon sozlamalari.
pub struct RescueRepo<'a> {
    conn: &'a Connection,
}

impl<'a> RescueRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi yozuv qo'shadi (o'zgartirilmaydi).
    pub fn insert(&self, rescue: &SavingsRescue) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO savings_rescues (id, household_id, kind, amount_minor, currency, occurred_on, source_id, created_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
            params![
                rescue.id,
                rescue.household_id,
                rescue.kind.code(),
                rescue.amount.minor(),
                rescue.amount.currency().iso_code(),
                format_date(rescue.occurred_on)?,
                rescue.source_id,
                format_ts(rescue.meta.created_at)?,
                rescue.meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Xonadonning barcha yozuvlari (sana bo'yicha). Hisob-kitob uchun ishlatiladi.
    pub fn list(&self, household_id: &str) -> Result<Vec<SavingsRescue>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, kind, amount_minor, currency, occurred_on, source_id, created_at, origin_device_id \
             FROM savings_rescues WHERE household_id = ?1 ORDER BY occurred_on, id",
        )?;
        let rows = statement.query_map([household_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, i64>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, String>(5)?,
                row.get::<_, Option<String>>(6)?,
                row.get::<_, String>(7)?,
                row.get::<_, String>(8)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (id, household_id, kind, minor, currency, occurred, source, created, origin) = row?;
            let kind = RescueKind::from_code(&kind)
                .ok_or_else(|| StorageError::InvalidData("qutqarish turi".to_owned()))?;
            let rescue = SavingsRescue::create(
                &id,
                &household_id,
                kind,
                money_of(minor, &currency)?,
                parse_date(&occurred)?,
                parse_ts(&created)?,
                &origin,
            )
            .map_err(|_| StorageError::InvalidData("qutqarish yozuvi".to_owned()))?
            .with_source(source);
            out.push(rescue);
        }
        Ok(out)
    }

    /// Xonadon sozlamasi (kalit bo'yicha). Yo'q bo'lsa — `None`.
    pub fn setting(&self, household_id: &str, key: &str) -> Result<Option<String>, StorageError> {
        Ok(self
            .conn
            .query_row(
                "SELECT value FROM household_settings WHERE household_id = ?1 AND key = ?2",
                params![household_id, key],
                |row| row.get(0),
            )
            .optional()?)
    }

    /// Xonadon sozlamasini yozadi (mavjud bo'lsa almashtiradi).
    pub fn set_setting(
        &self,
        household_id: &str,
        key: &str,
        value: &str,
    ) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO household_settings (household_id, key, value) VALUES (?1, ?2, ?3) \
             ON CONFLICT (household_id, key) DO UPDATE SET value = excluded.value",
            params![household_id, key, value],
        )?;
        Ok(())
    }
}

/// «Qutqarilgan pul»ni «Kelajagim»ga o'tkazadi: qutqarish yozuvi va kirim bitta tranzaksiyada yoziladi.
pub fn transfer_to_vault(
    conn: &Connection,
    rescue: &SavingsRescue,
    asset_id: &str,
    entry: &VaultEntry,
) -> Result<(), StorageError> {
    let tx = conn.unchecked_transaction()?;
    RescueRepo::new(&tx).insert(rescue)?;
    VaultRepo::new(&tx).insert_entry(asset_id, &rescue.household_id, entry)?;
    tx.commit()?;
    Ok(())
}
