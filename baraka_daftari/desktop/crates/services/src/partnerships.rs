//! Sheriklik: shartnoma ustasi, versiyalash, tasdiqlar, buyout (SPEC 2E.1, 2E.2, 2E.6).
//!
//! - Shartnomasiz sheriklik yo'q: yozuv shartnoma bilan birga yaratiladi.
//! - Shartlar o'zgarsa versiya oshadi, tasdiqlar qayta so'raladi.
//! - Kapital **kiritish** tayyorgarlik darvozasiga bo'ysunadi; kapital **qabul qilish** — yo'q, lekin
//!   barcha kattalarning oilaviy roziligi (PIN bilan) talab qilinadi.
//! - Ilova pul harakatini bajarmaydi va sheriklarni topishtirmaydi: faqat o'zaro tanish tomonlar kelishuvini yozadi.
use domain::{
    add_months, buyout_schedule, distribute, equal_buyout_payments, validate_parties,
    BuyoutPayment, BuyoutPlan, BuyoutSchedule, CapitalKind, Date, MemberRole, Meta, Outcome,
    Partnership, PartnershipCapital, PartnershipKind, PartnershipParty, PartnershipSignature,
    PartnershipStatus, PartnershipVersion, PartyInput, PartyRole, ReportPeriod, SignatureKind,
};
use money::{format_money, Locale, Money};
use storage::Connection;
use storage::{repo, Database};

use crate::{guard, local_date, members, sum_money, Ctx, Env, ServiceError};

#[derive(Debug, Clone)]
pub struct NewCapital {
    pub description: String,
    pub kind: CapitalKind,
    pub value: Money,
}

#[derive(Debug, Clone)]
pub struct NewParty {
    pub name: String,
    pub role: PartyRole,
    pub share_bp: u32,
    /// Xonadon a'zosi bo'lsa.
    pub member_id: Option<String>,
    pub capital: Vec<NewCapital>,
    /// Kapital egasiga qat'iy summa / kafolatlangan daromad: kiritishga urinish **rad etiladi**.
    pub fixed_return: Option<Money>,
}

#[derive(Debug, Clone)]
pub struct NewPartnership {
    pub name: String,
    pub kind: PartnershipKind,
    pub term_months: u32,
    pub report_period: ReportPeriod,
    pub end_clause: String,
    pub dispute_clause: String,
    pub witnesses: Vec<String>,
    pub parties: Vec<NewParty>,
}

fn clean(s: &str, max: usize) -> String {
    s.split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .chars()
        .take(max)
        .collect()
}

fn party_capital(p: &NewParty, ctx: &Ctx) -> Result<Money, ServiceError> {
    for c in &p.capital {
        if c.value.minor() < 0 || c.value.currency() != ctx.currency {
            return Err(ServiceError::Invalid("kapital qiymati manfiy bo'lmasin"));
        }
    }
    Ok(sum_money(ctx.currency, p.capital.iter().map(|c| c.value))?)
}

fn validate(conn: &Connection, ctx: &Ctx, new: &NewPartnership) -> Result<(), ServiceError> {
    if clean(&new.name, 80).is_empty() {
        return Err(ServiceError::Invalid("sheriklik nomini yozing"));
    }
    if !(1..=120).contains(&new.term_months) {
        return Err(ServiceError::Invalid("muddat 1 dan 120 oygacha bo'lsin"));
    }
    if clean(&new.end_clause, 500).is_empty() || clean(&new.dispute_clause, 500).is_empty() {
        return Err(ServiceError::Invalid(
            "muddat tugagandagi tartib va nizo tartibini yozing",
        ));
    }
    if new.witnesses.len() > 4 {
        return Err(ServiceError::Invalid("guvohlar 4 tadan oshmasin"));
    }
    if !(2..=6).contains(&new.parties.len()) {
        return Err(ServiceError::Invalid("tomonlar 2 dan 6 gacha bo'lsin"));
    }
    if new.parties.iter().any(|p| p.fixed_return.is_some()) {
        return Err(domain::PartnershipError::GuaranteedReturnForbidden.into());
    }
    let household = members::list(conn, ctx)?;
    let mut seen_members = Vec::new();
    let mut inputs = Vec::new();
    for p in &new.parties {
        if clean(&p.name, 60).is_empty() {
            return Err(ServiceError::Invalid("tomon ismini yozing"));
        }
        if let Some(m) = &p.member_id {
            if !household.iter().any(|h| &h.meta.id == m) {
                return Err(ServiceError::NotFound);
            }
            if seen_members.contains(m) {
                return Err(ServiceError::Invalid("bir a'zo ikki marta kiritilgan"));
            }
            seen_members.push(m.clone());
        }
        inputs.push(PartyInput {
            role: p.role,
            capital: party_capital(p, ctx)?,
            share_bp: p.share_bp,
        });
    }
    validate_parties(new.kind, &inputs)?;
    Ok(())
}

/// Bazis punkt → «50%» / «33,33%» (butun son arifmetikasi).
fn percent_text(bp: u32) -> String {
    let (whole, frac) = (bp / 100, bp % 100);
    match frac {
        0 => format!("{whole}%"),
        f if f % 10 == 0 => format!("{whole},{}%", f / 10),
        f => format!("{whole},{f:02}%"),
    }
}

fn kind_text(k: PartnershipKind) -> &'static str {
    match k {
        PartnershipKind::Mudaraba => "Mudaraba (bir tomon kapital, ikkinchisi mehnat)",
        PartnershipKind::Musharaka => "Musharaka (ikkala tomon kapital kiritadi)",
    }
}

fn role_text(r: PartyRole) -> &'static str {
    match r {
        PartyRole::CapitalProvider => "Kapital egasi",
        PartyRole::Worker => "Ishchi (mehnat)",
        PartyRole::Partner => "Sherik",
    }
}

fn snapshot(new: &NewPartnership, version: u32) -> String {
    let fm = |m: Money| format_money(m, Locale::Uz);
    let mut s = format!(
        "{} · {} · {} oy · hisobot: {:?} · {version}-versiya\n",
        new.name,
        kind_text(new.kind),
        new.term_months,
        new.report_period
    );
    for p in &new.parties {
        let cap = sum_money(
            new.parties
                .first()
                .and_then(|f| f.capital.first())
                .map_or(money::Currency::Uzs, |c| c.value.currency()),
            p.capital.iter().map(|c| c.value),
        )
        .map_or_else(|_| "?".to_owned(), fm);
        s.push_str(&format!(
            "- {} ({}): ulush {} bp, kapital {cap}\n",
            p.name,
            role_text(p.role),
            p.share_bp
        ));
        for c in &p.capital {
            s.push_str(&format!("    · {} — {}\n", c.description, fm(c.value)));
        }
    }
    s.push_str(&format!(
        "Tugaganda: {}\nNizo: {}\nGuvohlar: {}\n",
        new.end_clause,
        new.dispute_clause,
        new.witnesses.join(", ")
    ));
    s
}

fn insert_content(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    pid: &str,
    new: &NewPartnership,
) -> Result<(), ServiceError> {
    for p in &new.parties {
        let party = PartnershipParty {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            partnership_id: pid.to_owned(),
            name: clean(&p.name, 60),
            role: p.role,
            share_bp: p.share_bp,
            member_id: p.member_id.clone(),
        };
        repo::insert(conn, &party)?;
        for c in &p.capital {
            let desc = clean(&c.description, 80);
            if desc.is_empty() {
                return Err(ServiceError::Invalid("kapital qatoriga nom bering"));
            }
            repo::insert(
                conn,
                &PartnershipCapital {
                    meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                    partnership_id: pid.to_owned(),
                    party_id: party.meta.id.clone(),
                    description: desc,
                    kind: c.kind,
                    value: c.value,
                },
            )?;
        }
    }
    Ok(())
}

fn witnesses_of(new: &NewPartnership) -> Vec<String> {
    new.witnesses
        .iter()
        .map(|w| clean(w, 60))
        .filter(|w| !w.is_empty())
        .collect()
}

/// Shartnoma bilan birga sheriklikni yaratadi (1-versiya, qoralama).
///
/// # Errors
/// Shartnoma yaroqsiz bo'lsa (kafolatli daromad, ulushlar, rollar, bo'sh maydonlar).
pub fn create(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewPartnership,
) -> Result<PartnershipView, ServiceError> {
    validate(db.conn(), ctx, &new)?;
    let p = Partnership {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: clean(&new.name, 80),
        kind: new.kind,
        term_months: new.term_months,
        report_period: new.report_period,
        end_clause: clean(&new.end_clause, 500),
        dispute_clause: clean(&new.dispute_clause, 500),
        witnesses: witnesses_of(&new),
        version: 1,
        status: PartnershipStatus::Draft,
    };
    db.transaction::<(), ServiceError>(|tx| {
        repo::insert(tx, &p)?;
        insert_content(tx, env, ctx, &p.meta.id, &new)?;
        repo::insert(
            tx,
            &PartnershipVersion {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                partnership_id: p.meta.id.clone(),
                version: 1,
                snapshot: snapshot(&new, 1),
            },
        )?;
        Ok(())
    })?;
    view(db.conn(), env, ctx, &p.meta.id)
}

fn load(conn: &Connection, ctx: &Ctx, id: &str) -> Result<Partnership, ServiceError> {
    let p = repo::get::<Partnership>(conn, id)?.ok_or(ServiceError::NotFound)?;
    if p.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    Ok(p)
}

fn parties_of(
    conn: &Connection,
    ctx: &Ctx,
    pid: &str,
) -> Result<Vec<PartnershipParty>, ServiceError> {
    let mut v: Vec<PartnershipParty> = repo::list::<PartnershipParty>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|p| p.partnership_id == pid)
        .collect();
    v.sort_by(|a, b| a.meta.id.cmp(&b.meta.id));
    Ok(v)
}

fn capital_of(
    conn: &Connection,
    ctx: &Ctx,
    pid: &str,
) -> Result<Vec<PartnershipCapital>, ServiceError> {
    let mut v: Vec<PartnershipCapital> = repo::list::<PartnershipCapital>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|c| c.partnership_id == pid)
        .collect();
    v.sort_by(|a, b| a.meta.id.cmp(&b.meta.id));
    Ok(v)
}

/// Shartnomani o'zgartiradi: versiya oshadi, avvalgi tasdiqlar kuchsiz, faol sheriklik qoralamaga qaytadi
/// (qayta tasdiqlash kerak).
///
/// # Errors
/// Tugagan sheriklik yoki yaroqsiz shartnoma.
pub fn revise(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    new: NewPartnership,
) -> Result<PartnershipView, ServiceError> {
    let mut p = load(db.conn(), ctx, id)?;
    if p.status == PartnershipStatus::Ended {
        return Err(ServiceError::Invalid(
            "tugagan sheriklikni o'zgartirib bo'lmaydi",
        ));
    }
    validate(db.conn(), ctx, &new)?;
    let old_parties = parties_of(db.conn(), ctx, id)?;
    let old_capital = capital_of(db.conn(), ctx, id)?;
    let now = env.clock.now();
    p.name = clean(&new.name, 80);
    p.kind = new.kind;
    p.term_months = new.term_months;
    p.report_period = new.report_period;
    p.end_clause = clean(&new.end_clause, 500);
    p.dispute_clause = clean(&new.dispute_clause, 500);
    p.witnesses = witnesses_of(&new);
    p.version += 1;
    p.status = PartnershipStatus::Draft;
    db.transaction::<(), ServiceError>(|tx| {
        for c in &old_capital {
            repo::soft_delete::<PartnershipCapital>(tx, &c.meta.id, now)?;
        }
        for o in &old_parties {
            repo::soft_delete::<PartnershipParty>(tx, &o.meta.id, now)?;
        }
        repo::update(tx, &p, now)?;
        insert_content(tx, env, ctx, id, &new)?;
        repo::insert(
            tx,
            &PartnershipVersion {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                partnership_id: id.to_owned(),
                version: p.version,
                snapshot: snapshot(&new, p.version),
            },
        )?;
        Ok(())
    })?;
    view(db.conn(), env, ctx, id)
}

#[derive(Debug, Clone)]
pub struct PartyView {
    pub party: PartnershipParty,
    pub capital: Vec<PartnershipCapital>,
    pub capital_total: Money,
    /// Joriy versiyaga tasdiqlagan.
    pub signed: bool,
}

#[derive(Debug, Clone)]
pub struct WitnessView {
    pub name: String,
    pub signed: bool,
}

#[derive(Debug, Clone)]
pub struct ConsentView {
    pub member_id: String,
    pub name: String,
    pub consented: bool,
}

#[derive(Debug, Clone)]
pub struct PartnershipView {
    pub partnership: Partnership,
    pub parties: Vec<PartyView>,
    pub witnesses: Vec<WitnessView>,
    pub total_capital: Money,
    /// Xonadon a'zosi kapital **kiritadi** (darvozaga bo'ysunadi).
    pub self_provides_capital: bool,
    /// Xonadon a'zosi kapital **qabul qiladi** (oilaviy rozilik kerak).
    pub self_receives_capital: bool,
    pub consents: Vec<ConsentView>,
    pub versions: Vec<PartnershipVersion>,
    /// Faollashtirishga to'sqinlik: `PARTY_SIGNATURES` | `WITNESS_SIGNATURES` | `FAMILY_CONSENT` | `GATE_CLOSED`.
    pub blocker: Option<&'static str>,
}

fn sigs_for(
    conn: &Connection,
    ctx: &Ctx,
    p: &Partnership,
) -> Result<Vec<PartnershipSignature>, ServiceError> {
    Ok(repo::list::<PartnershipSignature>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|s| s.partnership_id == p.meta.id && s.version == p.version)
        .collect())
}

/// # Errors
/// Topilmasa yoki baza xatosi.
pub fn view(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<PartnershipView, ServiceError> {
    let p = load(conn, ctx, id)?;
    let sigs = sigs_for(conn, ctx, &p)?;
    let caps = capital_of(conn, ctx, id)?;
    let parties = parties_of(conn, ctx, id)?
        .into_iter()
        .map(|party| {
            let capital: Vec<PartnershipCapital> = caps
                .iter()
                .filter(|c| c.party_id == party.meta.id)
                .cloned()
                .collect();
            let capital_total = sum_money(ctx.currency, capital.iter().map(|c| c.value))?;
            let signed = sigs
                .iter()
                .any(|s| s.kind == SignatureKind::Party && s.signer == party.meta.id);
            Ok(PartyView {
                party,
                capital,
                capital_total,
                signed,
            })
        })
        .collect::<Result<Vec<_>, ServiceError>>()?;
    let witnesses: Vec<WitnessView> = p
        .witnesses
        .iter()
        .map(|w| WitnessView {
            name: w.clone(),
            signed: sigs
                .iter()
                .any(|s| s.kind == SignatureKind::Witness && &s.signer == w),
        })
        .collect();
    let total_capital = sum_money(ctx.currency, parties.iter().map(|x| x.capital_total))?;
    let self_provides_capital = parties.iter().any(|x| {
        x.party.member_id.is_some()
            && x.party.role != PartyRole::Worker
            && x.capital_total.minor() > 0
    });
    let self_receives_capital = parties
        .iter()
        .any(|x| x.party.member_id.is_some() && x.party.role == PartyRole::Worker);
    let consents: Vec<ConsentView> = if self_receives_capital {
        members::adults(conn, ctx)?
            .into_iter()
            .map(|m| ConsentView {
                consented: sigs
                    .iter()
                    .any(|s| s.kind == SignatureKind::FamilyConsent && s.signer == m.meta.id),
                member_id: m.meta.id,
                name: m.display_name,
            })
            .collect()
    } else {
        Vec::new()
    };
    let mut versions: Vec<PartnershipVersion> =
        repo::list::<PartnershipVersion>(conn, &ctx.household_id)?
            .into_iter()
            .filter(|v| v.partnership_id == id)
            .collect();
    versions.sort_by_key(|v| v.version);
    let blocker = if parties.iter().any(|x| !x.signed) {
        Some("PARTY_SIGNATURES")
    } else if witnesses.iter().any(|w| !w.signed) {
        Some("WITNESS_SIGNATURES")
    } else if consents.iter().any(|c| !c.consented) {
        Some("FAMILY_CONSENT")
    } else if self_provides_capital && !guard::gate(conn, env, ctx)?.open {
        Some("GATE_CLOSED")
    } else {
        None
    };
    Ok(PartnershipView {
        partnership: p,
        parties,
        witnesses,
        total_capital,
        self_provides_capital,
        self_receives_capital,
        consents,
        versions,
        blocker,
    })
}

/// # Errors
/// Baza xatosi.
pub fn list(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
) -> Result<Vec<PartnershipView>, ServiceError> {
    repo::list::<Partnership>(conn, &ctx.household_id)?
        .into_iter()
        .map(|p| view(conn, env, ctx, &p.meta.id))
        .collect()
}

/// Kim tasdiqlayapti.
#[derive(Debug, Clone)]
pub enum Signer {
    /// Tomon. Xonadon a'zosi bo'lsa `pin` majburiy (a'zoning shaxsiy PIN'i); tashqi tomon uchun —
    /// u shaxsan tasdiqlaganini qo'lda belgilash.
    Party {
        party_id: String,
        pin: Option<String>,
    },
    Witness {
        name: String,
    },
}

fn add_signature(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    p: &Partnership,
    kind: SignatureKind,
    signer: &str,
    name: &str,
) -> Result<(), ServiceError> {
    if sigs_for(db.conn(), ctx, p)?
        .iter()
        .any(|s| s.kind == kind && s.signer == signer)
    {
        return Ok(());
    }
    repo::insert(
        db.conn(),
        &PartnershipSignature {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            partnership_id: p.meta.id.clone(),
            version: p.version,
            kind,
            signer: signer.to_owned(),
            signer_name: name.to_owned(),
        },
    )?;
    Ok(())
}

/// Shartnomaning **joriy versiyasini** tasdiqlaydi.
///
/// # Errors
/// Tomon/guvoh topilmasa, PIN noto'g'ri/yo'q bo'lsa yoki sheriklik tugagan bo'lsa.
pub fn sign(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    signer: Signer,
) -> Result<(), ServiceError> {
    let p = load(db.conn(), ctx, id)?;
    if p.status == PartnershipStatus::Ended {
        return Err(ServiceError::Invalid("sheriklik tugagan"));
    }
    match signer {
        Signer::Party { party_id, pin } => {
            let party = parties_of(db.conn(), ctx, id)?
                .into_iter()
                .find(|x| x.meta.id == party_id)
                .ok_or(ServiceError::NotFound)?;
            if let Some(member) = &party.member_id {
                let pin = pin.ok_or(ServiceError::NoPin)?;
                members::verify(db, env, ctx, member, &pin)?;
            }
            add_signature(
                db,
                env,
                ctx,
                &p,
                SignatureKind::Party,
                &party.meta.id,
                &party.name,
            )
        }
        Signer::Witness { name } => {
            if !p.witnesses.contains(&name) {
                return Err(ServiceError::NotFound);
            }
            add_signature(db, env, ctx, &p, SignatureKind::Witness, &name, &name)
        }
    }
}

/// Kapital qabul qilinganda barcha kattalarning oilaviy roziligi (a'zoning o'z PIN'i bilan).
///
/// # Errors
/// A'zo kattalardan emas, PIN noto'g'ri yoki sheriklik topilmasa.
pub fn family_consent(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    member_id: &str,
    pin: &str,
) -> Result<(), ServiceError> {
    let p = load(db.conn(), ctx, id)?;
    let member = members::list(db.conn(), ctx)?
        .into_iter()
        .find(|m| m.meta.id == member_id)
        .ok_or(ServiceError::NotFound)?;
    if member.role != MemberRole::Adult {
        return Err(ServiceError::Invalid("rozilikni faqat kattalar beradi"));
    }
    members::verify(db, env, ctx, member_id, pin)?;
    add_signature(
        db,
        env,
        ctx,
        &p,
        SignatureKind::FamilyConsent,
        member_id,
        &member.display_name,
    )
}

/// Sheriklikni faollashtiradi: barcha tomon va guvoh tasdiqlagan, oilaviy rozilik olingan va (kapital
/// kiritilsa) tayyorgarlik darvozasi ochiq bo'lishi shart.
///
/// # Errors
/// Shartlardan biri bajarilmagan bo'lsa.
pub fn activate(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<PartnershipView, ServiceError> {
    let v = view(db.conn(), env, ctx, id)?;
    if v.partnership.status != PartnershipStatus::Draft {
        return Err(ServiceError::Invalid(
            "faqat qoralamani faollashtirish mumkin",
        ));
    }
    if let Some(b) = v.blocker {
        return Err(ServiceError::Invalid(match b {
            "PARTY_SIGNATURES" => "barcha tomonlar shartnomaning joriy versiyasini tasdiqlashi kerak",
            "WITNESS_SIGNATURES" => "barcha guvohlar tasdiqlashi kerak",
            "FAMILY_CONSENT" => "kapital qabul qilish uchun barcha kattalarning roziligi kerak",
            _ => "kapital kiritish uchun tayyorgarlik darvozasi ochiq bo'lishi kerak (qorovul pul va qarz rejasi)",
        }));
    }
    let mut p = v.partnership;
    p.status = PartnershipStatus::Active;
    repo::update(db.conn(), &p, env.clock.now())?;
    view(db.conn(), env, ctx, id)
}

/// Sheriklikni yakunlaydi.
///
/// # Errors
/// Topilmasa.
pub fn end(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let mut p = load(db.conn(), ctx, id)?;
    p.status = PartnershipStatus::Ended;
    repo::update(db.conn(), &p, env.clock.now())?;
    Ok(())
}

/// Foyda/zarar taqsimoti hisobi (tomonlar tartibida; zarar manfiy). Avtomatik davr yopilishi — D13.
///
/// # Errors
/// Beparvolik izohisiz, mudarabadan boshqa turda beparvolik yoki hisob xatosi.
pub fn preview_distribution(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    outcome: Outcome,
    amount: Money,
    negligence_note: Option<&str>,
) -> Result<Vec<(String, Money)>, ServiceError> {
    let v = view(conn, env, ctx, id)?;
    let negligence = negligence_note.is_some_and(|n| !n.trim().is_empty());
    if negligence_note.is_some() && !negligence {
        return Err(ServiceError::Invalid("beparvolik izohini yozing"));
    }
    if negligence && v.partnership.kind != PartnershipKind::Mudaraba {
        return Err(ServiceError::Invalid(
            "beparvolik bayrog'i faqat mudarabada qo'llanadi",
        ));
    }
    let inputs: Vec<PartyInput> = v
        .parties
        .iter()
        .map(|x| PartyInput {
            role: x.party.role,
            capital: x.capital_total,
            share_bp: x.party.share_bp,
        })
        .collect();
    let amounts = distribute(
        v.partnership.kind,
        outcome,
        amount,
        &inputs,
        negligence,
        None,
    )?;
    Ok(v.parties
        .iter()
        .map(|x| x.party.name.clone())
        .zip(amounts)
        .collect())
}

// ------------------------------------------------------------------ buyout

#[derive(Debug, Clone)]
pub struct BuyoutView {
    pub plan: BuyoutPlan,
    pub provider_name: String,
    pub total_value: Money,
    pub stake: Money,
    /// Rejadagi teng bo'laklar jadvali.
    pub planned: BuyoutSchedule,
    /// Rejadagi davr sanalari.
    pub planned_dates: Vec<Date>,
    /// Haqiqiy to'lovlar bo'yicha jadval.
    pub actual: BuyoutSchedule,
    pub payments: Vec<BuyoutPayment>,
}

fn plan_of(conn: &Connection, ctx: &Ctx, pid: &str) -> Result<Option<BuyoutPlan>, ServiceError> {
    Ok(repo::list::<BuyoutPlan>(conn, &ctx.household_id)?
        .into_iter()
        .find(|b| b.partnership_id == pid))
}

/// Buyout rejasi: ishchi/sherik kapital egasining ulushini `periods` davrda teng bo'laklarda sotib oladi.
///
/// # Errors
/// Faqat musharaka; kapital egasi tomoni kapitalsiz yoki davrlar 1..=240 emas bo'lsa.
pub fn set_buyout(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    provider_party_id: &str,
    periods: u32,
    start_date: Option<Date>,
) -> Result<BuyoutView, ServiceError> {
    let v = view(db.conn(), env, ctx, id)?;
    if v.partnership.kind != PartnershipKind::Musharaka {
        return Err(ServiceError::Invalid(
            "bosqichma-bosqich sotib olish (kamayib boruvchi musharaka) faqat musharakada",
        ));
    }
    let provider = v
        .parties
        .iter()
        .find(|x| x.party.meta.id == provider_party_id)
        .ok_or(ServiceError::NotFound)?;
    equal_buyout_payments(provider.capital_total, periods)?;
    if provider.capital_total.minor() >= v.total_capital.minor() {
        return Err(ServiceError::Invalid(
            "sotib oluvchi tomonning ham kapitali bo'lishi kerak",
        ));
    }
    let now = env.clock.now();
    if let Some(old) = plan_of(db.conn(), ctx, id)? {
        repo::soft_delete::<BuyoutPlan>(db.conn(), &old.meta.id, now)?;
    }
    repo::insert(
        db.conn(),
        &BuyoutPlan {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            partnership_id: id.to_owned(),
            provider_party_id: provider_party_id.to_owned(),
            periods,
            start_date: start_date.unwrap_or_else(|| local_date(now)),
        },
    )?;
    buyout_view(db.conn(), env, ctx, id)?.ok_or(ServiceError::NotFound)
}

/// # Errors
/// Baza xatosi yoki hisob xatosi.
pub fn buyout_view(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<Option<BuyoutView>, ServiceError> {
    let Some(plan) = plan_of(conn, ctx, id)? else {
        return Ok(None);
    };
    let v = view(conn, env, ctx, id)?;
    let provider = v
        .parties
        .iter()
        .find(|x| x.party.meta.id == plan.provider_party_id)
        .ok_or(ServiceError::NotFound)?;
    let stake = provider.capital_total;
    let planned_payments = equal_buyout_payments(stake, plan.periods)?;
    let planned = buyout_schedule(v.total_capital, stake, &planned_payments)?;
    let planned_dates = (0..plan.periods)
        .map(|i| add_months(plan.start_date, i))
        .collect();
    let mut payments: Vec<BuyoutPayment> = repo::list::<BuyoutPayment>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|p| p.plan_id == plan.meta.id)
        .collect();
    payments.sort_by_key(|p| (p.paid_on, p.meta.id.clone()));
    let amounts: Vec<Money> = payments.iter().map(|p| p.amount).collect();
    let actual = buyout_schedule(v.total_capital, stake, &amounts)?;
    Ok(Some(BuyoutView {
        provider_name: provider.party.name.clone(),
        total_value: v.total_capital,
        stake,
        planned,
        planned_dates,
        actual,
        payments,
        plan,
    }))
}

/// Haqiqiy buyout to'lovini qayd etadi (qoldiqdan oshmasin).
///
/// # Errors
/// Reja yo'q, summa yaroqsiz yoki qoldiqdan ko'p bo'lsa.
pub fn record_buyout_payment(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    amount: Money,
    paid_on: Option<Date>,
) -> Result<(), ServiceError> {
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    let bv = buyout_view(db.conn(), env, ctx, id)?.ok_or(ServiceError::NotFound)?;
    let left = bv.actual.rows.last().map_or(bv.stake, |r| r.remaining);
    if amount.minor() > left.minor() {
        return Err(ServiceError::Invalid("to'lov qolgan ulushdan ko'p"));
    }
    repo::insert(
        db.conn(),
        &BuyoutPayment {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            plan_id: bv.plan.meta.id,
            paid_on: paid_on.unwrap_or_else(|| local_date(env.clock.now())),
            amount,
        },
    )?;
    Ok(())
}

// ------------------------------------------------------------------ PDF

/// Shartnoma PDF'i (joriy versiya).
///
/// # Errors
/// Topilmasa yoki PDF xatosi.
pub fn contract_pdf(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<Vec<u8>, ServiceError> {
    // Relizda tasdiqlanmagan shartnoma shabloni PDF bo'lib chiqmaydi (SPEC 8, OPEN_QUESTIONS 65).
    if !pdf::templates_releasable(cfg!(debug_assertions)) {
        return Err(ServiceError::Invalid(
            "shartnoma shabloni hali yurist va ulamo tasdig'idan o'tmagan: PDF chiqarilmaydi",
        ));
    }
    let v = view(conn, env, ctx, id)?;
    let fm = |m: Money| format_money(m, Locale::Uz);
    let date_of = |signer: &str, kind: SignatureKind| -> Result<Option<String>, ServiceError> {
        Ok(sigs_for(conn, ctx, &v.partnership)?
            .into_iter()
            .find(|s| s.kind == kind && s.signer == signer)
            .map(|s| domain::date_to_string(local_date(s.meta.created_at)).unwrap_or_default()))
    };
    let p = &v.partnership;
    let mut rules = vec![
        "Foyda faqat sof foydaning kelishilgan foizi sifatida taqsimlanadi; kafolatlangan summa yoki daromad yo'q.".to_owned(),
    ];
    rules.extend(match p.kind {
        PartnershipKind::Mudaraba => vec![
            "Moliyaviy zarar kapital egasi zimmasida, ishchi esa mehnatidan ayriladi.".to_owned(),
            "Istisno: ishchining beparvoligi yoki shart buzilishi — faqat izoh va dalil bilan."
                .to_owned(),
        ],
        PartnershipKind::Musharaka => {
            vec!["Zarar har bir tomon kiritgan kapitaliga mutanosib taqsimlanadi.".to_owned()]
        }
    });
    let buyout = buyout_view(conn, env, ctx, id)?.map(|b| {
        format!(
            "{} ulushi ({}) {} davrda sotib olinadi; boshlanishi: {}.",
            b.provider_name,
            fm(b.stake),
            b.plan.periods,
            domain::date_to_string(b.plan.start_date).unwrap_or_default()
        )
    });
    let doc = pdf::ContractDoc {
        title: p.name.clone(),
        version: p.version,
        kind: kind_text(p.kind).to_owned(),
        status: match p.status {
            PartnershipStatus::Draft => "Qoralama",
            PartnershipStatus::Active => "Faol",
            PartnershipStatus::Ended => "Tugagan",
        }
        .to_owned(),
        parties: v
            .parties
            .iter()
            .map(|x| {
                Ok(pdf::ContractParty {
                    name: x.party.name.clone(),
                    role: role_text(x.party.role).to_owned(),
                    capital: format!("Kapital: {}", fm(x.capital_total)),
                    share: format!("Foyda ulushi: {}", percent_text(x.party.share_bp)),
                    items: x
                        .capital
                        .iter()
                        .map(|c| format!("{} \u{2014} {}", c.description, fm(c.value)))
                        .collect(),
                    signed_at: date_of(&x.party.meta.id, SignatureKind::Party)?,
                })
            })
            .collect::<Result<Vec<_>, ServiceError>>()?,
        rules,
        term: format!("Muddat: {} oy", p.term_months),
        reporting: format!(
            "Hisobot davri: {}",
            match p.report_period {
                ReportPeriod::Monthly => "har oy",
                ReportPeriod::Quarterly => "har chorak",
                ReportPeriod::Yearly => "har yil",
            }
        ),
        end_clause: p.end_clause.clone(),
        dispute_clause: p.dispute_clause.clone(),
        witnesses: p
            .witnesses
            .iter()
            .map(|w| Ok((w.clone(), date_of(w, SignatureKind::Witness)?)))
            .collect::<Result<Vec<_>, ServiceError>>()?,
        buyout,
        legal_note: "Shablon yurist va ulamo tasdig'idan o'tmagan: yuridik kuchi va islomiy muvofiqligi haqida va'da berilmaydi. Ilova pul o'tkazmaydi va sheriklarni topishtirmaydi.".to_owned(),
        disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    };
    pdf::partnership_contract(&doc)
        .map_err(|_| ServiceError::Invalid("shartnoma PDF'ini yaratib bo'lmadi"))
}

#[cfg(test)]
mod tests {
    use super::percent_text;

    #[test]
    fn percent_text_uses_integer_math() {
        assert_eq!(percent_text(5_000), "50%");
        assert_eq!(percent_text(3_333), "33,33%");
        assert_eq!(percent_text(6_250), "62,5%");
        assert_eq!(percent_text(105), "1,05%");
        assert_eq!(percent_text(0), "0%");
    }
}
