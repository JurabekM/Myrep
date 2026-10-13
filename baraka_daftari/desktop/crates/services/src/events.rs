//! Kelishuv voqealari (SPEC 2F.4, 2F.8): vazifa hodisasi, nizo ochish va hakam qarori.
//!
//! Har bir voqea kelishuv jurnaliga append-only yozuv sifatida tushadi. Nizo ochilganda kelishuv
//! `IN_DISPUTE` holatiga o'tadi va taqsimot bloklanadi (`ventures::close_period`).

use domain::{can_transition, AgreementStatus, Answer, JournalEntry, JournalKind};
use storage::Database;

use crate::agreements;
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
