//! «Hunardan ishga» (SPEC 2E.4) va «kafolatlangan foyda» detektori (SPEC 2E.5).
use domain::{
    craft_payback, offer_check, CapitalKind, CraftCapex, CraftIdea, CraftScenario,
    CraftScenarioInput, Meta, OfferAnswers, OfferCheck, PartnershipKind, PartyRole, ReportPeriod,
};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{
    partnerships::{self, NewCapital, NewPartnership, NewParty, PartnershipView},
    sum_money, Ctx, Env, ServiceError,
};

#[derive(Debug, Clone)]
pub struct NewIdea {
    pub name: String,
    pub note: Option<String>,
    /// Boshlang'ich xarajatlar (CAPEX): nom va narx.
    pub capex: Vec<(String, Money)>,
    /// Oylik kirim: `[pessimistik, o'rtacha, optimistik]`.
    pub income: [Money; 3],
    pub expense: [Money; 3],
    pub share_bp: Option<u32>,
}

#[derive(Debug, Clone)]
pub struct IdeaView {
    pub idea: CraftIdea,
    pub capex: Vec<CraftCapex>,
    pub capex_total: Money,
    /// `[pessimistik, o'rtacha, optimistik]`.
    pub scenarios: Vec<CraftScenario>,
}

fn view(conn: &Connection, ctx: &Ctx, idea: CraftIdea) -> Result<IdeaView, ServiceError> {
    let mut capex: Vec<CraftCapex> = repo::list::<CraftCapex>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|c| c.idea_id == idea.meta.id)
        .collect();
    capex.sort_by(|a, b| a.meta.id.cmp(&b.meta.id));
    let capex_total = sum_money(ctx.currency, capex.iter().map(|c| c.price))?;
    let inputs: Vec<CraftScenarioInput> = (0..3)
        .map(|i| CraftScenarioInput {
            income: idea.income[i],
            expense: idea.expense[i],
        })
        .collect();
    let scenarios = craft_payback(capex_total, &inputs, idea.share_bp)?;
    Ok(IdeaView {
        idea,
        capex,
        capex_total,
        scenarios,
    })
}

/// # Errors
/// Nom bo'sh, summalar manfiy/valyuta mos emas yoki ulush > 100%.
pub fn add_idea(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewIdea,
) -> Result<IdeaView, ServiceError> {
    let name = new.name.split_whitespace().collect::<Vec<_>>().join(" ");
    if name.is_empty() || name.chars().count() > 80 {
        return Err(ServiceError::Invalid("g'oya nomini yozing"));
    }
    let all = new.income.iter().chain(new.expense.iter());
    if all
        .clone()
        .any(|m| m.minor() < 0 || m.currency() != ctx.currency)
        || new
            .capex
            .iter()
            .any(|(_, p)| p.minor() < 0 || p.currency() != ctx.currency)
    {
        return Err(ServiceError::Invalid("summalar manfiy bo'lmasin"));
    }
    if new.share_bp.is_some_and(|s| s > 10_000) {
        return Err(ServiceError::Invalid("ulush 0–100% bo'lsin"));
    }
    let idea = CraftIdea {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name,
        note: new
            .note
            .map(|n| n.trim().to_owned())
            .filter(|n| !n.is_empty()),
        income: new.income,
        expense: new.expense,
        share_bp: new.share_bp,
    };
    db.transaction::<(), ServiceError>(|tx| {
        repo::insert(tx, &idea)?;
        for (item, price) in &new.capex {
            let item = item.trim();
            if item.is_empty() {
                return Err(ServiceError::Invalid("xarajat qatoriga nom bering"));
            }
            repo::insert(
                tx,
                &CraftCapex {
                    meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                    idea_id: idea.meta.id.clone(),
                    item: item.to_owned(),
                    price: *price,
                },
            )?;
        }
        Ok(())
    })?;
    view(db.conn(), ctx, idea)
}

/// # Errors
/// Baza xatosi.
pub fn list_ideas(conn: &Connection, ctx: &Ctx) -> Result<Vec<IdeaView>, ServiceError> {
    repo::list::<CraftIdea>(conn, &ctx.household_id)?
        .into_iter()
        .map(|i| view(conn, ctx, i))
        .collect()
}

/// # Errors
/// Topilmasa.
pub fn remove_idea(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<(), ServiceError> {
    let v = view(
        db.conn(),
        ctx,
        repo::get::<CraftIdea>(db.conn(), id)?
            .filter(|i| i.meta.household_id == ctx.household_id)
            .ok_or(ServiceError::NotFound)?,
    )?;
    let now = env.clock.now();
    db.transaction::<(), ServiceError>(|tx| {
        for c in &v.capex {
            repo::soft_delete::<CraftCapex>(tx, &c.meta.id, now)?;
        }
        repo::soft_delete::<CraftIdea>(tx, id, now)?;
        Ok(())
    })
}

/// Bir bosishda sheriklik shartnomasi **qoralamasi** (mudaraba): kapital egasi tashqi tomon —
/// CAPEX uskunalari uning kapitali; hunarmand — xonadonning asosiy a'zosi (mehnat). Foyda ulushi:
/// g'oyadagi ulush (hunarmandniki), qolgani kapital egasiniki. Matnlar tahrirlanishi kerak.
///
/// # Errors
/// G'oya topilmasa, CAPEX bo'sh (kapital 0) yoki shartnoma yaroqsiz bo'lsa.
pub fn idea_to_contract_draft(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    idea_id: &str,
    provider_name: &str,
) -> Result<PartnershipView, ServiceError> {
    let idea = repo::get::<CraftIdea>(db.conn(), idea_id)?
        .filter(|i| i.meta.household_id == ctx.household_id)
        .ok_or(ServiceError::NotFound)?;
    let v = view(db.conn(), ctx, idea)?;
    if v.capex_total.minor() <= 0 {
        return Err(ServiceError::Invalid(
            "shartnoma uchun kamida bitta uskuna/xarajat (CAPEX) kiriting",
        ));
    }
    let worker_bp = v.idea.share_bp.unwrap_or(6_000);
    let capital: Vec<NewCapital> = v
        .capex
        .iter()
        .map(|c| NewCapital {
            description: c.item.clone(),
            kind: CapitalKind::Equipment,
            value: c.price,
        })
        .collect();
    partnerships::create(
        db,
        env,
        ctx,
        NewPartnership {
            details: Default::default(),
            name: v.idea.name.clone(),
            kind: PartnershipKind::Mudaraba,
            term_months: 12,
            report_period: ReportPeriod::Monthly,
            end_clause: "Muddat tugagach uskunalar kapital egasiga qaytariladi yoki tomonlar kelishuvi bilan uzaytiriladi (tahrirlang).".into(),
            dispute_clause: "Nizolar avval tomonlar o'rtasida, so'ng ishonchli oqsoqol huzurida hal qilinadi (tahrirlang).".into(),
            witnesses: vec![],
            parties: vec![
                NewParty {
                    name: provider_name.to_owned(),
                    role: PartyRole::CapitalProvider,
                    share_bp: 10_000 - worker_bp,
                    member_id: None,
                    capital,
                    fixed_return: None,
                },
                NewParty {
                    name: "Hunarmand".into(),
                    role: PartyRole::Worker,
                    share_bp: worker_bp,
                    member_id: Some(ctx.member_id.clone()),
                    capital: vec![],
                    fixed_return: None,
                },
            ],
        },
    )
}

/// Taklifni tekshiruv ro'yxati bo'yicha baholaydi (saqlanmaydi).
#[must_use]
pub fn check_offer(answers: OfferAnswers) -> OfferCheck {
    offer_check(answers)
}
