//! `.baraka` eksport/import xizmati (DESKTOP_PROMPT 6.3): hujjat (`storage::interchange`) +
//! shifrlangan konteyner (`security::container`). Import avval **oldindan ko'rish** (tranzaksiya
//! orqaga qaytariladi), foydalanuvchi ziddiyatlarni ko'rgach tasdiqlaydi; qo'llash — yagona tranzaksiya.

use domain::OffsetDateTime;
use security::{container, KdfParams, SecurityError};
use storage::{
    interchange::{self, ExportDoc},
    Database,
};

use crate::{learning, Ctx, Env, ServiceError};

pub use storage::interchange::{Conflict, ConflictKind, ImportReport, Resolution};

const KEY_LAST_EXPORT: &str = "interchange.last_export";

fn map_sec(e: SecurityError) -> ServiceError {
    match e {
        SecurityError::WrongPassword => ServiceError::WrongPassword,
        SecurityError::WeakPassword => ServiceError::WeakPassword,
        SecurityError::Corrupt(m) => ServiceError::BadFile(m),
        _ => ServiceError::BadFile("shifrlashda xato".into()),
    }
}

fn apply_err(e: storage::StorageError) -> ServiceError {
    match e {
        storage::StorageError::Corrupt(m) => ServiceError::BadFile(m),
        other => ServiceError::Storage(other),
    }
}

fn bad(e: impl ToString) -> ServiceError {
    ServiceError::BadFile(e.to_string())
}

/// Oxirgi muvaffaqiyatli eksport vaqti (inkremental eksport uchun).
///
/// # Errors
/// Baza xatosi.
pub fn last_export(db: &Database, ctx: &Ctx) -> Result<Option<OffsetDateTime>, ServiceError> {
    Ok(learning::setting(db.conn(), ctx, KEY_LAST_EXPORT)?
        .and_then(|s| domain::ts_from_str(&s.value).ok()))
}

/// Eksport muvaffaqiyatli saqlangach chaqiriladi.
///
/// # Errors
/// Baza yoki format xatosi.
pub fn mark_exported(db: &Database, env: &Env<'_>, ctx: &Ctx) -> Result<(), ServiceError> {
    let now = domain::ts_to_string(env.clock.now()).map_err(bad)?;
    learning::put_setting(db.conn(), env, ctx, KEY_LAST_EXPORT, &now)
}

/// Shifrlangan `.baraka` baytlari. `incremental` bo'lsa faqat oxirgi eksportdan keyingi o'zgarishlar
/// (oldin eksport bo'lmagan bo'lsa to'liq).
///
/// # Errors
/// Parol qisqa, baza yoki kriptografiya xatosi.
pub fn export_bytes(
    db: &Database,
    env: &Env<'_>,
    ctx: &Ctx,
    password: &str,
    incremental: bool,
    kdf: KdfParams,
) -> Result<Vec<u8>, ServiceError> {
    let since = if incremental {
        last_export(db, ctx)?
    } else {
        None
    };
    let doc = interchange::export(
        db.conn(),
        &ctx.household_id,
        env.device_id,
        env.clock.now(),
        since,
    )?;
    let json = serde_json::to_vec(&doc).map_err(bad)?;
    container::seal(&json, password, kdf).map_err(map_sec)
}

fn decode(bytes: &[u8], password: &str) -> Result<ExportDoc, ServiceError> {
    let plain = container::open(bytes, password).map_err(map_sec)?;
    serde_json::from_slice(&plain)
        .map_err(|_| ServiceError::BadFile("JSON tuzilmasi noto'g'ri".into()))
}

/// Ziddiyatlar ro'yxati — hech narsa saqlanmaydi.
///
/// # Errors
/// Parol noto'g'ri, fayl yaroqsiz yoki baza xatosi.
pub fn preview(
    db: &Database,
    ctx: &Ctx,
    bytes: &[u8],
    password: &str,
) -> Result<ImportReport, ServiceError> {
    let doc = decode(bytes, password)?;
    let conn = db.conn();
    conn.execute_batch("SAVEPOINT imp_preview")
        .map_err(storage::StorageError::from)?;
    let res = interchange::apply(conn, &doc, Some(&ctx.household_id));
    conn.execute_batch("ROLLBACK TO imp_preview; RELEASE imp_preview")
        .map_err(storage::StorageError::from)?;
    res.map_err(apply_err)
}

/// Birlashtirishni qo'llaydi (yagona tranzaksiya; xatoda hech narsa o'zgarmaydi).
///
/// # Errors
/// Parol noto'g'ri, fayl yaroqsiz yoki baza xatosi.
pub fn import(
    db: &mut Database,
    ctx: &Ctx,
    bytes: &[u8],
    password: &str,
) -> Result<ImportReport, ServiceError> {
    let doc = decode(bytes, password)?;
    db.transaction::<ImportReport, ServiceError>(|tx| {
        interchange::apply(tx, &doc, Some(&ctx.household_id)).map_err(apply_err)
    })
}

/// Bo'sh bazaga (xonadonsiz) import: hujjatdagi xonadon qabul qilinadi. Faqat testlar va
/// «yangi qurilmaga ko'chirish» uchun.
///
/// # Errors
/// Import xatolari.
pub fn import_into_empty(
    db: &mut Database,
    bytes: &[u8],
    password: &str,
) -> Result<ImportReport, ServiceError> {
    let doc = decode(bytes, password)?;
    db.transaction::<ImportReport, ServiceError>(|tx| {
        interchange::apply(tx, &doc, None).map_err(apply_err)
    })
}
