//! D12 commandlari (5-qonun): sheriklik shartnomasi, tasdiqlar, taqsimot hisobi, buyout.

use domain::{
    date_from_str, date_to_string, CapitalKind, Outcome, PartnershipKind, PartyRole, ReportPeriod,
};
use money::{parse_amount, Locale, Money};
use serde::{Deserialize, Serialize};
use services::{
    agreements::AgreementView,
    partnerships::{
        self, BuyoutView, DutyInput, NewCapital, NewPartnership, NewParty, PartnershipDetails,
        PartnershipView, Signer,
    },
    Ctx, Env, ServiceError,
};
use specta::Type;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

use crate::{
    commands::{with_session, AppSession, CommandError},
    dto::MoneyDto,
};

const LOCALE: Locale = Locale::Uz;

fn m(v: Money) -> MoneyDto {
    MoneyDto::from_money(v, LOCALE)
}

fn amount(ctx: &Ctx, text: &str) -> Result<Money, ServiceError> {
    Ok(parse_amount(text, ctx.currency)?)
}

/// «8000000» yoki «8000000,50» (tiyin 100 ga bo'linadi; butun son arifmetikasi).
fn plain_text(v: Money) -> String {
    let (whole, frac) = (v.minor() / 100, (v.minor() % 100).abs());
    if frac == 0 {
        whole.to_string()
    } else {
        format!("{whole},{frac:02}")
    }
}

fn ds(d: domain::Date) -> String {
    date_to_string(d).unwrap_or_default()
}

// ---------------------------------------------------------------- kirish

#[derive(Debug, Deserialize, Type)]
pub struct CapitalInput {
    pub description: String,
    /// `CASH` | `EQUIPMENT`.
    pub kind: String,
    pub value: String,
}

#[derive(Debug, Deserialize, Type)]
pub struct PartyInputDto {
    pub name: String,
    /// `CAPITAL_PROVIDER` | `WORKER` | `PARTNER`.
    pub role: String,
    /// Foyda ulushi, bazis punkt (5000 = 50%).
    pub share_bp: u32,
    pub member_id: Option<String>,
    pub capital: Vec<CapitalInput>,
    /// Kafolatli summa kiritishga urinish: doim rad etiladi, tushuntirish bilan.
    pub fixed_return: Option<String>,
}

#[derive(Debug, Deserialize, Type)]
pub struct PartnershipInput {
    pub name: String,
    /// `MUDARABA` | `MUSHARAKA`.
    pub kind: String,
    pub term_months: u32,
    /// `MONTHLY` | `QUARTERLY` | `YEARLY`.
    pub report_period: String,
    pub end_clause: String,
    pub dispute_clause: String,
    pub witnesses: Vec<String>,
    pub parties: Vec<PartyInputDto>,
    /// 3-savol: vazifalar; har birida mas'ul tomon (ismi) va «bajarilmasa» bandi.
    #[serde(default)]
    pub duties: Vec<DutyInputDto>,
    /// 6-savol: pul qayerda turadi.
    #[serde(default)]
    pub custody_place: String,
    /// 8-savol: hakam ismi (tomonlardan biri bo'lmasin).
    #[serde(default)]
    pub arbiter_name: String,
    /// 9-savol: yangilash sanasi (`YYYY-MM-DD`); bo'sh bo'lsa boshlanishdan bir yil keyin.
    #[serde(default)]
    pub review_date: Option<String>,
}

#[derive(Debug, Deserialize, Type)]
pub struct DutyInputDto {
    pub text: String,
    pub owner_name: String,
    pub if_not_done: String,
}

fn parse_input(ctx: &Ctx, i: PartnershipInput) -> Result<NewPartnership, ServiceError> {
    let kind = PartnershipKind::parse(&i.kind).ok_or(ServiceError::Invalid("turni tanlang"))?;
    let report_period = ReportPeriod::parse(&i.report_period)
        .ok_or(ServiceError::Invalid("hisobot davrini tanlang"))?;
    let parties = i
        .parties
        .into_iter()
        .map(|p| {
            Ok(NewParty {
                name: p.name,
                role: PartyRole::parse(&p.role).ok_or(ServiceError::Invalid("rolni tanlang"))?,
                share_bp: p.share_bp,
                member_id: p.member_id.filter(|x| !x.is_empty()),
                capital: p
                    .capital
                    .into_iter()
                    .map(|c| {
                        Ok(NewCapital {
                            description: c.description,
                            kind: CapitalKind::parse(&c.kind)
                                .ok_or(ServiceError::Invalid("kapital turini tanlang"))?,
                            value: amount(ctx, &c.value)?,
                        })
                    })
                    .collect::<Result<Vec<_>, ServiceError>>()?,
                fixed_return: p
                    .fixed_return
                    .filter(|t| !t.trim().is_empty())
                    .map(|t| amount(ctx, &t))
                    .transpose()?,
            })
        })
        .collect::<Result<Vec<_>, ServiceError>>()?;
    let review_date = i
        .review_date
        .filter(|t| !t.trim().is_empty())
        .map(|t| date_from_str(t.trim()))
        .transpose()
        .map_err(|_| ServiceError::Invalid("yangilash sanasi YYYY-MM-DD ko'rinishida bo'lsin"))?;
    let details = PartnershipDetails {
        duties: i
            .duties
            .into_iter()
            .map(|d| DutyInput {
                text: d.text,
                owner_name: d.owner_name,
                if_not_done: d.if_not_done,
            })
            .collect(),
        custody_place: i.custody_place,
        arbiter_name: i.arbiter_name,
        review_date,
    };
    Ok(NewPartnership {
        name: i.name,
        kind,
        term_months: i.term_months,
        report_period,
        end_clause: i.end_clause,
        dispute_clause: i.dispute_clause,
        witnesses: i.witnesses,
        parties,
        details,
    })
}

// ---------------------------------------------------------------- chiqish

#[derive(Debug, Serialize, Type)]
pub struct CapitalItemDto {
    pub description: String,
    pub kind: String,
    pub value: MoneyDto,
    /// Tahrirlash uchun qayta kiritish mumkin bo'lgan summa matni (so'm).
    pub value_text: String,
}

#[derive(Debug, Serialize, Type)]
pub struct PartyDto {
    pub id: String,
    pub name: String,
    pub role: String,
    pub share_bp: u32,
    pub member_id: Option<String>,
    pub capital_total: MoneyDto,
    pub items: Vec<CapitalItemDto>,
    pub signed: bool,
}

#[derive(Debug, Serialize, Type)]
pub struct WitnessDto {
    pub name: String,
    pub signed: bool,
}

#[derive(Debug, Serialize, Type)]
pub struct ConsentDto {
    pub member_id: String,
    pub name: String,
    pub consented: bool,
}

#[derive(Debug, Serialize, Type)]
pub struct VersionDto {
    pub version: u32,
    pub snapshot: String,
}

#[derive(Debug, Serialize, Type)]
pub struct BuyoutRowDto {
    pub period: u32,
    pub date: Option<String>,
    pub applied: MoneyDto,
    pub remaining: MoneyDto,
    pub provider_bp: u32,
    pub worker_bp: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct BuyoutDto {
    pub provider_party_id: String,
    pub provider_name: String,
    pub total_value: MoneyDto,
    pub stake: MoneyDto,
    pub periods: u32,
    pub start_date: String,
    pub planned: Vec<BuyoutRowDto>,
    pub actual: Vec<BuyoutRowDto>,
    pub completed: bool,
}

fn buyout_dto(b: &BuyoutView) -> BuyoutDto {
    let rows = |s: &domain::BuyoutSchedule, dates: Option<&[domain::Date]>| {
        s.rows
            .iter()
            .enumerate()
            .map(|(i, r)| BuyoutRowDto {
                period: r.period,
                date: dates.and_then(|d| d.get(i)).copied().map(ds),
                applied: m(r.applied),
                remaining: m(r.remaining),
                provider_bp: r.provider_bp,
                worker_bp: r.worker_bp,
            })
            .collect()
    };
    BuyoutDto {
        provider_party_id: b.plan.provider_party_id.clone(),
        provider_name: b.provider_name.clone(),
        total_value: m(b.total_value),
        stake: m(b.stake),
        periods: b.plan.periods,
        start_date: ds(b.plan.start_date),
        planned: rows(&b.planned, Some(&b.planned_dates)),
        actual: rows(&b.actual, None),
        completed: b.actual.completed,
    }
}

/// Kelishuv holati (6-qonun): 9 savol, xatolar, kutilayotgan tasdiqlar va jurnal zanjiri.
#[derive(Debug, Serialize, Type)]
pub struct AgreementStatusDto {
    pub id: String,
    /// `DRAFT` | `SIGNED` | `ACTIVE` | `IN_DISPUTE` | `CLOSED`.
    pub status: String,
    pub current_version: u32,
    /// Eski ma'lumotdan ko'chirilgan: 9 savolli yangi versiya kerak.
    pub legacy: bool,
    /// Javobsiz savollar (1–9).
    pub missing_questions: Vec<u8>,
    pub errors: Vec<AgreementIssueDto>,
    pub warnings: Vec<AgreementIssueDto>,
    pub missing_signatures: Vec<SignatureNeedDto>,
    pub journal_length: u32,
    /// Jurnal zanjiri buzilmagan.
    pub journal_intact: bool,
    /// Joriy versiyadagi foydalanuvchi javoblari (tahrirlashda forma shulardan boshlanadi).
    pub duties: Vec<AgreementDutyDto>,
    pub custody_place: String,
    pub arbiter_name: String,
    /// `YYYY-MM-DD`; javob berilmagan bo'lsa bo'sh.
    pub review_date: String,
}

#[derive(Debug, Serialize, Type)]
pub struct AgreementDutyDto {
    pub text: String,
    pub owner_name: String,
    pub if_not_done: String,
}

#[derive(Debug, Serialize, Type)]
pub struct AgreementIssueDto {
    pub question: u8,
    pub code: String,
}

#[derive(Debug, Serialize, Type)]
pub struct SignatureNeedDto {
    /// `PARTY` | `WITNESS` | `ARBITER` | `FAMILY_CONSENT`.
    pub kind: String,
    pub key: String,
    pub name: String,
}

fn agreement_dto(a: &AgreementView) -> AgreementStatusDto {
    let doc = a.doc.as_ref();
    let party_name = |id: &str| -> String {
        doc.and_then(|d| match &d.questions.parties {
            domain::Answer::Answered(ps) => ps.iter().find(|p| p.id == id).map(|p| p.name.clone()),
            _ => None,
        })
        .unwrap_or_default()
    };
    let duties = match doc.map(|d| &d.questions.duties) {
        Some(domain::Answer::Answered(ds)) => ds
            .iter()
            .map(|d| AgreementDutyDto {
                text: d.text.clone(),
                owner_name: d
                    .owner_party_id
                    .as_deref()
                    .map(party_name)
                    .unwrap_or_default(),
                if_not_done: d.if_not_done.clone(),
            })
            .collect(),
        _ => Vec::new(),
    };
    let custody_place = match doc.map(|d| &d.questions.custody) {
        Some(domain::Answer::Answered(c)) => c.place.clone(),
        _ => String::new(),
    };
    let arbiter_name = match doc.map(|d| &d.questions.arbiter) {
        Some(domain::Answer::Answered(x)) => x.name.clone(),
        _ => String::new(),
    };
    let review_date = match doc.map(|d| &d.questions.term) {
        Some(domain::Answer::Answered(t)) => {
            domain::date_to_string(t.review_date).unwrap_or_default()
        }
        _ => String::new(),
    };
    AgreementStatusDto {
        duties,
        custody_place,
        arbiter_name,
        review_date,
        id: a.agreement.meta.id.clone(),
        status: a.agreement.status.as_str().to_owned(),
        current_version: a.agreement.current_version,
        legacy: a.agreement.legacy,
        missing_questions: a.completeness.missing.clone(),
        errors: a
            .completeness
            .errors
            .iter()
            .map(|i| AgreementIssueDto {
                question: i.question,
                code: i.code.to_owned(),
            })
            .collect(),
        warnings: a
            .warnings
            .iter()
            .map(|w| AgreementIssueDto {
                question: w.question,
                code: w.code.to_owned(),
            })
            .collect(),
        missing_signatures: a
            .missing_signatures
            .iter()
            .map(|r| SignatureNeedDto {
                kind: r.kind.as_str().to_owned(),
                key: r.key.clone(),
                name: r.name.clone(),
            })
            .collect(),
        journal_length: u32::try_from(a.chain.length).unwrap_or(u32::MAX),
        journal_intact: a.chain.broken_seq.is_none(),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct PartnershipDto {
    pub id: String,
    pub name: String,
    pub kind: String,
    pub term_months: u32,
    pub report_period: String,
    pub end_clause: String,
    pub dispute_clause: String,
    pub version: u32,
    /// `DRAFT` | `ACTIVE` | `ENDED`.
    pub status: String,
    pub parties: Vec<PartyDto>,
    pub witnesses: Vec<WitnessDto>,
    pub total_capital: MoneyDto,
    pub self_provides_capital: bool,
    pub self_receives_capital: bool,
    pub consents: Vec<ConsentDto>,
    pub versions: Vec<VersionDto>,
    /// `INCOMPLETE_AGREEMENT` | `PARTY_SIGNATURES` | `WITNESS_SIGNATURES` | `ARBITER_SIGNATURE` |
    /// `FAMILY_CONSENT` | `GATE_CLOSED`.
    pub blocker: Option<String>,
    pub buyout: Option<BuyoutDto>,
    /// Kelishuv (shartnoma dvigateli) holati.
    pub agreement: Option<AgreementStatusDto>,
}

fn dto(v: &PartnershipView, buyout: Option<&BuyoutView>) -> PartnershipDto {
    let p = &v.partnership;
    PartnershipDto {
        id: p.meta.id.clone(),
        name: p.name.clone(),
        kind: p.kind.as_str().to_owned(),
        term_months: p.term_months,
        report_period: p.report_period.as_str().to_owned(),
        end_clause: p.end_clause.clone(),
        dispute_clause: p.dispute_clause.clone(),
        version: p.version,
        status: p.status.as_str().to_owned(),
        parties: v
            .parties
            .iter()
            .map(|x| PartyDto {
                id: x.party.meta.id.clone(),
                name: x.party.name.clone(),
                role: x.party.role.as_str().to_owned(),
                share_bp: x.party.share_bp,
                member_id: x.party.member_id.clone(),
                capital_total: m(x.capital_total),
                items: x
                    .capital
                    .iter()
                    .map(|c| CapitalItemDto {
                        description: c.description.clone(),
                        kind: c.kind.as_str().to_owned(),
                        value: m(c.value),
                        value_text: plain_text(c.value),
                    })
                    .collect(),
                signed: x.signed,
            })
            .collect(),
        witnesses: v
            .witnesses
            .iter()
            .map(|w| WitnessDto {
                name: w.name.clone(),
                signed: w.signed,
            })
            .collect(),
        total_capital: m(v.total_capital),
        self_provides_capital: v.self_provides_capital,
        self_receives_capital: v.self_receives_capital,
        consents: v
            .consents
            .iter()
            .map(|c| ConsentDto {
                member_id: c.member_id.clone(),
                name: c.name.clone(),
                consented: c.consented,
            })
            .collect(),
        versions: v
            .versions
            .iter()
            .map(|x| VersionDto {
                version: x.version,
                snapshot: x.snapshot.clone(),
            })
            .collect(),
        blocker: v.blocker.map(str::to_owned),
        buyout: buyout.map(buyout_dto),
        agreement: v.agreement.as_ref().map(agreement_dto),
    }
}

pub(crate) fn full(
    conn: &storage::Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    v: &PartnershipView,
) -> Result<PartnershipDto, ServiceError> {
    let b = partnerships::buyout_view(conn, env, ctx, &v.partnership.meta.id)?;
    Ok(dto(v, b.as_ref()))
}

#[tauri::command]
#[specta::specta]
pub fn list_partnerships(
    state: State<'_, AppSession>,
) -> Result<Vec<PartnershipDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            partnerships::list(db.conn(), env, ctx)?
                .iter()
                .map(|v| full(db.conn(), env, ctx, v))
                .collect()
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn create_partnership(
    input: PartnershipInput,
    state: State<'_, AppSession>,
) -> Result<PartnershipDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let new = parse_input(ctx, input)?;
            let v = partnerships::create(db, env, ctx, new)?;
            full(db.conn(), env, ctx, &v)
        })
    })
}

/// Saqlanmagan shartnoma qoralamasi: javobsiz savollar, qoidaga zid javoblar va önizleme PDF.
#[derive(Debug, Serialize, Type)]
pub struct DraftCheckDto {
    /// Javobsiz savollar (1–9).
    pub missing_questions: Vec<u8>,
    pub errors: Vec<AgreementIssueDto>,
    /// Önizleme PDF baytlari; relizda shablon tasdiqlanmagan bo'lsa `null`.
    pub pdf: Option<Vec<u8>>,
}

/// Ustaning jonli önizlemasi uchun: hech narsa saqlanmaydi.
#[tauri::command]
#[specta::specta]
pub fn check_partnership_draft(
    input: PartnershipInput,
    state: State<'_, AppSession>,
) -> Result<DraftCheckDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let new = parse_input(ctx, input)?;
            let c = partnerships::draft_check(db.conn(), env, ctx, &new)?;
            Ok(DraftCheckDto {
                missing_questions: c.missing,
                errors: c
                    .errors
                    .into_iter()
                    .map(|i| AgreementIssueDto {
                        question: i.question,
                        code: i.code.to_owned(),
                    })
                    .collect(),
                pdf: c.pdf,
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn revise_partnership(
    id: String,
    input: PartnershipInput,
    state: State<'_, AppSession>,
) -> Result<PartnershipDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let new = parse_input(ctx, input)?;
            let v = partnerships::revise(db, env, ctx, &id, new)?;
            full(db.conn(), env, ctx, &v)
        })
    })
}

/// Kelishuv bo'yicha nizo ochadi (faqat faol kelishuvda) — SPEC 2F.8. Ayrilib ketgan jurnal (fork)
/// ogohlantirishidan ham chaqiriladi: nizo taqsimotni bloklaydi, hakam qaror beradi.
#[tauri::command]
#[specta::specta]
pub fn open_agreement_dispute(
    agreement_id: String,
    claimant_party_id: String,
    subject: String,
    claim: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            services::events::open_dispute(
                db,
                env,
                ctx,
                &agreement_id,
                &claimant_party_id,
                &subject,
                &claim,
            )?;
            Ok(())
        })
    })
}

/// Sheriklikning joriy kelishuvi bo'yicha nizo ochadi (faqat faol kelishuvda) — SPEC 2F.8.
#[tauri::command]
#[specta::specta]
pub fn open_partnership_dispute(
    partnership_id: String,
    claimant_party_id: String,
    subject: String,
    claim: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let agreement = agreement_id_of(db.conn(), ctx, &partnership_id)?;
            services::events::open_dispute(
                db,
                env,
                ctx,
                &agreement,
                &claimant_party_id,
                &subject,
                &claim,
            )?;
            Ok(())
        })
    })
}

/// Hakam qarorini yozadi va nizoni yopadi (kelishuv yana faol bo'ladi) — SPEC 2F.8.
#[tauri::command]
#[specta::specta]
pub fn resolve_partnership_dispute(
    partnership_id: String,
    decision: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let agreement = agreement_id_of(db.conn(), ctx, &partnership_id)?;
            services::events::resolve_dispute(db, env, ctx, &agreement, &decision)?;
            Ok(())
        })
    })
}

/// «Vazifamni bajara olmayapman»: `duty_index`-dagi bandning mas'ul tomoni hodisani qayd etadi (SPEC 2F.4).
#[tauri::command]
#[specta::specta]
pub fn report_duty_incident(
    partnership_id: String,
    duty_index: u32,
    reason: String,
    proposal: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let agreement = agreement_id_of(db.conn(), ctx, &partnership_id)?;
            let index = usize::try_from(duty_index)
                .map_err(|_| ServiceError::Invalid("bunday vazifa bandi yo'q"))?;
            services::events::report_duty_incident(
                db, env, ctx, &agreement, index, &reason, &proposal,
            )?;
            Ok(())
        })
    })
}

fn agreement_id_of(
    conn: &storage::Connection,
    ctx: &Ctx,
    partnership_id: &str,
) -> Result<String, ServiceError> {
    services::agreements::agreement_of_partnership(conn, ctx, partnership_id)?
        .map(|a| a.meta.id)
        .ok_or(ServiceError::Invalid(
            "sheriklik kelishuvi topilmadi: sheriklikni qayta saqlang",
        ))
}

#[derive(Debug, Serialize, Type)]
pub struct ReviewPartyDto {
    pub party_id: String,
    pub name: String,
    /// `null` — hali javob yo'q.
    pub agree: Option<bool>,
    pub note: Option<String>,
}

#[derive(Debug, Serialize, Type)]
pub struct ReviewLineDto {
    /// `YYYY-MM-DD`.
    pub date: String,
    pub label: String,
    pub party: String,
    /// Formatlangan summa; yo'q bo'lsa bo'sh.
    pub amount: String,
    pub note: String,
}

/// Oylik ko'rik holati (SPEC 2F.5): zanjir tekshiruvi, tomonlar javobi va davr yozuvlari.
#[derive(Debug, Serialize, Type)]
pub struct ReviewDto {
    pub period: String,
    pub closed: bool,
    pub chain_length: u32,
    pub chain_intact: bool,
    pub broken_seq: Option<u32>,
    /// Yopilgandagi zanjir boshi (bayonnomada); hali yopilmagan bo'lsa `null`.
    pub recorded_head: Option<String>,
    /// Qayd etilgan boshi hozirgi zanjirga mos keladimi; yopilmagan bo'lsa `null`.
    pub head_matches: Option<bool>,
    pub parties: Vec<ReviewPartyDto>,
    pub ledger: Vec<ReviewLineDto>,
    pub incidents: Vec<ReviewLineDto>,
}

fn review_dto(v: &services::review::ReviewView) -> ReviewDto {
    let name_of = |pid: Option<&str>| {
        pid.and_then(|id| v.parties.iter().find(|p| p.party_id == id))
            .map_or_else(String::new, |p| p.name.clone())
    };
    let line = |e: &domain::JournalEntry| ReviewLineDto {
        date: domain::date_to_string(e.entry_date).unwrap_or_default(),
        label: services::review::kind_label(e.kind).to_owned(),
        party: name_of(e.party_id.as_deref()),
        amount: e
            .amount
            .map_or_else(String::new, |m| money::format_money(m, Locale::Uz)),
        note: e.note.clone(),
    };
    ReviewDto {
        period: v.period.clone(),
        closed: v.closed,
        chain_length: u32::try_from(v.chain.length).unwrap_or(u32::MAX),
        chain_intact: v.chain.broken_seq.is_none(),
        broken_seq: v.chain.broken_seq,
        recorded_head: v.recorded_head.clone(),
        head_matches: v.head_matches,
        parties: v
            .parties
            .iter()
            .map(|p| ReviewPartyDto {
                party_id: p.party_id.clone(),
                name: p.name.clone(),
                agree: p.agree,
                note: p.note.clone(),
            })
            .collect(),
        ledger: v.ledger.iter().map(line).collect(),
        incidents: v.incidents.iter().map(line).collect(),
    }
}

/// Davr (`YYYY-MM`) ko'rigi holati. Kelishuv bo'yicha: sheriklik yoki oilaviy kelishuv.
#[tauri::command]
#[specta::specta]
pub fn review_view(
    agreement_id: String,
    period: String,
    state: State<'_, AppSession>,
) -> Result<ReviewDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _env, ctx| {
            let v = services::review::view(db.conn(), ctx, &agreement_id, &period)?;
            Ok(review_dto(&v))
        })
    })
}

/// Sheriklik tomonining javobi: roziman (`agree = true`) yoki e'tiroz + izoh. Oilaviy kelishuvda
/// javob PIN bilan (`record_family_review_answer`) yoziladi.
#[tauri::command]
#[specta::specta]
pub fn record_review_answer(
    agreement_id: String,
    period: String,
    party_id: String,
    agree: bool,
    note: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let answer = if agree {
                services::review::ReviewAnswer::Agree
            } else {
                services::review::ReviewAnswer::Object(note)
            };
            services::review::record_answer(
                db,
                env,
                ctx,
                &agreement_id,
                &period,
                &party_id,
                answer,
            )?;
            Ok(())
        })
    })
}

/// Ko'rikni yakunlaydi: barcha tomonlar javob bergan bo'lishi kerak.
#[tauri::command]
#[specta::specta]
pub fn close_review(
    agreement_id: String,
    period: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            services::review::close(db, env, ctx, &agreement_id, &period)?;
            Ok(())
        })
    })
}

/// Hakam uchun ish papkasini OS «saqlash» oynasi orqali yozadi; bekor qilinsa `None` (SPEC 2F.8).
#[tauri::command]
#[specta::specta]
pub async fn export_dispute_folder_pdf(
    partnership_id: String,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    let bytes = with_session(&state, |s| {
        s.run(|db, _env, ctx| {
            let agreement = agreement_id_of(db.conn(), ctx, &partnership_id)?;
            services::events::folder_pdf(db.conn(), ctx, &agreement)
        })
    })?;
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("PDF", &["pdf"])
        .set_file_name("hakam-ish-papkasi.pdf")
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let mut path = file.into_path().map_err(|_| CommandError::Internal {
        message: "fayl yo'li noto'g'ri".into(),
    })?;
    if path
        .extension()
        .is_none_or(|e| !e.eq_ignore_ascii_case("pdf"))
    {
        path.set_extension("pdf");
    }
    std::fs::write(&path, bytes).map_err(|_| CommandError::Internal {
        message: "faylni yozib bo'lmadi".into(),
    })?;
    Ok(path.file_name().map(|n| n.to_string_lossy().into_owned()))
}

/// Ko'rik bayonnomasini OS «saqlash» oynasi orqali yozadi; bekor qilinsa `None`.
#[tauri::command]
#[specta::specta]
pub async fn export_review_pdf(
    agreement_id: String,
    period: String,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    let bytes = with_session(&state, |s| {
        s.run(|db, _env, ctx| services::review::pdf(db.conn(), ctx, &agreement_id, &period))
    })?;
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("PDF", &["pdf"])
        .set_file_name(format!("kocher-bayonnoma-{period}.pdf"))
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let mut path = file.into_path().map_err(|_| CommandError::Internal {
        message: "fayl yo'li noto'g'ri".into(),
    })?;
    if path
        .extension()
        .is_none_or(|e| !e.eq_ignore_ascii_case("pdf"))
    {
        path.set_extension("pdf");
    }
    std::fs::write(&path, bytes).map_err(|_| CommandError::Internal {
        message: "faylni yozib bo'lmadi".into(),
    })?;
    Ok(path.file_name().map(|n| n.to_string_lossy().into_owned()))
}

#[derive(Debug, Serialize, Type)]
pub struct CenterRowDto {
    pub agreement_id: String,
    pub title: String,
    pub kind: String,
    /// `DRAFT` | `SIGNED` | `ACTIVE` | `IN_DISPUTE` | `CLOSED`.
    pub status: String,
    pub status_label: String,
    pub version: u32,
    /// `YYYY-MM-DD`; javob berilmagan bo'lsa `null`.
    pub review_date: Option<String>,
    /// Yangilashgacha kunlar (manfiy — muddati o'tgan); 30 kundan ko'p bo'lsa `null`.
    pub days_to_review: Option<i32>,
    pub incidents: u32,
    pub dispute_open: bool,
    /// Joriy oy ko'rigi yopilganmi; faqat faol yoki nizoli kelishuvda, aks holda `null`.
    pub monthly_closed: Option<bool>,
}

/// Kelishuvlar markazi: barcha kelishuvlar holati, yangilash eslatmasi va ko'rik holati (D13A).
#[tauri::command]
#[specta::specta]
pub fn agreements_center(state: State<'_, AppSession>) -> Result<Vec<CenterRowDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let rows = services::events::center(db.conn(), env, ctx)?;
            Ok(rows
                .into_iter()
                .map(|r| CenterRowDto {
                    agreement_id: r.agreement_id,
                    title: r.title,
                    kind: r.kind,
                    status: r.status,
                    status_label: r.status_label,
                    version: r.version,
                    review_date: r.review_date.and_then(|d| domain::date_to_string(d).ok()),
                    days_to_review: r.days_to_review.and_then(|d| i32::try_from(d).ok()),
                    incidents: u32::try_from(r.incidents).unwrap_or(u32::MAX),
                    dispute_open: r.dispute_open,
                    monthly_closed: r.monthly_closed,
                })
                .collect())
        })
    })
}

/// Yillik yangilash: «o'zgarishsiz tasdiqlash» — yangi versiya; tomonlar qayta tasdiqlaydi (D13A).
#[tauri::command]
#[specta::specta]
pub fn confirm_partnership_unchanged(
    id: String,
    state: State<'_, AppSession>,
) -> Result<PartnershipDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let v = partnerships::confirm_unchanged(db, env, ctx, &id)?;
            full(db.conn(), env, ctx, &v)
        })
    })
}

/// Tomon (`party_id`, a'zo bo'lsa `pin` bilan) yoki guvoh (`witness`) joriy versiyani tasdiqlaydi.
#[tauri::command]
#[specta::specta]
pub fn sign_partnership(
    id: String,
    party_id: Option<String>,
    witness: Option<String>,
    arbiter: Option<bool>,
    pin: Option<String>,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let signer = match (party_id, witness, arbiter.unwrap_or(false)) {
                (Some(party_id), None, false) => Signer::Party { party_id, pin },
                (None, Some(name), false) => Signer::Witness { name },
                (None, None, true) => Signer::Arbiter,
                _ => return Err(ServiceError::Invalid("kim tasdiqlayotganini ko'rsating")),
            };
            partnerships::sign(db, env, ctx, &id, signer)
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn partnership_family_consent(
    id: String,
    member_id: String,
    pin: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| partnerships::family_consent(db, env, ctx, &id, &member_id, &pin))
    })
}

#[tauri::command]
#[specta::specta]
pub fn activate_partnership(
    id: String,
    state: State<'_, AppSession>,
) -> Result<PartnershipDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let v = partnerships::activate(db, env, ctx, &id)?;
            full(db.conn(), env, ctx, &v)
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn end_partnership(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| partnerships::end(db, env, ctx, &id))
    })
}

#[derive(Debug, Serialize, Type)]
pub struct ShareAmountDto {
    pub name: String,
    /// Zarar manfiy ko'rsatiladi.
    pub amount: MoneyDto,
}

/// Foyda yoki zarar taqsimoti hisobi. `outcome`: `PROFIT` | `LOSS`; `negligence_note` — mudarabada
/// ishchining beparvoligi izohi (bo'sh emas bo'lsa zarar ishchi zimmasiga o'tadi).
#[tauri::command]
#[specta::specta]
pub fn preview_distribution(
    id: String,
    outcome: String,
    amount_text: String,
    negligence_note: Option<String>,
    state: State<'_, AppSession>,
) -> Result<Vec<ShareAmountDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let o = match outcome.as_str() {
                "PROFIT" => Outcome::Profit,
                "LOSS" => Outcome::Loss,
                _ => return Err(ServiceError::Invalid("foyda yoki zararni tanlang")),
            };
            Ok(partnerships::preview_distribution(
                db.conn(),
                env,
                ctx,
                &id,
                o,
                amount(ctx, &amount_text)?,
                negligence_note.as_deref(),
            )?
            .into_iter()
            .map(|(name, a)| ShareAmountDto { name, amount: m(a) })
            .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_buyout_plan(
    id: String,
    provider_party_id: String,
    periods: u32,
    start_date: Option<String>,
    state: State<'_, AppSession>,
) -> Result<BuyoutDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let start = start_date
                .as_deref()
                .filter(|t| !t.trim().is_empty())
                .map(|t| {
                    date_from_str(t)
                        .map_err(|_| ServiceError::Invalid("sana YYYY-MM-DD ko'rinishida bo'lsin"))
                })
                .transpose()?;
            let b =
                partnerships::set_buyout(db, env, ctx, &id, &provider_party_id, periods, start)?;
            Ok(buyout_dto(&b))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn record_buyout_payment(
    id: String,
    amount_text: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            partnerships::record_buyout_payment(db, env, ctx, &id, amount(ctx, &amount_text)?, None)
        })
    })
}

/// Shartnoma PDF'ini OS «saqlash» oynasi orqali yozadi; bekor qilinsa `None`.
#[tauri::command]
#[specta::specta]
pub async fn export_contract_pdf(
    id: String,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    let bytes = with_session(&state, |s| {
        s.run(|db, env, ctx| partnerships::contract_pdf(db.conn(), env, ctx, &id))
    })?;
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("PDF", &["pdf"])
        .set_file_name("sheriklik-shartnomasi.pdf")
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let mut path = file.into_path().map_err(|_| CommandError::Internal {
        message: "fayl yo'li noto'g'ri".into(),
    })?;
    if path
        .extension()
        .is_none_or(|e| !e.eq_ignore_ascii_case("pdf"))
    {
        path.set_extension("pdf");
    }
    std::fs::write(&path, bytes).map_err(|_| CommandError::Internal {
        message: "faylni yozib bo'lmadi".into(),
    })?;
    Ok(path.file_name().map(|n| n.to_string_lossy().into_owned()))
}
