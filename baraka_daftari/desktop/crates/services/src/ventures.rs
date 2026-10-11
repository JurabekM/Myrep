//! Sheriklik kassa daftari — venture ledger (SPEC 2E.3): davrlar, kirim/xarajat, dalillar (chek rasmlari),
//! fors-major, davrni yopish va avtomatik taqsimot (+ buyout), sherik uchun hisobot.
//!
//! - Biznes puli uy pulidan **ajratilgan**: xonadon byudjetiga faqat taqsimlangan foyda ulushi
//!   (daromad sifatida) orqali bog'lanadi.
//! - **Yopilgan davr o'zgarmaydi**: xizmat qatlamida ham, bazada triggerlar bilan ham.
//! - Kapital egasi (xonadonda faqat shunday tomon bo'lsa) ledgerni faqat o'qiydi.
use domain::{
    net_result, settle_period, BuyoutDue, BuyoutPayment, Date, IncomeSourceType, LedgerKind, Meta,
    PartnershipStatus, PartyInput, PartyRole, PaymentChannel, PeriodStatus, VentureAttachment,
    VentureDistribution, VentureEntry, VenturePeriod,
};
use money::{format_money, Locale, Money};
use storage::Connection;
use storage::{repo, Database};

use crate::{
    income, local_date,
    partnerships::{self, PartnershipView},
    sum_money, Ctx, Env, ServiceError,
};

/// Bitta dalil uchun eng katta hajm (3 MB) va yozuvga eng ko'pi.
pub const MAX_ATTACHMENT_BYTES: usize = 3 * 1024 * 1024;
const MAX_ATTACHMENTS_PER_ENTRY: usize = 5;

#[derive(Debug, Clone)]
pub struct AttachmentMeta {
    pub id: String,
    pub filename: String,
    pub mime: String,
    pub size: usize,
}

#[derive(Debug, Clone)]
pub struct EntryView {
    pub entry: VentureEntry,
    pub attachments: Vec<AttachmentMeta>,
}

#[derive(Debug, Clone)]
pub struct DistributionRow {
    pub party_id: String,
    pub party_name: String,
    pub role: PartyRole,
    pub amount: Money,
    pub buyout_delta: Money,
}

#[derive(Debug, Clone)]
pub struct PeriodView {
    pub period: VenturePeriod,
    pub entries: Vec<EntryView>,
    pub income: Money,
    pub expenses: Money,
    pub net: Money,
    pub distribution: Vec<DistributionRow>,
}

#[derive(Debug, Clone)]
pub struct LedgerView {
    pub open: Option<PeriodView>,
    pub closed: Vec<PeriodView>,
    /// Xonadon faqat kapital egasi: ledger faqat o'qish rejimida.
    pub read_only: bool,
    pub active: bool,
}

fn read_only(v: &PartnershipView) -> bool {
    let mine: Vec<_> = v
        .parties
        .iter()
        .filter(|p| p.party.member_id.is_some())
        .collect();
    !mine.is_empty()
        && mine
            .iter()
            .all(|p| p.party.role == PartyRole::CapitalProvider)
}

fn periods(conn: &Connection, ctx: &Ctx, pid: &str) -> Result<Vec<VenturePeriod>, ServiceError> {
    let mut v: Vec<VenturePeriod> = repo::list::<VenturePeriod>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|p| p.partnership_id == pid)
        .collect();
    v.sort_by_key(|p| p.period_no);
    Ok(v)
}

fn period_view(
    conn: &Connection,
    ctx: &Ctx,
    pv: &PartnershipView,
    period: VenturePeriod,
) -> Result<PeriodView, ServiceError> {
    let attachments = repo::list::<VentureAttachment>(conn, &ctx.household_id)?;
    let mut entries: Vec<VentureEntry> = repo::list::<VentureEntry>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|e| e.period_id == period.meta.id)
        .collect();
    entries.sort_by(|a, b| (a.occurred_on, &a.meta.id).cmp(&(b.occurred_on, &b.meta.id)));
    let inc = sum_money(
        ctx.currency,
        entries
            .iter()
            .filter(|e| e.kind == LedgerKind::Income)
            .map(|e| e.amount),
    )?;
    let exp = sum_money(
        ctx.currency,
        entries
            .iter()
            .filter(|e| e.kind == LedgerKind::Expense)
            .map(|e| e.amount),
    )?;
    let dist = repo::list::<VentureDistribution>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|d| d.period_id == period.meta.id)
        .filter_map(|d| {
            let p = pv.parties.iter().find(|x| x.party.meta.id == d.party_id)?;
            Some(DistributionRow {
                party_id: d.party_id.clone(),
                party_name: p.party.name.clone(),
                role: p.party.role,
                amount: d.amount,
                buyout_delta: d.buyout_delta,
            })
        })
        .collect();
    Ok(PeriodView {
        net: net_result(inc, exp)?,
        income: inc,
        expenses: exp,
        distribution: dist,
        entries: entries
            .into_iter()
            .map(|e| EntryView {
                attachments: attachments
                    .iter()
                    .filter(|a| a.entry_id == e.meta.id)
                    .map(|a| AttachmentMeta {
                        id: a.meta.id.clone(),
                        filename: a.filename.clone(),
                        mime: a.mime.clone(),
                        size: a.data.len(),
                    })
                    .collect(),
                entry: e,
            })
            .collect(),
        period,
    })
}

/// # Errors
/// Sheriklik topilmasa yoki baza xatosi.
pub fn ledger(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    pid: &str,
) -> Result<LedgerView, ServiceError> {
    let pv = partnerships::view(conn, env, ctx, pid)?;
    let mut open = None;
    let mut closed = Vec::new();
    for p in periods(conn, ctx, pid)? {
        let v = period_view(conn, ctx, &pv, p)?;
        if v.period.status == PeriodStatus::Open {
            open = Some(v);
        } else {
            closed.push(v);
        }
    }
    Ok(LedgerView {
        open,
        closed,
        read_only: read_only(&pv),
        active: pv.partnership.status == PartnershipStatus::Active,
    })
}

fn require_writable(pv: &PartnershipView) -> Result<(), ServiceError> {
    if pv.partnership.status != PartnershipStatus::Active {
        return Err(ServiceError::Invalid(
            "daftar faqat faol (tasdiqlangan) sheriklik uchun yuritiladi",
        ));
    }
    if read_only(pv) {
        return Err(ServiceError::Invalid(
            "siz kapital egasisiz: daftarni faqat o'qish mumkin",
        ));
    }
    Ok(())
}

fn open_period(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    pid: &str,
) -> Result<VenturePeriod, ServiceError> {
    let all = periods(db.conn(), ctx, pid)?;
    if let Some(p) = all.iter().find(|p| p.status == PeriodStatus::Open) {
        return Ok(p.clone());
    }
    let p = VenturePeriod {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        partnership_id: pid.to_owned(),
        period_no: u32::try_from(all.len() + 1).unwrap_or(u32::MAX),
        start_date: local_date(env.clock.now()),
        end_date: None,
        status: PeriodStatus::Open,
        net: None,
    };
    repo::insert(db.conn(), &p)?;
    Ok(p)
}

/// Yangi yozuv ma'lumotlari. `force_majeure` — hodisa izohi (`description`) majburiy, dalillar keyin
/// biriktiriladi.
#[derive(Debug, Clone)]
pub struct NewEntry<'a> {
    pub kind: LedgerKind,
    pub description: &'a str,
    pub amount: Money,
    pub occurred_on: Option<Date>,
    pub note: Option<&'a str>,
    pub force_majeure: bool,
}

/// Yangi yozuv.
///
/// # Errors
/// Faol bo'lmagan sheriklik, faqat o'qish rejimi, sana ochiq davrdan oldin, summa/izoh yaroqsiz.
pub fn add_entry(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    pid: &str,
    new: NewEntry<'_>,
) -> Result<VentureEntry, ServiceError> {
    let NewEntry {
        kind,
        description,
        amount,
        occurred_on,
        note,
        force_majeure,
    } = new;
    let pv = partnerships::view(db.conn(), env, ctx, pid)?;
    require_writable(&pv)?;
    let description = description.split_whitespace().collect::<Vec<_>>().join(" ");
    if description.is_empty() || description.chars().count() > 120 {
        return Err(ServiceError::Invalid("izoh 1..120 belgi bo'lishi kerak"));
    }
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    if force_majeure && kind != LedgerKind::Expense {
        return Err(ServiceError::Invalid(
            "fors-major xarajat sifatida qayd etiladi",
        ));
    }
    let period = open_period(db, env, ctx, pid)?;
    let date = occurred_on.unwrap_or_else(|| local_date(env.clock.now()));
    if date < period.start_date {
        return Err(ServiceError::Invalid(
            "sana joriy (ochiq) davr boshidan oldin bo'lmasin: yopilgan davr o'zgarmaydi",
        ));
    }
    let e = VentureEntry {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        partnership_id: pid.to_owned(),
        period_id: period.meta.id,
        kind,
        description,
        amount,
        occurred_on: date,
        note: note
            .map(str::trim)
            .filter(|n| !n.is_empty())
            .map(|n| n.chars().take(300).collect()),
        force_majeure,
    };
    repo::insert(db.conn(), &e)?;
    Ok(e)
}

fn load_entry(
    conn: &Connection,
    ctx: &Ctx,
    id: &str,
) -> Result<(VentureEntry, VenturePeriod), ServiceError> {
    let e = repo::get::<VentureEntry>(conn, id)?.ok_or(ServiceError::NotFound)?;
    if e.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    let p = repo::get::<VenturePeriod>(conn, &e.period_id)?.ok_or(ServiceError::NotFound)?;
    Ok((e, p))
}

const CLOSED_MSG: &str = "yopilgan davr o'zgarmaydi";

/// # Errors
/// Topilmasa, davr yopilgan yoki faqat o'qish rejimi.
pub fn remove_entry(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    entry_id: &str,
) -> Result<(), ServiceError> {
    let (e, p) = load_entry(db.conn(), ctx, entry_id)?;
    if p.status == PeriodStatus::Closed {
        return Err(ServiceError::Invalid(CLOSED_MSG));
    }
    require_writable(&partnerships::view(db.conn(), env, ctx, &e.partnership_id)?)?;
    repo::soft_delete::<VentureEntry>(db.conn(), entry_id, env.clock.now())?;
    Ok(())
}

fn sniff(data: &[u8]) -> Option<&'static str> {
    if data.starts_with(b"\x89PNG\r\n\x1a\n") {
        Some("image/png")
    } else if data.starts_with(&[0xFF, 0xD8, 0xFF]) {
        Some("image/jpeg")
    } else if data.starts_with(b"%PDF-") {
        Some("application/pdf")
    } else {
        None
    }
}

/// Yozuvga chek/rasm (PNG, JPEG, PDF; ≤ 3 MB; ≤ 5 ta) biriktiradi. Tur fayl mazmunidan aniqlanadi.
///
/// # Errors
/// Yozuv topilmasa, davr yopilgan, fayl turi/hajmi yaroqsiz yoki limit oshgan.
pub fn attach(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    entry_id: &str,
    filename: &str,
    data: Vec<u8>,
) -> Result<AttachmentMeta, ServiceError> {
    let (e, p) = load_entry(db.conn(), ctx, entry_id)?;
    if p.status == PeriodStatus::Closed {
        return Err(ServiceError::Invalid(CLOSED_MSG));
    }
    require_writable(&partnerships::view(db.conn(), env, ctx, &e.partnership_id)?)?;
    if data.is_empty() || data.len() > MAX_ATTACHMENT_BYTES {
        return Err(ServiceError::Invalid("fayl hajmi 3 MB dan oshmasin"));
    }
    let mime = sniff(&data).ok_or(ServiceError::Invalid(
        "faqat PNG, JPEG yoki PDF qabul qilinadi",
    ))?;
    let count = repo::list::<VentureAttachment>(db.conn(), &ctx.household_id)?
        .iter()
        .filter(|a| a.entry_id == entry_id)
        .count();
    if count >= MAX_ATTACHMENTS_PER_ENTRY {
        return Err(ServiceError::Invalid("bir yozuvga ko'pi bilan 5 ta dalil"));
    }
    let name: String = filename
        .rsplit(['/', '\\'])
        .next()
        .unwrap_or("dalil")
        .chars()
        .filter(|c| !c.is_control())
        .take(80)
        .collect();
    let a = VentureAttachment {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        entry_id: entry_id.to_owned(),
        filename: if name.is_empty() {
            "dalil".into()
        } else {
            name
        },
        mime: mime.to_owned(),
        data,
    };
    repo::insert(db.conn(), &a)?;
    Ok(AttachmentMeta {
        id: a.meta.id,
        filename: a.filename,
        mime: a.mime,
        size: a.data.len(),
    })
}

/// Dalil mazmuni (faqat o'qish; kapital egasi ham ko'ra oladi).
///
/// # Errors
/// Topilmasa.
pub fn attachment_data(
    conn: &Connection,
    ctx: &Ctx,
    id: &str,
) -> Result<(String, String, Vec<u8>), ServiceError> {
    let a = repo::get::<VentureAttachment>(conn, id)?.ok_or(ServiceError::NotFound)?;
    if a.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    Ok((a.filename, a.mime, a.data))
}

fn party_inputs(pv: &PartnershipView) -> Vec<PartyInput> {
    pv.parties
        .iter()
        .map(|x| PartyInput {
            role: x.party.role,
            capital: x.capital_total,
            share_bp: x.party.share_bp,
        })
        .collect()
}

/// Davrni yopadi: natija 2E.1 qoidalari bo'yicha taqsimlanadi (foyda bo'lsa buyout to'lovi ham),
/// taqsimot yozuvlari saqlanadi, davr o'zgarmas bo'ladi va keyingi davr ochiladi. A'zo tomonlarning
/// foyda ulushi xonadon daromadiga yoziladi (biznes puli bilan yagona bog'lanish).
///
/// # Errors
/// Ochiq davr yo'q, sana yaroqsiz, beparvolik izohisiz yoki hisob xatosi.
pub fn close_period(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    pid: &str,
    end_date: Option<Date>,
    negligence_note: Option<&str>,
) -> Result<PeriodView, ServiceError> {
    let pv = partnerships::view(db.conn(), env, ctx, pid)?;
    require_writable(&pv)?;
    let open = periods(db.conn(), ctx, pid)?
        .into_iter()
        .find(|p| p.status == PeriodStatus::Open)
        .ok_or(ServiceError::Invalid("yopiladigan ochiq davr yo'q"))?;
    let view = period_view(db.conn(), ctx, &pv, open.clone())?;
    let end = end_date.unwrap_or_else(|| local_date(env.clock.now()));
    let last = view.entries.iter().map(|e| e.entry.occurred_on).max();
    if end < open.start_date || last.is_some_and(|l| end < l) {
        return Err(ServiceError::Invalid(
            "yopilish sanasi davr boshidan va oxirgi yozuvdan oldin bo'lmasin",
        ));
    }
    if view.entries.is_empty() {
        return Err(ServiceError::Invalid("bo'sh davrni yopib bo'lmaydi"));
    }
    let negligence = negligence_note.is_some_and(|n| !n.trim().is_empty());
    if negligence_note.is_some() && !negligence {
        return Err(ServiceError::Invalid("beparvolik izohini yozing"));
    }
    // Buyout: reja bo'lsa va tugamagan bo'lsa — shu davr raqamiga mos teng bo'lak.
    let bo = partnerships::buyout_view(db.conn(), env, ctx, pid)?;
    let mut due: Option<(BuyoutDue, String)> = None;
    if let Some(b) = &bo {
        let seller = pv
            .parties
            .iter()
            .position(|x| x.party.meta.id == b.plan.provider_party_id);
        let payer = pv
            .parties
            .iter()
            .position(|x| x.party.meta.id != b.plan.provider_party_id);
        let idx = usize::try_from(open.period_no.saturating_sub(1)).unwrap_or(usize::MAX);
        let left = b.actual.rows.last().map_or(b.stake, |r| r.remaining);
        if let (Some(seller), Some(payer), Some(row)) = (seller, payer, b.planned.rows.get(idx)) {
            let due_amt = Money::new(row.applied.minor().min(left.minor()), ctx.currency);
            if due_amt.minor() > 0 {
                due = Some((
                    BuyoutDue {
                        payer,
                        seller,
                        due: due_amt,
                    },
                    b.plan.meta.id.clone(),
                ));
            }
        }
    }
    let settlement = settle_period(
        pv.partnership.kind,
        view.net,
        &party_inputs(&pv),
        negligence,
        due.as_ref().map(|(d, _)| *d),
    )?;
    let now = env.clock.now();
    let next_start = end.next_day().unwrap_or(end);
    db.transaction::<(), ServiceError>(|tx| {
        for (i, share) in settlement.shares.iter().enumerate() {
            let delta = match &due {
                Some((d, _)) if i == d.payer => {
                    Money::new(-settlement.buyout_applied.minor(), ctx.currency)
                }
                Some((d, _)) if i == d.seller => settlement.buyout_applied,
                _ => ctx.zero(),
            };
            repo::insert(
                tx,
                &VentureDistribution {
                    meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                    period_id: open.meta.id.clone(),
                    party_id: pv.parties[i].party.meta.id.clone(),
                    amount: *share,
                    buyout_delta: delta,
                },
            )?;
        }
        if settlement.buyout_applied.minor() > 0 {
            if let Some((_, plan_id)) = &due {
                repo::insert(
                    tx,
                    &BuyoutPayment {
                        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                        plan_id: plan_id.clone(),
                        paid_on: end,
                        amount: settlement.buyout_applied,
                    },
                )?;
            }
        }
        let mut closed = open.clone();
        closed.status = PeriodStatus::Closed;
        closed.end_date = Some(end);
        closed.net = Some(view.net);
        repo::update(tx, &closed, now)?;
        repo::insert(
            tx,
            &VenturePeriod {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                partnership_id: pid.to_owned(),
                period_no: open.period_no + 1,
                start_date: next_start,
                end_date: None,
                status: PeriodStatus::Open,
                net: None,
            },
        )?;
        Ok(())
    })?;
    // Xonadon a'zolarining foyda ulushi → daromad (biznes puli uy pulidan ajratilgan; yagona bog'lanish).
    for (i, share) in settlement.shares.iter().enumerate() {
        let party = &pv.parties[i].party;
        let (Some(member), true) = (&party.member_id, share.minor() > 0) else {
            continue;
        };
        income::record(
            db,
            env,
            ctx,
            income::NewIncome {
                amount: *share,
                source: "PARTNERSHIP".into(),
                channel: PaymentChannel::Card,
                received_on: Some(end),
                share: None,
                member_id: Some(member.clone()),
                source_type: Some(if party.role == PartyRole::Worker {
                    IncomeSourceType::Ter
                } else {
                    IncomeSourceType::Tavakkal
                }),
            },
        )?;
    }
    let pv2 = partnerships::view(db.conn(), env, ctx, pid)?;
    let closed =
        repo::get::<VenturePeriod>(db.conn(), &open.meta.id)?.ok_or(ServiceError::NotFound)?;
    period_view(db.conn(), ctx, &pv2, closed)
}

/// Yopilgan davr uchun sherik hisoboti (PDF).
///
/// # Errors
/// Davr topilmasa yoki ochiq bo'lsa, PDF xatosi.
pub fn report_pdf(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    period_id: &str,
) -> Result<Vec<u8>, ServiceError> {
    let p = repo::get::<VenturePeriod>(conn, period_id)?.ok_or(ServiceError::NotFound)?;
    if p.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    if p.status != PeriodStatus::Closed {
        return Err(ServiceError::Invalid("hisobot faqat yopilgan davr uchun"));
    }
    let pv = partnerships::view(conn, env, ctx, &p.partnership_id)?;
    let v = period_view(conn, ctx, &pv, p.clone())?;
    let fm = |m: Money| format_money(m, Locale::Uz);
    let date = |d: Date| domain::date_to_string(d).unwrap_or_default();
    let role = |r: PartyRole| match r {
        PartyRole::CapitalProvider => "Kapital egasi",
        PartyRole::Worker => "Ishchi",
        PartyRole::Partner => "Sherik",
    };
    let applied: i64 = v
        .distribution
        .iter()
        .map(|d| d.buyout_delta.minor().max(0))
        .sum();
    let doc = pdf::PeriodReportDoc {
        title: format!("{} \u{b7} davr hisoboti", pv.partnership.name),
        subtitle: format!(
            "{}-davr \u{b7} {} \u{2014} {}",
            p.period_no,
            date(p.start_date),
            p.end_date.map(date).unwrap_or_default()
        ),
        entries: v
            .entries
            .iter()
            .map(|e| pdf::ReportEntry {
                date: date(e.entry.occurred_on),
                kind: match e.entry.kind {
                    LedgerKind::Income => "Kirim",
                    LedgerKind::Expense => "Xarajat",
                }
                .to_owned(),
                description: e.entry.description.clone(),
                amount: fm(e.entry.amount),
                force_majeure: e.entry.force_majeure,
                evidence: e.attachments.len(),
            })
            .collect(),
        totals: vec![
            ("Kirim".to_owned(), fm(v.income)),
            ("Xarajat".to_owned(), fm(v.expenses)),
            ("Sof natija".to_owned(), fm(v.net)),
        ],
        distribution: v
            .distribution
            .iter()
            .map(|d| (d.party_name.clone(), role(d.role).to_owned(), fm(d.amount)))
            .collect(),
        buyout_note: (applied > 0).then(|| {
            format!(
                "Buyout: {} sotuvchi tomon ulushiga o'tdi (to'lovchining foyda ulushidan).",
                fm(Money::new(applied, ctx.currency))
            )
        }),
        disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    };
    pdf::period_report(&doc).map_err(|_| ServiceError::Invalid("hisobot PDF'ini yaratib bo'lmadi"))
}
