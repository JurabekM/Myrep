//! D8A xizmati: kelishuvlar (9 savol), imzolar, append-only jurnal va PDF.
//!
//! Qoidalar:
//! * imzo faqat 9/9 to'ldirilganda; javob o'zgarsa versiya oshadi va imzolar qayta so'raladi;
//! * `SIGNED` — barcha tomonlar (va hakam, bo'lsa) joriy versiyani imzolaganda;
//! * jurnalga faqat imzolangan kelishuv va faqat hisob yurituvchi qurilma (kelishuvni yaratgan qurilma) yozadi;
//! * og'zaki kelishuv: `effective_from` o'tmishda va `OPENING_BALANCE` yozuvi bilan.

use std::collections::BTreeMap;

use domain::agreement::{
    AgreementAnswers, AgreementStatus, AgreementType, Arbiter, Contribution, Custody, Duty,
    ExitClause, Party, ProfitRule, Term, completeness,
};
use domain::journal::{JournalEntry, JournalKind};
use domain::{DomainError, interchange};
use storage::{
    AgreementRepo, AgreementRow, Database, JournalRepo, SignatureRepo, SignatureRow, StorageError,
};
use time::format_description::well_known::Iso8601;
use time::{Date, OffsetDateTime};

use crate::dto::{
    AgreementAnswersDto, AgreementDto, AgreementInputDto, AgreementSummaryDto, CompletenessDto,
    JournalDto, JournalEntryDto, JournalEntryInputDto, MoneyDto, SaveAnswersInputDto, SignInputDto,
    SignatureDto, SignatureInputDto,
};
use crate::finance::{self, DEVICE_ID, UuidV7, date_text, parse_money};
use crate::session::SessionError;

const SIGNATURE_ROLES: [&str; 3] = ["PARTY", "WITNESS", "ARBITER"];

fn parse_date(text: &str) -> Result<Date, SessionError> {
    Date::parse(text, &Iso8601::DATE).map_err(|_| DomainError::InvalidDay.into())
}

fn parse_kind(code: &str) -> Result<AgreementType, SessionError> {
    AgreementType::from_code(code).ok_or_else(|| DomainError::InvalidRule.into())
}

fn ts_text(value: OffsetDateTime) -> String {
    value
        .format(&time::format_description::well_known::Rfc3339)
        .unwrap_or_default()
}

impl AgreementAnswersDto {
    /// Bo'sh javoblar (yangi qoralama).
    fn empty() -> Self {
        Self {
            parties: Vec::new(),
            contributions: Vec::new(),
            duties: Vec::new(),
            has_schedule: false,
            profit_shares: Vec::new(),
            profit_fixed_amount: String::new(),
            profit_not_applicable: None,
            loss_text: String::new(),
            loss_not_applicable: None,
            custody_location: String::new(),
            keeper_party_id: None,
            review_every_days: 30,
            exit_notice_days: 30,
            exit_valuation: String::new(),
            exit_payout: String::new(),
            exit_assets: String::new(),
            exit_not_applicable: None,
            arbiter_name: String::new(),
            arbiter_role: String::new(),
            term_months: 12,
            review_date: String::new(),
        }
    }
}

/// DTO → domen tuzilmasi. Summalar bo'sh bo'lsa `None`; noto'g'ri summa — xato.
fn to_domain(dto: &AgreementAnswersDto) -> Result<AgreementAnswers, SessionError> {
    let mut contributions = Vec::with_capacity(dto.contributions.len());
    for item in &dto.contributions {
        let amount = if item.amount.trim().is_empty() {
            None
        } else {
            Some(parse_money(&item.amount)?)
        };
        contributions.push(Contribution {
            party_id: item.party_id.clone(),
            kind: item.kind.clone(),
            amount,
            description: item.description.clone(),
        });
    }
    let fixed_amount = if dto.profit_fixed_amount.trim().is_empty() {
        None
    } else {
        Some(parse_money(&dto.profit_fixed_amount)?)
    };
    let mut shares = BTreeMap::new();
    for share in &dto.profit_shares {
        shares.insert(share.party_id.clone(), i64::from(share.share_bp));
    }
    let review_date = if dto.review_date.trim().is_empty() {
        None
    } else {
        Some(parse_date(&dto.review_date)?)
    };
    Ok(AgreementAnswers {
        profit_not_applicable: dto.profit_not_applicable.clone(),
        loss_not_applicable: dto.loss_not_applicable.clone(),
        exit_not_applicable: dto.exit_not_applicable.clone(),
        parties: dto
            .parties
            .iter()
            .map(|p| Party {
                id: p.id.clone(),
                name: p.name.clone(),
                role: p.role.clone(),
                relation: p.relation.clone(),
                is_me: p.is_me,
            })
            .collect(),
        contributions,
        duties: dto
            .duties
            .iter()
            .map(|d| Duty {
                id: d.id.clone(),
                title: d.title.clone(),
                owner_party_id: d.owner_party_id.clone().filter(|v| !v.is_empty()),
                breach_clause: d.breach_clause.clone(),
            })
            .collect(),
        profit: ProfitRule {
            shares,
            fixed_amount,
            text: String::new(),
        },
        loss_text: dto.loss_text.clone(),
        custody: Custody {
            location: dto.custody_location.clone(),
            keeper_party_id: dto.keeper_party_id.clone().filter(|v| !v.is_empty()),
            keeper_device_id: None,
            review_every_days: i64::from(dto.review_every_days),
        },
        exit: ExitClause {
            notice_days: i64::from(dto.exit_notice_days),
            valuation: dto.exit_valuation.clone(),
            payout: dto.exit_payout.clone(),
            assets: dto.exit_assets.clone(),
        },
        arbiter: if dto.arbiter_name.trim().is_empty() {
            None
        } else {
            Some(Arbiter {
                name: dto.arbiter_name.clone(),
                role: dto.arbiter_role.clone(),
            })
        },
        term: Term {
            term_months: i64::from(dto.term_months),
            review_date,
        },
    })
}

fn completeness_of(
    kind: AgreementType,
    dto: &AgreementAnswersDto,
) -> Result<CompletenessDto, SessionError> {
    let answers = to_domain(dto)?;
    let result = completeness(kind, &answers, dto.has_schedule);
    Ok(CompletenessDto {
        complete: result.complete,
        missing: result.missing.iter().map(|q| u32::from(*q)).collect(),
        errors: result.errors.iter().map(|e| (*e).to_owned()).collect(),
    })
}

fn parse_answers(json: &str) -> Result<AgreementAnswersDto, SessionError> {
    serde_json::from_str(json)
        .map_err(|_| StorageError::InvalidData("kelishuv javoblari".to_owned()).into())
}

fn load(db: &Database, id: &str) -> Result<AgreementRow, SessionError> {
    AgreementRepo::new(db.connection())
        .find(id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))
}

fn version_u32(version: i64) -> u32 {
    u32::try_from(version).unwrap_or(u32::MAX)
}

fn signature_dto(row: &SignatureRow) -> SignatureDto {
    SignatureDto {
        party_id: row.party_id.clone(),
        role: row.role.clone(),
        version: version_u32(row.version),
        signed_at: ts_text(row.created_at),
        image: row.image.clone(),
    }
}

fn build_dto(db: &Database, row: AgreementRow) -> Result<AgreementDto, SessionError> {
    let answers = parse_answers(&row.answers_json)?;
    let completeness = completeness_of(row.kind, &answers)?;
    let signatures = SignatureRepo::new(db.connection())
        .list_for_version(&row.id, row.version)?
        .iter()
        .map(signature_dto)
        .collect();
    let journal = JournalRepo::new(db.connection());
    let entries = journal.list(&row.id)?;
    let chain_ok = journal.verify(&row.id)?.is_ok();
    Ok(AgreementDto {
        id: row.id.clone(),
        kind: row.kind.code().to_owned(),
        title: row.title.clone(),
        status: row.status.code().to_owned(),
        version: version_u32(row.version),
        effective_from: row.effective_from.map(date_text),
        answers,
        completeness,
        signatures,
        journal_count: u32::try_from(entries.len()).unwrap_or(u32::MAX),
        chain_head: entries.last().map(|e| e.hash.clone()),
        chain_ok,
        can_write_journal: row.status == AgreementStatus::Signed
            && interchange::ensure_keeper(&row.origin_device_id, DEVICE_ID).is_ok(),
    })
}

/// Ro'yxat.
pub fn list(db: &Database, now: OffsetDateTime) -> Result<Vec<AgreementSummaryDto>, SessionError> {
    let ctx = finance::context(db, now)?;
    let rows = AgreementRepo::new(db.connection()).list(&ctx.household.id)?;
    let mut out = Vec::with_capacity(rows.len());
    for row in rows {
        let answers = parse_answers(&row.answers_json)?;
        let result = completeness_of(row.kind, &answers)?;
        out.push(AgreementSummaryDto {
            id: row.id,
            kind: row.kind.code().to_owned(),
            title: row.title,
            status: row.status.code().to_owned(),
            version: version_u32(row.version),
            answered: 9 - u32::try_from(result.missing.len()).unwrap_or(9).min(9),
            review_date: if answers.review_date.trim().is_empty() {
                None
            } else {
                Some(answers.review_date)
            },
        });
    }
    Ok(out)
}

/// Yangi qoralama.
pub fn create(
    db: &Database,
    now: OffsetDateTime,
    input: AgreementInputDto,
) -> Result<AgreementDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let kind = parse_kind(&input.kind)?;
    let title = domain::validate_name(&input.title)?;
    let row = AgreementRow {
        id: domain::IdGen::next_id(&UuidV7),
        household_id: ctx.household.id.clone(),
        kind,
        title,
        status: AgreementStatus::Draft,
        version: 1,
        answers_json: serde_json::to_string(&AgreementAnswersDto::empty())
            .map_err(|_| StorageError::InvalidData("kelishuv javoblari".to_owned()))?,
        effective_from: None,
        created_at: now,
        updated_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    };
    AgreementRepo::new(db.connection()).insert(&row)?;
    build_dto(db, row)
}

/// Bitta kelishuv.
pub fn get(db: &Database, _now: OffsetDateTime, id: &str) -> Result<AgreementDto, SessionError> {
    build_dto(db, load(db, id)?)
}

/// Javoblarni saqlaydi. Versiya oshadi; `SIGNED` bo'lsa yana `DRAFT` (qayta imzolash).
pub fn save_answers(
    db: &Database,
    now: OffsetDateTime,
    input: SaveAnswersInputDto,
) -> Result<AgreementDto, SessionError> {
    let row = load(db, &input.id)?;
    if matches!(
        row.status,
        AgreementStatus::InDispute | AgreementStatus::Ended
    ) {
        return Err(DomainError::AgreementLocked.into());
    }
    // Summalar va sanalar hozir tekshiriladi: noto'g'ri qiymat saqlanmaydi.
    to_domain(&input.answers)?;
    let json = serde_json::to_string(&input.answers)
        .map_err(|_| StorageError::InvalidData("kelishuv javoblari".to_owned()))?;
    AgreementRepo::new(db.connection()).update_answers(
        &input.id,
        i64::from(input.version),
        AgreementStatus::Draft,
        &json,
        now,
    )?;
    build_dto(db, load(db, &input.id)?)
}

/// Imzo qo'shadi: faqat 9/9 to'ldirilgan va qulflanmagan kelishuvga, joriy versiya uchun.
pub fn add_signature(
    db: &Database,
    now: OffsetDateTime,
    input: SignatureInputDto,
) -> Result<AgreementDto, SessionError> {
    let row = load(db, &input.agreement_id)?;
    if matches!(
        row.status,
        AgreementStatus::InDispute | AgreementStatus::Ended
    ) {
        return Err(DomainError::AgreementLocked.into());
    }
    if !SIGNATURE_ROLES.contains(&input.role.as_str()) || input.party_id.trim().is_empty() {
        return Err(DomainError::InvalidRule.into());
    }
    if !input.image.starts_with("data:image/png;base64,") {
        return Err(DomainError::InvalidRule.into());
    }
    let answers = parse_answers(&row.answers_json)?;
    if !completeness_of(row.kind, &answers)?.complete {
        return Err(DomainError::AgreementIncomplete.into());
    }
    SignatureRepo::new(db.connection()).upsert(
        &domain::IdGen::next_id(&UuidV7),
        &row.household_id,
        &row.id,
        &SignatureRow {
            party_id: input.party_id,
            role: input.role,
            version: row.version,
            image: input.image,
            created_at: now,
        },
        DEVICE_ID,
    )?;
    build_dto(db, load(db, &input.agreement_id)?)
}

/// Imzolashni yakunlaydi: hamma tomon (va hakam, bo'lsa) joriy versiyani imzolagan bo'lishi shart.
pub fn sign(
    db: &Database,
    now: OffsetDateTime,
    input: SignInputDto,
) -> Result<AgreementDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let row = load(db, &input.agreement_id)?;
    if matches!(
        row.status,
        AgreementStatus::InDispute | AgreementStatus::Ended
    ) {
        return Err(DomainError::AgreementLocked.into());
    }
    let answers = parse_answers(&row.answers_json)?;
    if !completeness_of(row.kind, &answers)?.complete {
        return Err(DomainError::AgreementIncomplete.into());
    }
    let signatures = SignatureRepo::new(db.connection()).list_for_version(&row.id, row.version)?;
    let signed = |party: &str, role: &str| {
        signatures
            .iter()
            .any(|s| s.party_id == party && s.role == role)
    };
    let all_parties = answers.parties.iter().all(|p| signed(&p.id, "PARTY"));
    let arbiter_ok = answers.arbiter_name.trim().is_empty() || signed("ARBITER", "ARBITER");
    if !all_parties || !arbiter_ok {
        return Err(DomainError::SignaturesMissing.into());
    }
    let effective_from = match input
        .effective_from
        .as_deref()
        .filter(|t| !t.trim().is_empty())
    {
        Some(text) => parse_date(text)?,
        None => ctx.today,
    };
    if effective_from > ctx.today {
        return Err(DomainError::InvalidDay.into());
    }
    AgreementRepo::new(db.connection()).set_status(
        &row.id,
        AgreementStatus::Signed,
        Some(effective_from),
        now,
    )?;

    // Og'zaki kelishuvni yozib olish: boshlang'ich balans amal qilish sanasi bilan.
    if let (Some(party), Some(amount)) = (
        input
            .opening_balance_party_id
            .filter(|p| !p.trim().is_empty()),
        input
            .opening_balance_amount
            .filter(|a| !a.trim().is_empty()),
    ) {
        let amount = parse_money(&amount)?;
        let entry = JournalEntry {
            id: domain::IdGen::next_id(&UuidV7),
            agreement_id: row.id.clone(),
            kind: JournalKind::OpeningBalance,
            party_id: party,
            amount,
            date: effective_from,
            note: Some("Boshlang'ich balans (og'zaki kelishuv yozib olindi)".to_owned()),
        };
        if amount.minor() <= 0 {
            return Err(DomainError::AmountNotPositive.into());
        }
        JournalRepo::new(db.connection()).append(&row.household_id, &entry, now, DEVICE_ID)?;
    }
    build_dto(db, load(db, &input.agreement_id)?)
}

fn journal_dto(db: &Database, agreement_id: &str) -> Result<JournalDto, SessionError> {
    let repo = JournalRepo::new(db.connection());
    let entries = repo
        .list(agreement_id)?
        .iter()
        .map(|stored| JournalEntryDto {
            seq: u32::try_from(stored.seq).unwrap_or(u32::MAX),
            kind: stored.entry.kind.code().to_owned(),
            party_id: stored.entry.party_id.clone(),
            amount: MoneyDto::of(stored.entry.amount),
            date: date_text(stored.entry.date),
            note: stored.entry.note.clone(),
            hash: stored.hash.clone(),
        })
        .collect();
    let verified = repo.verify(agreement_id)?;
    Ok(JournalDto {
        entries,
        chain_ok: verified.is_ok(),
        first_broken: verified
            .err()
            .map(|broken| u32::try_from(broken.first_broken).unwrap_or(u32::MAX)),
    })
}

/// Jurnal.
pub fn journal(db: &Database, agreement_id: &str) -> Result<JournalDto, SessionError> {
    load(db, agreement_id)?;
    journal_dto(db, agreement_id)
}

/// Jurnalga yozuv: imzolangan kelishuv, hisob yurituvchi qurilma, ma'lum tomon.
pub fn append_journal(
    db: &Database,
    now: OffsetDateTime,
    input: JournalEntryInputDto,
) -> Result<JournalDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let row = load(db, &input.agreement_id)?;
    if row.status != AgreementStatus::Signed {
        return Err(DomainError::AgreementNotSigned.into());
    }
    interchange::ensure_keeper(&row.origin_device_id, DEVICE_ID)?;
    let kind = JournalKind::from_code(&input.kind).ok_or(DomainError::InvalidRule)?;
    if kind == JournalKind::OpeningBalance {
        return Err(DomainError::InvalidRule.into());
    }
    let answers = parse_answers(&row.answers_json)?;
    if !answers.parties.iter().any(|p| p.id == input.party_id) {
        return Err(StorageError::NotFound.into());
    }
    let amount = parse_money(&input.amount)?;
    if amount.minor() <= 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    let date = match input.date.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => parse_date(text)?,
        None => ctx.today,
    };
    if date > ctx.today {
        return Err(DomainError::InvalidDay.into());
    }
    let entry = JournalEntry {
        id: domain::IdGen::next_id(&UuidV7),
        agreement_id: row.id.clone(),
        kind,
        party_id: input.party_id,
        amount,
        date,
        note: input.note.filter(|n| !n.trim().is_empty()),
    };
    JournalRepo::new(db.connection()).append(&row.household_id, &entry, now, DEVICE_ID)?;
    journal_dto(db, &input.agreement_id)
}

fn kind_label(kind: AgreementType) -> &'static str {
    match kind {
        AgreementType::Loan => "Qarz tilxati",
        AgreementType::Partnership => "Sheriklik",
        AgreementType::Family => "Oilaviy kelishuv",
        AgreementType::Other => "Kelishuv",
    }
}

fn status_label(status: AgreementStatus) -> &'static str {
    match status {
        AgreementStatus::Draft => "Qoralama",
        AgreementStatus::Signed => "Imzolangan",
        AgreementStatus::InDispute => "Nizoda",
        AgreementStatus::Ended => "Tugagan",
    }
}

fn dotted(date: Date) -> String {
    format!(
        "{:02}.{:02}.{:04}",
        date.day(),
        u8::from(date.month()),
        date.year()
    )
}

fn party_name<'a>(answers: &'a AgreementAnswersDto, id: &'a str) -> &'a str {
    answers
        .parties
        .iter()
        .find(|p| p.id == id)
        .map_or(id, |p| p.name.as_str())
}

fn na_or(value: &Option<String>, text: String) -> String {
    match value {
        Some(reason) => format!("Tegishli emas: {reason}"),
        None => text,
    }
}

/// Kelishuv hujjati (PDF uchun matnlar).
fn document(
    db: &Database,
    now: OffsetDateTime,
    row: &AgreementRow,
) -> Result<pdf::AgreementDocument, SessionError> {
    let ctx = finance::context(db, now)?;
    let a = parse_answers(&row.answers_json)?;
    let signatures = SignatureRepo::new(db.connection()).list_for_version(&row.id, row.version)?;
    let signed_text = |party: &str, role: &str| -> String {
        signatures
            .iter()
            .find(|s| s.party_id == party && s.role == role)
            .map_or_else(
                || "imzo yoʻq".to_owned(),
                |s| {
                    let date = (s.created_at + time::Duration::hours(5)).date();
                    format!("imzolangan {}", dotted(date))
                },
            )
    };
    let mut signature_rows: Vec<(String, String)> = a
        .parties
        .iter()
        .map(|p| (format!("{} (tomon)", p.name), signed_text(&p.id, "PARTY")))
        .collect();
    if !a.arbiter_name.trim().is_empty() {
        signature_rows.push((
            format!("{} (hakam)", a.arbiter_name),
            signed_text("ARBITER", "ARBITER"),
        ));
    }
    let profit = na_or(
        &a.profit_not_applicable,
        if row.kind == AgreementType::Loan {
            "Foiz yo'q (qarzi hasana).".to_owned()
        } else {
            let parts: Vec<String> = a
                .profit_shares
                .iter()
                .map(|s| {
                    format!(
                        "{} {},{} %",
                        party_name(&a, &s.party_id),
                        s.share_bp / 100,
                        (s.share_bp % 100) / 10
                    )
                })
                .collect();
            format!("Foyda ulush bo'yicha: {}.", parts.join(", "))
        },
    );
    let loss = na_or(
        &a.loss_not_applicable,
        if row.kind == AgreementType::Loan {
            "Foiz yo'q; zarar tushunchasi qo'llanmaydi.".to_owned()
        } else {
            a.loss_text.clone()
        },
    );
    let keeper = a
        .keeper_party_id
        .as_deref()
        .map_or("—".to_owned(), |id| party_name(&a, id).to_owned());
    let custody = format!(
        "Pul: {}. Hisobni yuritadi: {}. Ko'rib chiqish: har {} kunda.",
        a.custody_location, keeper, a.review_every_days
    );
    let exit = na_or(
        &a.exit_not_applicable,
        format!(
            "Ogohlantirish: {} kun. Baholash: {}. To'lash: {}.{}",
            a.exit_notice_days,
            a.exit_valuation,
            a.exit_payout,
            if a.exit_assets.trim().is_empty() {
                String::new()
            } else {
                format!(" Mol-mulk: {}.", a.exit_assets)
            }
        ),
    );
    let arbiter = if a.arbiter_name.trim().is_empty() {
        "Hakam belgilanmagan.".to_owned()
    } else {
        format!("{} ({}).", a.arbiter_name, a.arbiter_role)
    };
    let term = format!(
        "Muddat: {} oy. Keyingi ko'rib chiqish: {}.",
        a.term_months,
        if a.review_date.trim().is_empty() {
            "—".to_owned()
        } else {
            parse_date(&a.review_date)
                .map(dotted)
                .unwrap_or_else(|_| a.review_date.clone())
        }
    );
    let duties = if row.kind == AgreementType::Loan {
        vec![(
            "Qaytarish jadvali".to_owned(),
            if a.has_schedule {
                "kelishilgan".to_owned()
            } else {
                "yo'q".to_owned()
            },
        )]
    } else {
        a.duties
            .iter()
            .map(|d| {
                (
                    format!(
                        "{} — {}",
                        d.title,
                        d.owner_party_id
                            .as_deref()
                            .map_or("egasiz", |id| party_name(&a, id))
                    ),
                    format!("Bajarilmasa: {}", d.breach_clause),
                )
            })
            .collect()
    };
    Ok(pdf::AgreementDocument {
        title: row.title.clone(),
        subtitle: format!("{} · {}-versiya", kind_label(row.kind), row.version),
        status_line: format!(
            "{} · amal qiladi {} dan · tuzilgan {}",
            status_label(row.status),
            row.effective_from.map_or("—".to_owned(), dotted),
            dotted(ctx.today)
        ),
        parties: a
            .parties
            .iter()
            .map(|p| (p.name.clone(), if p.is_me { format!("{} (men)", p.role) } else { p.role.clone() }))
            .collect(),
        contributions: a
            .contributions
            .iter()
            .map(|c| {
                let amount = if c.amount.trim().is_empty() {
                    String::new()
                } else {
                    parse_money(&c.amount)
                        .map(|m| format!(": {}", MoneyDto::of(m).formatted))
                        .unwrap_or_default()
                };
                (
                    party_name(&a, &c.party_id).to_owned(),
                    format!("{}{} — {}", c.kind, amount, c.description),
                )
            })
            .collect(),
        duties,
        profit,
        loss,
        custody,
        exit,
        arbiter,
        term,
        signatures: signature_rows,
        disclaimer: "Shaxsiy hisob uchun yozuv. Yuridik maslahat emas. Taʼlimiy material — fatvo yoki moliyaviy maslahat emas."
            .to_owned(),
    })
}

/// Kelishuv PDF'i.
pub fn pdf(db: &Database, now: OffsetDateTime, id: &str) -> Result<Vec<u8>, SessionError> {
    let row = load(db, id)?;
    Ok(pdf::render_agreement(&document(db, now, &row)?)?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dto::{ContributionDto, DutyDto, PartyDto, ProfitShareDto};
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);
    const PNG: &str = "data:image/png;base64,iVBORw0KGgo=";

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([41; 32])).expect("xotirada baza")
    }

    fn full_answers() -> AgreementAnswersDto {
        let mut a = AgreementAnswersDto::empty();
        a.parties = vec![
            PartyDto {
                id: "P1".into(),
                name: "Anvar Karimov".into(),
                role: "sherik".into(),
                relation: String::new(),
                is_me: true,
            },
            PartyDto {
                id: "P2".into(),
                name: "Dilshod Rahimov".into(),
                role: "sherik".into(),
                relation: String::new(),
                is_me: false,
            },
        ];
        a.contributions = vec![
            ContributionDto {
                party_id: "P1".into(),
                kind: "money".into(),
                amount: "3 000 000".into(),
                description: "naqd".into(),
            },
            ContributionDto {
                party_id: "P2".into(),
                kind: "labor".into(),
                amount: String::new(),
                description: "yetkazish".into(),
            },
        ];
        a.duties = vec![DutyDto {
            id: "d1".into(),
            title: "Yetkazish".into(),
            owner_party_id: Some("P2".into()),
            breach_clause: "1 kun ichida xabar beradi".into(),
        }];
        a.profit_shares = vec![
            ProfitShareDto {
                party_id: "P1".into(),
                share_bp: 5_000,
            },
            ProfitShareDto {
                party_id: "P2".into(),
                share_bp: 5_000,
            },
        ];
        a.loss_text = "Zarar kapitalga mutanosib".into();
        a.custody_location = "Umumiy karta".into();
        a.keeper_party_id = Some("P1".into());
        a.exit_valuation = "Oxirgi ko'rik bo'yicha".into();
        a.exit_payout = "3 oy ichida".into();
        a.arbiter_name = "Sobir hoji".into();
        a.arbiter_role = "mahalla oqsoqoli".into();
        a.review_date = "2027-10-01".into();
        a
    }

    fn signature(id: &str, party: &str, role: &str) -> SignatureInputDto {
        SignatureInputDto {
            agreement_id: id.into(),
            party_id: party.into(),
            role: role.into(),
            image: PNG.into(),
        }
    }

    #[test]
    fn toliq_bolmagan_kelishuv_imzolanmaydi_toliq_bolsa_imzolanadi_va_jurnal_ochiladi() {
        let db = database();
        let created = create(
            &db,
            NOW,
            AgreementInputDto {
                kind: "PARTNERSHIP".into(),
                title: "Non sexi".into(),
            },
        )
        .expect("yaratildi");
        assert_eq!(created.completeness.missing.len(), 9);
        assert!(matches!(
            add_signature(&db, NOW, signature(&created.id, "P1", "PARTY")),
            Err(SessionError::Domain(DomainError::AgreementIncomplete))
        ));

        let saved = save_answers(
            &db,
            NOW,
            SaveAnswersInputDto {
                id: created.id.clone(),
                version: 1,
                answers: full_answers(),
            },
        )
        .expect("saqlandi");
        assert!(saved.completeness.complete, "{:?}", saved.completeness);
        assert_eq!(saved.version, 2);

        add_signature(&db, NOW, signature(&created.id, "P1", "PARTY")).expect("P1");
        assert!(matches!(
            sign(
                &db,
                NOW,
                SignInputDto {
                    agreement_id: created.id.clone(),
                    effective_from: None,
                    opening_balance_party_id: None,
                    opening_balance_amount: None
                }
            ),
            Err(SessionError::Domain(DomainError::SignaturesMissing))
        ));
        add_signature(&db, NOW, signature(&created.id, "P2", "PARTY")).expect("P2");
        add_signature(&db, NOW, signature(&created.id, "ARBITER", "ARBITER")).expect("hakam");

        // Og'zaki kelishuv: o'tmishdagi sana va boshlang'ich balans.
        let signed = sign(
            &db,
            NOW,
            SignInputDto {
                agreement_id: created.id.clone(),
                effective_from: Some("2026-09-01".into()),
                opening_balance_party_id: Some("P1".into()),
                opening_balance_amount: Some("3 000 000".into()),
            },
        )
        .expect("imzolandi");
        assert_eq!(signed.status, "SIGNED");
        assert_eq!(signed.effective_from.as_deref(), Some("2026-09-01"));
        assert_eq!(signed.journal_count, 1);
        assert!(signed.chain_ok && signed.can_write_journal);

        let journal = append_journal(
            &db,
            NOW,
            JournalEntryInputDto {
                agreement_id: created.id.clone(),
                kind: "CONTRIBUTION".into(),
                party_id: "P2".into(),
                amount: "500 000".into(),
                date: None,
                note: None,
            },
        )
        .expect("yozildi");
        assert_eq!(journal.entries.len(), 2);
        assert!(journal.chain_ok);

        let bytes = pdf(&db, NOW, &created.id).expect("pdf");
        assert!(bytes.starts_with(b"%PDF-"));
    }

    #[test]
    fn javob_ozgarsa_imzolar_qayta_soraladi() {
        let db = database();
        let created = create(
            &db,
            NOW,
            AgreementInputDto {
                kind: "FAMILY".into(),
                title: "Oila".into(),
            },
        )
        .expect("yaratildi");
        let mut answers = full_answers();
        answers.arbiter_name = String::new();
        answers.profit_not_applicable = Some("oilaviy".into());
        answers.loss_not_applicable = Some("oilaviy".into());
        let saved = save_answers(
            &db,
            NOW,
            SaveAnswersInputDto {
                id: created.id.clone(),
                version: 1,
                answers: answers.clone(),
            },
        )
        .expect("saqlandi");
        assert!(saved.completeness.complete);
        add_signature(&db, NOW, signature(&created.id, "P1", "PARTY")).expect("P1");
        add_signature(&db, NOW, signature(&created.id, "P2", "PARTY")).expect("P2");
        let signed = sign(
            &db,
            NOW,
            SignInputDto {
                agreement_id: created.id.clone(),
                effective_from: None,
                opening_balance_party_id: None,
                opening_balance_amount: None,
            },
        )
        .expect("imzolandi");
        assert_eq!(signed.signatures.len(), 2);

        let resaved = save_answers(
            &db,
            NOW,
            SaveAnswersInputDto {
                id: created.id.clone(),
                version: signed.version,
                answers,
            },
        )
        .expect("qayta saqlandi");
        assert_eq!(resaved.status, "DRAFT");
        assert!(
            resaved.signatures.is_empty(),
            "yangi versiya uchun imzo yo'q"
        );
        assert!(!resaved.can_write_journal);
    }
}
