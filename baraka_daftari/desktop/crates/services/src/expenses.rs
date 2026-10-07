//! Xarajatlarni yozish: yakka va «Hafta varag'i» (ommaviy) rejimida.
use domain::{Category, Date, Expense, Meta, Necessity, PaymentChannel};
use money::Money;
use storage::{repo, Connection, Database};

use crate::{local_date, Ctx, Env, ServiceError};

#[derive(Debug, Clone)]
pub struct NewExpense {
    pub date: Date,
    pub category_id: String,
    pub amount: Money,
    pub channel: PaymentChannel,
    pub note: Option<String>,
    /// `None` — kategoriyaning toifasi qo'llanadi.
    pub necessity: Option<Necessity>,
    /// Sovg'a: «siz olib kelsangiz hisobga kirmaydi» (havas hisobiga kirmaydi).
    pub is_gift: bool,
    /// Obro' uchun qilingan xarajat (isrof tahlilida alohida ko'rsatiladi).
    pub is_ostentation: bool,
    /// Qarz bilan qilingan xarajat: havas bo'lsa qizil bayroq.
    pub funded_by_debt: bool,
    pub member_id: Option<String>,
}

/// Hafta varag'idagi barcha qatorni **bitta** tranzaksiyada yozadi: bittasi xato bo'lsa hech biri yozilmaydi.
///
/// # Errors
/// Bo'sh ro'yxat, summa/sana/kategoriya/a'zo yaroqsiz bo'lsa.
pub fn add_many(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    items: Vec<NewExpense>,
) -> Result<usize, ServiceError> {
    if items.is_empty() {
        return Err(ServiceError::Invalid("kamida bitta xarajat kiriting"));
    }
    let today = local_date(env.clock.now());
    let categories = repo::list::<Category>(db.conn(), &ctx.household_id)?;
    let members = crate::members::list(db.conn(), ctx)?;
    for it in &items {
        if it.amount.minor() <= 0 || it.amount.currency() != ctx.currency {
            return Err(ServiceError::Invalid(
                "xarajat summasi musbat bo'lishi kerak",
            ));
        }
        if it.date > today {
            return Err(ServiceError::Invalid(
                "kelajak sanasiga xarajat yozib bo'lmaydi",
            ));
        }
        if !categories.iter().any(|c| c.meta.id == it.category_id) {
            return Err(ServiceError::NotFound);
        }
        if it
            .member_id
            .as_ref()
            .is_some_and(|m| !members.iter().any(|x| &x.meta.id == m))
        {
            return Err(ServiceError::NotFound);
        }
        if it.note.as_ref().is_some_and(|n| n.chars().count() > 120) {
            return Err(ServiceError::Invalid("izoh 120 belgigacha"));
        }
    }
    let count = items.len();
    db.transaction::<(), ServiceError>(|tx| {
        for it in items {
            repo::insert(
                tx,
                &Expense {
                    meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                    member_id: it.member_id.unwrap_or_else(|| ctx.member_id.clone()),
                    category_id: it.category_id,
                    amount: it.amount,
                    spent_on: it.date,
                    payment_channel: it.channel,
                    necessity: it.necessity,
                    envelope_id: None,
                    is_gift: Some(it.is_gift),
                    is_ostentation: Some(it.is_ostentation),
                    funded_by_debt: Some(it.funded_by_debt),
                    audit_month: None,
                    note: it
                        .note
                        .map(|n| n.trim().to_owned())
                        .filter(|n| !n.is_empty()),
                },
            )?;
        }
        Ok(())
    })?;
    Ok(count)
}

/// `from..=to` oralig'idagi xarajatlar (yangi → eski).
///
/// # Errors
/// Baza xatosi.
pub fn list_range(
    conn: &Connection,
    ctx: &Ctx,
    from: Date,
    to: Date,
) -> Result<Vec<Expense>, ServiceError> {
    let mut items: Vec<Expense> = repo::list::<Expense>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|e| e.spent_on >= from && e.spent_on <= to)
        .collect();
    items.sort_by(|a, b| (b.spent_on, &b.meta.id).cmp(&(a.spent_on, &a.meta.id)));
    Ok(items)
}

/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let e = repo::get::<Expense>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if e.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    repo::soft_delete::<Expense>(db.conn(), id, env.clock.now())?;
    Ok(())
}

/// Shu izoh bilan oxirgi yozilgan xarajatning kategoriyasi («somsa» → Gazak va ichimlik).
///
/// # Errors
/// Baza xatosi.
pub fn suggest_category(
    conn: &Connection,
    ctx: &Ctx,
    note: &str,
) -> Result<Option<String>, ServiceError> {
    let needle = note.trim().to_lowercase();
    if needle.is_empty() {
        return Ok(None);
    }
    Ok(repo::list::<Expense>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|e| e.note.as_ref().is_some_and(|n| n.to_lowercase() == needle))
        .max_by(|a, b| (a.spent_on, &a.meta.id).cmp(&(b.spent_on, &b.meta.id)))
        .map(|e| e.category_id))
}
