//! D11 repo: marosim rejalari, stsenariylar va byudjet qatorlari (sxema v12); kengash muhokamasi va
//! kattalar roziligi (sxema v17).
//!
//! Marosim bir nechta stsenariyga ega (masalan, «3 kun, 200 kishi» va «1 kun, 100 kishi»); har stsenariyning
//! o'z qatorlari bor. Holat (`PLANNED | CONFIRMED`) va oilaviy muhokama belgisi marosimda saqlanadi.

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

/// Marosim yozuvi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CeremonyRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Turi: `TOY | BESHIK | SUNNAT | MARAKA | OTHER`.
    pub kind: String,
    /// Nomi.
    pub title: String,
    /// Rejalashtirilgan sana (bo'lmasligi mumkin).
    pub event_on: Option<Date>,
    /// Holat: `PLANNED | CONFIRMED`.
    pub status: String,
    /// Oilaviy muhokama o'tkazilganmi.
    pub family_discussed: bool,
    /// Tanlangan stsenariy (tasdiqlashda).
    pub chosen_scenario_id: Option<String>,
    /// To'yona o'rniga jamg'arma maqsadi nomi.
    pub goal_name: Option<String>,
    /// Maqsad summasi.
    pub goal_target: Option<Money>,
    /// Yaratilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Stsenariy (qatorlari bilan).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScenarioRow {
    /// UUIDv7.
    pub id: String,
    /// Marosim.
    pub ceremony_id: String,
    /// Nomi.
    pub name: String,
    /// Mehmonlar soni.
    pub guests: u32,
    /// Kunlar soni.
    pub days: u32,
    /// Byudjet qatorlari (tartib bilan).
    pub lines: Vec<LineRow>,
}

/// Byudjet qatori.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LineRow {
    /// UUIDv7.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Miqdor.
    pub quantity: u64,
    /// Birlik narxi.
    pub unit_price: Money,
    /// Manba: `SAVINGS | FAMILY | EXPECTED_GIFTS | DEBT`.
    pub funding: String,
}

/// Marosimlar.
pub struct CeremonyRepo<'a> {
    conn: &'a Connection,
}

impl<'a> CeremonyRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi marosim.
    pub fn insert(&self, row: &CeremonyRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO ceremonies (id, household_id, kind, title, event_on, status, family_discussed, \
             chosen_scenario_id, goal_name, goal_target_minor, currency, created_at, updated_at, deleted_at, \
             version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, NULL, 1, ?13)",
            params![
                row.id,
                row.household_id,
                row.kind,
                row.title,
                row.event_on.map(format_date).transpose()?,
                row.status,
                i32::from(row.family_discussed),
                row.chosen_scenario_id,
                row.goal_name,
                row.goal_target.map(|m| m.minor()),
                row.goal_target
                    .map_or(Currency::Uzs, |m| m.currency())
                    .iso_code(),
                format_ts(row.created_at)?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Stsenariy qo'shadi (qatorlarsiz).
    pub fn insert_scenario(
        &self,
        scenario: &ScenarioRow,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let seq: i64 = self.conn.query_row(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM ceremony_scenarios WHERE ceremony_id = ?1",
            [scenario.ceremony_id.as_str()],
            |row| row.get(0),
        )?;
        self.conn.execute(
            "INSERT INTO ceremony_scenarios (id, ceremony_id, name, guests, days, seq, created_at) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                scenario.id,
                scenario.ceremony_id,
                scenario.name,
                scenario.guests,
                scenario.days,
                seq,
                format_ts(now)?,
            ],
        )?;
        Ok(())
    }

    /// Qator qo'shadi.
    pub fn insert_line(&self, scenario_id: &str, line: &LineRow) -> Result<(), StorageError> {
        let seq: i64 = self.conn.query_row(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM ceremony_lines WHERE scenario_id = ?1",
            [scenario_id],
            |row| row.get(0),
        )?;
        self.conn.execute(
            "INSERT INTO ceremony_lines (id, scenario_id, name, quantity, unit_minor, currency, funding, seq) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                line.id,
                scenario_id,
                line.name,
                i64::try_from(line.quantity).map_err(|_| StorageError::InvalidData("miqdor".to_owned()))?,
                line.unit_price.minor(),
                line.unit_price.currency().iso_code(),
                line.funding,
                seq,
            ],
        )?;
        Ok(())
    }

    /// Qatorning marosimi.
    pub fn line_ceremony(&self, line_id: &str) -> Result<Option<String>, StorageError> {
        Ok(self
            .conn
            .query_row(
                "SELECT s.ceremony_id FROM ceremony_lines l JOIN ceremony_scenarios s ON s.id = l.scenario_id \
                 WHERE l.id = ?1",
                [line_id],
                |row| row.get(0),
            )
            .optional()?)
    }

    /// Qatorni o'chiradi.
    pub fn delete_line(&self, line_id: &str) -> Result<(), StorageError> {
        let changed = self
            .conn
            .execute("DELETE FROM ceremony_lines WHERE id = ?1", [line_id])?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Stsenariyning marosimi.
    pub fn scenario_ceremony(&self, scenario_id: &str) -> Result<Option<String>, StorageError> {
        Ok(self
            .conn
            .query_row(
                "SELECT ceremony_id FROM ceremony_scenarios WHERE id = ?1",
                [scenario_id],
                |row| row.get(0),
            )
            .optional()?)
    }

    /// Oilaviy muhokama belgisini qo'yadi.
    pub fn set_discussed(&self, id: &str, now: OffsetDateTime) -> Result<(), StorageError> {
        self.touch(
            "UPDATE ceremonies SET family_discussed = 1, updated_at = ?2, version = version + 1 \
             WHERE id = ?1 AND deleted_at IS NULL",
            params![id, format_ts(now)?],
        )
    }

    /// Holat va tanlangan stsenariyni yozadi.
    pub fn set_status(
        &self,
        id: &str,
        status: &str,
        chosen_scenario_id: Option<&str>,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        self.touch(
            "UPDATE ceremonies SET status = ?2, chosen_scenario_id = ?3, updated_at = ?4, version = version + 1 \
             WHERE id = ?1 AND deleted_at IS NULL",
            params![id, status, chosen_scenario_id, format_ts(now)?],
        )
    }

    /// Jamg'arma maqsadini yozadi.
    pub fn set_goal(
        &self,
        id: &str,
        name: &str,
        target: Money,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        self.touch(
            "UPDATE ceremonies SET goal_name = ?2, goal_target_minor = ?3, currency = ?4, updated_at = ?5, \
             version = version + 1 WHERE id = ?1 AND deleted_at IS NULL",
            params![
                id,
                name,
                target.minor(),
                target.currency().iso_code(),
                format_ts(now)?
            ],
        )
    }

    fn touch(&self, sql: &str, params: &[&dyn rusqlite::ToSql]) -> Result<(), StorageError> {
        let changed = self.conn.execute(sql, params)?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Bitta marosim.
    pub fn find(&self, id: &str) -> Result<Option<CeremonyRow>, StorageError> {
        self.conn
            .query_row(
                &format!("{SELECT} WHERE c.id = ?1 AND c.deleted_at IS NULL"),
                [id],
                read_row,
            )
            .optional()?
            .map(Raw::into_row)
            .transpose()
    }

    /// Xonadon marosimlari, yaratilish tartibida.
    pub fn list(&self, household_id: &str) -> Result<Vec<CeremonyRow>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{SELECT} WHERE c.household_id = ?1 AND c.deleted_at IS NULL ORDER BY c.created_at, c.id"
        ))?;
        let rows = statement.query_map([household_id], read_row)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?.into_row()?);
        }
        Ok(out)
    }

    /// Marosim stsenariylari (qatorlari bilan), tartib bo'yicha.
    pub fn scenarios(&self, ceremony_id: &str) -> Result<Vec<ScenarioRow>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, ceremony_id, name, guests, days FROM ceremony_scenarios WHERE ceremony_id = ?1 ORDER BY seq",
        )?;
        let rows = statement.query_map([ceremony_id], |row| {
            Ok(ScenarioRow {
                id: row.get(0)?,
                ceremony_id: row.get(1)?,
                name: row.get(2)?,
                guests: row.get(3)?,
                days: row.get(4)?,
                lines: Vec::new(),
            })
        })?;
        let mut out = Vec::new();
        for row in rows {
            let mut scenario = row?;
            scenario.lines = self.lines(&scenario.id)?;
            out.push(scenario);
        }
        Ok(out)
    }

    fn lines(&self, scenario_id: &str) -> Result<Vec<LineRow>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, name, quantity, unit_minor, currency, funding FROM ceremony_lines \
             WHERE scenario_id = ?1 ORDER BY seq",
        )?;
        let rows = statement.query_map([scenario_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, i64>(2)?,
                row.get::<_, i64>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, String>(5)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (id, name, quantity, unit_minor, currency, funding) = row?;
            out.push(LineRow {
                id,
                name,
                quantity: u64::try_from(quantity)
                    .map_err(|_| StorageError::InvalidData("miqdor".to_owned()))?,
                unit_price: money_of(unit_minor, &currency)?,
                funding,
            });
        }
        Ok(out)
    }
}

const SELECT: &str = "SELECT c.id, c.household_id, c.kind, c.title, c.event_on, c.status, c.family_discussed, \
    c.chosen_scenario_id, c.goal_name, c.goal_target_minor, c.currency, c.created_at, c.updated_at, c.deleted_at, \
    c.version, c.origin_device_id FROM ceremonies c";

struct Raw {
    id: String,
    household_id: String,
    kind: String,
    title: String,
    event_on: Option<String>,
    status: String,
    family_discussed: i64,
    chosen_scenario_id: Option<String>,
    goal_name: Option<String>,
    goal_target_minor: Option<i64>,
    currency: String,
    meta: RawMeta,
}

fn read_row(row: &Row<'_>) -> rusqlite::Result<Raw> {
    Ok(Raw {
        id: row.get(0)?,
        household_id: row.get(1)?,
        kind: row.get(2)?,
        title: row.get(3)?,
        event_on: row.get(4)?,
        status: row.get(5)?,
        family_discussed: row.get(6)?,
        chosen_scenario_id: row.get(7)?,
        goal_name: row.get(8)?,
        goal_target_minor: row.get(9)?,
        currency: row.get(10)?,
        meta: RawMeta::read(row, 11)?,
    })
}

impl Raw {
    fn into_row(self) -> Result<CeremonyRow, StorageError> {
        let meta = self.meta.into_meta()?;
        Ok(CeremonyRow {
            id: self.id,
            household_id: self.household_id,
            kind: self.kind,
            title: self.title,
            event_on: self.event_on.as_deref().map(parse_date).transpose()?,
            status: self.status,
            family_discussed: self.family_discussed != 0,
            chosen_scenario_id: self.chosen_scenario_id,
            goal_name: self.goal_name,
            goal_target: self
                .goal_target_minor
                .map(|minor| money_of(minor, &self.currency))
                .transpose()?,
            created_at: meta.created_at,
            origin_device_id: meta.origin_device_id,
        })
    }
}

/// «Buni qarzsiz qanday o'tkazamiz?» muhokamasi (oxirgisi amal qiladi).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiscussionRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Marosim.
    pub ceremony_id: String,
    /// Muhokamada tanlangan stsenariy.
    pub scenario_id: String,
    /// Qaror matni (kamida 20 belgi).
    pub note: String,
    /// Boshlangan vaqt.
    pub started_at: OffsetDateTime,
    /// Hamma katta rozi bo'lgan vaqt (bo'lmasa — davom etmoqda).
    pub completed_at: Option<OffsetDateTime>,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Kengash muhokamalari.
pub struct DiscussionRepo<'a> {
    conn: &'a Connection,
}

impl<'a> DiscussionRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi muhokama (oldingisi tarixda qoladi, roziliklar qaytadan).
    pub fn insert(&self, row: &DiscussionRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO ceremony_discussions (id, household_id, ceremony_id, scenario_id, note, started_at, \
             completed_at, origin_device_id) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                row.id,
                row.household_id,
                row.ceremony_id,
                row.scenario_id,
                row.note,
                format_ts(row.started_at)?,
                row.completed_at.map(format_ts).transpose()?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Marosimning oxirgi muhokamasi.
    pub fn latest(&self, ceremony_id: &str) -> Result<Option<DiscussionRow>, StorageError> {
        let raw = self
            .conn
            .query_row(
                "SELECT id, household_id, ceremony_id, scenario_id, note, started_at, completed_at, origin_device_id \
                 FROM ceremony_discussions WHERE ceremony_id = ?1 ORDER BY started_at DESC, id DESC LIMIT 1",
                [ceremony_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, String>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, String>(5)?,
                        row.get::<_, Option<String>>(6)?,
                        row.get::<_, String>(7)?,
                    ))
                },
            )
            .optional()?;
        let Some((id, household_id, ceremony_id, scenario_id, note, started, completed, device)) =
            raw
        else {
            return Ok(None);
        };
        Ok(Some(DiscussionRow {
            id,
            household_id,
            ceremony_id,
            scenario_id,
            note,
            started_at: crate::repo::parse_ts(&started)?,
            completed_at: completed
                .as_deref()
                .map(crate::repo::parse_ts)
                .transpose()?,
            origin_device_id: device,
        }))
    }

    /// Katta a'zoning roziligi (takror — yo'q qilinmaydi, jim o'tadi).
    pub fn insert_consent(
        &self,
        id: &str,
        discussion_id: &str,
        member_id: &str,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT OR IGNORE INTO ceremony_discussion_consents (id, discussion_id, member_id, consented_at) \
             VALUES (?1, ?2, ?3, ?4)",
            params![id, discussion_id, member_id, format_ts(now)?],
        )?;
        Ok(())
    }

    /// Rozi bo'lgan a'zolar.
    pub fn consented_members(&self, discussion_id: &str) -> Result<Vec<String>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT member_id FROM ceremony_discussion_consents WHERE discussion_id = ?1 ORDER BY consented_at",
        )?;
        let rows = statement.query_map([discussion_id], |row| row.get::<_, String>(0))?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        Ok(out)
    }

    /// Muhokama yakunlandi (hamma katta rozi).
    pub fn set_completed(
        &self,
        discussion_id: &str,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE ceremony_discussions SET completed_at = ?2 WHERE id = ?1",
            params![discussion_id, format_ts(now)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }
}
