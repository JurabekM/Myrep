//! Oilaviy kelishuvlar (SPEC 2F.10, D13A): yengil format. Tomonlar — xonadonning kattalari; guvoh va hakam
//! ixtiyoriy; imzo o'rniga har bir kattaning PIN bilan tasdig'i yetarli (`AgreementSigner::FamilyConsent`).
//! Namunaviy shablonlarning matni UI'da (uz/ru); bu yerda kelishuv tuzilmasi va tasdiqlash oqimi.

use domain::{
    add_months, AgreementDoc, AgreementType, Answer, Custody, Date, Duty, MemberRole, Party,
    Questions, ReportPeriod, Term,
};
use storage::Database;

use crate::agreements::{self, AgreementSigner, AgreementView, NewAgreement};
use crate::{local_date, members, Ctx, Env, ServiceError};

/// Vazifa bandi: mas'ul — xonadon kattalaridan biri.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FamilyDuty {
    pub text: String,
    pub owner_member_id: String,
    /// «Bajarilmasa» bandi: masalan, «ertasi kuni o'zi tuzatadi».
    pub if_not_done: String,
}

/// Yangi oilaviy kelishuv (qoralama).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NewFamilyAgreement {
    pub title: String,
    /// Tomonlar: kattalarning xonadon a'zosi identifikatorlari (tartib saqlanadi).
    pub adult_ids: Vec<String>,
    pub duties: Vec<FamilyDuty>,
    /// Pul qayerda turadi va kim yuritadi (6-savol).
    pub custody_place: String,
    /// Yangilash (oila kengashi) sanasi; berilmasa — bir yil keyin.
    pub review_date: Option<Date>,
}

fn clean(s: &str, max: usize) -> String {
    s.split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .chars()
        .take(max)
        .collect()
}

/// Oilaviy kelishuvni qoralama sifatida yaratadi. Hech kim imzolamaydi.
///
/// # Errors
/// Nom yoki «pul qayerda» bo'sh, kattalar tanlanmagan, tanlangan a'zo katta bo'lmasa yoki topilmasa.
pub fn create(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewFamilyAgreement,
) -> Result<AgreementView, ServiceError> {
    let title = clean(&new.title, 80);
    if title.is_empty() {
        return Err(ServiceError::Invalid("kelishuv nomini yozing"));
    }
    let custody_place = clean(&new.custody_place, 200);
    if custody_place.is_empty() {
        return Err(ServiceError::Invalid("pul qayerda turishini yozing"));
    }
    let known = members::list(db.conn(), ctx)?;
    let mut parties: Vec<Party> = Vec::new();
    for id in &new.adult_ids {
        if parties.iter().any(|p| &p.id == id) {
            return Err(ServiceError::Invalid("bir katta ikki marta tanlanmasin"));
        }
        let m = known
            .iter()
            .find(|m| &m.meta.id == id)
            .ok_or(ServiceError::NotFound)?;
        if m.role != MemberRole::Adult {
            return Err(ServiceError::Invalid(
                "oilaviy kelishuvda faqat kattalar tomon bo'ladi",
            ));
        }
        parties.push(Party {
            id: id.clone(),
            name: m.display_name.clone(),
            role: "Oila a'zosi".to_owned(),
            member_id: Some(id.clone()),
        });
    }
    if parties.is_empty() {
        return Err(ServiceError::Invalid("kamida bitta katta a'zoni tanlang"));
    }
    let duties = new
        .duties
        .iter()
        .map(|d| Duty {
            text: clean(&d.text, 200),
            owner_party_id: Some(d.owner_member_id.clone()),
            if_not_done: clean(&d.if_not_done, 200),
        })
        .collect();
    let today = local_date(env.clock.now());
    let review_date = new.review_date.unwrap_or_else(|| add_months(today, 12));
    let doc = AgreementDoc {
        agreement_type: AgreementType::Family,
        effective_from: today,
        witnesses: Vec::new(),
        questions: Questions {
            parties: Answer::Answered(parties),
            contributions: Answer::NotApplicable {
                reason: "Oilada kapital qayd etilmaydi".to_owned(),
            },
            duties: Answer::Answered(duties),
            profit: Answer::NotApplicable {
                reason: "Oilada foyda taqsimlanmaydi".to_owned(),
            },
            loss: Answer::NotApplicable {
                reason: "Oilada zarar taqsimlanmaydi".to_owned(),
            },
            custody: Answer::Answered(Custody {
                place: custody_place,
                keeper_device_id: None,
                review_every: ReportPeriod::Monthly,
            }),
            exit: Answer::NotApplicable {
                reason: "Oila a'zolari ajralmaydi; alohida kelishuv kerak bo'lsa yangisi tuziladi"
                    .to_owned(),
            },
            arbiter: Answer::NotApplicable {
                reason: "Oila ichida hakam shart emas".to_owned(),
            },
            term: Answer::Answered(Term {
                months: None,
                review_date,
            }),
        },
    };
    agreements::create(
        db,
        env,
        ctx,
        NewAgreement {
            title,
            subject: None,
            doc,
        },
    )
}

/// Xonadonning oilaviy kelishuvlari.
///
/// # Errors
/// Baza xatosi.
pub fn list(conn: &storage::Connection, ctx: &Ctx) -> Result<Vec<AgreementView>, ServiceError> {
    Ok(agreements::list(conn, ctx)?
        .into_iter()
        .filter(|v| v.agreement.agreement_type == AgreementType::Family)
        .collect())
}

/// Katta a'zo PIN bilan tasdiqlaydi (`FamilyConsent`).
///
/// # Errors
/// Kelishuv yoki a'zo topilmasa, a'zo katta bo'lmasa, PIN noto'g'ri bo'lsa, yoki kelishuv 9/9 bo'lmasa.
pub fn consent(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    agreement_id: &str,
    member_id: &str,
    pin: &str,
) -> Result<AgreementView, ServiceError> {
    agreements::sign(
        db,
        env,
        ctx,
        agreement_id,
        AgreementSigner::FamilyConsent {
            member_id: member_id.to_owned(),
            pin: pin.to_owned(),
        },
    )
}

/// Barcha kattalar tasdiqlagach kelishuv faollashadi.
///
/// # Errors
/// Kelishuv imzolanmagan bo'lsa.
pub fn activate(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    agreement_id: &str,
) -> Result<AgreementView, ServiceError> {
    agreements::activate(db, env, ctx, agreement_id)
}
