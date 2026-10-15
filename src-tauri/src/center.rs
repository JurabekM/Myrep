//! D13A xizmati: kelishuvlar markazi — jadval, vazifa hodisalari (`DutyIncident`), oylik ochiq hisob ko'rigi
//! (belgilar + bayonnoma PDF `chain_head` bilan), nizo va hakam (ish papkasi PDF, qaror, yangi versiya),
//! yillik yangilash («o'zgarishsiz tasdiqlandi» ham versiya), oilaviy kelishuvlar (4 shablon, ADULT PIN tasdig'i).
//!
//! `IN_DISPUTE` da taqsimot bloklanadi — `ventures::close_period` (`ensure_distribution_allowed`).

use domain::MemberRole;
use domain::agreement::{AgreementStatus, AgreementType};
use domain::journal::{GENESIS_HASH, JournalKind};
use domain::review::review_reminder_due;
use money::Money;
use security::{SecurityError, verify_member_pin};
use storage::{
    AgreementRepo, AgreementRow, CenterRepo, Database, DisputeRow, IncidentRow, JournalRepo,
    MarkRow, MemberRepo, PinRepo, ReviewRow, StorageError, StoredEntry,
};
use time::format_description::well_known::Iso8601;
use time::{Date, Duration, OffsetDateTime};

use crate::agreements;
use crate::dto::{
    AgreementAnswersDto, AgreementDto, AgreementInputDto, AgreementOpsDto, CenterDto,
    CenterRowDto, DecideDisputeInputDto, DisputeDto, DisputeInputDto, DutyDto, FamilyAdultDto,
    FamilyConfirmInputDto, FamilyConsentsDto, FamilyTemplateDto, IncidentDto, IncidentInputDto,
    JournalEntryDto, MarkReviewInputDto, MoneyDto, OpenReviewInputDto, PartyDto, ReviewDto,
    ReviewMarkDto, SaveAnswersInputDto, SummaryLineDto, VersionNoteDto,
};
use crate::family::{ensure_not_locked, kdf_params};
use crate::finance::{self, CURRENCY, DEVICE_ID, UuidV7, date_text, Context};
use crate::session::SessionError;

const DISCLAIMER: &str = "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.";
const DECISIONS: [&str; 2] = ["AGREE", "OBJECT"];

/// Oilaviy kelishuv shabloni (SPEC 2F.10): sarlavha, tavsif, vazifalar, 6-savol matni.
struct FamilyTemplate {
    id: &'static str,
    title: &'static str,
    description: &'static str,
    duties: &'static [(&'static str, &'static str)],
    custody: &'static str,
}

const FAMILY_TEMPLATES: [FamilyTemplate; 4] = [
    FamilyTemplate {
        id: "FAMILY_CHORES",
        title: "Uyda kim nima qiladi",
        description: "Uy ishlari taqsimoti: har ishga bitta mas'ul va «bajarilmasa» bandi.",
        duties: &[
            ("Oshxona va dasturxon", "o'sha kuni boshqa a'zo yordam beradi, ertasiga qaytariladi"),
            ("Bozor va xaridlar", "ro'yxat oldindan yoziladi; unutilgan narsa ertasiga olinadi"),
            ("Bolalar darslari", "haftasiga 3 kun; bajarilmasa dam olish kuni qoplanadi"),
        ],
        custody: "Uy ishlari jadvali oshxona devorida; oyiga bir marta oila kengashida ko'riladi.",
    },
    FamilyTemplate {
        id: "FAMILY_MONEY",
        title: "Pul qayerda turadi va kim yuritadi",
        description: "Oila pulining joyi, hisob yurituvchi va ko'rib chiqish davriyligi.",
        duties: &[
            ("Daftarni yuritish", "haftada bir marta; qoldirilsa, keyingi kuni to'ldiriladi"),
            ("Qorovul zaxirasini to'ldirish", "har daromaddan ulush; qoldirilsa oila kengashida tushuntiriladi"),
        ],
        custody: "Naqd pul uy seyfida, karta egasining nomida; daftarni «O'zim» yuritadi, oyiga bir ko'rik.",
    },
    FamilyTemplate {
        id: "FAMILY_HAVAS",
        title: "Havas chegarasi",
        description: "Oylik havas xarajati chegarasi va uni kattalar roziligi bilan o'zgartirish tartibi (2B.3).",
        duties: &[
            ("Chegarani kuzatish", "oshsa — keyingi oy shuncha kam; ikki marta oshsa oila kengashi"),
            ("Katta xaridni oldindan aytish", "aytilmagan katta xarid oila kengashida ko'riladi"),
        ],
        custody: "Havas chegarasi ilovada; o'zgartirish faqat barcha kattalar roziligi bilan.",
    },
    FamilyTemplate {
        id: "FAMILY_COUNCIL",
        title: "Oylik oila kengashi qachon o'tadi",
        description: "Oila kengashi kuni, davomiyligi va kun tartibi.",
        duties: &[
            ("Kengashni chaqirish", "oyning birinchi juma kechqurun; o'tkazilmasa keyingi hafta"),
            ("Bayonnomani saqlash", "PDF ilova papkasida; yo'qolsa qayta yaratiladi"),
        ],
        custody: "Kengash bayonnomalari ilovada; har kengashda oldingisi o'qiladi.",
    },
];

fn parse_date(text: &str) -> Result<Date, SessionError> {
    Date::parse(text, &Iso8601::DATE).map_err(|_| DomainErrorInvalidDay.into())
}

/// `DomainError::InvalidDay` uchun qisqa nom (ko'p ishlatiladi).
struct DomainErrorInvalidDay;

impl From<DomainErrorInvalidDay> for SessionError {
    fn from(_: DomainErrorInvalidDay) -> Self {
        domain::DomainError::InvalidDay.into()
    }
}

fn add(left: Money, right: Money) -> Result<Money, SessionError> {
    Ok(left.checked_add(right).map_err(domain::DomainError::from)?)
}

fn pretty(date: Date) -> String {
    date.format(&time::macros::format_description!(
        "[day].[month].[year]"
    ))
    .unwrap_or_default()
}

fn kind_label(kind: JournalKind) -> &'static str {
    match kind {
        JournalKind::VentureIncome => "Kirim",
        JournalKind::VentureExpense => "Xarajat",
        JournalKind::ForceMajeure => "Fors-major",
        JournalKind::ProfitDistribution => "Foyda taqsimoti",
        JournalKind::LossDistribution => "Zarar taqsimoti",
        JournalKind::BuyoutPayment => "Buyout to'lovi",
        JournalKind::OpeningBalance => "Boshlang'ich balans",
        JournalKind::Contribution => "Hissa",
        JournalKind::LoanPayment => "Qarz to'lovi",
        JournalKind::Correction => "Tuzatish",
    }
}

fn load(db: &Database, id: &str) -> Result<AgreementRow, SessionError> {
    AgreementRepo::new(db.connection())
        .find(id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))
}

fn answers_of(row: &AgreementRow) -> Result<AgreementAnswersDto, SessionError> {
    serde_json::from_str(&row.answers_json)
        .map_err(|_| StorageError::InvalidData("kelishuv javoblari".to_owned()).into())
}

fn party_name(answers: &AgreementAnswersDto, id: &str) -> String {
    answers
        .parties
        .iter()
        .find(|p| p.id == id)
        .map_or_else(|| id.to_owned(), |p| p.name.clone())
}

fn duty_of<'a>(answers: &'a AgreementAnswersDto, id: &str) -> Option<&'a DutyDto> {
    answers.duties.iter().find(|d| d.id == id)
}

fn review_date_of(answers: &AgreementAnswersDto) -> Option<Date> {
    if answers.review_date.trim().is_empty() {
        None
    } else {
        Date::parse(&answers.review_date, &Iso8601::DATE).ok()
    }
}

fn entry_dto(stored: &StoredEntry) -> JournalEntryDto {
    JournalEntryDto {
        seq: u32::try_from(stored.seq).unwrap_or(u32::MAX),
        kind: stored.entry.kind.code().to_owned(),
        party_id: stored.entry.party_id.clone(),
        amount: MoneyDto::of(stored.entry.amount),
        date: date_text(stored.entry.date),
        note: stored.entry.note.clone(),
        hash: stored.hash.clone(),
    }
}

/// Davr yakuni: turlar bo'yicha yig'indilar (faqat nolmas qatorlar).
fn summary_of(entries: &[&StoredEntry]) -> Result<Vec<SummaryLineDto>, SessionError> {
    let groups: [(&str, &[JournalKind]); 6] = [
        ("Kirim", &[JournalKind::VentureIncome]),
        ("Xarajat", &[JournalKind::VentureExpense, JournalKind::ForceMajeure]),
        ("Hissalar", &[JournalKind::Contribution, JournalKind::OpeningBalance]),
        ("Qarz to'lovlari", &[JournalKind::LoanPayment]),
        (
            "Taqsimot",
            &[JournalKind::ProfitDistribution, JournalKind::LossDistribution],
        ),
        ("Buyout", &[JournalKind::BuyoutPayment]),
    ];
    let mut out = Vec::new();
    for (label, kinds) in groups {
        let mut total = Money::zero(CURRENCY);
        for stored in entries.iter().filter(|s| kinds.contains(&s.entry.kind)) {
            total = add(total, stored.entry.amount)?;
        }
        if total.minor() != 0 {
            out.push(SummaryLineDto {
                label: label.to_owned(),
                amount: MoneyDto::of(total),
            });
        }
    }
    Ok(out)
}

fn incident_dto(answers: &AgreementAnswersDto, row: &IncidentRow) -> IncidentDto {
    let duty = duty_of(answers, &row.duty_id);
    IncidentDto {
        id: row.id.clone(),
        duty_id: row.duty_id.clone(),
        duty_title: duty.map_or_else(|| row.duty_id.clone(), |d| d.title.clone()),
        breach_clause: duty.map_or_else(String::new, |d| d.breach_clause.clone()),
        party_id: row.party_id.clone(),
        party_name: party_name(answers, &row.party_id),
        reason: row.reason.clone(),
        proposed_fix: row.proposed_fix.clone(),
        occurred_on: date_text(row.occurred_on),
        resolved: row.resolved_at.is_some(),
    }
}

fn review_dto(
    db: &Database,
    answers: &AgreementAnswersDto,
    row: &ReviewRow,
) -> Result<ReviewDto, SessionError> {
    let repo = CenterRepo::new(db.connection());
    let all = JournalRepo::new(db.connection()).list(&row.agreement_id)?;
    let entries: Vec<&StoredEntry> = all
        .iter()
        .filter(|s| s.entry.date >= row.period_start && s.entry.date <= row.period_end)
        .collect();
    let marks = repo.marks(&row.id)?;
    let mark_dtos: Vec<ReviewMarkDto> = answers
        .parties
        .iter()
        .map(|party| {
            let mark = marks.iter().find(|m| m.party_id == party.id);
            ReviewMarkDto {
                party_id: party.id.clone(),
                name: party.name.clone(),
                decision: mark.map(|m| m.decision.clone()),
                comment: mark.and_then(|m| m.comment.clone()),
            }
        })
        .collect();
    let incidents = repo
        .incidents(&row.agreement_id)?
        .iter()
        .filter(|i| i.resolved_at.is_none())
        .map(|i| incident_dto(answers, i))
        .collect();
    Ok(ReviewDto {
        id: row.id.clone(),
        agreement_id: row.agreement_id.clone(),
        period_start: date_text(row.period_start),
        period_end: date_text(row.period_end),
        summary: summary_of(&entries)?,
        entries: entries.iter().map(|s| entry_dto(s)).collect(),
        incidents,
        chain_ok: row.chain_ok,
        chain_head: row.chain_head.clone(),
        complete: mark_dtos.iter().all(|m| m.decision.is_some()),
        marks: mark_dtos,
        created_on: date_text(row.created_at.date()),
    })
}

fn dispute_dto(answers: &AgreementAnswersDto, row: &DisputeRow) -> DisputeDto {
    DisputeDto {
        id: row.id.clone(),
        agreement_id: row.agreement_id.clone(),
        opened_by_party_id: row.opened_by_party_id.clone(),
        opened_by_name: party_name(answers, &row.opened_by_party_id),
        subject: row.subject.clone(),
        clauses: row.clauses.clone(),
        claim: row.claim.clone(),
        opened_on: date_text(row.opened_on),
        decision: row.decision.clone(),
        decided_on: row.decided_on.map(date_text),
    }
}

fn family_dto(
    db: &Database,
    ctx: &Context,
    row: &AgreementRow,
) -> Result<Option<FamilyConsentsDto>, SessionError> {
    if row.kind != AgreementType::Family {
        return Ok(None);
    }
    let consents = CenterRepo::new(db.connection()).family_consents(&row.id, row.version)?;
    let members = MemberRepo::new(db.connection()).list_for_household(&ctx.household.id)?;
    let mut adults = Vec::new();
    for member in members.iter().filter(|m| m.role == MemberRole::Adult) {
        let has_pin = PinRepo::new(db.connection())
            .find(&member.id)?
            .and_then(|p| p.verifier)
            .is_some();
        adults.push(FamilyAdultDto {
            member_id: member.id.clone(),
            name: member.name.clone(),
            has_pin,
            confirmed: consents.iter().any(|id| id == &member.id),
        });
    }
    let complete = !adults.is_empty() && adults.iter().all(|a| a.confirmed);
    Ok(Some(FamilyConsentsDto { adults, complete }))
}

/// Kelishuv amaliyotlari: hodisalar, ko'riklar, nizolar, versiya izohlari, oilaviy tasdiqlar.
pub fn ops(db: &Database, now: OffsetDateTime, agreement_id: &str) -> Result<AgreementOpsDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let row = load(db, agreement_id)?;
    let answers = answers_of(&row)?;
    let repo = CenterRepo::new(db.connection());
    let review_date = review_date_of(&answers);
    let mut reviews = Vec::new();
    for review in repo.reviews(&row.id)? {
        reviews.push(review_dto(db, &answers, &review)?);
    }
    Ok(AgreementOpsDto {
        agreement_id: row.id.clone(),
        status: row.status.code().to_owned(),
        version: u32::try_from(row.version).unwrap_or(u32::MAX),
        review_date: review_date.map(date_text),
        review_due: review_date.is_some_and(|d| review_reminder_due(d, ctx.today)),
        incidents: repo
            .incidents(&row.id)?
            .iter()
            .map(|i| incident_dto(&answers, i))
            .collect(),
        reviews,
        disputes: repo
            .disputes(&row.id)?
            .iter()
            .map(|d| dispute_dto(&answers, d))
            .collect(),
        version_notes: repo
            .version_notes(&row.id)?
            .into_iter()
            .map(|(version, note, at)| VersionNoteDto {
                version: u32::try_from(version).unwrap_or(u32::MAX),
                note,
                date: date_text(at.date()),
            })
            .collect(),
        family: family_dto(db, &ctx, &row)?,
    })
}

/// Markaz jadvali: barcha kelishuvlar — turi, holati, keyingi ko'rik, ochiq hodisalar, nizolar, zanjir.
pub fn center(db: &Database, now: OffsetDateTime) -> Result<CenterDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let repo = CenterRepo::new(db.connection());
    let journal = JournalRepo::new(db.connection());
    let rows = AgreementRepo::new(db.connection()).list(&ctx.household.id)?;
    let mut out = Vec::with_capacity(rows.len());
    for row in &rows {
        let answers = answers_of(row)?;
        let review_date = review_date_of(&answers);
        let family = family_dto(db, &ctx, row)?;
        out.push(CenterRowDto {
            id: row.id.clone(),
            kind: row.kind.code().to_owned(),
            title: row.title.clone(),
            status: row.status.code().to_owned(),
            version: u32::try_from(row.version).unwrap_or(u32::MAX),
            review_date: review_date.map(date_text),
            review_due: review_date.is_some_and(|d| review_reminder_due(d, ctx.today)),
            open_incidents: repo.open_incident_count(&row.id)?,
            open_disputes: repo.open_dispute_count(&row.id)?,
            chain_ok: journal.verify(&row.id)?.is_ok(),
            family_pending: family.map_or(0, |f| {
                u32::try_from(f.adults.iter().filter(|a| !a.confirmed).count()).unwrap_or(u32::MAX)
            }),
        });
    }
    Ok(CenterDto { rows: out })
}

fn ensure_active(row: &AgreementRow) -> Result<(), SessionError> {
    if matches!(row.status, AgreementStatus::Draft | AgreementStatus::Ended) {
        return Err(domain::DomainError::AgreementNotSigned.into());
    }
    Ok(())
}

/// «Vazifamni bajara olmayapman»: sabab, sana, taklif. Tegishli band javobda (`breach_clause`) ko'rsatiladi.
pub fn report_incident(
    db: &Database,
    now: OffsetDateTime,
    input: IncidentInputDto,
) -> Result<AgreementOpsDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let row = load(db, &input.agreement_id)?;
    ensure_active(&row)?;
    let answers = answers_of(&row)?;
    if duty_of(&answers, &input.duty_id).is_none() || !answers.parties.iter().any(|p| p.id == input.party_id) {
        return Err(StorageError::NotFound.into());
    }
    if input.reason.trim().is_empty() {
        return Err(domain::DomainError::ReasonRequired.into());
    }
    let occurred_on = match input.occurred_on.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => parse_date(text)?,
        None => ctx.today,
    };
    CenterRepo::new(db.connection()).insert_incident(&IncidentRow {
        id: domain::IdGen::next_id(&UuidV7),
        household_id: row.household_id.clone(),
        agreement_id: row.id.clone(),
        duty_id: input.duty_id,
        party_id: input.party_id,
        reason: input.reason.trim().to_owned(),
        proposed_fix: input.proposed_fix.filter(|f| !f.trim().is_empty()),
        occurred_on,
        resolved_at: None,
        created_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    })?;
    ops(db, now, &row.id)
}

/// Hodisani yopadi (kelishilgan qoidaga qaytildi).
pub fn resolve_incident(db: &Database, now: OffsetDateTime, id: &str) -> Result<AgreementOpsDto, SessionError> {
    let agreement_id = CenterRepo::new(db.connection()).resolve_incident(id, now)?;
    ops(db, now, &agreement_id)
}

/// Ochiq hisob ko'rigini ochadi: davr (standart — oxirgi ko'rikdan bugungacha), zanjir tekshiruvi va boshi.
pub fn open_review(
    db: &Database,
    now: OffsetDateTime,
    input: OpenReviewInputDto,
) -> Result<AgreementOpsDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let row = load(db, &input.agreement_id)?;
    ensure_active(&row)?;
    let repo = CenterRepo::new(db.connection());
    let journal = JournalRepo::new(db.connection());
    let entries = journal.list(&row.id)?;
    let last = repo.reviews(&row.id)?.last().map(|r| r.period_end);
    let period_end = match input.period_end.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => parse_date(text)?,
        None => ctx.today,
    };
    let period_start = match input.period_start.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => parse_date(text)?,
        None => last.map_or_else(
            || {
                entries
                    .iter()
                    .map(|s| s.entry.date)
                    .min()
                    .or(row.effective_from)
                    .unwrap_or(period_end)
            },
            |d| d + Duration::days(1),
        ),
    };
    if period_end > ctx.today || period_start > period_end {
        return Err(domain::DomainError::InvalidDay.into());
    }
    let chain_ok = journal.verify(&row.id)?.is_ok();
    repo.insert_review(&ReviewRow {
        id: domain::IdGen::next_id(&UuidV7),
        household_id: row.household_id.clone(),
        agreement_id: row.id.clone(),
        period_start,
        period_end,
        chain_head: entries
            .last()
            .map_or_else(|| GENESIS_HASH.to_owned(), |e| e.hash.clone()),
        chain_ok,
        created_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    })?;
    ops(db, now, &row.id)
}

/// Tomon belgisi: «ko'rdim, roziman» yoki «e'tirozim bor + izoh» (e'tirozda izoh majburiy).
pub fn mark_review(
    db: &Database,
    now: OffsetDateTime,
    input: MarkReviewInputDto,
) -> Result<AgreementOpsDto, SessionError> {
    let repo = CenterRepo::new(db.connection());
    let review = repo
        .find_review(&input.review_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    let row = load(db, &review.agreement_id)?;
    let answers = answers_of(&row)?;
    if !answers.parties.iter().any(|p| p.id == input.party_id) {
        return Err(StorageError::NotFound.into());
    }
    if !DECISIONS.contains(&input.decision.as_str()) {
        return Err(domain::DomainError::InvalidRule.into());
    }
    let comment = input.comment.filter(|c| !c.trim().is_empty());
    if input.decision == "OBJECT" && comment.is_none() {
        return Err(domain::DomainError::ReasonRequired.into());
    }
    repo.upsert_mark(
        &review.id,
        &MarkRow {
            party_id: input.party_id,
            decision: input.decision,
            comment,
        },
        now,
    )?;
    ops(db, now, &row.id)
}

/// Ko'rik bayonnomasi PDF baytlari (`chain_head` bilan).
pub fn review_pdf(db: &Database, now: OffsetDateTime, review_id: &str) -> Result<Vec<u8>, SessionError> {
    let ctx = finance::context(db, now)?;
    let review = CenterRepo::new(db.connection())
        .find_review(review_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    let row = load(db, &review.agreement_id)?;
    let answers = answers_of(&row)?;
    let dto = review_dto(db, &answers, &review)?;
    let minutes = pdf::ReviewMinutes {
        title: row.title.clone(),
        period: format!("{} — {}", pretty(review.period_start), pretty(review.period_end)),
        generated_on: pretty(ctx.today),
        entries: dto
            .entries
            .iter()
            .map(|e| {
                [
                    e.date.clone(),
                    JournalKind::from_code(&e.kind).map_or("Yozuv", kind_label).to_owned(),
                    party_name(&answers, &e.party_id),
                    e.amount.formatted.clone(),
                ]
            })
            .collect(),
        summary: dto
            .summary
            .iter()
            .map(|s| (s.label.clone(), s.amount.formatted.clone()))
            .collect(),
        incidents: dto
            .incidents
            .iter()
            .map(|i| {
                (
                    format!("{} · {}", i.duty_title, i.occurred_on),
                    match &i.proposed_fix {
                        Some(fix) => format!("{} — o'rniga: {fix}", i.reason),
                        None => i.reason.clone(),
                    },
                )
            })
            .collect(),
        marks: dto
            .marks
            .iter()
            .map(|m| {
                (
                    m.name.clone(),
                    match (m.decision.as_deref(), &m.comment) {
                        (Some("AGREE"), _) => "ko'rdim, roziman".to_owned(),
                        (Some("OBJECT"), Some(comment)) => format!("e'tirozim bor: {comment}"),
                        (Some("OBJECT"), None) => "e'tirozim bor".to_owned(),
                        _ => "belgi qo'yilmagan".to_owned(),
                    },
                )
            })
            .collect(),
        chain_line: format!(
            "Zanjir {} · boshi: {}",
            if review.chain_ok { "to'g'ri" } else { "BUZILGAN" },
            review.chain_head
        ),
        disclaimer: DISCLAIMER.to_owned(),
    };
    Ok(pdf::render_review_minutes(&minutes)?)
}

/// Nizo ochadi: holat `IN_DISPUTE` (taqsimot bloklanadi).
pub fn open_dispute(
    db: &Database,
    now: OffsetDateTime,
    input: DisputeInputDto,
) -> Result<AgreementOpsDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let row = load(db, &input.agreement_id)?;
    if row.status != AgreementStatus::Signed {
        return Err(domain::DomainError::AgreementLocked.into());
    }
    let answers = answers_of(&row)?;
    if !answers.parties.iter().any(|p| p.id == input.party_id) {
        return Err(StorageError::NotFound.into());
    }
    if input.subject.trim().is_empty() || input.claim.trim().is_empty() {
        return Err(domain::DomainError::ReasonRequired.into());
    }
    CenterRepo::new(db.connection()).insert_dispute(&DisputeRow {
        id: domain::IdGen::next_id(&UuidV7),
        household_id: row.household_id.clone(),
        agreement_id: row.id.clone(),
        opened_by_party_id: input.party_id,
        subject: input.subject.trim().to_owned(),
        clauses: input.clauses.trim().to_owned(),
        claim: input.claim.trim().to_owned(),
        opened_on: ctx.today,
        decision: None,
        decided_on: None,
        created_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    })?;
    AgreementRepo::new(db.connection()).set_status(&row.id, AgreementStatus::InDispute, None, now)?;
    ops(db, now, &row.id)
}

/// Hakam qarori: yoziladi, holat `SIGNED` ga qaytadi; kerak bo'lsa yangi versiya (qayta imzolash).
pub fn decide_dispute(
    db: &Database,
    now: OffsetDateTime,
    input: DecideDisputeInputDto,
) -> Result<AgreementOpsDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let repo = CenterRepo::new(db.connection());
    let dispute = repo
        .find_dispute(&input.dispute_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    if input.decision.trim().is_empty() {
        return Err(domain::DomainError::ReasonRequired.into());
    }
    let row = load(db, &dispute.agreement_id)?;
    repo.decide_dispute(&dispute.id, input.decision.trim(), ctx.today)?;
    if repo.open_dispute_count(&row.id)? == 0 {
        AgreementRepo::new(db.connection()).set_status(&row.id, AgreementStatus::Signed, None, now)?;
    }
    if input.new_version {
        let next = AgreementRepo::new(db.connection()).update_answers(
            &row.id,
            row.version,
            AgreementStatus::Draft,
            &row.answers_json,
            now,
        )?;
        repo.insert_version_note(&row.id, next, &format!("Hakam qarori: {}", input.decision.trim()), now)?;
    }
    ops(db, now, &row.id)
}

/// Hakam uchun ish papkasi PDF baytlari.
pub fn arbiter_pdf(db: &Database, now: OffsetDateTime, agreement_id: &str) -> Result<Vec<u8>, SessionError> {
    let ctx = finance::context(db, now)?;
    let row = load(db, agreement_id)?;
    let answers = answers_of(&row)?;
    let repo = CenterRepo::new(db.connection());
    let journal = JournalRepo::new(db.connection());
    let entries = journal.list(&row.id)?;
    let chain_ok = journal.verify(&row.id)?.is_ok();
    let parties_text = answers
        .parties
        .iter()
        .map(|p| format!("{} ({})", p.name, p.role))
        .collect::<Vec<_>>()
        .join("; ");
    let contributions = answers
        .contributions
        .iter()
        .map(|c| {
            let who = party_name(&answers, &c.party_id);
            if c.amount.trim().is_empty() {
                format!("{who}: {} — {}", c.kind, c.description)
            } else {
                format!("{who}: {} {} — {}", c.kind, c.amount, c.description)
            }
        })
        .collect::<Vec<_>>()
        .join("; ");
    let duties = answers
        .duties
        .iter()
        .map(|d| {
            format!(
                "{} — {}; bajarilmasa: {}",
                d.title,
                d.owner_party_id.as_deref().map_or_else(|| "egasiz".to_owned(), |id| party_name(&answers, id)),
                d.breach_clause
            )
        })
        .collect::<Vec<_>>()
        .join("; ");
    let shares = answers
        .profit_shares
        .iter()
        .map(|s| format!("{} {} %", party_name(&answers, &s.party_id), s.share_bp / 100))
        .collect::<Vec<_>>()
        .join(", ");
    let contract = vec![
        ("1. Tomonlar".to_owned(), parties_text),
        ("2. Hissalar".to_owned(), contributions),
        ("3. Vazifalar".to_owned(), duties),
        ("4. Foyda".to_owned(), shares),
        ("5. Zarar".to_owned(), answers.loss_text.clone()),
        ("6. Hisob".to_owned(), answers.custody_location.clone()),
        (
            "7. Ajralib chiqish".to_owned(),
            format!("{} · {}", answers.exit_valuation, answers.exit_payout),
        ),
        (
            "8. Hakam".to_owned(),
            format!("{} ({})", answers.arbiter_name, answers.arbiter_role),
        ),
        (
            "9. Muddat".to_owned(),
            format!("{} oy · ko'rik {}", answers.term_months, answers.review_date),
        ),
    ];
    let versions = repo
        .version_notes(&row.id)?
        .into_iter()
        .map(|(v, note, at)| (format!("{v}-versiya · {}", pretty(at.date())), note))
        .collect();
    let reviews = repo
        .reviews(&row.id)?
        .iter()
        .map(|r| {
            let marks = repo.marks(&r.id).unwrap_or_default();
            let agree = marks.iter().filter(|m| m.decision == "AGREE").count();
            let object = marks.len() - agree;
            Ok((
                format!("{} — {}", pretty(r.period_start), pretty(r.period_end)),
                format!(
                    "{} belgi: {agree} rozi, {object} e'tiroz · zanjir {} · boshi {}…",
                    marks.len(),
                    if r.chain_ok { "to'g'ri" } else { "BUZILGAN" },
                    &r.chain_head[..12.min(r.chain_head.len())]
                ),
            ))
        })
        .collect::<Result<Vec<_>, SessionError>>()?;
    let incidents = repo
        .incidents(&row.id)?
        .iter()
        .map(|i| {
            let duty = duty_of(&answers, &i.duty_id);
            (
                format!(
                    "{} · {}",
                    duty.map_or_else(|| i.duty_id.clone(), |d| d.title.clone()),
                    pretty(i.occurred_on)
                ),
                format!(
                    "{} · {}",
                    i.reason,
                    if i.resolved_at.is_some() { "yopilgan" } else { "ochiq" }
                ),
            )
        })
        .collect();
    let disputes = repo
        .disputes(&row.id)?
        .iter()
        .map(|d| {
            (
                format!("{} · {}", d.subject, party_name(&answers, &d.opened_by_party_id)),
                format!(
                    "Bandlar: {} · Talab: {} · qaror: {}",
                    d.clauses,
                    d.claim,
                    d.decision.as_deref().unwrap_or("yo'q")
                ),
            )
        })
        .collect();
    let folder = pdf::ArbiterFolder {
        title: row.title.clone(),
        generated_on: pretty(ctx.today),
        version_line: format!("{}-versiya · {}", row.version, row.status.code()),
        contract,
        versions,
        entries: entries
            .iter()
            .map(|e| {
                [
                    pretty(e.entry.date),
                    kind_label(e.entry.kind).to_owned(),
                    party_name(&answers, &e.entry.party_id),
                    MoneyDto::of(e.entry.amount).formatted,
                ]
            })
            .collect(),
        chain_line: format!(
            "Zanjir {} ({} yozuv).",
            if chain_ok { "to'g'ri" } else { "BUZILGAN" },
            entries.len()
        ),
        reviews,
        incidents,
        disputes,
        disclaimer: DISCLAIMER.to_owned(),
    };
    Ok(pdf::render_arbiter_folder(&folder)?)
}

/// Yillik yangilash: «o'zgarishsiz tasdiqlandi» — yangi versiya (imzolar qayta so'raladi).
pub fn confirm_unchanged(db: &Database, now: OffsetDateTime, agreement_id: &str) -> Result<AgreementOpsDto, SessionError> {
    let row = load(db, agreement_id)?;
    if matches!(row.status, AgreementStatus::InDispute | AgreementStatus::Ended) {
        return Err(domain::DomainError::AgreementLocked.into());
    }
    let next = AgreementRepo::new(db.connection()).update_answers(
        &row.id,
        row.version,
        AgreementStatus::Draft,
        &row.answers_json,
        now,
    )?;
    CenterRepo::new(db.connection()).insert_version_note(&row.id, next, "o'zgarishsiz tasdiqlandi", now)?;
    ops(db, now, &row.id)
}

/// Oilaviy kelishuv shablonlari.
pub fn family_templates() -> Vec<FamilyTemplateDto> {
    FAMILY_TEMPLATES
        .iter()
        .map(|t| FamilyTemplateDto {
            id: t.id.to_owned(),
            title: t.title.to_owned(),
            description: t.description.to_owned(),
        })
        .collect()
}

/// Shablondan `FAMILY` kelishuvi: tomonlar — ADULT a'zolar, vazifalar shablondan, 4–5-savollar «tegishli emas».
pub fn create_family_agreement(
    db: &Database,
    now: OffsetDateTime,
    template_id: &str,
) -> Result<AgreementDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let template = FAMILY_TEMPLATES
        .iter()
        .find(|t| t.id == template_id)
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    let created = agreements::create(
        db,
        now,
        AgreementInputDto {
            kind: "FAMILY".to_owned(),
            title: template.title.to_owned(),
        },
    )?;
    let adults: Vec<_> = MemberRepo::new(db.connection())
        .list_for_household(&ctx.household.id)?
        .into_iter()
        .filter(|m| m.role == MemberRole::Adult)
        .collect();
    let mut answers = created.answers.clone();
    answers.parties = adults
        .iter()
        .enumerate()
        .map(|(index, m)| PartyDto {
            id: format!("P{}", index + 1),
            name: m.name.clone(),
            role: "oila a'zosi".to_owned(),
            relation: String::new(),
            is_me: m.id == ctx.owner_id,
        })
        .collect();
    answers.contributions = answers
        .parties
        .iter()
        .map(|p| crate::dto::ContributionDto {
            party_id: p.id.clone(),
            kind: "labor".to_owned(),
            amount: String::new(),
            description: "uy ishlari va vaqt".to_owned(),
        })
        .collect();
    answers.duties = template
        .duties
        .iter()
        .enumerate()
        .map(|(index, (title, breach))| DutyDto {
            id: format!("d{}", index + 1),
            title: (*title).to_owned(),
            owner_party_id: answers.parties.get(index % answers.parties.len().max(1)).map(|p| p.id.clone()),
            breach_clause: (*breach).to_owned(),
        })
        .collect();
    answers.profit_not_applicable = Some("oilaviy kelishuv — foyda bo'linmaydi".to_owned());
    answers.loss_not_applicable = Some("oilaviy kelishuv — zarar bo'linmaydi".to_owned());
    answers.custody_location = template.custody.to_owned();
    answers.keeper_party_id = answers.parties.first().map(|p| p.id.clone());
    answers.exit_not_applicable = Some("oilaviy kelishuv — ajralib chiqish yo'q".to_owned());
    answers.term_months = 12;
    answers.review_date = date_text(ctx.today + Duration::days(365));
    agreements::save_answers(
        db,
        now,
        SaveAnswersInputDto {
            id: created.id.clone(),
            version: created.version,
            answers,
        },
    )
}

/// ADULT a'zo PIN bilan tasdiqlaydi; hamma kattalar tasdiqlagach — `SIGNED` (imzo chizish shart emas).
pub fn confirm_family(
    db: &Database,
    now: OffsetDateTime,
    input: FamilyConfirmInputDto,
) -> Result<AgreementOpsDto, SessionError> {
    let row = load(db, &input.agreement_id)?;
    if row.kind != AgreementType::Family {
        return Err(domain::DomainError::InvalidRule.into());
    }
    if matches!(row.status, AgreementStatus::InDispute | AgreementStatus::Ended) {
        return Err(domain::DomainError::AgreementLocked.into());
    }
    let member = MemberRepo::new(db.connection())
        .find(&input.member_id)?
        .ok_or(StorageError::NotFound)?;
    if member.role != MemberRole::Adult {
        return Err(domain::DomainError::InvalidRole.into());
    }
    let pins = PinRepo::new(db.connection());
    let state = pins.find(&member.id)?.ok_or(StorageError::NotFound)?;
    let verifier = state.verifier.clone().ok_or(domain::DomainError::PinNotSet)?;
    ensure_not_locked(&state, now)?;
    if !verify_member_pin(&input.pin, &verifier, kdf_params())? {
        pins.record_failure(&member.id, now)?;
        return Err(SecurityError::WrongPin.into());
    }
    pins.reset_failures(&member.id)?;
    let repo = CenterRepo::new(db.connection());
    repo.insert_family_consent(&row.id, &member.id, row.version, now)?;
    let ctx = finance::context(db, now)?;
    if family_dto(db, &ctx, &row)?.is_some_and(|f| f.complete) && row.status == AgreementStatus::Draft {
        AgreementRepo::new(db.connection()).set_status(&row.id, AgreementStatus::Signed, Some(ctx.today), now)?;
    }
    ops(db, now, &row.id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dto::{ContributionDto, PartyDto, ProfitShareDto, SignInputDto, SignatureInputDto};
    use crate::family;
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-12-01 06:00 UTC);
    const PNG: &str = "data:image/png;base64,iVBORw0KGgo=";

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([101; 32])).expect("xotirada baza")
    }

    fn full_answers() -> AgreementAnswersDto {
        let mut a = AgreementAnswersDto::empty();
        a.parties = vec![
            PartyDto { id: "P1".into(), name: "Anvar Karimov".into(), role: "sherik".into(), relation: String::new(), is_me: true },
            PartyDto { id: "P2".into(), name: "Dilshod Rahimov".into(), role: "sherik".into(), relation: String::new(), is_me: false },
        ];
        a.contributions = vec![
            ContributionDto { party_id: "P1".into(), kind: "money".into(), amount: "3 000 000".into(), description: "naqd".into() },
            ContributionDto { party_id: "P2".into(), kind: "labor".into(), amount: String::new(), description: "yetkazish".into() },
        ];
        a.duties = vec![DutyDto { id: "d1".into(), title: "Yetkazish".into(), owner_party_id: Some("P2".into()), breach_clause: "1 kun ichida xabar beradi".into() }];
        a.profit_shares = vec![
            ProfitShareDto { party_id: "P1".into(), share_bp: 5_000 },
            ProfitShareDto { party_id: "P2".into(), share_bp: 5_000 },
        ];
        a.loss_text = "Zarar kapitalga mutanosib".into();
        a.custody_location = "Umumiy karta".into();
        a.keeper_party_id = Some("P1".into());
        a.exit_valuation = "Oxirgi ko'rik bo'yicha".into();
        a.exit_payout = "3 oy ichida".into();
        a.arbiter_name = "Sobir hoji".into();
        a.arbiter_role = "mahalla oqsoqoli".into();
        a.review_date = "2026-12-20".into();
        a
    }

    fn signed(db: &Database) -> String {
        let created = agreements::create(db, NOW, AgreementInputDto { kind: "OTHER".into(), title: "Non sexi".into() }).expect("yaratildi");
        agreements::save_answers(db, NOW, SaveAnswersInputDto { id: created.id.clone(), version: 1, answers: full_answers() }).expect("saqlandi");
        for (party, role) in [("P1", "PARTY"), ("P2", "PARTY"), ("ARBITER", "ARBITER")] {
            agreements::add_signature(db, NOW, SignatureInputDto { agreement_id: created.id.clone(), party_id: party.into(), role: role.into(), image: PNG.into() }).expect("imzo");
        }
        agreements::sign(db, NOW, SignInputDto { agreement_id: created.id.clone(), effective_from: Some("2026-11-01".into()), opening_balance_party_id: Some("P1".into()), opening_balance_amount: Some("3 000 000".into()) }).expect("imzolandi");
        created.id
    }

    #[test]
    fn hodisa_band_bilan_korsatiladi_korik_belgilanadi_va_bayonnoma_chiqadi() {
        let db = database();
        let id = signed(&db);
        let ops = report_incident(&db, NOW, IncidentInputDto { agreement_id: id.clone(), duty_id: "d1".into(), party_id: "P2".into(), reason: "mashina buzildi".into(), proposed_fix: Some("kuryer".into()), occurred_on: None }).expect("hodisa");
        assert_eq!(ops.incidents[0].breach_clause, "1 kun ichida xabar beradi");
        assert!(!ops.incidents[0].resolved);
        let center = center(&db, NOW).expect("markaz");
        assert_eq!(center.rows[0].open_incidents, 1);
        assert!(center.rows[0].review_due, "ko'rik 2026-12-20, bugun 12-01 — 30 kun ichida");

        let ops = open_review(&db, NOW, OpenReviewInputDto { agreement_id: id.clone(), period_start: None, period_end: None }).expect("ko'rik");
        let review = &ops.reviews[0];
        assert_eq!(review.period_start, "2026-11-01");
        assert_eq!(review.entries.len(), 1, "boshlang'ich balans yozuvi");
        assert_eq!(review.incidents.len(), 1);
        assert!(review.chain_ok);
        assert!(!review.complete);
        assert!(matches!(
            mark_review(&db, NOW, MarkReviewInputDto { review_id: review.id.clone(), party_id: "P2".into(), decision: "OBJECT".into(), comment: None }),
            Err(SessionError::Domain(domain::DomainError::ReasonRequired))
        ));
        mark_review(&db, NOW, MarkReviewInputDto { review_id: review.id.clone(), party_id: "P1".into(), decision: "AGREE".into(), comment: None }).expect("belgi");
        let ops = mark_review(&db, NOW, MarkReviewInputDto { review_id: review.id.clone(), party_id: "P2".into(), decision: "OBJECT".into(), comment: Some("chek yo'q".into()) }).expect("belgi");
        assert!(ops.reviews[0].complete);
        let bytes = review_pdf(&db, NOW, &review.id).expect("bayonnoma");
        assert!(bytes.starts_with(b"%PDF-"));
        let ops = resolve_incident(&db, NOW, &ops.incidents[0].id).expect("yopildi");
        assert!(ops.incidents[0].resolved);
    }

    #[test]
    fn nizo_taqsimotni_bloklaydi_qaror_yangi_versiya_va_hakam_papkasi() {
        let db = database();
        let id = signed(&db);
        let ops = open_dispute(&db, NOW, DisputeInputDto { agreement_id: id.clone(), party_id: "P2".into(), subject: "Xarajat cheki".into(), clauses: "6-band".into(), claim: "cheklar taqdim etilsin".into() }).expect("nizo");
        assert_eq!(ops.status, "IN_DISPUTE");
        assert!(matches!(
            domain::review::ensure_distribution_allowed(AgreementStatus::InDispute),
            Err(domain::DomainError::DistributionBlocked)
        ));
        let bytes = arbiter_pdf(&db, NOW, &id).expect("papka");
        assert!(bytes.starts_with(b"%PDF-"));
        let ops = decide_dispute(&db, NOW, DecideDisputeInputDto { dispute_id: ops.disputes[0].id.clone(), decision: "Cheklar 7 kun ichida taqdim etiladi".into(), new_version: true }).expect("qaror");
        assert_eq!(ops.status, "DRAFT", "yangi versiya qayta imzolanadi");
        assert_eq!(ops.version, 3);
        assert_eq!(ops.version_notes[0].version, 3);
        assert!(ops.disputes[0].decision.is_some());
        let ops = confirm_unchanged(&db, NOW, &id).expect("yangilash");
        assert_eq!(ops.version, 4);
        assert_eq!(ops.version_notes[1].note, "o'zgarishsiz tasdiqlandi");
    }

    #[test]
    fn oilaviy_shablon_pin_bilan_tasdiqlanadi_va_imzosiz_signed_boladi() {
        let db = database();
        let ctx = finance::context(&db, NOW).expect("kontekst");
        family::set_member_pin(&db, NOW, &ctx.owner_id, None, "246813").expect("egasi PIN");
        assert_eq!(family_templates().len(), 4);
        let created = create_family_agreement(&db, NOW, "FAMILY_MONEY").expect("shablon");
        assert_eq!(created.kind, "FAMILY");
        assert_eq!(created.answers.duties.len(), 2);
        assert!(matches!(
            confirm_family(&db, NOW, FamilyConfirmInputDto { agreement_id: created.id.clone(), member_id: ctx.owner_id.clone(), pin: "000000".into() }),
            Err(SessionError::Security(SecurityError::WrongPin))
        ));
        let ops = confirm_family(&db, NOW, FamilyConfirmInputDto { agreement_id: created.id.clone(), member_id: ctx.owner_id.clone(), pin: "246813".into() }).expect("tasdiq");
        let family = ops.family.expect("oilaviy");
        assert!(family.complete);
        assert_eq!(ops.status, "SIGNED");
        let center = center(&db, NOW).expect("markaz");
        assert_eq!(center.rows[0].family_pending, 0);
    }
}
