use domain::{Household, Member, MemberRole, Meta, validate_name};
use rusqlite::{Connection, OptionalExtension, Row, params};
use time::format_description::well_known::Rfc3339;
use time::{OffsetDateTime, UtcOffset};

use crate::StorageError;

/// Xonadonlar repo'si. Mantiqiy o'chirilgan yozuvlar oddiy o'qishda ko'rinmaydi.
pub struct HouseholdRepo<'a> {
    conn: &'a Connection,
}

impl<'a> HouseholdRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi xonadon qo'shadi.
    pub fn insert(&self, household: &Household) -> Result<(), StorageError> {
        let meta = &household.meta;
        self.conn.execute(
            "INSERT INTO households (id, name, created_at, updated_at, deleted_at, version, origin_device_id, month_start_day) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                household.id,
                household.name,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
                household.month_start_day,
            ],
        )?;
        Ok(())
    }

    /// ID bo'yicha faol xonadon. Yo'q yoki o'chirilgan bo'lsa — `None`.
    pub fn find(&self, id: &str) -> Result<Option<Household>, StorageError> {
        let raw = self
            .conn
            .query_row(
                "SELECT id, name, created_at, updated_at, deleted_at, version, origin_device_id, month_start_day \
                 FROM households WHERE id = ?1 AND deleted_at IS NULL",
                [id],
                RawHousehold::from_row,
            )
            .optional()?;
        raw.map(RawHousehold::into_domain).transpose()
    }

    /// Faol xonadonlar, yaratilish vaqti bo'yicha.
    pub fn list(&self) -> Result<Vec<Household>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, name, created_at, updated_at, deleted_at, version, origin_device_id, month_start_day \
             FROM households WHERE deleted_at IS NULL ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([], RawHousehold::from_row)?;
        rows.map(|row| row?.into_domain()).collect()
    }

    /// Nomini o'zgartiradi. `expected_version` joriy versiyaga teng bo'lishi shart (optimistik nazorat).
    pub fn rename(
        &self,
        id: &str,
        new_name: &str,
        expected_version: i64,
        now: OffsetDateTime,
    ) -> Result<Household, StorageError> {
        let name = validate_name(new_name)?;
        let changed = self.conn.execute(
            "UPDATE households SET name = ?1, updated_at = ?2, version = version + 1 \
             WHERE id = ?3 AND version = ?4 AND deleted_at IS NULL",
            params![name, format_ts(now)?, id, expected_version],
        )?;
        if changed == 0 {
            return Err(self.missing_or_conflict(id)?);
        }
        self.find(id)?.ok_or(StorageError::NotFound)
    }

    /// Mantiqiy o'chiradi (qatorni o'chirmaydi): `deleted_at` o'rnatiladi, versiya oshadi.
    pub fn soft_delete(
        &self,
        id: &str,
        expected_version: i64,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let timestamp = format_ts(now)?;
        let changed = self.conn.execute(
            "UPDATE households SET deleted_at = ?1, updated_at = ?1, version = version + 1 \
             WHERE id = ?2 AND version = ?3 AND deleted_at IS NULL",
            params![timestamp, id, expected_version],
        )?;
        if changed == 0 {
            return Err(self.missing_or_conflict(id)?);
        }
        Ok(())
    }

    /// Yangilash bajarilmagan sababni aniqlaydi: yozuv yo'q bo'lsa `NotFound`, bor bo'lsa `VersionConflict`.
    fn missing_or_conflict(&self, id: &str) -> Result<StorageError, StorageError> {
        let active: Option<bool> = self
            .conn
            .query_row(
                "SELECT deleted_at IS NULL FROM households WHERE id = ?1",
                [id],
                |row| row.get(0),
            )
            .optional()?;
        Ok(match active {
            Some(true) => StorageError::VersionConflict,
            _ => StorageError::NotFound,
        })
    }
}

/// A'zolar repo'si. Xonadon ichida ishlaydi; `household_id` tashqi kalit sifatida tekshiriladi.
pub struct MemberRepo<'a> {
    conn: &'a Connection,
}

impl<'a> MemberRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi a'zo qo'shadi. Xonadon mavjud bo'lishi shart (tashqi kalit).
    pub fn insert(&self, member: &Member) -> Result<(), StorageError> {
        let meta = &member.meta;
        self.conn.execute(
            "INSERT INTO members (id, household_id, name, role, created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
            params![
                member.id,
                member.household_id,
                member.name,
                member.role.code(),
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// ID bo'yicha faol a'zo.
    pub fn find(&self, id: &str) -> Result<Option<Member>, StorageError> {
        let raw = self
            .conn
            .query_row(
                "SELECT id, household_id, name, role, created_at, updated_at, deleted_at, version, origin_device_id \
                 FROM members WHERE id = ?1 AND deleted_at IS NULL",
                [id],
                RawMember::from_row,
            )
            .optional()?;
        raw.map(RawMember::into_domain).transpose()
    }

    /// Xonadonning faol a'zolari, yaratilish vaqti bo'yicha.
    pub fn list_for_household(&self, household_id: &str) -> Result<Vec<Member>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, name, role, created_at, updated_at, deleted_at, version, origin_device_id \
             FROM members WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([household_id], RawMember::from_row)?;
        rows.map(|row| row?.into_domain()).collect()
    }

    /// Mantiqiy o'chiradi. `expected_version` mos kelishi shart.
    pub fn soft_delete(
        &self,
        id: &str,
        expected_version: i64,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let timestamp = format_ts(now)?;
        let changed = self.conn.execute(
            "UPDATE members SET deleted_at = ?1, updated_at = ?1, version = version + 1 \
             WHERE id = ?2 AND version = ?3 AND deleted_at IS NULL",
            params![timestamp, id, expected_version],
        )?;
        if changed == 0 {
            let active: Option<bool> = self
                .conn
                .query_row(
                    "SELECT deleted_at IS NULL FROM members WHERE id = ?1",
                    [id],
                    |row| row.get(0),
                )
                .optional()?;
            return Err(match active {
                Some(true) => StorageError::VersionConflict,
                _ => StorageError::NotFound,
            });
        }
        Ok(())
    }
}

/// Bazadan o'qilgan xom qator; vaqt va rol satr ko'rinishida, keyin domen turiga aylanadi.
struct RawHousehold {
    id: String,
    name: String,
    created_at: String,
    updated_at: String,
    deleted_at: Option<String>,
    version: i64,
    origin_device_id: String,
    month_start_day: u8,
}

impl RawHousehold {
    fn from_row(row: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            id: row.get(0)?,
            name: row.get(1)?,
            created_at: row.get(2)?,
            updated_at: row.get(3)?,
            deleted_at: row.get(4)?,
            version: row.get(5)?,
            origin_device_id: row.get(6)?,
            month_start_day: row.get(7)?,
        })
    }

    fn into_domain(self) -> Result<Household, StorageError> {
        Ok(Household {
            id: self.id,
            name: self.name,
            month_start_day: self.month_start_day,
            meta: Meta {
                created_at: parse_ts(&self.created_at)?,
                updated_at: parse_ts(&self.updated_at)?,
                deleted_at: self.deleted_at.as_deref().map(parse_ts).transpose()?,
                version: self.version,
                origin_device_id: self.origin_device_id,
            },
        })
    }
}

struct RawMember {
    id: String,
    household_id: String,
    name: String,
    role: String,
    created_at: String,
    updated_at: String,
    deleted_at: Option<String>,
    version: i64,
    origin_device_id: String,
}

impl RawMember {
    fn from_row(row: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            id: row.get(0)?,
            household_id: row.get(1)?,
            name: row.get(2)?,
            role: row.get(3)?,
            created_at: row.get(4)?,
            updated_at: row.get(5)?,
            deleted_at: row.get(6)?,
            version: row.get(7)?,
            origin_device_id: row.get(8)?,
        })
    }

    fn into_domain(self) -> Result<Member, StorageError> {
        let role = MemberRole::from_code(&self.role)
            .ok_or_else(|| StorageError::InvalidData("a'zo roli".to_owned()))?;
        Ok(Member {
            id: self.id,
            household_id: self.household_id,
            name: self.name,
            role,
            meta: Meta {
                created_at: parse_ts(&self.created_at)?,
                updated_at: parse_ts(&self.updated_at)?,
                deleted_at: self.deleted_at.as_deref().map(parse_ts).transpose()?,
                version: self.version,
                origin_device_id: self.origin_device_id,
            },
        })
    }
}

/// Vaqtni bazaga RFC 3339 (UTC) ko'rinishida yozish.
pub(crate) fn format_ts(value: OffsetDateTime) -> Result<String, StorageError> {
    value
        .to_offset(UtcOffset::UTC)
        .format(&Rfc3339)
        .map_err(|_| StorageError::InvalidData("vaqt".to_owned()))
}

/// Bazadagi RFC 3339 satrini vaqtga aylantirish.
pub(crate) fn parse_ts(text: &str) -> Result<OffsetDateTime, StorageError> {
    OffsetDateTime::parse(text, &Rfc3339)
        .map_err(|_| StorageError::InvalidData("vaqt formati".to_owned()))
}
