//! Oilaviy kelishuvlar buyruqlari (SPEC 2F.10, D13A): yaratish, kattalar PIN tasdig'i, faollashtirish,
//! oylik ko'rik va vazifa hodisasi. «Havas chegarasi» shabloni havas moduli holatini faqat o'qiydi.

use domain::{
    date_from_str, date_to_string, AgreementSignKind, AgreementStatus, Answer, FamilyTemplate,
};
use serde::{Deserialize, Serialize};
use services::{
    agreements::AgreementView,
    family_agreements::{self, FamilyDuty, FamilyIncident, FamilyReply, NewFamilyAgreement},
    review::ReviewAnswer,
    ServiceError,
};
use specta::Type;
use tauri::State;

use crate::commands::{with_session, AppSession, CommandError};

/// Xonadon katta a'zosi va uning tasdig'i.
#[derive(Debug, Serialize, Type)]
pub struct FamilyAdultDto {
    pub member_id: String,
    pub name: String,
    /// PIN bilan tasdiqlaganmi (joriy versiya bo'yicha).
    pub signed: bool,
}

/// Oilaviy vazifa bandi: mas'ul katta a'zosi identifikatori bilan (hodisani u yozadi).
#[derive(Debug, Serialize, Type)]
pub struct FamilyDutyDto {
    pub text: String,
    pub owner_member_id: String,
    pub owner_name: String,
    pub if_not_done: String,
}

/// Havas chegarasi (havas moduli, faqat o'qish): «havas chegarasi» shabloni uchun.
#[derive(Debug, Serialize, Type)]
pub struct FamilyHavasDto {
    /// Faol chegara (formatlangan, masalan «1 500 000 so'm»); belgilanmagan bo'lsa `null`.
    pub limit: Option<String>,
    /// Yangi chegara taklifi bor, lekin hali barcha kattalar rozi emas.
    pub pending: bool,
}

/// Oilaviy kelishuv holati: kattalar, vazifalar, pul joyi, yangilash sanasi va tasdiqlar.
#[derive(Debug, Serialize, Type)]
pub struct FamilyAgreementDto {
    pub id: String,
    pub title: String,
    /// `DRAFT` | `SIGNED` | `ACTIVE` | `IN_DISPUTE` | `CLOSED`.
    pub status: String,
    pub status_label: String,
    pub version: u32,
    pub adults: Vec<FamilyAdultDto>,
    pub duties: Vec<FamilyDutyDto>,
    pub custody_place: String,
    /// `YYYY-MM-DD`; javob berilmagan bo'lsa `null`.
    pub review_date: Option<String>,
    /// Javobsiz savollar (1–9).
    pub missing_questions: Vec<u8>,
    /// Barcha kattalar tasdiqlagan: faollashtirish mumkin.
    pub can_activate: bool,
    /// Namunaviy shablon kodi (`HOUSE_DUTIES` | `HOUSE_MONEY` | `DESIRE_LIMIT` | `COUNCIL_SCHEDULE`); eski kelishuvda `null`.
    pub template: Option<String>,
    /// Faqat «havas chegarasi» shablonida: havas moduli holati.
    pub havas: Option<FamilyHavasDto>,
}

/// Vazifa bandi: mas'ul — xonadon katta a'zosi.
#[derive(Debug, Deserialize, Type)]
pub struct FamilyDutyInput {
    pub text: String,
    pub owner_member_id: String,
    pub if_not_done: String,
}

/// Yangi oilaviy kelishuv (qoralama).
#[derive(Debug, Deserialize, Type)]
pub struct FamilyAgreementInput {
    pub title: String,
    pub adult_ids: Vec<String>,
    pub duties: Vec<FamilyDutyInput>,
    pub custody_place: String,
    /// `YYYY-MM-DD`; bo'sh bo'lsa — bir yil keyin.
    pub review_date: Option<String>,
    /// Namunaviy shablon kodi; `null` bo'lsa shablonsiz.
    pub template: Option<String>,
}

fn family_dto(v: &AgreementView, havas: Option<FamilyHavasDto>) -> FamilyAgreementDto {
    let doc = v.doc.as_ref();
    let parties: Vec<(String, String)> = match doc.map(|d| &d.questions.parties) {
        Some(Answer::Answered(ps)) => ps.iter().map(|p| (p.id.clone(), p.name.clone())).collect(),
        _ => Vec::new(),
    };
    let adults = parties
        .iter()
        .map(|(id, name)| FamilyAdultDto {
            member_id: id.clone(),
            name: name.clone(),
            signed: !v
                .missing_signatures
                .iter()
                .any(|s| s.kind == AgreementSignKind::FamilyConsent && s.key == *id),
        })
        .collect();
    let duties = match doc.map(|d| &d.questions.duties) {
        Some(Answer::Answered(ds)) => ds
            .iter()
            .map(|d| FamilyDutyDto {
                text: d.text.clone(),
                owner_member_id: d.owner_party_id.clone().unwrap_or_default(),
                owner_name: parties
                    .iter()
                    .find(|(id, _)| d.owner_party_id.as_deref() == Some(id.as_str()))
                    .map(|(_, n)| n.clone())
                    .unwrap_or_default(),
                if_not_done: d.if_not_done.clone(),
            })
            .collect(),
        _ => Vec::new(),
    };
    let custody_place = match doc.map(|d| &d.questions.custody) {
        Some(Answer::Answered(c)) => c.place.clone(),
        _ => String::new(),
    };
    let review_date = match doc.map(|d| &d.questions.term) {
        Some(Answer::Answered(t)) => date_to_string(t.review_date).ok(),
        _ => None,
    };
    FamilyAgreementDto {
        id: v.agreement.meta.id.clone(),
        title: v.agreement.title.clone(),
        status: v.agreement.status.as_str().to_owned(),
        status_label: services::agreements::status_text(v.agreement.status).to_owned(),
        version: v.agreement.current_version,
        adults,
        duties,
        custody_place,
        review_date,
        missing_questions: v.completeness.missing.clone(),
        can_activate: v.agreement.status == AgreementStatus::Signed,
        template: v.agreement.family_template.map(|t| t.as_str().to_owned()),
        havas,
    }
}

/// «Havas chegarasi» shablonida havas moduli holatini o'qiydi; boshqa shablonlarda havas bog'lanmaydi.
fn havas_of(
    conn: &storage::Connection,
    ctx: &services::Ctx,
    v: &AgreementView,
) -> Result<Option<FamilyHavasDto>, ServiceError> {
    if v.agreement.family_template != Some(FamilyTemplate::DesireLimit) {
        return Ok(None);
    }
    let link = family_agreements::havas_link(conn, ctx)?;
    Ok(Some(FamilyHavasDto {
        limit: link
            .limit
            .map(|m| money::format_money(m, money::Locale::Uz)),
        pending: link.pending,
    }))
}

/// Xonadonning oilaviy kelishuvlari.
#[tauri::command]
#[specta::specta]
pub fn family_agreements_list(
    state: State<'_, AppSession>,
) -> Result<Vec<FamilyAgreementDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _env, ctx| {
            let views = family_agreements::list(db.conn(), ctx)?;
            views
                .iter()
                .map(|v| -> Result<FamilyAgreementDto, ServiceError> {
                    Ok(family_dto(v, havas_of(db.conn(), ctx, v)?))
                })
                .collect()
        })
    })
}

/// Yangi oilaviy kelishuv (qoralama). Hech kim hali imzolamagan.
#[tauri::command]
#[specta::specta]
pub fn create_family_agreement(
    input: FamilyAgreementInput,
    state: State<'_, AppSession>,
) -> Result<FamilyAgreementDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let review_date = input
                .review_date
                .filter(|t| !t.trim().is_empty())
                .map(|t| date_from_str(t.trim()))
                .transpose()
                .map_err(|_| {
                    ServiceError::Invalid("yangilash sanasi YYYY-MM-DD ko'rinishida bo'lsin")
                })?;
            let template = input
                .template
                .filter(|t| !t.trim().is_empty())
                .map(|t| {
                    FamilyTemplate::parse(t.trim())
                        .ok_or(ServiceError::Invalid("noma'lum namunaviy shablon"))
                })
                .transpose()?;
            let view = family_agreements::create(
                db,
                env,
                ctx,
                NewFamilyAgreement {
                    title: input.title,
                    adult_ids: input.adult_ids,
                    duties: input
                        .duties
                        .into_iter()
                        .map(|d| FamilyDuty {
                            text: d.text,
                            owner_member_id: d.owner_member_id,
                            if_not_done: d.if_not_done,
                        })
                        .collect(),
                    custody_place: input.custody_place,
                    review_date,
                    template,
                },
            )?;
            let havas = havas_of(db.conn(), ctx, &view)?;
            Ok(family_dto(&view, havas))
        })
    })
}

/// Katta a'zo PIN bilan tasdiqlaydi.
#[tauri::command]
#[specta::specta]
pub fn sign_family_agreement(
    agreement_id: String,
    member_id: String,
    pin: String,
    state: State<'_, AppSession>,
) -> Result<FamilyAgreementDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let view = family_agreements::consent(db, env, ctx, &agreement_id, &member_id, &pin)?;
            let havas = havas_of(db.conn(), ctx, &view)?;
            Ok(family_dto(&view, havas))
        })
    })
}

/// Barcha kattalar tasdiqlagach kelishuvni faollashtiradi.
#[tauri::command]
#[specta::specta]
pub fn activate_family_agreement(
    agreement_id: String,
    state: State<'_, AppSession>,
) -> Result<FamilyAgreementDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let view = family_agreements::activate(db, env, ctx, &agreement_id)?;
            let havas = havas_of(db.conn(), ctx, &view)?;
            Ok(family_dto(&view, havas))
        })
    })
}

/// Mas'ul katta o'z PIN'i bilan «bajara olmayapman» deydi: vazifa hodisasi jurnalga yoziladi.
#[tauri::command]
#[specta::specta]
pub fn report_family_duty_incident(
    agreement_id: String,
    duty_index: u32,
    member_id: String,
    pin: String,
    reason: String,
    proposal: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let index = usize::try_from(duty_index)
                .map_err(|_| ServiceError::Invalid("bunday vazifa bandi yo'q"))?;
            family_agreements::report_incident(
                db,
                env,
                ctx,
                &agreement_id,
                FamilyIncident {
                    member_id,
                    pin,
                    duty_index: index,
                    reason,
                    proposal,
                },
            )?;
            Ok(())
        })
    })
}

/// Oylik ko'rikda katta a'zoning javobi: kattaning o'z PIN'i bilan. `agree = false` bo'lsa izoh shart.
#[tauri::command]
#[specta::specta]
pub fn record_family_review_answer(
    agreement_id: String,
    period: String,
    member_id: String,
    pin: String,
    agree: bool,
    note: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let answer = if agree {
                ReviewAnswer::Agree
            } else {
                ReviewAnswer::Object(note)
            };
            family_agreements::review_answer(
                db,
                env,
                ctx,
                &agreement_id,
                &period,
                FamilyReply {
                    member_id,
                    pin,
                    answer,
                },
            )?;
            Ok(())
        })
    })
}
