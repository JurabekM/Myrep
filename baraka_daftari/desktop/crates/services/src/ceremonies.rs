//! Marosim rejalovchisi (SPEC 2D.8): byudjet qatorlari, moliyalash manbalari, qarz bo'lsa oilaviy
//! muhokama, stsenariylarni solishtirish, to'yona o'rniga maqsad va chop etiladigan smeta.
use domain::{
    ceremony_totals, check_ceremony_confirm, line_total, months_to_repay, CeremonyKind,
    CeremonyLine, CeremonyPlan, CeremonyStatus, CeremonyTotals, Date, FundingSource, LineInput,
    Meta,
};
use money::{format_money, Locale, Money};
use storage::Connection;
use storage::{repo, Database};

use crate::{goals, Ctx, Env, ServiceError};

fn name_of(s: &str) -> Result<String, ServiceError> {
    let t = s.split_whitespace().collect::<Vec<_>>().join(" ");
    if t.is_empty() || t.chars().count() > 80 {
        return Err(ServiceError::Invalid("nom 1..80 belgi bo'lishi kerak"));
    }
    Ok(t)
}

#[derive(Debug, Clone)]
pub struct LineView {
    pub line: CeremonyLine,
    pub total: Money,
}

#[derive(Debug, Clone)]
pub struct PlanView {
    pub plan: CeremonyPlan,
    pub lines: Vec<LineView>,
    pub totals: CeremonyTotals,
    /// Hozir tasdiqlab bo'lmasa sababi (`DISCUSSION_REQUIRED` | `DATE_REQUIRED`).
    pub confirm_blocker: Option<&'static str>,
}

fn load_plan(conn: &Connection, ctx: &Ctx, id: &str) -> Result<CeremonyPlan, ServiceError> {
    let p = repo::get::<CeremonyPlan>(conn, id)?.ok_or(ServiceError::NotFound)?;
    if p.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    Ok(p)
}

fn load_line(conn: &Connection, ctx: &Ctx, id: &str) -> Result<CeremonyLine, ServiceError> {
    let l = repo::get::<CeremonyLine>(conn, id)?.ok_or(ServiceError::NotFound)?;
    if l.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    Ok(l)
}

fn view(conn: &Connection, ctx: &Ctx, plan: CeremonyPlan) -> Result<PlanView, ServiceError> {
    let mut lines: Vec<CeremonyLine> = repo::list::<CeremonyLine>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|l| l.plan_id == plan.meta.id)
        .collect();
    lines.sort_by(|a, b| a.meta.id.cmp(&b.meta.id));
    let inputs: Vec<LineInput> = lines
        .iter()
        .map(|l| LineInput {
            qty: l.qty,
            unit_price: l.unit_price,
            funding: l.funding,
        })
        .collect();
    let totals = ceremony_totals(&inputs, ctx.currency)?;
    let confirm_blocker = check_ceremony_confirm(totals.debt, plan.discussed, plan.date.is_some())
        .err()
        .map(|e| e.code());
    let lines = lines
        .into_iter()
        .map(|l| {
            let total = line_total(l.qty, l.unit_price)?;
            Ok(LineView { line: l, total })
        })
        .collect::<Result<Vec<_>, ServiceError>>()?;
    Ok(PlanView {
        plan,
        lines,
        totals,
        confirm_blocker,
    })
}

/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, ctx: &Ctx) -> Result<Vec<PlanView>, ServiceError> {
    repo::list::<CeremonyPlan>(conn, &ctx.household_id)?
        .into_iter()
        .map(|p| view(conn, ctx, p))
        .collect()
}

/// # Errors
/// Topilmasa.
pub fn get(conn: &Connection, ctx: &Ctx, id: &str) -> Result<PlanView, ServiceError> {
    view(conn, ctx, load_plan(conn, ctx, id)?)
}

/// # Errors
/// Nom yaroqsiz bo'lsa.
pub fn create(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    name: &str,
    kind: CeremonyKind,
    date: Option<Date>,
) -> Result<PlanView, ServiceError> {
    let plan = CeremonyPlan {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: name_of(name)?,
        kind,
        date,
        status: CeremonyStatus::Draft,
        discussed: false,
        discussion_note: None,
    };
    repo::insert(db.conn(), &plan)?;
    view(db.conn(), ctx, plan)
}

/// Tasdiqlangan rejaga o'zgartirish kirsa, u qoralamaga qaytadi (qayta tasdiqlash kerak).
fn touch(conn: &Connection, env: &Env<'_>, mut plan: CeremonyPlan) -> Result<(), ServiceError> {
    if plan.status == CeremonyStatus::Confirmed {
        plan.status = CeremonyStatus::Draft;
        repo::update(conn, &plan, env.clock.now())?;
    }
    Ok(())
}

/// # Errors
/// Topilmasa.
pub fn set_date(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    date: Option<Date>,
) -> Result<(), ServiceError> {
    let mut p = load_plan(db.conn(), ctx, id)?;
    p.date = date;
    if p.status == CeremonyStatus::Confirmed && date.is_none() {
        p.status = CeremonyStatus::Draft;
    }
    repo::update(db.conn(), &p, env.clock.now())?;
    Ok(())
}

/// Yangi byudjet qatori.
#[derive(Debug, Clone, Copy)]
pub struct NewLine<'a> {
    pub plan_id: &'a str,
    pub name: &'a str,
    pub qty: u32,
    pub unit_price: Money,
    pub funding: FundingSource,
}

/// Qator qo'shish.
///
/// # Errors
/// Reja topilmasa, nom yoki miqdor/narx yaroqsiz bo'lsa.
pub fn add_line(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewLine<'_>,
) -> Result<(), ServiceError> {
    let plan = load_plan(db.conn(), ctx, new.plan_id)?;
    if new.unit_price.currency() != ctx.currency {
        return Err(ServiceError::Invalid("valyuta mos emas"));
    }
    line_total(new.qty, new.unit_price)?;
    let line = CeremonyLine {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        plan_id: new.plan_id.to_owned(),
        name: name_of(new.name)?,
        qty: new.qty,
        unit_price: new.unit_price,
        funding: new.funding,
    };
    db.transaction::<(), ServiceError>(|tx| {
        repo::insert(tx, &line)?;
        touch(tx, env, plan)
    })
}

/// Qatorni o'zgartirish (miqdor, narx, manba).
///
/// # Errors
/// Topilmasa yoki qiymatlar yaroqsiz bo'lsa.
pub fn update_line(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    line_id: &str,
    qty: u32,
    unit_price: Money,
    funding: FundingSource,
) -> Result<(), ServiceError> {
    let mut l = load_line(db.conn(), ctx, line_id)?;
    if unit_price.currency() != ctx.currency {
        return Err(ServiceError::Invalid("valyuta mos emas"));
    }
    line_total(qty, unit_price)?;
    let plan = load_plan(db.conn(), ctx, &l.plan_id)?;
    l.qty = qty;
    l.unit_price = unit_price;
    l.funding = funding;
    db.transaction::<(), ServiceError>(|tx| {
        repo::update(tx, &l, env.clock.now())?;
        touch(tx, env, plan)
    })
}

/// # Errors
/// Topilmasa.
pub fn remove_line(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    line_id: &str,
) -> Result<(), ServiceError> {
    let l = load_line(db.conn(), ctx, line_id)?;
    let plan = load_plan(db.conn(), ctx, &l.plan_id)?;
    db.transaction::<(), ServiceError>(|tx| {
        repo::soft_delete::<CeremonyLine>(tx, line_id, env.clock.now())?;
        touch(tx, env, plan)
    })
}

/// «Buni qarzsiz qanday o'tkazamiz?» muhokamasi o'tkazilganini qayd etadi (xulosa matni majburiy).
///
/// # Errors
/// Xulosa bo'sh bo'lsa yoki reja topilmasa.
pub fn record_discussion(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    note: &str,
) -> Result<(), ServiceError> {
    let note = note.trim();
    if note.is_empty() {
        return Err(ServiceError::Invalid("muhokama xulosasini yozing"));
    }
    let mut p = load_plan(db.conn(), ctx, id)?;
    p.discussed = true;
    p.discussion_note = Some(note.chars().take(500).collect());
    repo::update(db.conn(), &p, env.clock.now())?;
    Ok(())
}

/// Holatni o'zgartiradi. `CONFIRMED` — sana belgilangan va (qarz bor bo'lsa) muhokama o'tkazilgan bo'lishi shart.
///
/// # Errors
/// Shartlar bajarilmagan bo'lsa ([`ServiceError::Invalid`]).
pub fn set_status(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    status: CeremonyStatus,
) -> Result<(), ServiceError> {
    let v = get(db.conn(), ctx, id)?;
    let mut p = v.plan;
    if status == CeremonyStatus::Confirmed {
        check_ceremony_confirm(v.totals.debt, p.discussed, p.date.is_some()).map_err(|e| {
            ServiceError::Invalid(match e {
                domain::CeremonyError::DiscussionRequired => {
                    "qarz bilan moliyalangan qatorlar bor: avval «Buni qarzsiz qanday o'tkazamiz?» muhokamasini o'tkazing"
                }
                domain::CeremonyError::DateRequired => "tasdiqlash uchun marosim sanasini belgilang",
                _ => "tasdiqlab bo'lmaydi",
            })
        })?;
    }
    p.status = status;
    repo::update(db.conn(), &p, env.clock.now())?;
    Ok(())
}

/// Reja va uning qatorlarini o'chiradi.
///
/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let v = get(db.conn(), ctx, id)?;
    let now = env.clock.now();
    db.transaction::<(), ServiceError>(|tx| {
        for l in &v.lines {
            repo::soft_delete::<CeremonyLine>(tx, &l.line.meta.id, now)?;
        }
        repo::soft_delete::<CeremonyPlan>(tx, id, now)?;
        Ok(())
    })
}

#[derive(Debug, Clone)]
pub struct ScenarioView {
    pub view: PlanView,
    /// Eng qimmat stsenariydan qancha arzon.
    pub cheaper_than_max: Money,
    /// Qarzni oylik imkoniyatga ko'ra qaytarish muddati (oy); qarz yo'q — `Some(0)`; imkoniyat berilmagan
    /// yoki 50 yilda ham sig'masa — `None`.
    pub repay_months: Option<u32>,
    pub repay_too_long: bool,
    /// Shu pulga erishiladigan muqobil maqsadlar (maqsad nomi, necha marta — 1/1000).
    pub alternatives: Vec<goals::Equivalence>,
}

/// 2–3 stsenariyni yonma-yon solishtiradi (umumiy narx, qarz, qaytarish muddati — D10 formulasi bilan,
/// muqobil maqsadlar).
///
/// # Errors
/// Soni 2..=3 bo'lmasa, reja topilmasa yoki hisob sig'masa.
pub fn compare(
    conn: &Connection,
    ctx: &Ctx,
    ids: &[String],
    monthly_capacity: Option<Money>,
    annual_bp: u32,
) -> Result<Vec<ScenarioView>, ServiceError> {
    if !(2..=3).contains(&ids.len()) {
        return Err(ServiceError::Invalid(
            "solishtirish uchun 2 yoki 3 ta stsenariy tanlang",
        ));
    }
    let views = ids
        .iter()
        .map(|id| get(conn, ctx, id))
        .collect::<Result<Vec<_>, _>>()?;
    let max = views
        .iter()
        .map(|v| v.totals.total.minor())
        .max()
        .unwrap_or(0);
    views
        .into_iter()
        .map(|v| {
            let (repay_months, repay_too_long) = match monthly_capacity {
                Some(cap) if v.totals.debt.minor() > 0 => {
                    match months_to_repay(v.totals.debt, annual_bp, cap) {
                        Ok(n) => (Some(n), false),
                        Err(domain::PlanError::InvalidMonths) => (None, true),
                        Err(e) => return Err(e.into()),
                    }
                }
                Some(cap) if cap.minor() > 0 => (Some(0), false),
                _ => (None, false),
            };
            Ok(ScenarioView {
                cheaper_than_max: Money::new(max - v.totals.total.minor(), ctx.currency),
                repay_months,
                repay_too_long,
                alternatives: goals::equivalences(conn, ctx, v.totals.total)?,
                view: v,
            })
        })
        .collect()
}

/// To'yona o'rniga yosh oila uchun maqsadli jamg'arma (`Goal`) ochadi. MVP'da virtual: mehmonlarga
/// ulashiladigan havola keyinroq (hamkor bank bilan).
///
/// # Errors
/// Reja topilmasa yoki maqsad summasi yaroqsiz bo'lsa.
pub fn open_gift_goal(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    plan_id: &str,
    target: Money,
) -> Result<(), ServiceError> {
    let p = load_plan(db.conn(), ctx, plan_id)?;
    goals::add(
        db,
        env,
        ctx,
        &format!("{}: yosh oila jamg'armasi", p.name),
        target,
        p.date,
    )?;
    Ok(())
}

fn funding_label(f: FundingSource) -> &'static str {
    match f {
        FundingSource::Savings => "Jamg'arma",
        FundingSource::Family => "Oila hissasi",
        FundingSource::ExpectedGifts => "Kutilayotgan to'yona",
        FundingSource::Debt => "Qarz",
    }
}

fn kind_label(k: CeremonyKind) -> &'static str {
    match k {
        CeremonyKind::Wedding => "To'y",
        CeremonyKind::Beshik => "Beshik to'y",
        CeremonyKind::Sunnat => "Sunnat to'y",
        CeremonyKind::Maraka => "Ma'raka",
        CeremonyKind::Other => "Marosim",
    }
}

/// Chop etiladigan smeta (PDF).
///
/// # Errors
/// Topilmasa yoki PDF xatosi.
pub fn budget_pdf(conn: &Connection, ctx: &Ctx, id: &str) -> Result<Vec<u8>, ServiceError> {
    let _ = ctx;
    let v = get(conn, ctx, id)?;
    let fm = |m: Money| format_money(m, Locale::Uz);
    let status = match v.plan.status {
        CeremonyStatus::Draft => "Qoralama",
        CeremonyStatus::Confirmed => "Tasdiqlangan",
    };
    let date = v.plan.date.map_or_else(
        || "sana belgilanmagan".to_owned(),
        |d| domain::date_to_string(d).unwrap_or_default(),
    );
    let t = &v.totals;
    let doc = pdf::CeremonyBudgetDoc {
        title: v.plan.name.clone(),
        subtitle: format!("{} · {date} · {status}", kind_label(v.plan.kind)),
        lines: v
            .lines
            .iter()
            .map(|l| pdf::BudgetLine {
                name: l.line.name.clone(),
                qty: l.line.qty.to_string(),
                unit_price: fm(l.line.unit_price),
                total: fm(l.total),
                funding: funding_label(l.line.funding).to_owned(),
            })
            .collect(),
        totals: vec![
            ("Jami".to_owned(), fm(t.total)),
            (funding_label(FundingSource::Savings).to_owned(), fm(t.savings)),
            (funding_label(FundingSource::Family).to_owned(), fm(t.family)),
            (funding_label(FundingSource::ExpectedGifts).to_owned(), fm(t.expected_gifts)),
            (funding_label(FundingSource::Debt).to_owned(), fm(t.debt)),
        ],
        debt_note: (t.debt.minor() > 0).then(|| {
            format!(
                "Diqqat: {} qarz bilan moliyalanadi. Qarz — o'z qo'li bilan taqilgan qog'oz kishan; foizsiz muqobillarni ko'rib chiqing.",
                fm(t.debt)
            )
        }),
        discussion_note: v.plan.discussion_note.clone(),
        disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    };
    pdf::ceremony_budget(&doc).map_err(|_| ServiceError::Invalid("smeta PDF'ini yaratib bo'lmadi"))
}
