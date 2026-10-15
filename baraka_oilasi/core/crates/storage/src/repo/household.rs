use rusqlite::{params, Connection, OptionalExtension, Transaction};

use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdRow {
    pub id: String,
    pub name: String,
    pub base_currency: String,
    pub locale: String,
    pub tz: String,
    pub month_start_day: u32,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SpaceRow {
    pub id: String,
    pub household_id: String,
    pub kind: String,
    pub name: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MemberRow {
    pub id: String,
    pub household_id: String,
    pub display_name: String,
    pub role: String,
}

pub fn insert_household(
    tx: &Transaction<'_>,
    h: &HouseholdRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO households (id, household_id, name, base_currency, locale, tz, month_start_day,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?1, ?2, ?3, ?4, ?5, ?6, ?7, ?7, ?8, ?8)",
        params![h.id, h.name, h.base_currency, h.locale, h.tz, h.month_start_day, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn get_household(c: &Connection) -> Result<Option<HouseholdRow>, StorageError> {
    Ok(c.query_row(
        "SELECT id, name, base_currency, locale, tz, month_start_day FROM households
         WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1",
        [],
        |r| {
            Ok(HouseholdRow {
                id: r.get(0)?,
                name: r.get(1)?,
                base_currency: r.get(2)?,
                locale: r.get(3)?,
                tz: r.get(4)?,
                month_start_day: r.get(5)?,
            })
        },
    )
    .optional()?)
}

pub fn insert_device(
    tx: &Transaction<'_>,
    household_id: &str,
    name: &str,
    platform: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO devices (id, household_id, name, platform, paired_at, created_at, updated_at,
            origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?5, ?5, ?1, ?1)",
        params![m.device_id, household_id, name, platform, m.now],
    )?;
    Ok(())
}

pub fn insert_space(tx: &Transaction<'_>, s: &SpaceRow, m: &Meta) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO spaces (id, household_id, kind, name, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?5, ?6, ?6)",
        params![s.id, s.household_id, s.kind, s.name, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn list_spaces(c: &Connection, household_id: &str) -> Result<Vec<SpaceRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, household_id, kind, name FROM spaces
         WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
    )?;
    let rows = st.query_map([household_id], |r| {
        Ok(SpaceRow {
            id: r.get(0)?,
            household_id: r.get(1)?,
            kind: r.get(2)?,
            name: r.get(3)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn insert_member(tx: &Transaction<'_>, mem: &MemberRow, m: &Meta) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO members (id, household_id, display_name, role, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?5, ?6, ?6)",
        params![mem.id, mem.household_id, mem.display_name, mem.role, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn list_members(c: &Connection, household_id: &str) -> Result<Vec<MemberRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, household_id, display_name, role FROM members
         WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
    )?;
    let rows = st.query_map([household_id], |r| {
        Ok(MemberRow {
            id: r.get(0)?,
            household_id: r.get(1)?,
            display_name: r.get(2)?,
            role: r.get(3)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn add_member_to_space(
    tx: &Transaction<'_>,
    id: &str,
    household_id: &str,
    space_id: &str,
    member_id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO space_members (id, household_id, space_id, member_id, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?5, ?6, ?6)",
        params![id, household_id, space_id, member_id, m.now, m.device_id],
    )?;
    Ok(())
}
