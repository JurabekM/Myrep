//! Kategoriyalar, uch toifa (Zarur/Kerak/Havas) va o'zgarishlar tarixi (SPEC 2B.2).
use domain::{Category, MoneyOwner, Necessity, NecessityChange};
use storage::{repo, Connection, Database};

use crate::{Ctx, Env, ServiceError};

/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, ctx: &Ctx) -> Result<Vec<Category>, ServiceError> {
    Ok(repo::list::<Category>(conn, &ctx.household_id)?)
}

fn find(conn: &Connection, ctx: &Ctx, id: &str) -> Result<Category, ServiceError> {
    repo::get::<Category>(conn, id)?
        .filter(|c| c.meta.household_id == ctx.household_id)
        .ok_or(ServiceError::NotFound)
}

/// Yangi kategoriya ma'lumotlari.
#[derive(Debug, Clone)]
pub struct NewCategory {
    pub name: String,
    pub necessity: Option<Necessity>,
    pub owner: Option<MoneyOwner>,
    pub is_charity: bool,
    pub is_habit: bool,
}

/// # Errors
/// Nom bo'sh/takror yoki baza xatosi.
pub fn add(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewCategory,
) -> Result<Category, ServiceError> {
    let name = new.name.trim();
    if name.is_empty() || name.chars().count() > 60 {
        return Err(ServiceError::Invalid("nom 1..60 belgi bo'lishi kerak"));
    }
    if list(db.conn(), ctx)?
        .iter()
        .any(|c| c.name.to_lowercase() == name.to_lowercase())
    {
        return Err(ServiceError::Invalid("bunday kategoriya allaqachon bor"));
    }
    let c = Category {
        meta: domain::Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: name.to_owned(),
        necessity: new.necessity,
        owner: new.owner,
        is_charity: new.is_charity,
        is_habit: new.is_habit,
    };
    repo::insert(db.conn(), &c)?;
    Ok(c)
}

/// Toifani o'zgartiradi va **kim** (`by_member`) hamda qachon o'zgartirgani tarixga yoziladi.
/// Oldingisi bilan bir xil bo'lsa hech narsa qilmaydi.
///
/// # Errors
/// Kategoriya yoki a'zo topilmasa.
pub fn set_necessity(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    category_id: &str,
    necessity: Necessity,
    by_member: &str,
) -> Result<(), ServiceError> {
    if !crate::members::list(db.conn(), ctx)?
        .iter()
        .any(|m| m.meta.id == by_member)
    {
        return Err(ServiceError::NotFound);
    }
    let mut c = find(db.conn(), ctx, category_id)?;
    if c.necessity == Some(necessity) {
        return Ok(());
    }
    let from = c.necessity;
    db.transaction::<(), ServiceError>(|tx| {
        c.necessity = Some(necessity);
        repo::update(tx, &c, env.clock.now())?;
        repo::insert(
            tx,
            &NecessityChange {
                meta: domain::Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                category_id: category_id.to_owned(),
                from,
                to: necessity,
                changed_by: by_member.to_owned(),
            },
        )?;
        Ok(())
    })
}

/// O'zgarishlar tarixi (eski → yangi).
///
/// # Errors
/// Baza xatosi.
pub fn history(
    conn: &Connection,
    ctx: &Ctx,
    category_id: Option<&str>,
) -> Result<Vec<NecessityChange>, ServiceError> {
    Ok(repo::list::<NecessityChange>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|h| category_id.is_none_or(|id| h.category_id == id))
        .collect())
}

/// Odat belgisini qo'yadi/olib tashlaydi (faqat statistika uchun).
///
/// # Errors
/// Kategoriya topilmasa.
pub fn set_habit(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    category_id: &str,
    is_habit: bool,
) -> Result<(), ServiceError> {
    let mut c = find(db.conn(), ctx, category_id)?;
    if c.is_habit != is_habit {
        c.is_habit = is_habit;
        repo::update(db.conn(), &c, env.clock.now())?;
    }
    Ok(())
}

/// Kategoriya ID'si bo'yicha nom bilan topish (xizmatlar uchun).
///
/// # Errors
/// Baza xatosi.
pub fn by_name(conn: &Connection, ctx: &Ctx, name: &str) -> Result<Option<Category>, ServiceError> {
    Ok(list(conn, ctx)?.into_iter().find(|c| c.name == name))
}
