//! Qatorlarni domain tiplariga o'girish yordamchilari.
use domain::{date_from_str, ts_from_str, Date, Meta, OffsetDateTime};
use money::{Currency, Money};
use rusqlite::{Error, Row};

/// Barcha jadvallarning birinchi 7 ustuni.
pub const META_COLS: &str =
    "id, household_id, created_at, updated_at, deleted_at, version, origin_device_id";

fn conv<E: std::error::Error + Send + Sync + 'static>(idx: usize, e: E) -> Error {
    Error::FromSqlConversionFailure(idx, rusqlite::types::Type::Text, Box::new(e))
}

#[derive(Debug)]
struct Bad(String);
impl std::fmt::Display for Bad {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}
impl std::error::Error for Bad {}

pub fn ts(row: &Row<'_>, idx: usize) -> Result<OffsetDateTime, Error> {
    ts_from_str(&row.get::<_, String>(idx)?).map_err(|e| conv(idx, e))
}

pub fn opt_ts(row: &Row<'_>, idx: usize) -> Result<Option<OffsetDateTime>, Error> {
    row.get::<_, Option<String>>(idx)?
        .map(|s| ts_from_str(&s).map_err(|e| conv(idx, e)))
        .transpose()
}

pub fn date(row: &Row<'_>, idx: usize) -> Result<Date, Error> {
    date_from_str(&row.get::<_, String>(idx)?).map_err(|e| conv(idx, e))
}

pub fn currency(row: &Row<'_>, idx: usize) -> Result<Currency, Error> {
    Currency::from_code(&row.get::<_, String>(idx)?).map_err(|e| conv(idx, e))
}

pub fn opt_currency(row: &Row<'_>, idx: usize) -> Result<Option<Currency>, Error> {
    row.get::<_, Option<String>>(idx)?
        .map(|s| Currency::from_code(&s).map_err(|e| conv(idx, e)))
        .transpose()
}

pub fn money(row: &Row<'_>, minor_idx: usize, currency_idx: usize) -> Result<Money, Error> {
    Ok(Money::new(
        row.get(minor_idx)?,
        currency(row, currency_idx)?,
    ))
}

pub fn parsed<T>(row: &Row<'_>, idx: usize, parse: impl Fn(&str) -> Option<T>) -> Result<T, Error> {
    let s: String = row.get(idx)?;
    parse(&s).ok_or_else(|| conv(idx, Bad(format!("noma'lum qiymat `{s}`"))))
}

pub fn opt_parsed<T>(
    row: &Row<'_>,
    idx: usize,
    parse: impl Fn(&str) -> Option<T>,
) -> Result<Option<T>, Error> {
    row.get::<_, Option<String>>(idx)?
        .map(|s| parse(&s).ok_or_else(|| conv(idx, Bad(format!("noma'lum qiymat `{s}`")))))
        .transpose()
}

pub fn meta(row: &Row<'_>) -> Result<Meta, Error> {
    Ok(Meta {
        id: row.get(0)?,
        household_id: row.get(1)?,
        created_at: ts(row, 2)?,
        updated_at: ts(row, 3)?,
        deleted_at: opt_ts(row, 4)?,
        version: row.get(5)?,
        origin_device_id: row.get(6)?,
    })
}
