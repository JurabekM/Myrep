//! Oylik ochiq hisob ko'rigi (SPEC 2F.5, 2F.6). Har bir tomon davr uchun «ko'rdim, roziman» yoki
//! «e'tirozim bor + izoh» deb javob beradi. Yakunda bayonnoma uchun zanjir boshi jurnalga qayd etiladi
//! (`REVIEW_CLOSED`, `reference` = «davr|boshi»): keyin yozuv o'zgarsa, qayd etilgan boshi mos kelmaydi.
//!
//! Davr `YYYY-MM` ko'rinishida. Javoblar `REVIEW_ACK` (oxirgisi amal qiladi), yakun `REVIEW_CLOSED`.

use domain::{
    chain_head, date_to_string, AgreementStatus, AgreementType, Answer, JournalEntry, JournalKind,
};
use money::{format_money, Locale};
use storage::{Connection, Database};

use crate::agreements;
use crate::journal::{self, ChainCheck};
use crate::{local_date, Ctx, Env, ServiceError};

const AGREE_NOTE: &str = "Ko'rdim, roziman";
const OBJECT_PREFIX: &str = "E'tiroz: ";

/// Tomonning shu davrdagi javobi (oxirgi `REVIEW_ACK`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartyAnswer {
    pub party_id: String,
    pub name: String,
    /// `Some(true)` — roziman; `Some(false)` — e'tiroz; `None` — hali javob yo'q.
    pub agree: Option<bool>,
    /// E'tiroz izohi (faqat `Some(false)` bo'lganda).
    pub note: Option<String>,
}

/// Davr ko'rigi holati: yozuvlar, hodisalar, tomonlar javobi va zanjir tekshiruvi.
#[derive(Debug, Clone)]
pub struct ReviewView {
    pub period: String,
    pub closed: bool,
    pub chain: ChainCheck,
    /// Yopilganda bayonnomaga yozilgan zanjir boshi.
    pub recorded_head: Option<String>,
    /// Qayd etilgan boshi hozirgi (qayta hisoblangan) zanjir bilan mos keladimi. Yopilmagan bo'lsa `None`.
    pub head_matches: Option<bool>,
    /// Davrdagi moliyaviy yozuvlar (ko'rik yozuvlarisiz).
    pub ledger: Vec<JournalEntry>,
    /// Davrdagi vazifa hodisalari.
    pub incidents: Vec<JournalEntry>,
    pub parties: Vec<PartyAnswer>,
}

fn check_period(period: &str) -> Result<(), ServiceError> {
    let ok = period.len() == 7
        && period.as_bytes()[4] == b'-'
        && period[..4].bytes().all(|b| b.is_ascii_digit())
        && matches!(period[5..].parse::<u8>(), Ok(1..=12));
    if ok {
        Ok(())
    } else {
        Err(ServiceError::Invalid("davr YYYY-MM ko'rinishida bo'lsin"))
    }
}

fn in_period(e: &JournalEntry, period: &str) -> bool {
    date_to_string(e.entry_date).is_ok_and(|s| s.starts_with(period))
}

fn is_close_of(e: &JournalEntry, period: &str) -> bool {
    e.kind == JournalKind::ReviewClosed
        && e.reference
            .as_deref()
            .is_some_and(|r| r.split_once('|').is_some_and(|(p, _)| p == period))
}

fn parties_of(
    conn: &Connection,
    ctx: &Ctx,
    agreement_id: &str,
) -> Result<Vec<(String, String)>, ServiceError> {
    let a = agreements::load(conn, ctx, agreement_id)?;
    let doc = agreements::current_doc(conn, ctx, &a)?.ok_or(ServiceError::Invalid(
        "eski matnli kelishuvda ko'rik yo'q: avval 9 savolli versiya yarating",
    ))?;
    Ok(match &doc.questions.parties {
        Answer::Answered(ps) => ps.iter().map(|p| (p.id.clone(), p.name.clone())).collect(),
        _ => Vec::new(),
    })
}

/// Tomonning javobi: «ko'rdim, roziman» yoki «e'tirozim bor» (izoh bilan).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReviewAnswer {
    Agree,
    Object(String),
}

/// Davr ko'rigining holati (faqat o'qish).
///
/// # Errors
/// Davr formati noto'g'ri, kelishuv topilmasa yoki eski matnli bo'lsa.
pub fn view(
    conn: &Connection,
    ctx: &Ctx,
    agreement_id: &str,
    period: &str,
) -> Result<ReviewView, ServiceError> {
    check_period(period)?;
    agreements::load(conn, ctx, agreement_id)?;
    let parties = parties_of(conn, ctx, agreement_id)?;
    let all = journal::entries(conn, ctx, agreement_id)?;
    let chain = journal::verify(conn, ctx, agreement_id)?;
    let closed = all.iter().find(|e| is_close_of(e, period));
    let (recorded_head, head_matches) = match closed {
        Some(c) => {
            let recorded = c
                .reference
                .as_deref()
                .and_then(|r| r.split_once('|'))
                .map(|(_, h)| h.to_owned());
            // Yopilgunga qadar bo'lgan yozuvlarni qayta hisoblaymiz: boshi qayd etilganiga mos keladimi?
            let prefix = all
                .iter()
                .take_while(|e| e.seq < c.seq)
                .map(JournalEntry::hashed)
                .collect::<Result<Vec<_>, _>>()
                .map_err(|_| ServiceError::Invalid("jurnal sanasi buzilgan"))?;
            let recomputed = chain_head(&prefix)
                .map_err(|_| ServiceError::Invalid("jurnal mazmuni yaroqsiz"))?;
            let matches = recorded.as_deref() == Some(recomputed.as_str());
            (recorded, Some(matches))
        }
        None => (None, None),
    };
    let answers = parties
        .into_iter()
        .map(|(id, name)| {
            let last = all.iter().rev().find(|e| {
                e.kind == JournalKind::ReviewAck
                    && e.party_id.as_deref() == Some(id.as_str())
                    && e.reference.as_deref() == Some(period)
            });
            let agree = last.map(|e| !e.note.starts_with(OBJECT_PREFIX));
            let note = last
                .filter(|e| e.note.starts_with(OBJECT_PREFIX))
                .map(|e| e.note.trim_start_matches(OBJECT_PREFIX).to_owned());
            PartyAnswer {
                party_id: id,
                name,
                agree,
                note,
            }
        })
        .collect();
    let ledger = all
        .iter()
        .filter(|e| {
            in_period(e, period)
                && !matches!(e.kind, JournalKind::ReviewAck | JournalKind::ReviewClosed)
        })
        .cloned()
        .collect();
    let incidents = all
        .iter()
        .filter(|e| e.kind == JournalKind::DutyIncident && in_period(e, period))
        .cloned()
        .collect();
    Ok(ReviewView {
        period: period.to_owned(),
        closed: closed.is_some(),
        chain,
        recorded_head,
        head_matches,
        ledger,
        incidents,
        parties: answers,
    })
}

fn open_agreement(
    conn: &Connection,
    ctx: &Ctx,
    agreement_id: &str,
) -> Result<domain::Agreement, ServiceError> {
    let a = agreements::load(conn, ctx, agreement_id)?;
    if !matches!(
        a.status,
        AgreementStatus::Active | AgreementStatus::InDispute
    ) {
        return Err(ServiceError::Invalid(
            "ko'rik faqat faol kelishuvda o'tkaziladi",
        ));
    }
    Ok(a)
}

/// Javob yozilishidan oldingi tekshiruv (hech narsa yozmaydi): davr, faol kelishuv, yopilmagan ko'rik,
/// tomon kelishuvda bormi va izoh to'g'rimi. Jurnalga yoziladigan matnni qaytaradi.
///
/// # Errors
/// Kelishuv faol emas, davr yakunlangan, tomon topilmasa, yoki e'tiroz izohsiz bo'lsa.
pub fn prepare_answer(
    conn: &Connection,
    ctx: &Ctx,
    agreement_id: &str,
    period: &str,
    party_id: &str,
    answer: &ReviewAnswer,
) -> Result<String, ServiceError> {
    check_period(period)?;
    open_agreement(conn, ctx, agreement_id)?;
    let v = view(conn, ctx, agreement_id, period)?;
    if v.closed {
        return Err(ServiceError::Invalid(
            "bu davr ko'rigi allaqachon yakunlangan",
        ));
    }
    if !v.parties.iter().any(|p| p.party_id == party_id) {
        return Err(ServiceError::Invalid("tomon kelishuvda topilmadi"));
    }
    match answer {
        ReviewAnswer::Agree => Ok(AGREE_NOTE.to_owned()),
        ReviewAnswer::Object(note) => {
            let reason = note.trim();
            if reason.is_empty() {
                return Err(ServiceError::Invalid("e'tiroz uchun izoh yozing"));
            }
            Ok(format!("{OBJECT_PREFIX}{reason}"))
        }
    }
}

/// Tomonning javobini yozadi (jurnalga `REVIEW_ACK`). Oilaviy kelishuvda javob kattaning PIN'i bilan
/// yoziladi (`services::family_agreements::review_answer`), shuning uchun bu yo'l u yerda rad etiladi.
///
/// # Errors
/// Kelishuv oilaviy bo'lsa, yoki `prepare_answer` dagi xatolar.
pub fn record_answer(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    agreement_id: &str,
    period: &str,
    party_id: &str,
    answer: ReviewAnswer,
) -> Result<JournalEntry, ServiceError> {
    if agreements::load(db.conn(), ctx, agreement_id)?.agreement_type == AgreementType::Family {
        return Err(ServiceError::Invalid(
            "oilaviy kelishuvda javob kattaning PIN'i bilan beriladi",
        ));
    }
    write_answer(db, env, ctx, agreement_id, period, party_id, answer)
}

/// Javobni tekshirib, jurnalga yozadi. Oilaviy kelishuvda kattaning PIN'i chaqiruvchi tomonidan
/// tekshirilgan bo'lishi shart.
pub(crate) fn write_answer(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    agreement_id: &str,
    period: &str,
    party_id: &str,
    answer: ReviewAnswer,
) -> Result<JournalEntry, ServiceError> {
    let text = prepare_answer(db.conn(), ctx, agreement_id, period, party_id, &answer)?;
    let a = open_agreement(db.conn(), ctx, agreement_id)?;
    let date = local_date(env.clock.now());
    journal::append(
        db.conn(),
        env,
        ctx,
        &a,
        journal::NewEntry {
            kind: JournalKind::ReviewAck,
            party_id: Some(party_id),
            amount: None,
            date,
            note: &text,
            reference: Some(period),
            corrects: None,
        },
    )
}

/// Ko'rikni yakunlaydi: barcha tomonlar javob bergan bo'lishi kerak. Zanjir boshi yozuvga qayd etiladi.
///
/// # Errors
/// Kelishuv faol emas, davr allaqachon yakunlangan, yoki kimdir hali javob bermagan bo'lsa.
pub fn close(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    agreement_id: &str,
    period: &str,
) -> Result<JournalEntry, ServiceError> {
    check_period(period)?;
    let a = open_agreement(db.conn(), ctx, agreement_id)?;
    let v = view(db.conn(), ctx, agreement_id, period)?;
    if v.closed {
        return Err(ServiceError::Invalid(
            "bu davr ko'rigi allaqachon yakunlangan",
        ));
    }
    if v.parties.iter().any(|p| p.agree.is_none()) {
        return Err(ServiceError::Invalid(
            "ko'rikni yakunlash uchun barcha tomonlar javob bersin",
        ));
    }
    let objections = v.parties.iter().filter(|p| p.agree == Some(false)).count();
    let note = format!("Ko'rik yakunlandi ({period}): e'tirozlar {objections}");
    let reference = format!("{period}|{}", v.chain.head);
    let date = local_date(env.clock.now());
    journal::append(
        db.conn(),
        env,
        ctx,
        &a,
        journal::NewEntry {
            kind: JournalKind::ReviewClosed,
            party_id: None,
            amount: None,
            date,
            note: &note,
            reference: Some(&reference),
            corrects: None,
        },
    )
}

/// Jurnal turining foydalanuvchiga ko'rinadigan nomi (bayonnoma va UI uchun).
#[must_use]
pub fn kind_label(kind: JournalKind) -> &'static str {
    match kind {
        JournalKind::OpeningBalance => "Boshlang'ich holat",
        JournalKind::Contribution => "Hissa",
        JournalKind::VentureIncome => "Kirim",
        JournalKind::VentureExpense => "Chiqim",
        JournalKind::ProfitDistribution => "Foyda taqsimoti",
        JournalKind::LossShare => "Zarar ulushi",
        JournalKind::BuyoutPayment => "Buyout to'lovi",
        JournalKind::Payment => "To'lov",
        JournalKind::PeriodClosed => "Davr yopildi",
        JournalKind::Correction => "Tuzatish",
        JournalKind::DutyIncident => "Vazifa hodisasi",
        JournalKind::DisputeOpened => "Nizo ochildi",
        JournalKind::DisputeResolved => "Hakam qarori",
        JournalKind::ProfitAlertAck => "Katta foyda tasdig'i",
        JournalKind::ReviewAck => "Ko'rik javobi",
        JournalKind::ReviewClosed => "Ko'rik yakuni",
    }
}

fn month_label(period: &str) -> String {
    const MONTHS: [&str; 12] = [
        "yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr",
        "noyabr", "dekabr",
    ];
    let month: usize = period[5..].parse().unwrap_or(1);
    format!("{} yil, {}", &period[..4], MONTHS[month - 1])
}

/// Ko'rik bayonnomasi (PDF). Shablon tasdiqlanmagan relizda chiqmaydi (SPEC 8).
///
/// # Errors
/// Shablon tasdiqlanmagan, davr noto'g'ri yoki PDF yaratib bo'lmasa.
pub fn pdf(
    conn: &Connection,
    ctx: &Ctx,
    agreement_id: &str,
    period: &str,
) -> Result<Vec<u8>, ServiceError> {
    if !pdf::templates_releasable(cfg!(debug_assertions)) {
        return Err(ServiceError::Invalid(
            "kelishuv shabloni hali yurist va ulamo tasdig'idan o'tmagan: PDF chiqarilmaydi",
        ));
    }
    let a = agreements::load(conn, ctx, agreement_id)?;
    let v = view(conn, ctx, agreement_id, period)?;
    let chain_status = match v.chain.broken_seq {
        Some(n) => format!("Zanjir buzilgan: yozuv #{n}"),
        None => format!("Zanjir buzilmagan ({} ta yozuv)", v.chain.length),
    };
    let (head, head_status) = match (&v.recorded_head, v.head_matches) {
        (Some(h), Some(true)) => (
            h.clone(),
            "Yopilgandagi zanjir boshi bilan mos keladi".to_owned(),
        ),
        (Some(h), _) => (
            h.clone(),
            "MOS KELMAYDI: yozuvlar yopilgandan keyin o'zgargan bo'lishi mumkin".to_owned(),
        ),
        (None, _) => (
            v.chain.head.clone(),
            "Hali yakunlanmagan: joriy zanjir boshi".to_owned(),
        ),
    };
    let name_of = |pid: Option<&str>| -> String {
        pid.and_then(|id| v.parties.iter().find(|p| p.party_id == id))
            .map_or_else(String::new, |p| p.name.clone())
    };
    let parties = v
        .parties
        .iter()
        .map(|p| {
            let answer = match (p.agree, &p.note) {
                (Some(true), _) => AGREE_NOTE.to_owned(),
                (Some(false), Some(n)) => format!("E'tiroz: {n}"),
                (Some(false), None) => "E'tiroz".to_owned(),
                (None, _) => "Javob yo'q".to_owned(),
            };
            (p.name.clone(), answer)
        })
        .collect();
    let ledger = v
        .ledger
        .iter()
        .map(|e| {
            let date = date_to_string(e.entry_date).unwrap_or_default();
            let amount = e.amount.map_or_else(String::new, |m| {
                format!(" · {}", format_money(m, Locale::Uz))
            });
            format!(
                "{date} · {} · {}{amount} — {}",
                kind_label(e.kind),
                name_of(e.party_id.as_deref()),
                e.note
            )
        })
        .collect();
    let incidents = v
        .incidents
        .iter()
        .map(|e| {
            format!(
                "{} · {} · {}",
                date_to_string(e.entry_date).unwrap_or_default(),
                name_of(e.party_id.as_deref()),
                e.note
            )
        })
        .collect();
    let doc = pdf::ReviewPdfDoc {
        title: a.title.clone(),
        period: month_label(period),
        closed: v.closed,
        chain_status,
        chain_head: head,
        head_status,
        parties,
        ledger,
        incidents,
        legal_note: "Shablon yurist va ulamo tasdig'idan o'tmagan: yuridik kuchi va islomiy muvofiqligi haqida va'da berilmaydi. Ilova pul o'tkazmaydi.".to_owned(),
        disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    };
    pdf::review_pdf(&doc)
        .map_err(|_| ServiceError::Invalid("ko'rik bayonnomasini yaratib bo'lmadi"))
}
