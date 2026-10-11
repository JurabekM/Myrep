//! D12 commandlari (5-qonun): sheriklik shartnomasi, tasdiqlar, taqsimot hisobi, buyout.

use domain::{
    date_from_str, date_to_string, CapitalKind, Outcome, PartnershipKind, PartyRole, ReportPeriod,
};
use money::{parse_amount, Locale, Money};
use serde::{Deserialize, Serialize};
use services::{
    partnerships::{
        self, BuyoutView, NewCapital, NewPartnership, NewParty, PartnershipView, Signer,
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
    Ok(NewPartnership {
        name: i.name,
        kind,
        term_months: i.term_months,
        report_period,
        end_clause: i.end_clause,
        dispute_clause: i.dispute_clause,
        witnesses: i.witnesses,
        parties,
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
    /// `PARTY_SIGNATURES` | `WITNESS_SIGNATURES` | `FAMILY_CONSENT` | `GATE_CLOSED`.
    pub blocker: Option<String>,
    pub buyout: Option<BuyoutDto>,
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

/// Tomon (`party_id`, a'zo bo'lsa `pin` bilan) yoki guvoh (`witness`) joriy versiyani tasdiqlaydi.
#[tauri::command]
#[specta::specta]
pub fn sign_partnership(
    id: String,
    party_id: Option<String>,
    witness: Option<String>,
    pin: Option<String>,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let signer = match (party_id, witness) {
                (Some(party_id), None) => Signer::Party { party_id, pin },
                (None, Some(name)) => Signer::Witness { name },
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
