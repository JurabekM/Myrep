//! Sheriklik: shartnoma ustasi, versiyalash, tasdiqlar, buyout (SPEC 2E.1, 2E.2, 2E.6).
//!
//! - Shartnomasiz sheriklik yo'q: yozuv shartnoma bilan birga yaratiladi.
//! - Shartlar o'zgarsa versiya oshadi, tasdiqlar qayta so'raladi.
//! - Kapital **kiritish** tayyorgarlik darvozasiga bo'ysunadi; kapital **qabul qilish** — yo'q, lekin
//!   barcha kattalarning oilaviy roziligi (PIN bilan) talab qilinadi.
//! - Ilova pul harakatini bajarmaydi va sheriklarni topishtirmaydi: faqat o'zaro tanish tomonlar kelishuvini yozadi.
use domain::{
    add_months, buyout_schedule, distribute, equal_buyout_payments, validate_parties, AgreementDoc,
    AgreementSignKind, AgreementSignature, AgreementStatus, AgreementType, Answer, Arbiter,
    BuyoutPayment, BuyoutPlan, BuyoutSchedule, CapitalKind, Contribution, Custody, Date, Duty,
    ExitClause, LossRule, Meta, Outcome, Partnership, PartnershipCapital, PartnershipKind,
    PartnershipParty, PartnershipStatus, PartnershipVersion, Party, PartyInput, PartyRole,
    ProfitRule, ProfitShare, Questions, ReportPeriod, SubjectKind, Term,
};
use money::{format_money, Locale, Money};
use storage::Connection;
use storage::{repo, Database};

use crate::{
    agreements::{self, AgreementSigner, AgreementView, NewAgreement},
    guard, local_date, members, sum_money, Ctx, Env, ServiceError,
};

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
    /// Muddat tugagandagi tartib (7-savol).
    pub end_clause: String,
    /// Nizolarni hal qilish tartibi (8-savolga tegishli).
    pub dispute_clause: String,
    pub witnesses: Vec<String>,
    pub parties: Vec<NewParty>,
    /// Foydalanuvchi kiritadigan qism: vazifalar, pul joyi, hakam (SPEC 2F.2).
    pub details: PartnershipDetails,
}

/// Shartnomaning foydalanuvchi kiritadigan javoblari (SPEC 2F.2). Qolgan savollar sheriklikdan avtomatik olinadi.
#[derive(Debug, Clone, Default)]
pub struct PartnershipDetails {
    /// 3-savol: vazifalar. Har birida mas'ul tomon (ismi bo'yicha) va «bajarilmasa» bandi bo'lishi shart.
    pub duties: Vec<DutyInput>,
    /// 6-savol: pul qayerda turadi. Bo'sh bo'lsa savol javobsiz qoladi.
    pub custody_place: String,
    /// 8-savol: hakam ismi. Bo'sh bo'lsa savol javobsiz qoladi.
    pub arbiter_name: String,
    /// 9-savol: yangilash sanasi; `None` — boshlanishdan bir yil keyin (standart, SPEC 2F.3).
    pub review_date: Option<Date>,
}

#[derive(Debug, Clone)]
pub struct DutyInput {
    pub text: String,
    /// Mas'ul tomonning ismi (sheriklikdagi tomon nomi bo'yicha).
    pub owner_name: String,
    /// «Bajarilmasa» bandi: masalan, «1 kun ichida xabar beradi va o'rnini topadi».
    pub if_not_done: String,
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
    let mut keys: Vec<String> = new
        .parties
        .iter()
        .map(|p| clean(&p.name, 60).to_lowercase())
        .collect();
    keys.sort();
    if keys.windows(2).any(|w| w[0] == w[1]) {
        return Err(ServiceError::Invalid("tomon nomlari takrorlanmasin"));
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
    party_metas: &[Meta],
) -> Result<(), ServiceError> {
    for (p, meta) in new.parties.iter().zip(party_metas) {
        let party = PartnershipParty {
            meta: meta.clone(),
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

fn loss_text(kind: PartnershipKind) -> &'static str {
    match kind {
        PartnershipKind::Mudaraba => {
            "Moliyaviy zarar kapital egasi zimmasida; ishchi mehnatidan ayriladi. Beparvolik bundan mustasno."
        }
        PartnershipKind::Musharaka => "Zarar har bir tomon kiritgan kapitaliga mutanosib taqsimlanadi.",
    }
}

/// Shartnoma hujjati (9 savol): tomonlar, hissalar, foyda, zarar, chiqish va muddat sheriklikdan olinadi;
/// vazifalar, pul joyi va hakam — `details` dan. Yetishmasa savol «javobsiz» qoladi (imzolash bloklanadi).
fn build_doc(new: &NewPartnership, party_ids: &[String], effective: Date) -> AgreementDoc {
    let parties: Vec<Party> = new
        .parties
        .iter()
        .zip(party_ids)
        .map(|(p, id)| Party {
            id: id.clone(),
            name: clean(&p.name, 60),
            role: role_text(p.role).to_owned(),
            member_id: p.member_id.clone(),
        })
        .collect();
    let contributions: Vec<Contribution> = new
        .parties
        .iter()
        .zip(party_ids)
        .flat_map(|(p, id)| {
            if p.capital.is_empty() {
                vec![Contribution {
                    party_id: id.clone(),
                    description: "Mehnat (ish)".into(),
                    amount: None,
                }]
            } else {
                p.capital
                    .iter()
                    .map(|c| Contribution {
                        party_id: id.clone(),
                        description: clean(&c.description, 80),
                        amount: Some(c.value),
                    })
                    .collect()
            }
        })
        .collect();
    let owner_of = |name: &str| -> Option<String> {
        let key = clean(name, 60).to_lowercase();
        new.parties
            .iter()
            .zip(party_ids)
            .find(|(p, _)| clean(&p.name, 60).to_lowercase() == key)
            .map(|(_, id)| id.clone())
    };
    let duties: Vec<Duty> = new
        .details
        .duties
        .iter()
        .map(|d| Duty {
            text: clean(&d.text, 300),
            owner_party_id: owner_of(&d.owner_name),
            if_not_done: clean(&d.if_not_done, 300),
        })
        .collect();
    let custody_place = clean(&new.details.custody_place, 200);
    let arbiter_name = clean(&new.details.arbiter_name, 60);
    let shares: Vec<ProfitShare> = new
        .parties
        .iter()
        .zip(party_ids)
        .map(|(p, id)| ProfitShare {
            party_id: id.clone(),
            share_bp: p.share_bp,
        })
        .collect();
    AgreementDoc {
        agreement_type: AgreementType::Partnership,
        effective_from: effective,
        witnesses: witnesses_of(new),
        questions: Questions {
            parties: Answer::Answered(parties),
            contributions: Answer::Answered(contributions),
            duties: if duties.is_empty() {
                Answer::Missing
            } else {
                Answer::Answered(duties)
            },
            profit: Answer::Answered(ProfitRule {
                shares,
                fixed_amount: None,
            }),
            loss: Answer::Answered(LossRule {
                text: loss_text(new.kind).to_owned(),
            }),
            custody: if custody_place.is_empty() {
                Answer::Missing
            } else {
                Answer::Answered(Custody {
                    place: custody_place,
                    keeper_device_id: None,
                    review_every: new.report_period,
                })
            },
            exit: Answer::Answered(ExitClause {
                text: clean(&new.end_clause, 500),
            }),
            arbiter: if arbiter_name.is_empty() {
                Answer::Missing
            } else {
                Answer::Answered(Arbiter {
                    name: arbiter_name,
                    party_id: None,
                })
            },
            term: Answer::Answered(Term {
                months: Some(new.term_months),
                review_date: new
                    .details
                    .review_date
                    .unwrap_or_else(|| add_months(effective, 12)),
            }),
        },
    }
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
    let party_metas: Vec<Meta> = new
        .parties
        .iter()
        .map(|_| Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id))
        .collect();
    let party_ids: Vec<String> = party_metas.iter().map(|m| m.id.clone()).collect();
    let effective = local_date(env.clock.now());
    db.transaction::<(), ServiceError>(|tx| {
        repo::insert(tx, &p)?;
        insert_content(tx, env, ctx, &p.meta.id, &new, &party_metas)?;
        repo::insert(
            tx,
            &PartnershipVersion {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                partnership_id: p.meta.id.clone(),
                version: 1,
                snapshot: snapshot(&new, 1),
            },
        )?;
        agreements::create_in(
            tx,
            env,
            ctx,
            NewAgreement {
                title: p.name.clone(),
                subject: Some((SubjectKind::Partnership, p.meta.id.clone())),
                doc: build_doc(&new, &party_ids, effective),
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
    let agreement =
        agreements::agreement_of_partnership(db.conn(), ctx, id)?.ok_or(ServiceError::NotFound)?;
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
    let party_metas: Vec<Meta> = new
        .parties
        .iter()
        .map(|_| Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id))
        .collect();
    let party_ids: Vec<String> = party_metas.iter().map(|m| m.id.clone()).collect();
    let effective = agreement.effective_from;
    db.transaction::<(), ServiceError>(|tx| {
        for c in &old_capital {
            repo::soft_delete::<PartnershipCapital>(tx, &c.meta.id, now)?;
        }
        for o in &old_parties {
            repo::soft_delete::<PartnershipParty>(tx, &o.meta.id, now)?;
        }
        repo::update(tx, &p, now)?;
        insert_content(tx, env, ctx, id, &new, &party_metas)?;
        repo::insert(
            tx,
            &PartnershipVersion {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                partnership_id: id.to_owned(),
                version: p.version,
                snapshot: snapshot(&new, p.version),
            },
        )?;
        agreements::save_version_in(
            tx,
            env,
            ctx,
            &agreement.meta.id,
            build_doc(&new, &party_ids, effective),
            Some("Sheriklik shartlari o'zgartirildi"),
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
    /// Faollashtirishga to'sqinlik: `INCOMPLETE_AGREEMENT` | `PARTY_SIGNATURES` | `WITNESS_SIGNATURES` |
    /// `ARBITER_SIGNATURE` | `FAMILY_CONSENT` | `GATE_CLOSED`.
    pub blocker: Option<&'static str>,
    /// Shartnoma (kelishuv dvigateli): 9 savol holati, tasdiqlar va jurnal zanjiri.
    pub agreement: Option<AgreementView>,
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
    let agreement = match agreements::agreement_of_partnership(conn, ctx, id)? {
        Some(a) => Some(agreements::view(conn, ctx, &a.meta.id)?),
        None => None,
    };
    let sigs: Vec<AgreementSignature> = agreement
        .as_ref()
        .map_or_else(Vec::new, |a| a.signatures.clone());
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
                .any(|s| s.kind == AgreementSignKind::Party && s.signer_key == party.meta.id);
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
                .any(|s| s.kind == AgreementSignKind::Witness && &s.signer_key == w),
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
                consented: sigs.iter().any(|s| {
                    s.kind == AgreementSignKind::FamilyConsent && s.signer_key == m.meta.id
                }),
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
    let complete = agreement
        .as_ref()
        .is_some_and(|a| a.completeness.is_complete());
    let arbiter_pending = agreement.as_ref().is_some_and(|a| {
        a.missing_signatures
            .iter()
            .any(|m| m.kind == AgreementSignKind::Arbiter)
    });
    let blocker = if !complete {
        Some("INCOMPLETE_AGREEMENT")
    } else if parties.iter().any(|x| !x.signed) {
        Some("PARTY_SIGNATURES")
    } else if witnesses.iter().any(|w| !w.signed) {
        Some("WITNESS_SIGNATURES")
    } else if arbiter_pending {
        Some("ARBITER_SIGNATURE")
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
        agreement,
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
    /// Hakam: hakamlikka roziligini imzo bilan bildiradi.
    Arbiter,
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
    let agreement =
        agreements::agreement_of_partnership(db.conn(), ctx, id)?.ok_or(ServiceError::NotFound)?;
    let signer = match signer {
        Signer::Party { party_id, pin } => AgreementSigner::Party { party_id, pin },
        Signer::Witness { name } => AgreementSigner::Witness { name },
        Signer::Arbiter => AgreementSigner::Arbiter,
    };
    agreements::sign(db, env, ctx, &agreement.meta.id, signer)?;
    Ok(())
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
    load(db.conn(), ctx, id)?;
    let agreement =
        agreements::agreement_of_partnership(db.conn(), ctx, id)?.ok_or(ServiceError::NotFound)?;
    agreements::sign(
        db,
        env,
        ctx,
        &agreement.meta.id,
        AgreementSigner::FamilyConsent {
            member_id: member_id.to_owned(),
            pin: pin.to_owned(),
        },
    )?;
    Ok(())
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
            "INCOMPLETE_AGREEMENT" => {
                "kelishuvning 9 savoli to'liq emas: barcha savollarga javob bering"
            }
            "PARTY_SIGNATURES" => "barcha tomonlar shartnomaning joriy versiyasini tasdiqlashi kerak",
            "WITNESS_SIGNATURES" => "barcha guvohlar tasdiqlashi kerak",
            "ARBITER_SIGNATURE" => "hakam kelishuvni tasdiqlashi kerak",
            "FAMILY_CONSENT" => "kapital qabul qilish uchun barcha kattalarning roziligi kerak",
            _ => "kapital kiritish uchun tayyorgarlik darvozasi ochiq bo'lishi kerak (qorovul pul va qarz rejasi)",
        }));
    }
    let agreement_id = v
        .agreement
        .as_ref()
        .map(|a| a.agreement.meta.id.clone())
        .ok_or(ServiceError::NotFound)?;
    let mut p = v.partnership;
    db.transaction::<(), ServiceError>(|tx| {
        agreements::activate_in(tx, env, ctx, &agreement_id)?;
        p.status = PartnershipStatus::Active;
        repo::update(tx, &p, env.clock.now())?;
        Ok(())
    })?;
    view(db.conn(), env, ctx, id)
}

/// Sheriklikni yakunlaydi.
///
/// # Errors
/// Topilmasa.
pub fn end(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let mut p = load(db.conn(), ctx, id)?;
    db.transaction::<(), ServiceError>(|tx| {
        p.status = PartnershipStatus::Ended;
        repo::update(tx, &p, env.clock.now())?;
        if let Some(a) = agreements::agreement_of_partnership(tx, ctx, id)? {
            if a.status != AgreementStatus::Closed {
                agreements::close_in(tx, env, ctx, &a.meta.id)?;
            }
        }
        Ok(())
    })
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
    // 9 savolli joriy versiya: kelishuv PDF'i (SPEC 2F.2). Eski matnli versiya — eski shablon.
    if let Some(a) = v.agreement.as_ref().filter(|a| a.doc.is_some()) {
        return agreements::pdf(conn, ctx, &a.agreement.meta.id);
    }
    let fm = |m: Money| format_money(m, Locale::Uz);
    let sigs: Vec<AgreementSignature> = v
        .agreement
        .as_ref()
        .map_or_else(Vec::new, |a| a.signatures.clone());
    let date_of = |signer: &str, kind: AgreementSignKind| -> Option<String> {
        sigs.iter()
            .find(|s| s.kind == kind && s.signer_key == signer)
            .map(|s| domain::date_to_string(local_date(s.meta.created_at)).unwrap_or_default())
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
                    signed_at: date_of(&x.party.meta.id, AgreementSignKind::Party),
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
            .map(|w| Ok((w.clone(), date_of(w, AgreementSignKind::Witness))))
            .collect::<Result<Vec<_>, ServiceError>>()?,
        buyout,
        legal_note: "Shablon yurist va ulamo tasdig'idan o'tmagan: yuridik kuchi va islomiy muvofiqligi haqida va'da berilmaydi. Ilova pul o'tkazmaydi va sheriklarni topishtirmaydi.".to_owned(),
        disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    };
    pdf::partnership_contract(&doc)
        .map_err(|_| ServiceError::Invalid("shartnoma PDF'ini yaratib bo'lmadi"))
}

/// Hali saqlanmagan sheriklik qoralamasining tekshiruvi: shartnoma ustasining jonli holati uchun.
#[derive(Debug, Clone)]
pub struct DraftCheck {
    /// Javobsiz savollar (1..=9).
    pub missing: Vec<u8>,
    /// Javob bor, lekin qoidaga zid.
    pub errors: Vec<domain::Issue>,
    /// Önizleme PDF; relizda shablon tasdiqlanmagan bo'lsa `None`.
    pub pdf: Option<Vec<u8>>,
}

/// Kiritilayotgan (hali yozilmagan) shartnoma uchun to'liqlik va önizleme. Hech narsa yozmaydi.
///
/// # Errors
/// Kiritilgan ma'lumot yaroqsiz bo'lsa (masalan, nom bo'sh yoki tomon nomlari takrorlangan).
pub fn draft_check(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    new: &NewPartnership,
) -> Result<DraftCheck, ServiceError> {
    validate(conn, ctx, new)?;
    let effective = local_date(env.clock.now());
    let placeholder_ids: Vec<String> = (0..new.parties.len())
        .map(|i| format!("draft-{i}"))
        .collect();
    // Saqlashda kabi: hisob yurituvchi bo'sh bo'lsa, yaratayotgan qurilma.
    let doc = agreements::prepare(env, build_doc(new, &placeholder_ids, effective));
    let c = domain::completeness(&doc);
    let pdf = agreements::draft_pdf(
        &doc,
        &clean(&new.name, 80),
        AgreementType::Partnership,
        effective,
    )?;
    Ok(DraftCheck {
        missing: c.missing,
        errors: c.errors,
        pdf,
    })
}

/// Yillik yangilash: «o'zgarishsiz tasdiqlash». Shartnoma matni o'zgarmaydi, lekin yangi versiya hisoblanadi
/// (SPEC 2F.10 / D13A): barcha tomonlar qayta tasdiqlaydi, faol sheriklik qoralamaga qaytadi.
///
/// # Errors
/// Sheriklik tugagan, kelishuv yo'q yoki eski matnli bo'lsa.
pub fn confirm_unchanged(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<PartnershipView, ServiceError> {
    let p = load(db.conn(), ctx, id)?;
    if p.status == PartnershipStatus::Ended {
        return Err(ServiceError::Invalid("tugagan sheriklik yangilanmaydi"));
    }
    let a = agreements::agreement_of_partnership(db.conn(), ctx, id)?.ok_or(
        ServiceError::Invalid("sheriklik kelishuvi topilmadi: sheriklikni qayta saqlang"),
    )?;
    let doc = agreements::current_doc(db.conn(), ctx, &a)?.ok_or(ServiceError::Invalid(
        "eski matnli sheriklik yangilanmaydi: avval 9 savolli versiya yarating",
    ))?;
    let now = env.clock.now();
    db.transaction::<(), ServiceError>(|tx| {
        agreements::save_version_in(
            tx,
            env,
            ctx,
            &a.meta.id,
            doc,
            Some("O'zgarishsiz tasdiqlash"),
        )?;
        // Matn o'zgarmagan: oxirgi versiya qatorining mazmuni ko'chiriladi, raqami oshadi.
        let snapshot = repo::list::<PartnershipVersion>(tx, &ctx.household_id)?
            .into_iter()
            .filter(|v| v.partnership_id == id)
            .max_by_key(|v| v.version)
            .map(|v| v.snapshot)
            .unwrap_or_default();
        let version = p.version + 1;
        let mut next = p.clone();
        next.version = version;
        if next.status == PartnershipStatus::Active {
            next.status = PartnershipStatus::Draft;
        }
        repo::update(tx, &next, now)?;
        repo::insert(
            tx,
            &PartnershipVersion {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                partnership_id: id.to_owned(),
                version,
                snapshot,
            },
        )?;
        Ok(())
    })?;
    view(db.conn(), env, ctx, id)
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
