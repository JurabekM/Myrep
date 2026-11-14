//! D5 repo'lari: haftalik vazifa bajarilishi va «Daftar sahifasi» (sxema v3).
//!
//! Sanalar `YYYY-MM-DD` (Toshkent kalendar sanasi), vaqtlar RFC 3339 UTC. Vazifa belgisi mantiqiy
//! o'chiriladi: birinchi bajarilish tarixi (ochilish uchun kerak) hech qachon yo'qolmaydi.

use std::collections::BTreeMap;

use domain::{DaftarPage, TaskCompletion};
use rusqlite::{Connection, OptionalExtension, Row, params};
use time::{Date, OffsetDateTime};

use crate::StorageError;
use crate::finance::{RawMeta, format_date, parse_date};
use crate::repo::{format_ts, parse_ts};

/// Haftalik vazifa bajarilishlari.
pub struct TaskCompletionRepo<'a> {
    conn: &'a Connection,
}

impl<'a> TaskCompletionRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi bajarilish qo'shadi.
    pub fn insert(&self, completion: &TaskCompletion) -> Result<(), StorageError> {
        let meta = &completion.meta;
        self.conn.execute(
            "INSERT INTO task_completions (id, household_id, task_id, week_start, is_auto, \
             created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
            params![
                completion.id,
                completion.household_id,
                completion.task_id,
                format_date(completion.week_start)?,
                i64::from(completion.is_auto),
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Shu hafta (boshlanish sanasi bo'yicha) faol bajarilishlar.
    pub fn list_for_week(
        &self,
        household_id: &str,
        week_start: Date,
    ) -> Result<Vec<TaskCompletion>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, task_id, week_start, is_auto, \
             created_at, updated_at, deleted_at, version, origin_device_id \
             FROM task_completions \
             WHERE household_id = ?1 AND week_start = ?2 AND deleted_at IS NULL \
             ORDER BY created_at, id",
        )?;
        let rows = statement.query_map(params![household_id, format_date(week_start)?], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
                row.get::<_, i64>(4)?,
                RawMeta::read(row, 5)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (id, household_id, task_id, week, is_auto, meta) = row?;
            out.push(TaskCompletion {
                id,
                household_id,
                task_id,
                week_start: parse_date(&week)?,
                is_auto: is_auto == 1,
                meta: meta.into_meta()?,
            });
        }
        Ok(out)
    }

    /// Har vazifaning birinchi bajarilish vaqti. O'chirilgan yozuvlar ham hisobga olinadi:
    /// belgi olib tashlangan bo'lsa ham bob ochiq qoladi.
    pub fn first_completed_at(
        &self,
        household_id: &str,
    ) -> Result<BTreeMap<String, OffsetDateTime>, StorageError> {
        let mut statement = self
            .conn
            .prepare("SELECT task_id, created_at FROM task_completions WHERE household_id = ?1")?;
        let rows = statement.query_map([household_id], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })?;
        let mut first: BTreeMap<String, OffsetDateTime> = BTreeMap::new();
        for row in rows {
            let (task_id, created) = row?;
            let at = parse_ts(&created)?;
            first
                .entry(task_id)
                .and_modify(|known| {
                    if at < *known {
                        *known = at;
                    }
                })
                .or_insert(at);
        }
        Ok(first)
    }

    /// Bajarilishni mantiqiy o'chiradi (vazifa belgisi olib tashlandi).
    pub fn soft_delete(&self, id: &str, now: OffsetDateTime) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE task_completions SET deleted_at = ?2, updated_at = ?2, version = version + 1 \
             WHERE id = ?1 AND deleted_at IS NULL",
            params![id, format_ts(now)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }
}

/// «Daftar sahifasi» repo'si: bob uchun bitta sahifa.
pub struct DaftarPageRepo<'a> {
    conn: &'a Connection,
}

/// Bazadan o'qilgan sahifa (meta hali ajratilmagan).
struct RawPage {
    id: String,
    household_id: String,
    chapter_id: String,
    law_number: i64,
    body: String,
    meta: RawMeta,
}

impl RawPage {
    fn read(row: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            id: row.get(0)?,
            household_id: row.get(1)?,
            chapter_id: row.get(2)?,
            law_number: row.get(3)?,
            body: row.get(4)?,
            meta: RawMeta::read(row, 5)?,
        })
    }

    fn into_page(self) -> Result<DaftarPage, StorageError> {
        Ok(DaftarPage {
            id: self.id,
            household_id: self.household_id,
            chapter_id: self.chapter_id,
            law_number: u32::try_from(self.law_number)
                .map_err(|_| StorageError::InvalidData("qonun raqami".to_owned()))?,
            body: self.body,
            meta: self.meta.into_meta()?,
        })
    }
}

impl<'a> DaftarPageRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Bob uchun faol sahifa.
    pub fn find_for_chapter(
        &self,
        household_id: &str,
        chapter_id: &str,
    ) -> Result<Option<DaftarPage>, StorageError> {
        let raw = self
            .conn
            .query_row(
                "SELECT id, household_id, chapter_id, law_number, body, \
                 created_at, updated_at, deleted_at, version, origin_device_id \
                 FROM daftar_pages WHERE household_id = ?1 AND chapter_id = ?2 AND deleted_at IS NULL",
                params![household_id, chapter_id],
                RawPage::read,
            )
            .optional()?;
        raw.map(RawPage::into_page).transpose()
    }

    /// Yangi sahifa qo'shadi.
    pub fn insert(&self, page: &DaftarPage) -> Result<(), StorageError> {
        let meta = &page.meta;
        self.conn.execute(
            "INSERT INTO daftar_pages (id, household_id, chapter_id, law_number, body, \
             created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
            params![
                page.id,
                page.household_id,
                page.chapter_id,
                i64::from(page.law_number),
                page.body,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Sahifa matni va versiyasini yangilaydi.
    pub fn update_body(&self, page: &DaftarPage) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE daftar_pages SET body = ?2, updated_at = ?3, version = ?4 WHERE id = ?1",
            params![
                page.id,
                page.body,
                format_ts(page.meta.updated_at)?,
                page.meta.version,
            ],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }
}
