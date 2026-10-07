//! «Narx daftari» (SPEC 2C.1) va «Sichqon kemirgani» (SPEC 2C.2): shaxsiy inflyatsiya va xarid
//! qobiliyati. Faqat foydalanuvchi kiritgan narxlar bilan ishlaydi (rasmiy CPI yo'q).
use domain::{
    compute_streak, future_price, personal_inflation, quantity_milli, real_value, BasketLine, Date,
    Meta, PriceItem, PricePoint, StreakSummary,
};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{home::WEEK_ANCHOR, local_date, vault, Ctx, Env, ServiceError};

#[derive(Debug, Clone)]
pub struct ItemView {
    pub item: PriceItem,
    pub first: Option<PricePoint>,
    pub last: Option<PricePoint>,
    pub points: usize,
    /// Birinchi → oxirgi narx o'zgarishi (bp); kamida 2 ta narx bo'lsa.
    pub change_bp: Option<i64>,
}

fn points_of(conn: &Connection, ctx: &Ctx, item_id: &str) -> Result<Vec<PricePoint>, ServiceError> {
    let mut pts: Vec<PricePoint> = repo::list::<PricePoint>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|p| p.item_id == item_id)
        .collect();
    // Sana, so'ng yaratilish tartibi (UUIDv7).
    pts.sort_by(|a, b| (a.observed_on, &a.meta.id).cmp(&(b.observed_on, &b.meta.id)));
    Ok(pts)
}

fn item(conn: &Connection, ctx: &Ctx, id: &str) -> Result<PriceItem, ServiceError> {
    let it = repo::get::<PriceItem>(conn, id)?.ok_or(ServiceError::NotFound)?;
    if it.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    Ok(it)
}

/// # Errors
/// Nom bo'sh/takror, og'irlik 0..=10000 dan tashqari bo'lsa.
pub fn add_item(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    name: &str,
    unit: &str,
    weight_bp: u32,
) -> Result<PriceItem, ServiceError> {
    let (name, unit) = (name.trim(), unit.trim());
    if name.is_empty() || unit.is_empty() {
        return Err(ServiceError::Invalid("mahsulot nomi va birligini yozing"));
    }
    if weight_bp > 10_000 {
        return Err(ServiceError::Invalid("og'irlik 0–100% bo'lishi kerak"));
    }
    if repo::list::<PriceItem>(db.conn(), &ctx.household_id)?
        .iter()
        .any(|i| i.name == name)
    {
        return Err(ServiceError::Invalid("bunday mahsulot allaqachon bor"));
    }
    let it = PriceItem {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: name.to_owned(),
        unit: unit.to_owned(),
        weight_bp,
        active: true,
    };
    repo::insert(db.conn(), &it)?;
    Ok(it)
}

/// # Errors
/// Topilmasa yoki og'irlik noto'g'ri bo'lsa.
pub fn set_item(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    weight_bp: u32,
    active: bool,
) -> Result<(), ServiceError> {
    if weight_bp > 10_000 {
        return Err(ServiceError::Invalid("og'irlik 0–100% bo'lishi kerak"));
    }
    let mut it = item(db.conn(), ctx, id)?;
    it.weight_bp = weight_bp;
    it.active = active;
    repo::update(db.conn(), &it, env.clock.now())?;
    Ok(())
}

/// Mahsulot va uning narxlari o'chiriladi.
///
/// # Errors
/// Topilmasa.
pub fn remove_item(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<(), ServiceError> {
    item(db.conn(), ctx, id)?;
    let now = env.clock.now();
    let pts = points_of(db.conn(), ctx, id)?;
    db.transaction(|tx| {
        for p in pts {
            repo::soft_delete::<PricePoint>(tx, &p.meta.id, now)?;
        }
        repo::soft_delete::<PriceItem>(tx, id, now)?;
        Ok(())
    })
}

/// # Errors
/// Mahsulot topilmasa yoki narx musbat bo'lmasa.
pub fn add_price(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    item_id: &str,
    price: Money,
    observed_on: Option<Date>,
    place: Option<&str>,
) -> Result<PricePoint, ServiceError> {
    item(db.conn(), ctx, item_id)?;
    if price.minor() <= 0 || price.currency() != ctx.currency {
        return Err(ServiceError::Invalid("narx musbat bo'lishi kerak"));
    }
    let place = place.map(str::trim).filter(|p| !p.is_empty());
    let p = PricePoint {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        item_id: item_id.to_owned(),
        price,
        observed_on: observed_on.unwrap_or_else(|| local_date(env.clock.now())),
        place: place.map(str::to_owned),
    };
    repo::insert(db.conn(), &p)?;
    Ok(p)
}

/// # Errors
/// Topilmasa.
pub fn remove_price(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<(), ServiceError> {
    let p = repo::get::<PricePoint>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if p.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    repo::soft_delete::<PricePoint>(db.conn(), id, env.clock.now())?;
    Ok(())
}

/// Mahsulotning narx tarixi (yangi → eski).
///
/// # Errors
/// Topilmasa.
pub fn history(
    conn: &Connection,
    ctx: &Ctx,
    item_id: &str,
) -> Result<Vec<PricePoint>, ServiceError> {
    item(conn, ctx, item_id)?;
    let mut pts = points_of(conn, ctx, item_id)?;
    pts.reverse();
    Ok(pts)
}

fn change_bp(first: &PricePoint, last: &PricePoint) -> Result<i64, ServiceError> {
    let line = BasketLine {
        weight_bp: 1,
        first: first.price,
        last: last.price,
    };
    Ok(personal_inflation(&[line])?.index_bp)
}

/// # Errors
/// Baza xatosi.
pub fn items(conn: &Connection, ctx: &Ctx) -> Result<Vec<ItemView>, ServiceError> {
    repo::list::<PriceItem>(conn, &ctx.household_id)?
        .into_iter()
        .map(|it| {
            let pts = points_of(conn, ctx, &it.meta.id)?;
            let (first, last) = (pts.first().cloned(), pts.last().cloned());
            let change = match (&first, &last) {
                (Some(f), Some(l)) if pts.len() >= 2 => Some(change_bp(f, l)?),
                _ => None,
            };
            Ok(ItemView {
                item: it,
                first,
                last,
                points: pts.len(),
                change_bp: change,
            })
        })
        .collect()
}

#[derive(Debug, Clone)]
pub struct Inflation {
    pub index_bp: i64,
    /// Indeksga kirgan mahsulotlar: (nomi, o'zgarish bp, og'irlik bp).
    pub per_item: Vec<(String, i64, u32)>,
    /// Birinchi va oxirgi kuzatuv orasidagi kunlar.
    pub span_days: i64,
}

/// Shaxsiy inflyatsiya indeksi: faol, og'irligi musbat va kamida 2 ta narxi bor mahsulotlar
/// bo'yicha. Ma'lumot yetmasa — `None`.
///
/// # Errors
/// Baza xatosi yoki hisob sig'masa.
pub fn inflation(conn: &Connection, ctx: &Ctx) -> Result<Option<Inflation>, ServiceError> {
    let mut lines = Vec::new();
    let mut meta = Vec::new();
    let (mut min_d, mut max_d): (Option<Date>, Option<Date>) = (None, None);
    for v in items(conn, ctx)? {
        let (Some(f), Some(l)) = (&v.first, &v.last) else {
            continue;
        };
        if !v.item.active || v.item.weight_bp == 0 || v.points < 2 {
            continue;
        }
        lines.push(BasketLine {
            weight_bp: v.item.weight_bp,
            first: f.price,
            last: l.price,
        });
        meta.push((v.item.name.clone(), v.item.weight_bp));
        min_d = Some(min_d.map_or(f.observed_on, |d| d.min(f.observed_on)));
        max_d = Some(max_d.map_or(l.observed_on, |d| d.max(l.observed_on)));
    }
    if lines.is_empty() {
        return Ok(None);
    }
    let idx = personal_inflation(&lines)?;
    Ok(Some(Inflation {
        index_bp: idx.index_bp,
        per_item: meta
            .into_iter()
            .zip(idx.per_item_bp)
            .map(|((n, w), bp)| (n, bp, w))
            .collect(),
        span_days: match (min_d, max_d) {
            (Some(a), Some(b)) => (b - a).whole_days(),
            _ => 0,
        },
    }))
}

/// Narx kiritish odati: hafta bo'yicha ketma-ketlik (kamida bitta narx kiritilgan hafta).
///
/// # Errors
/// Baza xatosi.
pub fn streak(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<StreakSummary, ServiceError> {
    let dates: Vec<Date> = repo::list::<PricePoint>(conn, &ctx.household_id)?
        .into_iter()
        .map(|p| p.observed_on)
        .collect();
    Ok(compute_streak(
        &dates,
        local_date(env.clock.now()),
        WEEK_ANCHOR,
    ))
}

/// Shu haftada kamida bitta narx kiritilganmi (haftalik eslatma uchun).
///
/// # Errors
/// Baza xatosi.
pub fn logged_this_week(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<bool, ServiceError> {
    let today = local_date(env.clock.now());
    let ws = domain::week_start(today, WEEK_ANCHOR);
    Ok(repo::list::<PricePoint>(conn, &ctx.household_id)?
        .iter()
        .any(|p| p.observed_on >= ws && p.observed_on <= today))
}

#[derive(Debug, Clone)]
pub struct ItemExample {
    pub name: String,
    pub unit: String,
    pub price_today: Money,
    pub price_future: Money,
    /// Bugungi narxda summaga necha birlik (1/1000).
    pub quantity_now_milli: i64,
    pub quantity_future_milli: i64,
}

#[derive(Debug, Clone)]
pub struct Purchasing {
    /// «Kelajagim» nominal balansi.
    pub nominal: Money,
    /// `years` yildan keyin bugungi narxlarda qiymati.
    pub real: Money,
    pub annual_bp: u32,
    pub years: u32,
    pub example: Option<ItemExample>,
}

/// «Sichqon kemirgani»: yotgan jamg'arma `years` yildan keyin qancha tursa, va tanlangan mahsulotdan
/// nechta olinadi. `annual_bp` — foydalanuvchi kiritgan taxminiy yillik narx o'sishi.
///
/// # Errors
/// Mahsulot topilmasa yoki mahsulotda narx bo'lmasa; hisob sig'masa.
pub fn purchasing(
    conn: &Connection,
    ctx: &Ctx,
    annual_bp: u32,
    years: u32,
    item_id: Option<&str>,
) -> Result<Purchasing, ServiceError> {
    if years > 50 || annual_bp > 100_000 {
        return Err(ServiceError::Invalid("yil yoki foiz juda katta"));
    }
    let nominal = vault::balance(conn, ctx)?;
    let real = real_value(nominal, annual_bp, years)?;
    let example = match item_id {
        None => None,
        Some(id) => {
            let it = item(conn, ctx, id)?;
            let last = points_of(conn, ctx, id)?
                .pop()
                .ok_or(ServiceError::Invalid("avval bu mahsulot narxini kiriting"))?;
            let future = future_price(last.price, annual_bp, years)?;
            Some(ItemExample {
                name: it.name,
                unit: it.unit,
                price_today: last.price,
                price_future: future,
                quantity_now_milli: quantity_milli(nominal, last.price)?,
                quantity_future_milli: quantity_milli(nominal, future)?,
            })
        }
    };
    Ok(Purchasing {
        nominal,
        real,
        annual_bp,
        years,
        example,
    })
}
