//! D13 commandlari: sheriklik kassa daftari (venture ledger), dalillar, davr hisoboti, «Hunardan ishga»,
//! taklif detektori. Fayllar OS dialogi orqali Rust tomonida o'qiladi/yoziladi.

use domain::{date_from_str, date_to_string, LedgerKind, OfferAnswers};
use money::{parse_amount, Locale, Money};
use serde::{Deserialize, Serialize};
use services::{
    crafts::{self, IdeaView, NewIdea},
    ventures::{self, AttachmentMeta, EntryView, LedgerView, NewEntry, PeriodView},
    Ctx, ServiceError,
};
use specta::Type;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

use crate::{
    commands::{with_session, AppSession, CommandError},
    dto::MoneyDto,
    partnerships::{full, PartnershipDto},
};

const LOCALE: Locale = Locale::Uz;

fn m(v: Money) -> MoneyDto {
    MoneyDto::from_money(v, LOCALE)
}

fn amount(ctx: &Ctx, text: &str) -> Result<Money, ServiceError> {
    Ok(parse_amount(text, ctx.currency)?)
}

fn ds(d: domain::Date) -> String {
    date_to_string(d).unwrap_or_default()
}

fn opt_date(text: Option<&str>) -> Result<Option<domain::Date>, ServiceError> {
    text.filter(|t| !t.trim().is_empty())
        .map(|t| {
            date_from_str(t)
                .map_err(|_| ServiceError::Invalid("sana YYYY-MM-DD ko'rinishida bo'lsin"))
        })
        .transpose()
}

fn internal(msg: &str) -> CommandError {
    CommandError::Internal {
        message: msg.into(),
    }
}

// ---------------------------------------------------------------- ledger

#[derive(Debug, Serialize, Type)]
pub struct AttachmentDto {
    pub id: String,
    pub filename: String,
    pub mime: String,
    pub size: u32,
}

fn att_dto(a: &AttachmentMeta) -> AttachmentDto {
    AttachmentDto {
        id: a.id.clone(),
        filename: a.filename.clone(),
        mime: a.mime.clone(),
        size: u32::try_from(a.size).unwrap_or(u32::MAX),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct EntryDto {
    pub id: String,
    /// `INCOME` | `EXPENSE`.
    pub kind: String,
    pub description: String,
    pub amount: MoneyDto,
    pub occurred_on: String,
    pub note: Option<String>,
    pub force_majeure: bool,
    pub attachments: Vec<AttachmentDto>,
}

fn entry_dto(e: &EntryView) -> EntryDto {
    EntryDto {
        id: e.entry.meta.id.clone(),
        kind: e.entry.kind.as_str().to_owned(),
        description: e.entry.description.clone(),
        amount: m(e.entry.amount),
        occurred_on: ds(e.entry.occurred_on),
        note: e.entry.note.clone(),
        force_majeure: e.entry.force_majeure,
        attachments: e.attachments.iter().map(att_dto).collect(),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct DistributionDto {
    pub party_name: String,
    /// `CAPITAL_PROVIDER` | `WORKER` | `PARTNER`.
    pub role: String,
    pub amount: MoneyDto,
    pub buyout_delta: MoneyDto,
}

#[derive(Debug, Serialize, Type)]
pub struct PeriodDto {
    pub id: String,
    pub period_no: u32,
    pub start_date: String,
    pub end_date: Option<String>,
    pub closed: bool,
    pub income: MoneyDto,
    pub expenses: MoneyDto,
    pub net: MoneyDto,
    pub entries: Vec<EntryDto>,
    pub distribution: Vec<DistributionDto>,
}

fn period_dto(p: &PeriodView) -> PeriodDto {
    PeriodDto {
        id: p.period.meta.id.clone(),
        period_no: p.period.period_no,
        start_date: ds(p.period.start_date),
        end_date: p.period.end_date.map(ds),
        closed: p.period.status == domain::PeriodStatus::Closed,
        income: m(p.income),
        expenses: m(p.expenses),
        net: m(p.net),
        entries: p.entries.iter().map(entry_dto).collect(),
        distribution: p
            .distribution
            .iter()
            .map(|d| DistributionDto {
                party_name: d.party_name.clone(),
                role: d.role.as_str().to_owned(),
                amount: m(d.amount),
                buyout_delta: m(d.buyout_delta),
            })
            .collect(),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct LedgerDto {
    pub open: Option<PeriodDto>,
    pub closed: Vec<PeriodDto>,
    /// Xonadon faqat kapital egasi: o'qish rejimi.
    pub read_only: bool,
    pub active: bool,
    /// «Katta foyda»: taqsimotdan oldin 4–5-bandlarni qayta o'qish va tasdiq kerak (SPEC 2F.7).
    pub spike_alert: bool,
}

fn ledger_dto(l: &LedgerView) -> LedgerDto {
    LedgerDto {
        open: l.open.as_ref().map(period_dto),
        closed: l.closed.iter().map(period_dto).collect(),
        read_only: l.read_only,
        active: l.active,
        spike_alert: l.spike_alert,
    }
}

#[tauri::command]
#[specta::specta]
pub fn venture_ledger(
    partnership_id: String,
    state: State<'_, AppSession>,
) -> Result<LedgerDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            Ok(ledger_dto(&ventures::ledger(
                db.conn(),
                env,
                ctx,
                &partnership_id,
            )?))
        })
    })
}

#[derive(Debug, Deserialize, Type)]
pub struct EntryInput {
    /// `INCOME` | `EXPENSE`.
    pub kind: String,
    pub description: String,
    pub amount: String,
    pub occurred_on: Option<String>,
    pub note: Option<String>,
    pub force_majeure: bool,
}

#[tauri::command]
#[specta::specta]
pub fn add_venture_entry(
    partnership_id: String,
    input: EntryInput,
    state: State<'_, AppSession>,
) -> Result<EntryDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let kind = LedgerKind::parse(&input.kind)
                .ok_or(ServiceError::Invalid("kirim yoki xarajatni tanlang"))?;
            let e = ventures::add_entry(
                db,
                env,
                ctx,
                &partnership_id,
                NewEntry {
                    kind,
                    description: &input.description,
                    amount: amount(ctx, &input.amount)?,
                    occurred_on: opt_date(input.occurred_on.as_deref())?,
                    note: input.note.as_deref(),
                    force_majeure: input.force_majeure,
                },
            )?;
            Ok(EntryDto {
                id: e.meta.id,
                kind: e.kind.as_str().to_owned(),
                description: e.description,
                amount: m(e.amount),
                occurred_on: ds(e.occurred_on),
                note: e.note,
                force_majeure: e.force_majeure,
                attachments: vec![],
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_venture_entry(
    entry_id: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| ventures::remove_entry(db, env, ctx, &entry_id))
    })
}

/// Chek/rasm tanlash oynasi (PNG, JPEG, PDF) — fayl Rust tomonida o'qiladi. Bekor qilinsa `None`.
#[tauri::command]
#[specta::specta]
pub async fn attach_evidence(
    entry_id: String,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<AttachmentDto>, CommandError> {
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("Chek / rasm", &["png", "jpg", "jpeg", "pdf"])
        .blocking_pick_file()
    else {
        return Ok(None);
    };
    let path = file
        .into_path()
        .map_err(|_| internal("fayl yo'li noto'g'ri"))?;
    let meta = std::fs::metadata(&path).map_err(|_| internal("faylni o'qib bo'lmadi"))?;
    if meta.len() > u64::try_from(ventures::MAX_ATTACHMENT_BYTES).unwrap_or(u64::MAX) {
        return Err(CommandError::Invalid {
            message: "fayl hajmi 3 MB dan oshmasin".into(),
        });
    }
    let data = std::fs::read(&path).map_err(|_| internal("faylni o'qib bo'lmadi"))?;
    let name = path
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default();
    let a = with_session(&state, |s| {
        s.run(|db, env, ctx| ventures::attach(db, env, ctx, &entry_id, &name, data))
    })?;
    Ok(Some(att_dto(&a)))
}

/// Dalilni OS «saqlash» oynasi orqali nusxalaydi.
#[tauri::command]
#[specta::specta]
pub async fn export_evidence(
    id: String,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    let (name, _mime, data) = with_session(&state, |s| {
        s.run(|db, _, ctx| ventures::attachment_data(db.conn(), ctx, &id))
    })?;
    let Some(file) = app
        .dialog()
        .file()
        .set_file_name(&name)
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let path = file
        .into_path()
        .map_err(|_| internal("fayl yo'li noto'g'ri"))?;
    std::fs::write(&path, data).map_err(|_| internal("faylni yozib bo'lmadi"))?;
    Ok(path.file_name().map(|n| n.to_string_lossy().into_owned()))
}

#[tauri::command]
#[specta::specta]
pub fn close_venture_period(
    partnership_id: String,
    end_date: Option<String>,
    negligence_note: Option<String>,
    spike_ack: bool,
    state: State<'_, AppSession>,
) -> Result<PeriodDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let p = ventures::close_period(
                db,
                env,
                ctx,
                &partnership_id,
                opt_date(end_date.as_deref())?,
                negligence_note.as_deref(),
                spike_ack,
            )?;
            Ok(period_dto(&p))
        })
    })
}

/// Yopilgan davr hisoboti (PDF) — OS «saqlash» oynasi orqali.
#[tauri::command]
#[specta::specta]
pub async fn export_period_report(
    period_id: String,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    let bytes = with_session(&state, |s| {
        s.run(|db, env, ctx| ventures::report_pdf(db.conn(), env, ctx, &period_id))
    })?;
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("PDF", &["pdf"])
        .set_file_name("davr-hisoboti.pdf")
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let mut path = file
        .into_path()
        .map_err(|_| internal("fayl yo'li noto'g'ri"))?;
    if path
        .extension()
        .is_none_or(|e| !e.eq_ignore_ascii_case("pdf"))
    {
        path.set_extension("pdf");
    }
    std::fs::write(&path, bytes).map_err(|_| internal("faylni yozib bo'lmadi"))?;
    Ok(path.file_name().map(|n| n.to_string_lossy().into_owned()))
}

// ---------------------------------------------------------------- hunardan ishga

#[derive(Debug, Deserialize, Type)]
pub struct CapexInput {
    pub item: String,
    pub price: String,
}

#[derive(Debug, Deserialize, Type)]
pub struct IdeaInput {
    pub name: String,
    pub note: Option<String>,
    pub capex: Vec<CapexInput>,
    /// Oylik kirim: pessimistik, o'rtacha, optimistik.
    pub income: Vec<String>,
    pub expense: Vec<String>,
    /// Sheriklik bo'lsa mening ulushim (bp).
    pub share_bp: Option<u32>,
}

#[derive(Debug, Serialize, Type)]
pub struct CraftScenarioDto {
    pub net: MoneyDto,
    pub net_after_share: MoneyDto,
    pub payback_months: Option<u32>,
}

#[derive(Debug, Serialize, Type)]
pub struct IdeaDto {
    pub id: String,
    pub name: String,
    pub note: Option<String>,
    pub capex: Vec<CapexItemDto>,
    pub capex_total: MoneyDto,
    pub share_bp: Option<u32>,
    /// Pessimistik, o'rtacha, optimistik.
    pub scenarios: Vec<CraftScenarioDto>,
}

#[derive(Debug, Serialize, Type)]
pub struct CapexItemDto {
    pub item: String,
    pub price: MoneyDto,
}

fn idea_dto(v: &IdeaView) -> IdeaDto {
    IdeaDto {
        id: v.idea.meta.id.clone(),
        name: v.idea.name.clone(),
        note: v.idea.note.clone(),
        capex: v
            .capex
            .iter()
            .map(|c| CapexItemDto {
                item: c.item.clone(),
                price: m(c.price),
            })
            .collect(),
        capex_total: m(v.capex_total),
        share_bp: v.idea.share_bp,
        scenarios: v
            .scenarios
            .iter()
            .map(|s| CraftScenarioDto {
                net: m(s.net),
                net_after_share: m(s.net_after_share),
                payback_months: s.payback_months,
            })
            .collect(),
    }
}

fn three(ctx: &Ctx, v: &[String]) -> Result<[Money; 3], ServiceError> {
    let bad = || {
        ServiceError::Invalid("uch stsenariy (pessimistik, o'rtacha, optimistik) summasini yozing")
    };
    let [a, b, c] = v else {
        return Err(bad());
    };
    Ok([amount(ctx, a)?, amount(ctx, b)?, amount(ctx, c)?])
}

#[tauri::command]
#[specta::specta]
pub fn list_craft_ideas(state: State<'_, AppSession>) -> Result<Vec<IdeaDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(crafts::list_ideas(db.conn(), ctx)?
                .iter()
                .map(idea_dto)
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_craft_idea(
    input: IdeaInput,
    state: State<'_, AppSession>,
) -> Result<IdeaDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let v = crafts::add_idea(
                db,
                env,
                ctx,
                NewIdea {
                    name: input.name,
                    note: input.note,
                    capex: input
                        .capex
                        .iter()
                        .map(|c| Ok((c.item.clone(), amount(ctx, &c.price)?)))
                        .collect::<Result<Vec<_>, ServiceError>>()?,
                    income: three(ctx, &input.income)?,
                    expense: three(ctx, &input.expense)?,
                    share_bp: input.share_bp,
                },
            )?;
            Ok(idea_dto(&v))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_craft_idea(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| crafts::remove_idea(db, env, ctx, &id))
    })
}

/// Bir bosishda sheriklik shartnomasi qoralamasi.
#[tauri::command]
#[specta::specta]
pub fn craft_to_contract(
    idea_id: String,
    provider_name: String,
    state: State<'_, AppSession>,
) -> Result<PartnershipDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let v = crafts::idea_to_contract_draft(db, env, ctx, &idea_id, &provider_name)?;
            full(db.conn(), env, ctx, &v)
        })
    })
}

// ---------------------------------------------------------------- taklif detektori

#[derive(Debug, Deserialize, Type)]
pub struct OfferInput {
    pub guaranteed_profit: bool,
    pub loss_shared: bool,
    pub real_goods_or_work: bool,
    pub requires_recruiting: bool,
    pub pressure_to_hurry: bool,
    pub written_contract: bool,
}

#[derive(Debug, Serialize, Type)]
pub struct OfferDto {
    /// `GREEN` | `YELLOW` | `RED`.
    pub verdict: String,
    pub flags: Vec<String>,
}

#[tauri::command]
#[specta::specta]
pub fn check_offer(input: OfferInput) -> OfferDto {
    let r = crafts::check_offer(OfferAnswers {
        guaranteed_profit: input.guaranteed_profit,
        loss_shared: input.loss_shared,
        real_goods_or_work: input.real_goods_or_work,
        requires_recruiting: input.requires_recruiting,
        pressure_to_hurry: input.pressure_to_hurry,
        written_contract: input.written_contract,
    });
    OfferDto {
        verdict: r.verdict.code().to_owned(),
        flags: r.flags.iter().map(|f| f.code().to_owned()).collect(),
    }
}
