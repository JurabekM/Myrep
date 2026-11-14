//! D8 repo: «Narx daftari» yozuvlari (sxema v9).

use domain::inflation::PriceItem;
use money::{Currency, Money};
use rusqlite::{Connection, OptionalExtension, Row, params};

use crate::StorageError;
use crate::finance::RawMeta;
use crate::repo::format_ts;

fn money_of(minor: i64, currency: &str) -> Result<Money, StorageError> {
    let currency = Currency::from_iso(currency)
        .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?;
    Ok(Money::new(minor, currency))
}

/// Narx yozuvlari.
pub struct PriceRepo<'a> {
    conn: &'a Connection,
}

impl<'a> PriceRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi yozuv.
    pub fn insert(&self, item: &PriceItem) -> Result<(), StorageError> {
        let meta = &item.meta;
        self.conn.execute(
            "INSERT INTO price_items (id, household_id, name, base_minor, current_minor, currency, weight_bp, \
             created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
            params![
                item.id,
                item.household_id,
                item.name,
                item.base_price.minor(),
                item.current_price.minor(),
                item.base_price.currency().iso_code(),
                item.weight_bp,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Joriy narxni yangilaydi (versiya bilan).
    pub fn update_current(&self, item: &PriceItem) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE price_items SET current_minor = ?2, updated_at = ?3, version = ?4 WHERE id = ?1 AND deleted_at IS NULL",
            params![
                item.id,
                item.current_price.minor(),
                format_ts(item.meta.updated_at)?,
                item.meta.version,
            ],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Mantiqiy o'chirish.
    pub fn delete(&self, id: &str, deleted_at: time::OffsetDateTime) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE price_items SET deleted_at = ?2 WHERE id = ?1 AND deleted_at IS NULL",
            params![id, format_ts(deleted_at)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Bitta yozuv.
    pub fn find(&self, id: &str) -> Result<Option<PriceItem>, StorageError> {
        self.conn
            .query_row(
                "SELECT id, household_id, name, base_minor, current_minor, currency, weight_bp, \
                 created_at, updated_at, deleted_at, version, origin_device_id \
                 FROM price_items WHERE id = ?1 AND deleted_at IS NULL",
                [id],
                read_row,
            )
            .optional()?
            .map(Raw::into_item)
            .transpose()
    }

    /// Xonadonning faol yozuvlari, yaratilish tartibida.
    pub fn list(&self, household_id: &str) -> Result<Vec<PriceItem>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, name, base_minor, current_minor, currency, weight_bp, \
             created_at, updated_at, deleted_at, version, origin_device_id \
             FROM price_items WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([household_id], read_row)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?.into_item()?);
        }
        Ok(out)
    }
}

struct Raw {
    id: String,
    household_id: String,
    name: String,
    base_minor: i64,
    current_minor: i64,
    currency: String,
    weight_bp: i64,
    meta: RawMeta,
}

fn read_row(row: &Row<'_>) -> rusqlite::Result<Raw> {
    Ok(Raw {
        id: row.get(0)?,
        household_id: row.get(1)?,
        name: row.get(2)?,
        base_minor: row.get(3)?,
        current_minor: row.get(4)?,
        currency: row.get(5)?,
        weight_bp: row.get(6)?,
        meta: RawMeta::read(row, 7)?,
    })
}

impl Raw {
    fn into_item(self) -> Result<PriceItem, StorageError> {
        Ok(PriceItem {
            id: self.id,
            household_id: self.household_id,
            name: self.name,
            base_price: money_of(self.base_minor, &self.currency)?,
            current_price: money_of(self.current_minor, &self.currency)?,
            weight_bp: self.weight_bp,
            meta: self.meta.into_meta()?,
        })
    }
}
