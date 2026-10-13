//! Kelishuv voqealari (SPEC 2F.4, 2F.8): vazifa hodisasi, nizo ochish va hakam qarori.
//!
//! Har bir voqea kelishuv jurnaliga append-only yozuv sifatida tushadi. Nizo ochilganda kelishuv
//! `IN_DISPUTE` holatiga o'tadi va taqsimot bloklanadi (`ventures::close_period`).

use domain::{can_transition, date_to_string, AgreementStatus, Answer, JournalEntry, JournalKind};
use money::{format_money, Locale};
use storage::{Connection, Database};

use crate::agreements;
use crate::review;
use crate::{journal, local_date, Ctx, Env, ServiceError};

/// «Vazifamni bajara olmayapman»: `duty_index`-dagi bandning mas'ul tomoni hodisani qayd etadi.
/// Maqsad aybdor qidirish emas: izohda sabab va o'rniga taklif yoziladi (SPEC 2F.4).
///
/// # Errors
/// Kelishuv imzolanmagan yoki yopilgan bo'lsa, band topilmasa, mas'ul tomon bo'lmasa, izoh bo'sh
/// yoki juda uzun bo'lsa, yoki qurilma hisob yurituvchi bo'lmasa.
pub fn report_duty_incident(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    agreement_id: &str,
    duty_index: usize,
    reason: &str,
    proposal: &str,
) -> Result<JournalEntry, ServiceError> {
    let a = agreements::load(db.conn(), ctx, agreement_id)?;
    if !matches!(
        a.status,
        AgreementStatus::Signed | AgreementStatus::Active | AgreementStatus::InDispute
    ) {
        return Err(ServiceError::Invalid(
            "vazifa hodisasi faqat imzolangan kelishuvda yoziladi",
        ));
    }
    let doc = agreements::current_doc(db.conn(), ctx, &a)?.ok_or(ServiceError::Invalid(
        "eski matnli kelishuvda vazifa bandlari yo'q: avval 9 savolli versiya yarating",
    ))?;
    let duty = match &doc.questions.duties {
        Answer::Answered(ds) => ds.get(duty_index),
        _ => None,
    }
    .ok_or(ServiceError::Invalid("bunday vazifa bandi yo'q"))?;
    let owner = duty.owner_party_id.as_deref().ok_or(ServiceError::Invalid(
        "bu bandning mas'ul tomoni belgilanmagan",
    ))?;
    let reason = reason.trim();
    let proposal = proposal.trim();
    let note = if proposal.is_empty() {
        reason.to_owned()
    } else {
        format!("{reason}. Taklif: {proposal}")
    };
    let reference = format!("v{}/duty:{duty_index}", a.current_version);
    let date = local_date(env.clock.now());
    journal::append(
        db.conn(),
        env,
        ctx,
        &a,
        journal::NewEntry {
            kind: JournalKind::DutyIncident,
            party_id: Some(owner),
            amount: None,
            date,
            note: &note,
            reference: Some(&reference),
            corrects: None,
        },
    )
}

/// Nizo ochadi: faqat faol kelishuvda. Da'vogar — kelishuvning tomoni; talab jurnalga yoziladi.
///
/// # Errors
/// Kelishuv faol emas, da'vogar tomon topilmasa, talab bo'sh yoki juda uzun bo'lsa.
pub fn open_dispute(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    agreement_id: &str,
    claimant_party_id: &str,
    subject: &str,
    claim: &str,
) -> Result<JournalEntry, ServiceError> {
    let mut a = agreements::load(db.conn(), ctx, agreement_id)?;
    if !can_transition(a.status, AgreementStatus::InDispute) {
        return Err(ServiceError::Invalid("nizo faqat faol kelishuvda ochiladi"));
    }
    let doc = agreements::current_doc(db.conn(), ctx, &a)?.ok_or(ServiceError::Invalid(
        "eski matnli kelishuvda nizo ochib bo'lmaydi: avval 9 savolli versiya yarating",
    ))?;
    let known = match &doc.questions.parties {
        Answer::Answered(ps) => ps.iter().any(|p| p.id == claimant_party_id),
        _ => false,
    };
    if !known {
        return Err(ServiceError::Invalid("da'vogar tomon kelishuvda topilmadi"));
    }
    let note = format!("{}: {}", subject.trim(), claim.trim());
    let date = local_date(env.clock.now());
    let entry = db.transaction::<JournalEntry, ServiceError>(|tx| {
        let entry = journal::append(
            tx,
            env,
            ctx,
            &a,
            journal::NewEntry {
                kind: JournalKind::DisputeOpened,
                party_id: Some(claimant_party_id),
                amount: None,
                date,
                note: &note,
                reference: None,
                corrects: None,
            },
        )?;
        a.status = AgreementStatus::InDispute;
        storage::repo::update(tx, &a, env.clock.now())?;
        Ok(entry)
    })?;
    Ok(entry)
}

/// Hakam qarori: nizo yopiladi (`IN_DISPUTE` → faol). Qaror jurnalga yoziladi; kerak bo'lsa keyin
/// kelishuvning yangi versiyasi yaratiladi.
///
/// # Errors
/// Kelishuvda ochiq nizo bo'lmasa yoki qaror bo'sh/uzun bo'lsa.
pub fn resolve_dispute(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    agreement_id: &str,
    decision: &str,
) -> Result<JournalEntry, ServiceError> {
    let mut a = agreements::load(db.conn(), ctx, agreement_id)?;
    if a.status != AgreementStatus::InDispute {
        return Err(ServiceError::Invalid("kelishuvda ochiq nizo yo'q"));
    }
    let date = local_date(env.clock.now());
    let decision = decision.trim().to_owned();
    let entry = db.transaction::<JournalEntry, ServiceError>(|tx| {
        let entry = journal::append(
            tx,
            env,
            ctx,
            &a,
            journal::NewEntry {
                kind: JournalKind::DisputeResolved,
                party_id: None,
                amount: None,
                date,
                note: &decision,
                reference: None,
                corrects: None,
            },
        )?;
        a.status = AgreementStatus::Active;
        storage::repo::update(tx, &a, env.clock.now())?;
        Ok(entry)
    })?;
    Ok(entry)
}

/// Hakam uchun ish papkasi (PDF, SPEC 2F.8): mundarija bilan — versiyalar, hisob yozuvlari, zanjir holati,
/// ko'rik bayonnomalari (zanjir boshi bilan), vazifa hodisalari, talablar va hakam qarorlari.
/// Shablon tasdiqlanmagan relizda chiqmaydi (SPEC 8).
///
/// # Errors
/// Shablon tasdiqlanmagan, kelishuv topilmasa yoki PDF yaratib bo'lmasa.
pub fn folder_pdf(
    conn: &Connection,
    ctx: &Ctx,
    agreement_id: &str,
) -> Result<Vec<u8>, ServiceError> {
    if !pdf::templates_releasable(cfg!(debug_assertions)) {
        return Err(ServiceError::Invalid(
            "kelishuv shabloni hali yurist va ulamo tasdig'idan o'tmagan: PDF chiqarilmaydi",
        ));
    }
    let v = agreements::view(conn, ctx, agreement_id)?;
    let all = journal::entries(conn, ctx, agreement_id)?;
    let names: Vec<(String, String)> = match v.doc.as_ref().map(|d| &d.questions.parties) {
        Some(Answer::Answered(ps)) => ps.iter().map(|p| (p.id.clone(), p.name.clone())).collect(),
        _ => Vec::new(),
    };
    let name_of = |pid: Option<&str>| -> String {
        pid.and_then(|id| names.iter().find(|(i, _)| i == id))
            .map_or_else(String::new, |(_, n)| n.clone())
    };
    let date_of = |e: &JournalEntry| date_to_string(e.entry_date).unwrap_or_default();
    let amount_of = |e: &JournalEntry| {
        e.amount.map_or_else(String::new, |m| {
            format!(" · {}", format_money(m, Locale::Uz))
        })
    };
    let versions = v
        .versions
        .iter()
        .map(|ver| {
            let head: String = ver.content_hash.chars().take(12).collect();
            let when = date_to_string(local_date(ver.created_at)).unwrap_or_default();
            format!("v{} · {when} · xesh {head}", ver.version_no)
        })
        .collect();
    let is_event = |k: JournalKind| {
        matches!(
            k,
            JournalKind::ReviewAck
                | JournalKind::ReviewClosed
                | JournalKind::DutyIncident
                | JournalKind::DisputeOpened
                | JournalKind::DisputeResolved
        )
    };
    let entries = all
        .iter()
        .filter(|e| !is_event(e.kind))
        .map(|e| {
            format!(
                "#{} · {} · {} · {}{} — {}",
                e.seq,
                date_of(e),
                review::kind_label(e.kind),
                name_of(e.party_id.as_deref()),
                amount_of(e),
                e.note
            )
        })
        .collect();
    let mut reviews = Vec::new();
    for e in all.iter().filter(|e| e.kind == JournalKind::ReviewClosed) {
        let Some(period) = e
            .reference
            .as_deref()
            .and_then(|r| r.split_once('|'))
            .map(|(p, _)| p)
        else {
            continue;
        };
        let rv = review::view(conn, ctx, agreement_id, period)?;
        let head: String = rv
            .recorded_head
            .clone()
            .unwrap_or_default()
            .chars()
            .take(12)
            .collect();
        let verdict = if rv.head_matches == Some(true) {
            "boshi mos keladi"
        } else {
            "BOSHI MOS KELMAYDI"
        };
        reviews.push(format!("{period} · yopilgan boshi: {head} · {verdict}"));
    }
    let incidents = all
        .iter()
        .filter(|e| e.kind == JournalKind::DutyIncident)
        .map(|e| {
            format!(
                "{} · {} · {}",
                date_of(e),
                name_of(e.party_id.as_deref()),
                e.note
            )
        })
        .collect();
    let claims = all
        .iter()
        .filter(|e| e.kind == JournalKind::DisputeOpened)
        .map(|e| {
            format!(
                "{} · {} · {}",
                date_of(e),
                name_of(e.party_id.as_deref()),
                e.note
            )
        })
        .collect();
    let decisions = all
        .iter()
        .filter(|e| e.kind == JournalKind::DisputeResolved)
        .map(|e| format!("{} · {}", date_of(e), e.note))
        .collect();
    let chain_status = match v.chain.broken_seq {
        Some(n) => format!("Zanjir buzilgan: yozuv #{n}"),
        None => format!("Zanjir buzilmagan ({} ta yozuv)", v.chain.length),
    };
    let doc = pdf::DisputeFolderDoc {
        title: v.agreement.title.clone(),
        status: agreements::status_text(v.agreement.status).to_owned(),
        chain_status,
        chain_head: v.chain.head.clone(),
        versions,
        entries,
        reviews,
        incidents,
        claims,
        decisions,
        legal_note: "Shablon yurist va ulamo tasdig'idan o'tmagan: yuridik kuchi va islomiy muvofiqligi haqida va'da berilmaydi. Hakam qarorini ilova almashtirmaydi.".to_owned(),
        disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".to_owned(),
    };
    pdf::dispute_folder_pdf(&doc)
        .map_err(|_| ServiceError::Invalid("hakam papkasini yaratib bo'lmadi"))
}
