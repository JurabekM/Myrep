//! D4 repo'lari: kategoriya, daromad, xarajat, majburiyat, «Kelajagim», ulush qoidasi, nasiya va oylik hisobot.
//!
//! Sanalar bazada `YYYY-MM-DD` (Toshkent kalendar sanasi), vaqtlar RFC 3339 UTC, pul — minor birlikda
//! (`*_minor`) va valyuta kodi bilan. Mantiqiy o'chirish yo'q bo'lgan jadvallarda ham `deleted_at` bor.

use domain::Channel;
use domain::Meta;
use domain::calendar::DateRange;
use domain::{
    Category, CategoryKey, DebtPayment, Expense, Income, MonthlyReport, Necessity, NecessityChange,
    Obligation, ObligationKind, ShareRule, ShareTarget, ShopDebt, VaultEntry, VaultMovement,
};
use money::{Currency, Money};
use rusqlite::{Connection, OptionalExtension, Row, params};
use time::Date;
use time::OffsetDateTime;
use time::format_description::well_known::Iso8601;

use crate::StorageError;
use crate::repo::{format_ts, parse_ts};

/// «Kelajagim» jamg'armasi uchun aktiv nomi.
const VAULT_ASSET_NAME: &str = "Kelajagim";
/// Yagona «Kelajagim» hovuzi turi (qorovul; D8 da ajratiladi).
const VAULT_TYPE: &str = "QOROVUL";

pub(crate) fn format_date(date: Date) -> Result<String, StorageError> {
    date.format(&Iso8601::DATE)
        .map_err(|_| StorageError::InvalidData("sana".to_owned()))
}

pub(crate) fn parse_date(text: &str) -> Result<Date, StorageError> {
    Date::parse(text, &Iso8601::DATE)
        .map_err(|_| StorageError::InvalidData("sana formati".to_owned()))
}

fn money_of(minor: i64, currency: &str) -> Result<Money, StorageError> {
    let currency = Currency::from_iso(currency)
        .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?;
    Ok(Money::new(minor, currency))
}

fn currency_code(money: Money) -> &'static str {
    money.currency().iso_code()
}

/// Bazadagi metama'lumot ustunlari (`created_at`, `updated_at`, `deleted_at`, `version`, `origin_device_id`).
pub(crate) struct RawMeta {
    created_at: String,
    updated_at: String,
    deleted_at: Option<String>,
    version: i64,
    origin_device_id: String,
}

impl RawMeta {
    /// `start` dan boshlab besh ustunni o'qiydi.
    pub(crate) fn read(row: &Row<'_>, start: usize) -> rusqlite::Result<Self> {
        Ok(Self {
            created_at: row.get(start)?,
            updated_at: row.get(start + 1)?,
            deleted_at: row.get(start + 2)?,
            version: row.get(start + 3)?,
            origin_device_id: row.get(start + 4)?,
        })
    }

    pub(crate) fn into_meta(self) -> Result<Meta, StorageError> {
        Ok(Meta {
            created_at: parse_ts(&self.created_at)?,
            updated_at: parse_ts(&self.updated_at)?,
            deleted_at: self.deleted_at.as_deref().map(parse_ts).transpose()?,
            version: self.version,
            origin_device_id: self.origin_device_id,
        })
    }
}

/// Kategoriyalar. Tizim kategoriyasi `system_key` bilan saqlanadi.
pub struct CategoryRepo<'a> {
    conn: &'a Connection,
}

impl<'a> CategoryRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi kategoriya qo'shadi.
    pub fn insert(&self, category: &Category) -> Result<(), StorageError> {
        let meta = &category.meta;
        self.conn.execute(
            "INSERT INTO categories (id, household_id, name, system_key, default_necessity, created_at, updated_at, deleted_at, version, origin_device_id, is_habit) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                category.id,
                category.household_id,
                category.name,
                category.system_key.map(CategoryKey::code),
                category.necessity.code(),
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
                i64::from(category.is_habit),
            ],
        )?;
        Ok(())
    }

    /// Xonadonning faol kategoriyalari.
    pub fn list(&self, household_id: &str) -> Result<Vec<Category>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, name, system_key, COALESCE(default_necessity, 'KERAK'), created_at, updated_at, deleted_at, version, origin_device_id, is_habit \
             FROM categories WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([household_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, Option<String>>(3)?,
                row.get::<_, String>(4)?,
                RawMeta::read(row, 5)?,
                row.get::<_, i64>(10)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (id, household_id, name, key, necessity, meta, is_habit) = row?;
            out.push(Category {
                id,
                household_id,
                name,
                system_key: key
                    .map(|code| {
                        CategoryKey::from_code(&code).ok_or_else(|| {
                            StorageError::InvalidData("kategoriya kaliti".to_owned())
                        })
                    })
                    .transpose()?,
                necessity: Necessity::from_code(&necessity)
                    .ok_or_else(|| StorageError::InvalidData("toifa".to_owned()))?,
                is_habit: is_habit == 1,
                meta: meta.into_meta()?,
            });
        }
        Ok(out)
    }

    /// Kategoriya toifasini va versiyasini yangilaydi.
    pub fn update_necessity(&self, category: &Category) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE categories SET default_necessity = ?2, updated_at = ?3, version = ?4 WHERE id = ?1 AND deleted_at IS NULL",
            params![
                category.id,
                category.necessity.code(),
                format_ts(category.meta.updated_at)?,
                category.meta.version,
            ],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Toifa o'zgarishi tarixiga yozuv qo'shadi (kim, qachon, qaysidan qaysiga).
    pub fn insert_necessity_change(&self, change: &NecessityChange) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO necessity_changes (id, household_id, category_id, from_necessity, to_necessity, changed_by, created_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                change.id,
                change.household_id,
                change.category_id,
                change.from.code(),
                change.to.code(),
                change.changed_by,
                format_ts(change.meta.created_at)?,
                change.meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Kategoriyaning toifa o'zgarishlari tarixi (eng yangisi birinchi).
    pub fn list_necessity_changes(
        &self,
        category_id: &str,
    ) -> Result<Vec<(Necessity, Necessity, String)>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT from_necessity, to_necessity, changed_by FROM necessity_changes \
             WHERE category_id = ?1 ORDER BY created_at DESC, id DESC",
        )?;
        let rows = statement.query_map([category_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (from, to, by) = row?;
            let from = Necessity::from_code(&from)
                .ok_or_else(|| StorageError::InvalidData("toifa".to_owned()))?;
            let to = Necessity::from_code(&to)
                .ok_or_else(|| StorageError::InvalidData("toifa".to_owned()))?;
            out.push((from, to, by));
        }
        Ok(out)
    }

    /// Tizim kategoriyasining identifikatori; yo'q bo'lsa — `None`.
    pub fn find_system(
        &self,
        household_id: &str,
        key: CategoryKey,
    ) -> Result<Option<String>, StorageError> {
        Ok(self
            .conn
            .query_row(
                "SELECT id FROM categories WHERE household_id = ?1 AND system_key = ?2 AND deleted_at IS NULL",
                params![household_id, key.code()],
                |row| row.get(0),
            )
            .optional()?)
    }
}

/// Daromadlar.
pub struct IncomeRepo<'a> {
    conn: &'a Connection,
}

impl<'a> IncomeRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi daromad qo'shadi.
    pub fn insert(&self, income: &Income) -> Result<(), StorageError> {
        let meta = &income.meta;
        self.conn.execute(
            "INSERT INTO incomes (id, household_id, member_id, source, channel, amount_minor, currency, occurred_on, note, \
             created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
            params![
                income.id,
                income.household_id,
                income.member_id,
                income.source,
                income.channel.code(),
                income.amount.minor(),
                currency_code(income.amount),
                format_date(income.occurred_on)?,
                income.note,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// ID bo'yicha faol daromad.
    pub fn find(&self, id: &str) -> Result<Option<Income>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{INCOME_SELECT} WHERE id = ?1 AND deleted_at IS NULL"
        ))?;
        let mut rows = statement.query_map([id], RawIncome::from_row)?;
        match rows.next() {
            Some(row) => Ok(Some(row?.into_domain()?)),
            None => Ok(None),
        }
    }

    /// Davr ichidagi faol daromadlar, eng yangisi birinchi.
    pub fn list_in_range(
        &self,
        household_id: &str,
        range: DateRange,
    ) -> Result<Vec<Income>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{INCOME_SELECT} WHERE household_id = ?1 AND deleted_at IS NULL \
             AND occurred_on >= ?2 AND occurred_on < ?3 ORDER BY occurred_on DESC, created_at DESC"
        ))?;
        let rows = statement.query_map(
            params![
                household_id,
                format_date(range.start)?,
                format_date(range.end)?
            ],
            RawIncome::from_row,
        )?;
        rows.map(|row| row?.into_domain()).collect()
    }

    /// So'nggi daromadlar (tez kiritishda oxirgi manba va kanal taklif qilinadi).
    pub fn list_recent(&self, household_id: &str, limit: u32) -> Result<Vec<Income>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{INCOME_SELECT} WHERE household_id = ?1 AND deleted_at IS NULL \
             ORDER BY created_at DESC, id DESC LIMIT ?2"
        ))?;
        let rows = statement.query_map(params![household_id, limit], RawIncome::from_row)?;
        rows.map(|row| row?.into_domain()).collect()
    }
}

const INCOME_SELECT: &str = "SELECT id, household_id, member_id, source, channel, amount_minor, currency, occurred_on, note, \
     created_at, updated_at, deleted_at, version, origin_device_id FROM incomes";

struct RawIncome {
    id: String,
    household_id: String,
    member_id: String,
    source: String,
    channel: String,
    amount_minor: i64,
    currency: String,
    occurred_on: String,
    note: Option<String>,
    meta: RawMeta,
}

impl RawIncome {
    fn from_row(row: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            id: row.get(0)?,
            household_id: row.get(1)?,
            member_id: row.get(2)?,
            source: row.get(3)?,
            channel: row.get(4)?,
            amount_minor: row.get(5)?,
            currency: row.get(6)?,
            occurred_on: row.get(7)?,
            note: row.get(8)?,
            meta: RawMeta::read(row, 9)?,
        })
    }

    fn into_domain(self) -> Result<Income, StorageError> {
        Ok(Income {
            id: self.id,
            household_id: self.household_id,
            member_id: self.member_id,
            source: self.source,
            channel: Channel::from_code(&self.channel)
                .ok_or_else(|| StorageError::InvalidData("kanal".to_owned()))?,
            amount: money_of(self.amount_minor, &self.currency)?,
            occurred_on: parse_date(&self.occurred_on)?,
            note: self.note,
            meta: self.meta.into_meta()?,
        })
    }
}

/// Xarajatlar.
pub struct ExpenseRepo<'a> {
    conn: &'a Connection,
}

impl<'a> ExpenseRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi xarajat qo'shadi.
    pub fn insert(&self, expense: &Expense) -> Result<(), StorageError> {
        let meta = &expense.meta;
        self.conn.execute(
            "INSERT INTO expenses (id, household_id, member_id, category_id, channel, amount_minor, currency, occurred_on, note, \
             necessity, is_gift, is_ostentation, funded_by_debt, \
             created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, 'CASH', ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17)",
            params![
                expense.id,
                expense.household_id,
                expense.member_id,
                expense.category_id,
                expense.amount.minor(),
                currency_code(expense.amount),
                format_date(expense.occurred_on)?,
                expense.note,
                expense.necessity.code(),
                i64::from(expense.is_gift),
                i64::from(expense.is_ostentation),
                i64::from(expense.funded_by_debt),
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Davr ichidagi faol xarajatlar.
    pub fn list_in_range(
        &self,
        household_id: &str,
        range: DateRange,
    ) -> Result<Vec<Expense>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, member_id, category_id, amount_minor, currency, occurred_on, note, \
             necessity, is_gift, is_ostentation, funded_by_debt, \
             created_at, updated_at, deleted_at, version, origin_device_id \
             FROM expenses WHERE household_id = ?1 AND deleted_at IS NULL \
             AND occurred_on >= ?2 AND occurred_on < ?3 ORDER BY occurred_on DESC, created_at DESC",
        )?;
        let rows = statement.query_map(
            params![
                household_id,
                format_date(range.start)?,
                format_date(range.end)?
            ],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, Option<String>>(3)?,
                    row.get::<_, i64>(4)?,
                    row.get::<_, String>(5)?,
                    row.get::<_, String>(6)?,
                    row.get::<_, Option<String>>(7)?,
                    row.get::<_, String>(8)?,
                    row.get::<_, i64>(9)?,
                    row.get::<_, i64>(10)?,
                    row.get::<_, i64>(11)?,
                    RawMeta::read(row, 12)?,
                ))
            },
        )?;
        let mut out = Vec::new();
        for row in rows {
            let (
                id,
                household_id,
                member_id,
                category_id,
                minor,
                currency,
                occurred,
                note,
                necessity,
                is_gift,
                is_ostentation,
                funded_by_debt,
                meta,
            ) = row?;
            out.push(Expense {
                id,
                household_id,
                member_id,
                category_id,
                amount: money_of(minor, &currency)?,
                occurred_on: parse_date(&occurred)?,
                note,
                necessity: Necessity::from_code(&necessity)
                    .ok_or_else(|| StorageError::InvalidData("toifa".to_owned()))?,
                is_gift: is_gift == 1,
                is_ostentation: is_ostentation == 1,
                funded_by_debt: funded_by_debt == 1,
                meta: meta.into_meta()?,
            });
        }
        Ok(out)
    }
}

/// Majburiyatlar (ijara, kredit, kommunal, telefon, benzin).
pub struct ObligationRepo<'a> {
    conn: &'a Connection,
}

impl<'a> ObligationRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi majburiyat qo'shadi.
    pub fn insert(&self, obligation: &Obligation) -> Result<(), StorageError> {
        let meta = &obligation.meta;
        self.conn.execute(
            "INSERT INTO obligations (id, household_id, title, kind, amount_minor, currency, due_day, category_id, active, \
             created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
            params![
                obligation.id,
                obligation.household_id,
                obligation.title,
                obligation.kind.code(),
                obligation.amount.minor(),
                currency_code(obligation.amount),
                obligation.due_day,
                obligation.category_id,
                obligation.active,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Faol majburiyatlar (o'chirilmaganlari va yoqilganlari).
    pub fn list_active(&self, household_id: &str) -> Result<Vec<Obligation>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, title, kind, amount_minor, currency, due_day, category_id, active, \
             created_at, updated_at, deleted_at, version, origin_device_id \
             FROM obligations WHERE household_id = ?1 AND deleted_at IS NULL AND active = 1 \
             ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([household_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
                row.get::<_, i64>(4)?,
                row.get::<_, String>(5)?,
                row.get::<_, Option<u8>>(6)?,
                row.get::<_, Option<String>>(7)?,
                row.get::<_, bool>(8)?,
                RawMeta::read(row, 9)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (
                id,
                household_id,
                title,
                kind,
                minor,
                currency,
                due_day,
                category_id,
                active,
                meta,
            ) = row?;
            out.push(Obligation {
                id,
                household_id,
                title,
                kind: ObligationKind::from_code(&kind)
                    .ok_or_else(|| StorageError::InvalidData("majburiyat turi".to_owned()))?,
                amount: money_of(minor, &currency)?,
                due_day,
                category_id,
                active,
                meta: meta.into_meta()?,
            });
        }
        Ok(out)
    }

    /// Majburiyatni yoqadi yoki o'chiradi (faolligini o'zgartiradi).
    pub fn set_active(
        &self,
        id: &str,
        active: bool,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE obligations SET active = ?1, updated_at = ?2, version = version + 1 \
             WHERE id = ?3 AND deleted_at IS NULL",
            params![active, format_ts(now)?, id],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }
}

/// «Kelajagim» jamg'armasi: aktiv (bitta hovuz) va uning yozuvlari.
pub struct VaultRepo<'a> {
    conn: &'a Connection,
}

impl<'a> VaultRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Xonadonning «Kelajagim» aktivi. Yo'q bo'lsa, `new_id` bilan yaratiladi. Aktiv identifikatori qaytadi.
    pub fn ensure_asset(
        &self,
        new_id: &str,
        household_id: &str,
        currency: Currency,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<String, StorageError> {
        let existing: Option<String> = self
            .conn
            .query_row(
                "SELECT id FROM assets WHERE household_id = ?1 AND type = 'VAULT' AND deleted_at IS NULL \
                 ORDER BY created_at, id LIMIT 1",
                [household_id],
                |row| row.get(0),
            )
            .optional()?;
        if let Some(id) = existing {
            return Ok(id);
        }
        let timestamp = format_ts(now)?;
        self.conn.execute(
            "INSERT INTO assets (id, household_id, type, name, quantity, unit, currency, acquired_at, \
             created_at, updated_at, version, origin_device_id) \
             VALUES (?1, ?2, 'VAULT', ?3, 0, 'minor', ?4, ?5, ?6, ?6, 1, ?7)",
            params![
                new_id,
                household_id,
                VAULT_ASSET_NAME,
                currency.iso_code(),
                timestamp,
                timestamp,
                origin_device_id,
            ],
        )?;
        Ok(new_id.to_owned())
    }

    /// Yozuv qo'shadi: boshlang'ich balans, daromad ulushi yoki pul olish.
    pub fn insert_entry(
        &self,
        asset_id: &str,
        household_id: &str,
        entry: &VaultEntry,
    ) -> Result<(), StorageError> {
        let (kind, reason, income_id) = match &entry.movement {
            VaultMovement::Initial => ("INITIAL", None, None),
            VaultMovement::IncomeShare { income_id } => ("DEPOSIT", None, Some(income_id.as_str())),
            VaultMovement::Withdrawal { reason } => ("WITHDRAWAL", Some(reason.as_str()), None),
        };
        let meta = &entry.meta;
        self.conn.execute(
            "INSERT INTO vault_transactions (id, household_id, asset_id, vault_type, kind, amount_minor, currency, occurred_on, \
             reason, income_id, created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)",
            params![
                entry.id,
                household_id,
                asset_id,
                VAULT_TYPE,
                kind,
                entry.amount.minor(),
                currency_code(entry.amount),
                format_date(entry.occurred_on)?,
                reason,
                income_id,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Aktivning barcha faol yozuvlari, sana bo'yicha.
    pub fn list_entries(&self, asset_id: &str) -> Result<Vec<VaultEntry>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, kind, amount_minor, currency, occurred_on, reason, income_id, \
             created_at, updated_at, deleted_at, version, origin_device_id \
             FROM vault_transactions WHERE asset_id = ?1 AND deleted_at IS NULL \
             ORDER BY occurred_on, created_at, id",
        )?;
        let rows = statement.query_map([asset_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, i64>(2)?,
                row.get::<_, String>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, Option<String>>(5)?,
                row.get::<_, Option<String>>(6)?,
                RawMeta::read(row, 7)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (id, kind, minor, currency, occurred, reason, income_id, meta) = row?;
            let movement = match kind.as_str() {
                "INITIAL" => VaultMovement::Initial,
                "DEPOSIT" => VaultMovement::IncomeShare {
                    income_id: income_id
                        .ok_or_else(|| StorageError::InvalidData("ulush daromadi".to_owned()))?,
                },
                "WITHDRAWAL" => VaultMovement::Withdrawal {
                    reason: reason
                        .ok_or_else(|| StorageError::InvalidData("pul olish sababi".to_owned()))?,
                },
                _ => return Err(StorageError::InvalidData("yozuv turi".to_owned())),
            };
            out.push(VaultEntry {
                id,
                amount: money_of(minor, &currency)?,
                occurred_on: parse_date(&occurred)?,
                movement,
                meta: meta.into_meta()?,
            });
        }
        Ok(out)
    }
}

/// Ulush qoidasi (`allocation_rules`): xonadonning faol qoidasi.
pub struct RuleRepo<'a> {
    conn: &'a Connection,
}

/// Saqlangan qoida va uning identifikatori.
pub struct StoredRule {
    /// Qoida identifikatori (UUIDv7).
    pub id: String,
    /// Qoida.
    pub rule: ShareRule,
}

impl<'a> RuleRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Faol qoida. Yo'q bo'lsa — `None`.
    pub fn find_active(
        &self,
        household_id: &str,
        currency: Currency,
    ) -> Result<Option<StoredRule>, StorageError> {
        let row = self
            .conn
            .query_row(
                "SELECT id, mode, value, progressive, progression_offered_on FROM allocation_rules \
                 WHERE household_id = ?1 AND active = 1 AND deleted_at IS NULL ORDER BY created_at, id LIMIT 1",
                [household_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, i64>(2)?,
                        row.get::<_, bool>(3)?,
                        row.get::<_, Option<String>>(4)?,
                    ))
                },
            )
            .optional()?;
        let Some((id, mode, value, progressive, offered)) = row else {
            return Ok(None);
        };
        let target = match mode.as_str() {
            "PERCENT" => ShareTarget::Percent(value),
            "FIXED" => ShareTarget::Fixed(Money::new(value, currency)),
            _ => return Err(StorageError::InvalidData("qoida turi".to_owned())),
        };
        Ok(Some(StoredRule {
            id,
            rule: ShareRule {
                target,
                progressive,
                progression_offered_on: offered.as_deref().map(parse_date).transpose()?,
            },
        }))
    }

    /// Yangi qoida yozadi.
    pub fn insert(
        &self,
        id: &str,
        household_id: &str,
        rule: &ShareRule,
        now: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<(), StorageError> {
        let (mode, value) = encode_target(rule.target);
        self.conn.execute(
            "INSERT INTO allocation_rules (id, household_id, name, mode, value, progressive, active, progression_offered_on, \
             created_at, updated_at, version, origin_device_id) \
             VALUES (?1, ?2, 'Asosiy', ?3, ?4, ?5, 1, ?6, ?7, ?7, 1, ?8)",
            params![
                id,
                household_id,
                mode,
                value,
                rule.progressive,
                rule.progression_offered_on.map(format_date).transpose()?,
                format_ts(now)?,
                origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Mavjud qoidani yangilaydi (versiya oshadi).
    pub fn update(
        &self,
        id: &str,
        rule: &ShareRule,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        let (mode, value) = encode_target(rule.target);
        let changed = self.conn.execute(
            "UPDATE allocation_rules SET mode = ?1, value = ?2, progressive = ?3, progression_offered_on = ?4, \
             updated_at = ?5, version = version + 1 WHERE id = ?6 AND deleted_at IS NULL",
            params![
                mode,
                value,
                rule.progressive,
                rule.progression_offered_on.map(format_date).transpose()?,
                format_ts(now)?,
                id,
            ],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }
}

fn encode_target(target: ShareTarget) -> (&'static str, i64) {
    match target {
        ShareTarget::Percent(bp) => ("PERCENT", bp),
        ShareTarget::Fixed(amount) => ("FIXED", amount.minor()),
    }
}

/// Nasiya (do'kon qarzi) va to'lovlari.
pub struct DebtRepo<'a> {
    conn: &'a Connection,
}

impl<'a> DebtRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi nasiya qo'shadi.
    pub fn insert_debt(&self, debt: &ShopDebt) -> Result<(), StorageError> {
        let meta = &debt.meta;
        self.conn.execute(
            "INSERT INTO debts (id, household_id, kind, creditor, principal_minor, currency, incurred_on, note, \
             created_at, updated_at, deleted_at, version, origin_device_id) \
             VALUES (?1, ?2, 'SHOP', ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
            params![
                debt.id,
                debt.household_id,
                debt.creditor,
                debt.principal.minor(),
                currency_code(debt.principal),
                format_date(debt.incurred_on)?,
                debt.note,
                format_ts(meta.created_at)?,
                format_ts(meta.updated_at)?,
                meta.deleted_at.map(format_ts).transpose()?,
                meta.version,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Xonadonning faol nasiyalari, yaratilish tartibida.
    pub fn list_debts(&self, household_id: &str) -> Result<Vec<ShopDebt>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, creditor, principal_minor, currency, incurred_on, note, \
             created_at, updated_at, deleted_at, version, origin_device_id \
             FROM debts WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
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
                RawMeta::read(row, 7)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (id, household_id, creditor, minor, currency, incurred, note, meta) = row?;
            out.push(ShopDebt {
                id,
                household_id,
                creditor,
                principal: money_of(minor, &currency)?,
                incurred_on: parse_date(&incurred)?,
                note,
                meta: meta.into_meta()?,
            });
        }
        Ok(out)
    }

    /// Nasiyaga to'lov qo'shadi.
    pub fn insert_payment(
        &self,
        household_id: &str,
        payment: &DebtPayment,
    ) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO debt_payments (id, household_id, debt_id, amount_minor, currency, paid_on, created_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                payment.id,
                household_id,
                payment.debt_id,
                payment.amount.minor(),
                currency_code(payment.amount),
                format_date(payment.paid_on)?,
                format_ts(payment.meta.created_at)?,
                payment.meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Nasiyaning barcha to'lovlari summalari.
    pub fn payment_amounts(
        &self,
        debt_id: &str,
        currency: Currency,
    ) -> Result<Vec<Money>, StorageError> {
        let mut statement = self
            .conn
            .prepare("SELECT amount_minor FROM debt_payments WHERE debt_id = ?1")?;
        let rows = statement.query_map([debt_id], |row| row.get::<_, i64>(0))?;
        let mut out = Vec::new();
        for minor in rows {
            out.push(Money::new(minor?, currency));
        }
        Ok(out)
    }
}

/// Oylik audit hisobotlari (o'zgarmas).
pub struct ReportRepo<'a> {
    conn: &'a Connection,
}

impl<'a> ReportRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Hisobot yozadi. Shu davr uchun ikkinchi marta yozilmaydi (`UNIQUE`).
    pub fn insert(&self, report: &MonthlyReport) -> Result<(), StorageError> {
        let meta = &report.meta;
        self.conn.execute(
            "INSERT INTO monthly_reports (id, household_id, period_start, period_end, currency, income_minor, expenses_minor, \
             obligations_minor, obligations_unrecorded_minor, net_savings_minor, unexplained_minor, created_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
            params![
                report.id,
                report.household_id,
                format_date(report.period.start)?,
                format_date(report.period.end)?,
                report.currency.iso_code(),
                report.income.minor(),
                report.expenses.minor(),
                report.obligations_total.minor(),
                report.obligations_unrecorded.minor(),
                report.net_savings.minor(),
                report.unexplained.minor(),
                format_ts(meta.created_at)?,
                meta.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Davr uchun hisobot yozilganmi (audit o'tkazilganmi).
    pub fn exists_for(&self, household_id: &str, period_start: Date) -> Result<bool, StorageError> {
        let found: Option<i64> = self
            .conn
            .query_row(
                "SELECT 1 FROM monthly_reports WHERE household_id = ?1 AND period_start = ?2",
                params![household_id, format_date(period_start)?],
                |row| row.get(0),
            )
            .optional()?;
        Ok(found.is_some())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sana_matni_qaytarilib_oqiladi() {
        let date = Date::from_calendar_date(2026, time::Month::October, 9).expect("sana");
        let text = format_date(date).expect("matn");
        assert_eq!(text, "2026-10-09");
        assert_eq!(parse_date(&text).expect("sana"), date);
    }
}
