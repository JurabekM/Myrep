//! Kelishuv dvigateli (SPEC 2F.1–2F.3, 2F.9): kelishuv, o'zgarmas versiyalar, tasdiqlar va holat.
//!
//! - Qoralama to'liq bo'lmasligi mumkin. Imzolash faqat 9/9 va xatosiz versiya uchun ochiladi.
//! - Versiya o'zgarsa kelishuv qoralamaga qaytadi va tasdiqlar qayta so'raladi (eski versiya tasdiqlari o'tmaydi).
//! - Eski sheriklik va qarz tilxatlari `adopt_legacy` bilan ko'chiriladi: versiyalar matn holida saqlanadi,
//!   boshlang'ich holat esa bitta `OPENING_BALANCE` jurnal yozuvi bo'ladi. Ko'chirilgan kelishuvni 9/9 yangi
//!   versiya bilan yangilash majburiy (OPEN_QUESTIONS 87).
use domain::{
    can_transition, canonical, completeness, required_signatures, sha256_hex, warnings, Agreement,
    AgreementDoc, AgreementSignKind, AgreementSignature, AgreementStatus, AgreementType,
    AgreementVersion, Answer, Completeness, Date, Debt, JournalKind, LoanReceipt, MemberRole, Meta,
    Partnership, PartnershipCapital, PartnershipSignature, PartnershipStatus, PartnershipVersion,
    ReceiptKind, Receivable, RequiredSignature, SignMethod, SignatureKind, SubjectKind, Warning,
};
use storage::{repo, Connection, Database};
use time::OffsetDateTime;

use crate::journal::{self, ChainCheck};
use crate::{local_date, members, sum_money, Ctx, Env, ServiceError};

/// Eski ma'lumotdan ko'chirilgan versiyalar mazmuni `format` kaliti bilan belgilanadi.
const LEGACY_FORMAT_KEY: &str = "format";
const MAX_WITNESSES: usize = 4;
const QUESTIONS: u8 = 9;

/// Yangi kelishuv ma'lumoti. `doc.effective_from` o'tmishda bo'lishi mumkin (SPEC 2F.9).
#[derive(Debug, Clone)]
pub struct NewAgreement {
    pub title: String,
    /// Bog'langan obyekt (sheriklik, qarz, berilgan qarz); `None` — mustaqil kelishuv.
    pub subject: Option<(SubjectKind, String)>,
    pub doc: AgreementDoc,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VersionView {
    pub version_no: u32,
    pub content_hash: String,
    pub change_note: Option<String>,
    pub created_at: OffsetDateTime,
}

#[derive(Debug, Clone)]
pub struct AgreementView {
    pub agreement: Agreement,
    /// Joriy versiya hujjati. Eski (matnli) versiya bo'lsa `None`.
    pub doc: Option<AgreementDoc>,
    pub completeness: Completeness,
    pub warnings: Vec<Warning>,
    /// Joriy versiya uchun majburiy tasdiqlar.
    pub required: Vec<RequiredSignature>,
    /// Joriy versiyaga berilgan tasdiqlar.
    pub signatures: Vec<AgreementSignature>,
    pub missing_signatures: Vec<RequiredSignature>,
    pub versions: Vec<VersionView>,
    pub chain: ChainCheck,
}

/// Kim tasdiqlaydi.
#[derive(Debug, Clone)]
pub enum AgreementSigner {
    /// Tomon. Xonadon a'zosi bo'lsa — uning PIN'i majburiy.
    Party {
        party_id: String,
        pin: Option<String>,
    },
    Witness {
        name: String,
    },
    /// Hakam: hakamlikka roziligini imzo bilan bildiradi.
    Arbiter,
    /// Oilaviy rozilik (kattalar, o'z PIN'i bilan).
    FamilyConsent {
        member_id: String,
        pin: String,
    },
}

fn clean(s: &str, max: usize) -> String {
    s.split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .chars()
        .take(max)
        .collect()
}

fn load(conn: &Connection, ctx: &Ctx, id: &str) -> Result<Agreement, ServiceError> {
    let a = repo::get::<Agreement>(conn, id)?.ok_or(ServiceError::NotFound)?;
    if a.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    Ok(a)
}

fn versions_of(
    conn: &Connection,
    ctx: &Ctx,
    id: &str,
) -> Result<Vec<AgreementVersion>, ServiceError> {
    let mut v: Vec<AgreementVersion> = repo::list::<AgreementVersion>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|x| x.agreement_id == id)
        .collect();
    v.sort_by_key(|x| x.version_no);
    Ok(v)
}

fn signatures_of(
    conn: &Connection,
    ctx: &Ctx,
    id: &str,
    version_no: u32,
) -> Result<Vec<AgreementSignature>, ServiceError> {
    Ok(repo::list::<AgreementSignature>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|s| s.agreement_id == id && s.version_no == version_no)
        .collect())
}

/// Joriy versiya hujjati. Eski matnli versiya bo'lsa `None` (9 savol yo'q, faqat ko'rish uchun).
fn current_doc(
    conn: &Connection,
    ctx: &Ctx,
    a: &Agreement,
) -> Result<Option<AgreementDoc>, ServiceError> {
    let row = versions_of(conn, ctx, &a.meta.id)?
        .into_iter()
        .find(|v| v.version_no == a.current_version)
        .ok_or(ServiceError::NotFound)?;
    let value: serde_json::Value = serde_json::from_str(&row.content)
        .map_err(|_| ServiceError::Invalid("kelishuv mazmuni buzilgan"))?;
    if value.get(LEGACY_FORMAT_KEY).is_some() {
        return Ok(None);
    }
    AgreementDoc::from_value(&value)
        .map(Some)
        .map_err(|_| ServiceError::Invalid("kelishuv mazmuni buzilgan"))
}

/// Hisob yurituvchi qurilma: hujjatda ko'rsatilmasa, kelishuvni yaratgan qurilma.
fn prepare(env: &Env<'_>, mut doc: AgreementDoc) -> AgreementDoc {
    if let Answer::Answered(c) = &mut doc.questions.custody {
        if c.keeper_device_id
            .as_deref()
            .is_none_or(|k| k.trim().is_empty())
        {
            c.keeper_device_id = Some(env.device_id.to_owned());
        }
    }
    doc
}

fn keeper_of(doc: &AgreementDoc) -> Option<String> {
    match &doc.questions.custody {
        Answer::Answered(c) => c.keeper_device_id.clone(),
        _ => None,
    }
}

fn content_of(doc: &AgreementDoc) -> Result<(String, String), ServiceError> {
    let text = doc
        .canonical_text()
        .map_err(|_| ServiceError::Invalid("kelishuv mazmuni yaroqsiz"))?;
    let hash = sha256_hex(&text);
    Ok((text, hash))
}

fn validate_header(title: &str, doc: &AgreementDoc) -> Result<(), ServiceError> {
    if clean(title, 80).is_empty() {
        return Err(ServiceError::Invalid("kelishuv nomini yozing"));
    }
    if doc.witnesses.len() > MAX_WITNESSES {
        return Err(ServiceError::Invalid("guvohlar 4 tadan oshmasin"));
    }
    if doc.witnesses.iter().any(|w| clean(w, 60).is_empty()) {
        return Err(ServiceError::Invalid("guvoh ismini yozing"));
    }
    Ok(())
}

fn insert_agreement(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    title: &str,
    subject: Option<(SubjectKind, String)>,
    doc: &AgreementDoc,
    legacy: bool,
) -> Result<Agreement, ServiceError> {
    let (subject_kind, subject_id) = match subject {
        Some((kind, id)) => (kind, Some(id)),
        None => (SubjectKind::Unlinked, None),
    };
    let (text, hash) = content_of(doc)?;
    let agreement = Agreement {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        agreement_type: doc.agreement_type,
        title: clean(title, 80),
        status: AgreementStatus::Draft,
        subject_kind,
        subject_id,
        current_version: 1,
        effective_from: doc.effective_from,
        keeper_device_id: keeper_of(doc).or_else(|| Some(env.device_id.to_owned())),
        legacy,
    };
    repo::insert(conn, &agreement)?;
    repo::insert(
        conn,
        &AgreementVersion {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            agreement_id: agreement.meta.id.clone(),
            version_no: 1,
            content: text,
            content_hash: hash,
            change_note: None,
        },
    )?;
    Ok(agreement)
}

/// Yangi kelishuv (qoralama, 1-versiya) — boshqa tranzaksiya ichida ham chaqirilishi mumkin.
/// To'liqlik shart emas: imzolashda tekshiriladi.
///
/// # Errors
/// Sarlavha, guvohlar yoki bog'langan obyekt uchun kelishuv allaqachon borligi.
pub fn create_in(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewAgreement,
) -> Result<String, ServiceError> {
    validate_header(&new.title, &new.doc)?;
    if let Some((kind, id)) = &new.subject {
        let taken = repo::list::<Agreement>(conn, &ctx.household_id)?
            .iter()
            .any(|a| a.subject_kind == *kind && a.subject_id.as_deref() == Some(id.as_str()));
        if taken {
            return Err(ServiceError::Invalid(
                "bu obyekt uchun kelishuv allaqachon bor",
            ));
        }
    }
    let doc = prepare(env, new.doc);
    let a = insert_agreement(conn, env, ctx, &new.title, new.subject, &doc, false)?;
    Ok(a.meta.id)
}

/// Yangi kelishuv (qoralama, 1-versiya) va uning ko'rinishi.
///
/// # Errors
/// [`create_in`] dagi xatolar.
pub fn create(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewAgreement,
) -> Result<AgreementView, ServiceError> {
    let id = db.transaction::<String, ServiceError>(|tx| create_in(tx, env, ctx, new))?;
    view(db.conn(), ctx, &id)
}

/// Yangi versiya. Holat qoralamaga qaytadi, joriy versiya tasdiqlari yangi versiyaga o'tmaydi.
///
/// # Errors
/// Kelishuv yopilgan, tur o'zgartirilmoqchi yoki sarlavha/guvoh noto'g'ri.
/// Yangi versiya (tranzaksiya ichida). Holat qoralamaga qaytadi; yopilgan kelishuv o'zgarmaydi.
///
/// # Errors
/// Kelishuv yopilgan, tur o'zgartirilmoqchi yoki noto'g'ri ma'lumot.
pub fn save_version_in(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    doc: AgreementDoc,
    change_note: Option<&str>,
) -> Result<(), ServiceError> {
    let note = change_note.map(|n| clean(n, 200)).filter(|n| !n.is_empty());
    let mut a = load(conn, ctx, id)?;
    if a.status == AgreementStatus::Closed {
        return Err(ServiceError::Invalid("yopilgan kelishuv o'zgarmaydi"));
    }
    if doc.agreement_type != a.agreement_type {
        return Err(ServiceError::Invalid(
            "kelishuv turini o'zgartirib bo'lmaydi",
        ));
    }
    let doc = prepare(env, doc);
    let (text, hash) = content_of(&doc)?;
    let next = a.current_version + 1;
    repo::insert(
        conn,
        &AgreementVersion {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            agreement_id: id.to_owned(),
            version_no: next,
            content: text,
            content_hash: hash,
            change_note: note,
        },
    )?;
    a.current_version = next;
    a.effective_from = doc.effective_from;
    if let Some(k) = keeper_of(&doc) {
        a.keeper_device_id = Some(k);
    }
    if matches!(
        a.status,
        AgreementStatus::Signed | AgreementStatus::Active | AgreementStatus::InDispute
    ) {
        a.status = AgreementStatus::Draft;
    }
    repo::update(conn, &a, env.clock.now())?;
    Ok(())
}

/// Yangi versiya va uning ko'rinishi.
///
/// # Errors
/// [`save_version_in`] dagi xatolar.
pub fn save_version(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    doc: AgreementDoc,
    change_note: Option<&str>,
) -> Result<AgreementView, ServiceError> {
    db.transaction::<(), ServiceError>(|tx| save_version_in(tx, env, ctx, id, doc, change_note))?;
    view(db.conn(), ctx, id)
}

/// Sheriklikka bog'langan kelishuv (subject = sheriklik id).
///
/// # Errors
/// Baza xatosi.
pub fn agreement_of_partnership(
    conn: &Connection,
    ctx: &Ctx,
    partnership_id: &str,
) -> Result<Option<Agreement>, ServiceError> {
    Ok(repo::list::<Agreement>(conn, &ctx.household_id)?
        .into_iter()
        .find(|a| {
            a.subject_kind == SubjectKind::Partnership
                && a.subject_id.as_deref() == Some(partnership_id)
        }))
}

/// Kelishuvning joriy versiyasidagi tasdiqlar (ko'rinish uchun).
///
/// # Errors
/// Baza xatosi.
pub fn current_signatures(
    conn: &Connection,
    ctx: &Ctx,
    a: &Agreement,
) -> Result<Vec<AgreementSignature>, ServiceError> {
    signatures_of(conn, ctx, &a.meta.id, a.current_version)
}

fn all_required_signed(
    conn: &Connection,
    ctx: &Ctx,
    a: &Agreement,
    doc: &AgreementDoc,
) -> Result<bool, ServiceError> {
    let sigs = signatures_of(conn, ctx, &a.meta.id, a.current_version)?;
    Ok(required_signatures(doc).iter().all(|r| {
        sigs.iter()
            .any(|s| s.kind == r.kind && s.signer_key == r.key)
    }))
}

/// Joriy versiyani tasdiqlaydi. 9/9 va xatosiz bo'lishi shart; tomon PIN'i ham tekshiriladi.
///
/// # Errors
/// Eski versiya, to'liq bo'lmagan kelishuv, noma'lum tomon/guvoh/a'zo, noto'g'ri PIN.
pub fn sign(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    signer: AgreementSigner,
) -> Result<AgreementView, ServiceError> {
    let a = load(db.conn(), ctx, id)?;
    if a.status == AgreementStatus::Closed {
        return Err(ServiceError::Invalid("kelishuv yopilgan"));
    }
    let doc = current_doc(db.conn(), ctx, &a)?.ok_or(ServiceError::Invalid(
        "bu eski matnli versiya: avval 9 savolli yangi versiya yarating",
    ))?;
    if !completeness(&doc).is_complete() {
        return Err(ServiceError::Invalid(
            "9 savolning hammasiga javob bering va xatolarni tuzating",
        ));
    }
    let (kind, key, name, method) = match signer {
        AgreementSigner::Party { party_id, pin } => {
            let party = match &doc.questions.parties {
                Answer::Answered(ps) => ps.iter().find(|p| p.id == party_id).cloned(),
                _ => None,
            }
            .ok_or(ServiceError::NotFound)?;
            if let Some(member) = &party.member_id {
                let pin = pin.ok_or(ServiceError::NoPin)?;
                members::verify(db, env, ctx, member, &pin)?;
            }
            (
                AgreementSignKind::Party,
                party.id,
                party.name,
                SignMethod::InApp,
            )
        }
        AgreementSigner::Witness { name } => {
            if !doc.witnesses.contains(&name) {
                return Err(ServiceError::NotFound);
            }
            (
                AgreementSignKind::Witness,
                name.clone(),
                name,
                SignMethod::InApp,
            )
        }
        AgreementSigner::Arbiter => match &doc.questions.arbiter {
            Answer::Answered(arbiter) => (
                AgreementSignKind::Arbiter,
                "arbiter".to_owned(),
                arbiter.name.clone(),
                SignMethod::InApp,
            ),
            _ => return Err(ServiceError::Invalid("bu kelishuvda hakam belgilanmagan")),
        },
        AgreementSigner::FamilyConsent { member_id, pin } => {
            let member = members::list(db.conn(), ctx)?
                .into_iter()
                .find(|m| m.meta.id == member_id)
                .ok_or(ServiceError::NotFound)?;
            if member.role != MemberRole::Adult {
                return Err(ServiceError::Invalid("rozilikni faqat kattalar beradi"));
            }
            members::verify(db, env, ctx, &member_id, &pin)?;
            (
                AgreementSignKind::FamilyConsent,
                member_id,
                member.display_name,
                SignMethod::FamilyPin,
            )
        }
    };
    let already = signatures_of(db.conn(), ctx, id, a.current_version)?
        .iter()
        .any(|s| s.kind == kind && s.signer_key == key);
    if !already {
        repo::insert(
            db.conn(),
            &AgreementSignature {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                agreement_id: id.to_owned(),
                version_no: a.current_version,
                kind,
                signer_key: key,
                signer_name: name,
                method,
            },
        )?;
    }
    let mut fresh = load(db.conn(), ctx, id)?;
    if fresh.status == AgreementStatus::Draft
        && all_required_signed(db.conn(), ctx, &fresh, &doc)?
        && can_transition(fresh.status, AgreementStatus::Signed)
    {
        fresh.status = AgreementStatus::Signed;
        repo::update(db.conn(), &fresh, env.clock.now())?;
    }
    view(db.conn(), ctx, id)
}

/// Imzolangan kelishuvni faollashtiradi (SIGNED → ACTIVE). Qo'shimcha shartlar (darvoza, oilaviy rozilik)
/// chaqiruvchi qatlamda tekshiriladi.
///
/// # Errors
/// Kelishuv imzolanmagan yoki yopilgan bo'lsa.
pub fn activate_in(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<(), ServiceError> {
    let mut a = load(conn, ctx, id)?;
    if !can_transition(a.status, AgreementStatus::Active) {
        return Err(ServiceError::Invalid(
            "faqat imzolangan kelishuv faollashadi",
        ));
    }
    a.status = AgreementStatus::Active;
    repo::update(conn, &a, env.clock.now())?;
    Ok(())
}

/// Imzolangan kelishuvni faollashtiradi va ko'rinishini qaytaradi.
///
/// # Errors
/// [`activate_in`] dagi xatolar.
pub fn activate(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<AgreementView, ServiceError> {
    activate_in(db.conn(), env, ctx, id)?;
    view(db.conn(), ctx, id)
}

/// Kelishuvni yopadi (muddati tugadi yoki bekor qilindi).
///
/// # Errors
/// Kelishuv allaqachon yopilgan bo'lsa.
pub fn close_in(conn: &Connection, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let mut a = load(conn, ctx, id)?;
    if !can_transition(a.status, AgreementStatus::Closed) {
        return Err(ServiceError::Invalid("kelishuv allaqachon yopilgan"));
    }
    a.status = AgreementStatus::Closed;
    repo::update(conn, &a, env.clock.now())?;
    Ok(())
}

/// Kelishuvni yopadi.
///
/// # Errors
/// [`close_in`] dagi xatolar.
pub fn close(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    close_in(db.conn(), env, ctx, id)
}

/// Joriy versiya 9/9, xatosiz va barcha majburiy tasdiqlar bilan: davrni yopish va taqsimot uchun shart.
///
/// # Errors
/// Baza xatosi.
pub fn is_fully_signed(conn: &Connection, ctx: &Ctx, id: &str) -> Result<bool, ServiceError> {
    let a = load(conn, ctx, id)?;
    let Some(doc) = current_doc(conn, ctx, &a)? else {
        return Ok(false);
    };
    Ok(completeness(&doc).is_complete() && all_required_signed(conn, ctx, &a, &doc)?)
}

fn versions_view(conn: &Connection, ctx: &Ctx, id: &str) -> Result<Vec<VersionView>, ServiceError> {
    Ok(versions_of(conn, ctx, id)?
        .into_iter()
        .map(|v| VersionView {
            version_no: v.version_no,
            content_hash: v.content_hash,
            change_note: v.change_note,
            created_at: v.meta.created_at,
        })
        .collect())
}

/// Kelishuvning to'liq ko'rinishi: hujjat, to'liqlik, tasdiqlar, versiyalar va jurnal zanjiri.
///
/// # Errors
/// Topilmasa yoki baza xatosi.
pub fn view(conn: &Connection, ctx: &Ctx, id: &str) -> Result<AgreementView, ServiceError> {
    let a = load(conn, ctx, id)?;
    let doc = current_doc(conn, ctx, &a)?;
    let (done, notes, required) = match &doc {
        Some(d) => (completeness(d), warnings(d), required_signatures(d)),
        None => (
            Completeness {
                missing: (1..=QUESTIONS).collect(),
                errors: Vec::new(),
            },
            Vec::new(),
            Vec::new(),
        ),
    };
    let signatures = signatures_of(conn, ctx, id, a.current_version)?;
    let missing_signatures = required
        .iter()
        .filter(|r| {
            !signatures
                .iter()
                .any(|s| s.kind == r.kind && s.signer_key == r.key)
        })
        .cloned()
        .collect();
    let chain = journal::verify(conn, ctx, id)?;
    Ok(AgreementView {
        versions: versions_view(conn, ctx, id)?,
        agreement: a,
        doc,
        completeness: done,
        warnings: notes,
        required,
        signatures,
        missing_signatures,
        chain,
    })
}

/// Xonadonning barcha kelishuvlari (yaratilish tartibida).
///
/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, ctx: &Ctx) -> Result<Vec<AgreementView>, ServiceError> {
    repo::list::<Agreement>(conn, &ctx.household_id)?
        .into_iter()
        .map(|a| view(conn, ctx, &a.meta.id))
        .collect()
}

// ------------------------------------------------------------------ eski ma'lumotni ko'chirish

fn legacy_content(value: &serde_json::Value) -> Result<(String, String), ServiceError> {
    let text = canonical(value).map_err(|_| ServiceError::Invalid("eski ma'lumot yaroqsiz"))?;
    let hash = sha256_hex(&text);
    Ok((text, hash))
}

fn adopt_partnership(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    p: &Partnership,
) -> Result<(), ServiceError> {
    let status = match p.status {
        PartnershipStatus::Draft => AgreementStatus::Draft,
        PartnershipStatus::Active => AgreementStatus::Active,
        PartnershipStatus::Ended => AgreementStatus::Closed,
    };
    let effective_from: Date = local_date(p.meta.created_at);
    let agreement = Agreement {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        agreement_type: AgreementType::Partnership,
        title: clean(&p.name, 80),
        status,
        subject_kind: SubjectKind::Partnership,
        subject_id: Some(p.meta.id.clone()),
        current_version: p.version,
        effective_from,
        keeper_device_id: Some(env.device_id.to_owned()),
        legacy: true,
    };
    repo::insert(conn, &agreement)?;

    let snapshots: Vec<PartnershipVersion> =
        repo::list::<PartnershipVersion>(conn, &ctx.household_id)?
            .into_iter()
            .filter(|v| v.partnership_id == p.meta.id)
            .collect();
    let mut has_current = false;
    for v in &snapshots {
        has_current |= v.version == p.version;
        let (content, hash) = legacy_content(&serde_json::json!({
            LEGACY_FORMAT_KEY: "LEGACY_TEXT",
            "text": v.snapshot,
        }))?;
        repo::insert(
            conn,
            &AgreementVersion {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                agreement_id: agreement.meta.id.clone(),
                version_no: v.version,
                content,
                content_hash: hash,
                change_note: Some("Eski ma'lumotdan ko'chirildi".into()),
            },
        )?;
    }
    if !has_current {
        let (content, hash) = legacy_content(&serde_json::json!({
            LEGACY_FORMAT_KEY: "LEGACY_TEXT",
            "text": "",
        }))?;
        repo::insert(
            conn,
            &AgreementVersion {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                agreement_id: agreement.meta.id.clone(),
                version_no: p.version,
                content,
                content_hash: hash,
                change_note: Some("Eski ma'lumotdan ko'chirildi (matn saqlanmagan)".into()),
            },
        )?;
    }

    let signatures: Vec<PartnershipSignature> =
        repo::list::<PartnershipSignature>(conn, &ctx.household_id)?
            .into_iter()
            .filter(|s| s.partnership_id == p.meta.id)
            .collect();
    for s in &signatures {
        let (kind, method) = match s.kind {
            SignatureKind::Party => (AgreementSignKind::Party, SignMethod::InApp),
            SignatureKind::Witness => (AgreementSignKind::Witness, SignMethod::InApp),
            SignatureKind::FamilyConsent => {
                (AgreementSignKind::FamilyConsent, SignMethod::FamilyPin)
            }
        };
        repo::insert(
            conn,
            &AgreementSignature {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                agreement_id: agreement.meta.id.clone(),
                version_no: s.version,
                kind,
                signer_key: s.signer.clone(),
                signer_name: s.signer_name.clone(),
                method,
            },
        )?;
    }

    let capital: Vec<PartnershipCapital> =
        repo::list::<PartnershipCapital>(conn, &ctx.household_id)?
            .into_iter()
            .filter(|c| c.partnership_id == p.meta.id)
            .collect();
    let total = sum_money(ctx.currency, capital.iter().map(|c| c.value))?;
    journal::append(
        conn,
        env,
        ctx,
        &agreement,
        journal::NewEntry {
            kind: JournalKind::OpeningBalance,
            party_id: None,
            amount: Some(total),
            date: effective_from,
            note: "Ko'chirish: sheriklikning boshlang'ich kapitali",
            reference: Some(p.meta.id.as_str()),
            corrects: None,
        },
    )?;
    Ok(())
}

/// Qarz tilxati (`LoanReceipt`) uchun kelishuv. Obyekt topilmasa `false` (o'tkazib yuboriladi).
fn adopt_receipt(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    r: &LoanReceipt,
) -> Result<bool, ServiceError> {
    let (subject_kind, title, date, amount) = match r.kind {
        ReceiptKind::Debt => {
            let Some(d) = repo::get::<Debt>(conn, &r.ref_id)? else {
                return Ok(false);
            };
            (
                SubjectKind::Debt,
                format!("Qarz: {}", d.creditor),
                d.borrowed_on,
                d.principal,
            )
        }
        ReceiptKind::Receivable => {
            let Some(rv) = repo::get::<Receivable>(conn, &r.ref_id)? else {
                return Ok(false);
            };
            (
                SubjectKind::Receivable,
                format!("Berilgan qarz: {}", rv.debtor),
                rv.given_on,
                rv.amount,
            )
        }
    };
    let agreement = Agreement {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        agreement_type: AgreementType::Loan,
        title: clean(&title, 80),
        status: AgreementStatus::Draft,
        subject_kind,
        subject_id: Some(r.ref_id.clone()),
        current_version: 1,
        effective_from: date,
        keeper_device_id: Some(env.device_id.to_owned()),
        legacy: true,
    };
    repo::insert(conn, &agreement)?;
    let (content, hash) = legacy_content(&serde_json::json!({
        LEGACY_FORMAT_KEY: "LEGACY_REF",
        "kind": r.kind.as_str(),
        "refId": r.ref_id,
        "witnesses": r.witnesses,
        "confirmedByCounterparty": r.confirmed_by_counterparty,
    }))?;
    repo::insert(
        conn,
        &AgreementVersion {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            agreement_id: agreement.meta.id.clone(),
            version_no: 1,
            content,
            content_hash: hash,
            change_note: Some("Eski tilxatdan ko'chirildi".into()),
        },
    )?;
    journal::append(
        conn,
        env,
        ctx,
        &agreement,
        journal::NewEntry {
            kind: JournalKind::OpeningBalance,
            party_id: None,
            amount: Some(amount),
            date,
            note: "Ko'chirish: qarzning boshlang'ich summasi",
            reference: Some(r.ref_id.as_str()),
            corrects: None,
        },
    )?;
    Ok(true)
}

/// Eski sheriklik va qarz tilxatlarini kelishuvlarga ko'chiradi. Idempotent: ikkinchi chaqiruvda hech narsa
/// qo'shilmaydi. Ilova ochilganda chaqiriladi.
///
/// # Errors
/// Baza xatosi (tranzaksiya bekor qilinadi).
pub fn adopt_legacy(db: &mut Database, env: &Env<'_>, ctx: &Ctx) -> Result<usize, ServiceError> {
    let existing = repo::list::<Agreement>(db.conn(), &ctx.household_id)?;
    let has = |kind: SubjectKind, id: &str| {
        existing
            .iter()
            .any(|a| a.subject_kind == kind && a.subject_id.as_deref() == Some(id))
    };
    let partnerships: Vec<Partnership> = repo::list::<Partnership>(db.conn(), &ctx.household_id)?
        .into_iter()
        .filter(|p| !has(SubjectKind::Partnership, &p.meta.id))
        .collect();
    let receipts: Vec<LoanReceipt> = repo::list::<LoanReceipt>(db.conn(), &ctx.household_id)?
        .into_iter()
        .filter(|r| {
            let kind = match r.kind {
                ReceiptKind::Debt => SubjectKind::Debt,
                ReceiptKind::Receivable => SubjectKind::Receivable,
            };
            !has(kind, &r.ref_id)
        })
        .collect();
    db.transaction::<usize, ServiceError>(|tx| {
        for p in &partnerships {
            adopt_partnership(tx, env, ctx, p)?;
        }
        let mut loans = 0;
        for r in &receipts {
            if adopt_receipt(tx, env, ctx, r)? {
                loans += 1;
            }
        }
        Ok(partnerships.len() + loans)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn clean_collapses_spaces_and_limits_length() {
        assert_eq!(clean("  Anvar   va  Dilshod ", 80), "Anvar va Dilshod");
        assert_eq!(clean("abcdef", 3), "abc");
    }

    #[test]
    fn legacy_marker_is_the_format_key() {
        let (text, _) =
            legacy_content(&serde_json::json!({"format": "LEGACY_TEXT", "text": "x"})).unwrap();
        assert!(text.starts_with("{\"format\":"));
    }
}
