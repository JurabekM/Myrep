//! Havas uchun oylik chegara va oilaviy kelishuv (SPEC 2B.3). Chegara **faqat barcha kattalar
//! (`ADULT`) o'z PIN'i bilan rozilik berganda** faol bo'ladi; bir tomonlama chegara kuchga kirmaydi.
//! Chegaraga yaqinlashganda va oshganda yumshoq ogohlantirish bor, bloklash yo'q.
use std::collections::{BTreeSet, HashMap};

use domain::{
    counts_as_havas, effective_necessity, havas_status, Category, Expense, HavasLimit, HavasStatus,
    LimitConsent, Member, Meta,
};
use money::Money;
use storage::{repo, Connection, Database};

use crate::{members, sum_money, Ctx, Env, ServiceError, YearMonth};

#[derive(Debug, Clone)]
pub struct Pending {
    pub limit_id: String,
    pub amount: Money,
    pub consented: Vec<Member>,
    pub missing: Vec<Member>,
}

#[derive(Debug, Clone)]
pub struct Report {
    pub month: YearMonth,
    /// Faol (barcha kattalar rozi bo'lgan) chegara.
    pub limit: Option<Money>,
    /// Hali to'liq kelishilmagan yangi taklif.
    pub pending: Option<Pending>,
    /// Havas hisobiga kirgan jami (sovg'a va sadaqasiz).
    pub spent: Money,
    /// Faqat faol chegara bo'lganda.
    pub status: Option<HavasStatus>,
    /// Obro' uchun belgilangan xarajatlar.
    pub ostentation: Money,
    /// Qarz bilan qilingan havas (qizil bayroq).
    pub debt_funded: Money,
    /// Sadaqa: havas ham, «oqib ketish» ham emas.
    pub charity: Money,
    /// Sovg'a deb belgilangan havas xarajatlari (hisobga kirmagan).
    pub gifts_excluded: Money,
}

fn sorted_limits(conn: &Connection, ctx: &Ctx) -> Result<Vec<HavasLimit>, ServiceError> {
    // UUIDv7 yaratilish tartibida o'sadi.
    Ok(repo::list::<HavasLimit>(conn, &ctx.household_id)?)
}

fn consenters(
    conn: &Connection,
    ctx: &Ctx,
) -> Result<HashMap<String, BTreeSet<String>>, ServiceError> {
    let mut map: HashMap<String, BTreeSet<String>> = HashMap::new();
    for c in repo::list::<LimitConsent>(conn, &ctx.household_id)? {
        map.entry(c.limit_id).or_default().insert(c.member_id);
    }
    Ok(map)
}

fn require_adult(conn: &Connection, ctx: &Ctx, member_id: &str) -> Result<(), ServiceError> {
    if members::adults(conn, ctx)?
        .iter()
        .any(|m| m.meta.id == member_id)
    {
        Ok(())
    } else {
        Err(ServiceError::Invalid(
            "faqat kattalar (ADULT) rozilik bera oladi",
        ))
    }
}

fn add_consent(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    limit_id: &str,
    member_id: &str,
) -> Result<(), ServiceError> {
    let exists = repo::list::<LimitConsent>(db.conn(), &ctx.household_id)?
        .iter()
        .any(|c| c.limit_id == limit_id && c.member_id == member_id);
    if !exists {
        repo::insert(
            db.conn(),
            &LimitConsent {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                limit_id: limit_id.to_owned(),
                member_id: member_id.to_owned(),
                consented_at: env.clock.now(),
            },
        )?;
    }
    Ok(())
}

/// Yangi chegara taklif qiladi. Taklif qiluvchi o'z PIN'ini kiritadi va uning roziligi darrov yoziladi;
/// qolgan kattalar [`consent`] bilan tasdiqlaguncha chegara **faol bo'lmaydi**.
///
/// # Errors
/// Summa yaroqsiz, taklif qiluvchi kattalardan emas yoki PIN noto'g'ri bo'lsa.
pub fn propose(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    proposer: &str,
    pin: &str,
    amount: Money,
) -> Result<HavasLimit, ServiceError> {
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("chegara musbat summa bo'lishi kerak"));
    }
    require_adult(db.conn(), ctx, proposer)?;
    members::verify(db, env, ctx, proposer, pin)?;
    let limit = HavasLimit {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        amount,
        proposed_by: proposer.to_owned(),
    };
    db.transaction::<(), ServiceError>(|tx| {
        repo::insert(tx, &limit)?;
        repo::insert(
            tx,
            &LimitConsent {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                limit_id: limit.meta.id.clone(),
                member_id: proposer.to_owned(),
                consented_at: env.clock.now(),
            },
        )?;
        Ok(())
    })?;
    Ok(limit)
}

/// A'zo o'z PIN'i bilan **eng so'nggi** taklifga rozilik beradi (eskirgan taklifga rozilik rad etiladi).
///
/// # Errors
/// Taklif topilmasa/eskirgan, a'zo kattalardan emas yoki PIN noto'g'ri bo'lsa.
pub fn consent(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    limit_id: &str,
    member_id: &str,
    pin: &str,
) -> Result<(), ServiceError> {
    let limits = sorted_limits(db.conn(), ctx)?;
    let latest = limits.last().ok_or(ServiceError::NotFound)?;
    if latest.meta.id != limit_id {
        return Err(ServiceError::Invalid(
            "bu taklif eskirgan: yangi taklifga rozilik bering",
        ));
    }
    require_adult(db.conn(), ctx, member_id)?;
    members::verify(db, env, ctx, member_id, pin)?;
    add_consent(db, env, ctx, limit_id, member_id)
}

/// Faol chegara va hali kelishilmagan taklif.
///
/// # Errors
/// Baza xatosi.
pub fn effective_and_pending(
    conn: &Connection,
    ctx: &Ctx,
) -> Result<(Option<HavasLimit>, Option<Pending>), ServiceError> {
    let limits = sorted_limits(conn, ctx)?;
    let adults = members::adults(conn, ctx)?;
    let by_limit = consenters(conn, ctx)?;
    let covered = |l: &HavasLimit| {
        by_limit
            .get(&l.meta.id)
            .is_some_and(|set| adults.iter().all(|a| set.contains(&a.meta.id)))
    };
    let effective = limits.iter().rev().find(|l| covered(l)).cloned();
    let pending = limits.last().filter(|l| !covered(l)).map(|l| {
        let set = by_limit.get(&l.meta.id).cloned().unwrap_or_default();
        let (consented, missing) = adults
            .iter()
            .cloned()
            .partition(|a| set.contains(&a.meta.id));
        Pending {
            limit_id: l.meta.id.clone(),
            amount: l.amount,
            consented,
            missing,
        }
    });
    Ok((effective, pending))
}

/// Oylik havas hisoboti.
///
/// # Errors
/// Baza xatosi yoki valyuta mos kelmasa.
pub fn report(conn: &Connection, ctx: &Ctx, ym: YearMonth) -> Result<Report, ServiceError> {
    let cur = ctx.currency;
    let categories: HashMap<String, Category> = repo::list::<Category>(conn, &ctx.household_id)?
        .into_iter()
        .map(|c| (c.meta.id.clone(), c))
        .collect();
    let mut havas = Vec::new();
    let mut ostentation = Vec::new();
    let mut debt = Vec::new();
    let mut charity = Vec::new();
    let mut gifts = Vec::new();
    for e in repo::list::<Expense>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|e| ym.contains(e.spent_on))
    {
        let Some(cat) = categories.get(&e.category_id) else {
            continue;
        };
        let is_gift = e.is_gift == Some(true);
        let nec = effective_necessity(e.necessity, cat.necessity);
        if cat.is_charity {
            charity.push(e.amount);
            continue;
        }
        if e.is_ostentation == Some(true) {
            ostentation.push(e.amount);
        }
        if counts_as_havas(nec, is_gift, cat.is_charity) {
            havas.push(e.amount);
            if e.funded_by_debt == Some(true) {
                debt.push(e.amount);
            }
        } else if is_gift && nec == Some(domain::Necessity::Havas) {
            gifts.push(e.amount);
        }
    }
    let spent = sum_money(cur, havas)?;
    let (effective, pending) = effective_and_pending(conn, ctx)?;
    let status = effective
        .as_ref()
        .map(|l| havas_status(spent, l.amount))
        .transpose()
        .map_err(|_| ServiceError::Invalid("havas holatini hisoblab bo'lmadi"))?;
    Ok(Report {
        month: ym,
        limit: effective.map(|l| l.amount),
        pending,
        spent,
        status,
        ostentation: sum_money(cur, ostentation)?,
        debt_funded: sum_money(cur, debt)?,
        charity: sum_money(cur, charity)?,
        gifts_excluded: sum_money(cur, gifts)?,
    })
}
