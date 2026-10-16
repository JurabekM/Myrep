//! D12 xizmati: sheriklik — `PARTNERSHIP` kelishuvi (D8A dvigateli) ustiga tur (`MUDARABA | MUSHARAKA`),
//! mening rolim, tayyorgarlik darvozasi (faqat kapital kirituvchiga), kapital qabul qilishda oilaviy rozilik,
//! kamayib boruvchi sheriklik (buyout) jadvali.
//!
//! Qoidalar domen'da: tuzilma (`partnership::validate_structure`), kafolatli daromad taqiqi, ulushlar 100 %.
//! Imzolashdan oldin [`check_before_sign`] chaqiriladi (`agreements::sign`).

use domain::DomainError;
use domain::agreement::AgreementType;
use domain::partnership::{
    FULL_SHARE_BP, PartnerInput, PartnershipKind, buyout_schedule, validate_structure,
};
use money::{Money, round_half_up_div};
use security::{SecurityError, verify_member_pin};
use storage::{
    AgreementRow, BuyoutPaymentRow, Database, GateOverrideRepo, MemberRepo, PartnershipRepo,
    PartnershipRow, PinRepo, StorageError,
};
use time::format_description::well_known::Iso8601;
use time::{Date, OffsetDateTime};

use crate::agreements;
use crate::dto::{
    AgreementAnswersDto, AgreementInputDto, BuyoutDto, BuyoutInputDto, BuyoutPaymentInputDto,
    BuyoutRowDto, ConsentInputDto, MoneyDto, PartnerSummaryDto, PartnershipDto,
    PartnershipInputDto, PartnershipsDto,
};
use crate::finance::{self, CURRENCY, DEVICE_ID, UuidV7, date_text, parse_money};
use crate::reserve;
use crate::session::SessionError;

const KIND_MUDARABA: &str = "MUDARABA";
const KIND_MUSHARAKA: &str = "MUSHARAKA";
const ROLE_CAPITAL: &str = "CAPITAL_PROVIDER";
const ROLE_WORKER: &str = "WORKER";

fn parse_date(text: &str) -> Result<Date, SessionError> {
    Date::parse(text, &Iso8601::DATE).map_err(|_| DomainError::InvalidDay.into())
}

fn kind_of(code: &str) -> Result<PartnershipKind, SessionError> {
    match code {
        KIND_MUDARABA => Ok(PartnershipKind::Mudaraba),
        KIND_MUSHARAKA => Ok(PartnershipKind::Musharaka),
        _ => Err(DomainError::InvalidRule.into()),
    }
}

fn add(left: Money, right: Money) -> Result<Money, SessionError> {
    Ok(left.checked_add(right).map_err(DomainError::from)?)
}

/// Kelishuv javoblaridan sheriklar: kapital = pul hissalari yig'indisi, ulush — 4-savoldan.
pub(crate) fn partner_inputs(
    answers: &AgreementAnswersDto,
) -> Result<Vec<(PartnerInput, PartnerSummaryDto)>, SessionError> {
    let mut out = Vec::with_capacity(answers.parties.len());
    for party in &answers.parties {
        let mut capital = Money::zero(CURRENCY);
        for contribution in answers
            .contributions
            .iter()
            .filter(|c| c.party_id == party.id && c.kind == "money" && !c.amount.trim().is_empty())
        {
            capital = add(capital, parse_money(&contribution.amount)?)?;
        }
        let share_bp = answers
            .profit_shares
            .iter()
            .find(|s| s.party_id == party.id)
            .map_or(0, |s| u64::from(s.share_bp));
        let fixed_return = if answers.profit_fixed_amount.trim().is_empty() {
            None
        } else {
            Some(parse_money(&answers.profit_fixed_amount)?)
        };
        out.push((
            PartnerInput {
                share_bp,
                capital,
                fixed_return,
                is_capital_provider: capital.minor() > 0,
            },
            PartnerSummaryDto {
                party_id: party.id.clone(),
                name: party.name.clone(),
                role: party.role.clone(),
                capital: MoneyDto::of(capital),
                share_bp: u32::try_from(share_bp).unwrap_or(u32::MAX),
                is_me: party.is_me,
            },
        ));
    }
    Ok(out)
}

/// Muammolar ro'yxati (ko'rsatish uchun, bloklamaydi): tuzilma, ulushlar, rozilik.
fn issues_of(
    row: &PartnershipRow,
    answers: &AgreementAnswersDto,
) -> Result<Vec<String>, SessionError> {
    let kind = kind_of(&row.kind)?;
    let inputs: Vec<PartnerInput> = partner_inputs(answers)?
        .into_iter()
        .map(|(input, _)| input)
        .collect();
    let mut issues = Vec::new();
    if !inputs.is_empty()
        && let Err(error) = validate_structure(kind, &inputs)
    {
        issues.push(error.code().to_owned());
    }
    let share_total = inputs
        .iter()
        .fold(0_u64, |acc, p| acc.saturating_add(p.share_bp));
    if !inputs.is_empty() && share_total != FULL_SHARE_BP {
        issues.push(DomainError::ProfitSharesNotHundred.code().to_owned());
    }
    if row.my_role == ROLE_WORKER && row.consent_member.is_none() {
        issues.push(DomainError::FamilyConsentRequired.code().to_owned());
    }
    Ok(issues)
}

/// Imzolashdan oldingi tekshiruv (`agreements::sign` chaqiradi): sheriklik bo'lsa — tuzilma qoidasi va
/// kapital qabul qiluvchida oilaviy rozilik. Oddiy kelishuvga ta'sir qilmaydi.
pub fn check_before_sign(
    db: &Database,
    agreement: &AgreementRow,
    answers: &AgreementAnswersDto,
) -> Result<(), SessionError> {
    if agreement.kind != AgreementType::Partnership {
        return Ok(());
    }
    let Some(row) = PartnershipRepo::new(db.connection()).find_by_agreement(&agreement.id)? else {
        return Ok(());
    };
    if row.my_role == ROLE_WORKER && row.consent_member.is_none() {
        return Err(DomainError::FamilyConsentRequired.into());
    }
    let inputs: Vec<PartnerInput> = partner_inputs(answers)?
        .into_iter()
        .map(|(input, _)| input)
        .collect();
    validate_structure(kind_of(&row.kind)?, &inputs)?;
    Ok(())
}

pub(crate) fn buyout_dto(
    db: &Database,
    row: &PartnershipRow,
) -> Result<Option<BuyoutDto>, SessionError> {
    let (Some(total), Some(months), Some(start)) =
        (row.buyout_total, row.buyout_months, row.buyout_start)
    else {
        return Ok(None);
    };
    let payments = PartnershipRepo::new(db.connection()).payments(&row.id)?;
    let mut paid = Money::zero(total.currency());
    for (amount, _) in &payments {
        paid = add(paid, *amount)?;
    }
    let remaining = Money::new(
        total.minor().saturating_sub(paid.minor()).max(0),
        total.currency(),
    );
    let remaining_share_bp = round_half_up_div(
        i128::from(remaining.minor()) * i128::from(FULL_SHARE_BP),
        i128::from(total.minor()),
    )
    .map_err(DomainError::from)?;
    let steps = buyout_schedule(total, months, start)?;
    let mut cumulative: i64 = 0;
    let rows = steps
        .iter()
        .map(|step| {
            cumulative = cumulative.saturating_add(step.amount.minor());
            BuyoutRowDto {
                seq: step.seq,
                due_on: date_text(step.due_on),
                amount: MoneyDto::of(step.amount),
                remaining_share_bp: u32::try_from(step.remaining_share_bp).unwrap_or(0),
                paid: paid.minor() >= cumulative,
            }
        })
        .collect();
    Ok(Some(BuyoutDto {
        total: MoneyDto::of(total),
        months,
        start_on: date_text(start),
        paid: MoneyDto::of(paid),
        remaining: MoneyDto::of(remaining),
        remaining_share_bp: u32::try_from(remaining_share_bp).unwrap_or(0),
        rows,
    }))
}

fn dto(
    db: &Database,
    now: OffsetDateTime,
    row: &PartnershipRow,
    gate: (&str, &[String]),
) -> Result<PartnershipDto, SessionError> {
    let agreement = agreements::get(db, now, &row.agreement_id)?;
    let parties: Vec<PartnerSummaryDto> = partner_inputs(&agreement.answers)?
        .into_iter()
        .map(|(_, summary)| summary)
        .collect();
    let mut capital_total = Money::zero(CURRENCY);
    for (input, _) in partner_inputs(&agreement.answers)? {
        capital_total = add(capital_total, input.capital)?;
    }
    Ok(PartnershipDto {
        id: row.id.clone(),
        agreement_id: row.agreement_id.clone(),
        title: agreement.title,
        kind: row.kind.clone(),
        my_role: row.my_role.clone(),
        status: agreement.status,
        version: agreement.version,
        parties,
        capital_total: MoneyDto::of(capital_total),
        issues: issues_of(row, &agreement.answers)?,
        gate: gate.0.to_owned(),
        gate_reasons: gate.1.to_vec(),
        consent_member: row.consent_member.clone(),
        consent_at: row.consent_at.map(|t| date_text(t.date())),
        buyout: buyout_dto(db, row)?,
        gate_override_reason: GateOverrideRepo::new(db.connection()).reason_for(&row.id)?,
    })
}

/// Sherikliklar ro'yxati (darvoza holati bilan).
pub fn list(db: &Database, now: OffsetDateTime) -> Result<PartnershipsDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let reserve = reserve::reserve(db, now)?;
    let rows = PartnershipRepo::new(db.connection()).list(&ctx.household.id)?;
    let mut items = Vec::with_capacity(rows.len());
    for row in &rows {
        items.push(dto(db, now, row, (&reserve.gate, &reserve.reasons))?);
    }
    Ok(PartnershipsDto {
        items,
        gate: reserve.gate,
        gate_reasons: reserve.reasons,
    })
}

fn load(db: &Database, id: &str) -> Result<PartnershipRow, SessionError> {
    PartnershipRepo::new(db.connection())
        .find(id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))
}

/// Yangi sheriklik: `PARTNERSHIP` kelishuvi qoralamasi + sheriklik yozuvi.
/// Kapital kirituvchi uchun tayyorgarlik darvozasi `OPEN` bo'lishi shart (SPEC 2E.6); kapital qabul qiluvchi
/// darvozaga bo'ysunmaydi, lekin imzolashdan oldin oilaviy rozilik so'raladi.
pub fn create(
    db: &Database,
    now: OffsetDateTime,
    input: PartnershipInputDto,
) -> Result<PartnershipsDto, SessionError> {
    let ctx = finance::context(db, now)?;
    kind_of(&input.kind)?;
    if input.my_role != ROLE_CAPITAL && input.my_role != ROLE_WORKER {
        return Err(DomainError::InvalidRule.into());
    }
    // Darvoza yopiq + kapital kirituvchi: faqat ongli chetlab o'tish bilan (sabab ≥ 20 belgi, ADULT PIN).
    let mut override_record: Option<(String, String)> = None;
    if input.my_role == ROLE_CAPITAL && reserve::reserve(db, now)?.gate != "OPEN" {
        let Some(gate_override) = input.gate_override.as_ref() else {
            return Err(DomainError::ReadinessGateLocked.into());
        };
        let reason = gate_override.reason.trim();
        if reason.chars().count() < 20 {
            return Err(DomainError::OverrideReasonRequired.into());
        }
        let member = MemberRepo::new(db.connection())
            .find(&gate_override.member_id)?
            .ok_or(StorageError::NotFound)?;
        if member.role != domain::MemberRole::Adult || member.household_id != ctx.household.id {
            return Err(DomainError::InvalidRole.into());
        }
        let pins = PinRepo::new(db.connection());
        let state = pins.find(&member.id)?.ok_or(StorageError::NotFound)?;
        let verifier = state.verifier.clone().ok_or(DomainError::PinNotSet)?;
        crate::family::ensure_not_locked(&state, now)?;
        if !verify_member_pin(&gate_override.pin, &verifier, crate::family::kdf_params())? {
            pins.record_failure(&member.id, now)?;
            return Err(SecurityError::WrongPin.into());
        }
        pins.reset_failures(&member.id)?;
        override_record = Some((member.id, reason.to_owned()));
    }
    let agreement = agreements::create(
        db,
        now,
        AgreementInputDto {
            kind: "PARTNERSHIP".to_owned(),
            title: input.title,
        },
    )?;
    let partnership_id = domain::IdGen::next_id(&UuidV7);
    PartnershipRepo::new(db.connection()).insert(&PartnershipRow {
        id: partnership_id.clone(),
        household_id: ctx.household.id.clone(),
        agreement_id: agreement.id,
        kind: input.kind,
        my_role: input.my_role,
        buyout_total: None,
        buyout_months: None,
        buyout_start: None,
        consent_member: None,
        consent_at: None,
        created_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    })?;
    if let Some((member_id, reason)) = override_record {
        GateOverrideRepo::new(db.connection()).insert(
            &domain::IdGen::next_id(&UuidV7),
            &ctx.household.id,
            "PARTNERSHIP_CAPITAL",
            &partnership_id,
            &reason,
            &member_id,
            now,
            DEVICE_ID,
        )?;
    }
    list(db, now)
}

/// Buyout shartlari: ulush qiymati, oylar, boshlanish sanasi (jadval domen'da).
pub fn set_buyout(
    db: &Database,
    now: OffsetDateTime,
    input: BuyoutInputDto,
) -> Result<PartnershipsDto, SessionError> {
    let row = load(db, &input.id)?;
    let total = parse_money(&input.total)?;
    let start = parse_date(&input.start_on)?;
    // Jadval qurilib ko'riladi: summa > 0, oylar ≥ 1 — xato bo'lsa saqlanmaydi.
    buyout_schedule(total, input.months, start)?;
    PartnershipRepo::new(db.connection()).set_buyout(&row.id, total, input.months, start, now)?;
    list(db, now)
}

/// Buyout to'lovi: qoldiqdan oshmaydi.
pub fn pay_buyout(
    db: &Database,
    now: OffsetDateTime,
    input: BuyoutPaymentInputDto,
) -> Result<PartnershipsDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let row = load(db, &input.id)?;
    let Some(buyout) = buyout_dto(db, &row)? else {
        return Err(DomainError::InvalidRule.into());
    };
    let amount = parse_money(&input.amount)?;
    if amount.minor() <= 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    let remaining: i64 = buyout.remaining.minor.parse().unwrap_or(0);
    if amount.minor() > remaining {
        return Err(DomainError::DebtOverpaid.into());
    }
    let paid_on = match input.paid_on.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => parse_date(text)?,
        None => ctx.today,
    };
    if paid_on > ctx.today {
        return Err(DomainError::InvalidDay.into());
    }
    PartnershipRepo::new(db.connection()).insert_payment(&BuyoutPaymentRow {
        id: domain::IdGen::next_id(&UuidV7),
        partnership_id: row.id.clone(),
        amount,
        paid_on,
        created_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    })?;
    list(db, now)
}

/// Kapital qabul qilishda oilaviy rozilik (er va xotin): a'zo nomi yoziladi.
pub fn consent(
    db: &Database,
    now: OffsetDateTime,
    input: ConsentInputDto,
) -> Result<PartnershipsDto, SessionError> {
    let row = load(db, &input.id)?;
    let member = domain::validate_name(&input.member_name)?;
    PartnershipRepo::new(db.connection()).set_consent(&row.id, &member, now)?;
    list(db, now)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dto::{ContributionDto, PartyDto, ProfitShareDto};
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([81; 32])).expect("xotirada baza")
    }

    fn input(kind: &str, role: &str) -> PartnershipInputDto {
        PartnershipInputDto {
            title: "Non sexi".into(),
            kind: kind.into(),
            my_role: role.into(),
            gate_override: None,
        }
    }

    fn answers(capital_p2: &str) -> AgreementAnswersDto {
        let mut a = AgreementAnswersDto::empty();
        a.parties = vec![
            PartyDto {
                id: "P1".into(),
                name: "Anvar Karimov".into(),
                role: "mehnat".into(),
                relation: String::new(),
                is_me: true,
            },
            PartyDto {
                id: "P2".into(),
                name: "Dilshod Rahimov".into(),
                role: "kapital".into(),
                relation: String::new(),
                is_me: false,
            },
        ];
        a.contributions = vec![
            ContributionDto {
                party_id: "P1".into(),
                kind: "labor".into(),
                amount: String::new(),
                description: "tikuvchilik".into(),
            },
            ContributionDto {
                party_id: "P2".into(),
                kind: "money".into(),
                amount: capital_p2.into(),
                description: "overlock uchun".into(),
            },
        ];
        a.profit_shares = vec![
            ProfitShareDto {
                party_id: "P1".into(),
                share_bp: 6_000,
            },
            ProfitShareDto {
                party_id: "P2".into(),
                share_bp: 4_000,
            },
        ];
        a
    }

    #[test]
    fn kapital_kirituvchi_darvoza_yopiq_bolsa_yaratolmaydi_mehnat_egasi_yaratadi() {
        let db = database();
        assert!(matches!(
            create(&db, NOW, input("MUDARABA", "CAPITAL_PROVIDER")),
            Err(SessionError::Domain(DomainError::ReadinessGateLocked))
        ));
        let view = create(&db, NOW, input("MUDARABA", "WORKER")).expect("yaratildi");
        assert_eq!(view.items.len(), 1);
        assert_eq!(view.gate, "LOCKED");
        assert!(
            view.items[0]
                .issues
                .contains(&"FAMILY_CONSENT_REQUIRED".to_owned())
        );
    }

    #[test]
    fn rozilik_va_tuzilma_imzolashdan_oldin_tekshiriladi() {
        let db = database();
        let view = create(&db, NOW, input("MUDARABA", "WORKER")).expect("yaratildi");
        let item = &view.items[0];
        let agreement = storage::AgreementRepo::new(db.connection())
            .find(&item.agreement_id)
            .expect("so'rov")
            .expect("kelishuv");
        // Rozilik yo'q — imzolab bo'lmaydi.
        assert!(matches!(
            check_before_sign(&db, &agreement, &answers("5 000 000")),
            Err(SessionError::Domain(DomainError::FamilyConsentRequired))
        ));
        let view = consent(
            &db,
            NOW,
            ConsentInputDto {
                id: item.id.clone(),
                member_name: "Nodira".into(),
            },
        )
        .expect("rozilik");
        assert_eq!(view.items[0].consent_member.as_deref(), Some("Nodira"));
        assert!(check_before_sign(&db, &agreement, &answers("5 000 000")).is_ok());
        // Mudarabada ikkala tomon kapital kiritsa — tuzilma noto'g'ri.
        let mut both = answers("5 000 000");
        both.contributions[0] = ContributionDto {
            party_id: "P1".into(),
            kind: "money".into(),
            amount: "1 000 000".into(),
            description: String::new(),
        };
        assert!(matches!(
            check_before_sign(&db, &agreement, &both),
            Err(SessionError::Domain(
                DomainError::PartnershipStructureInvalid
            ))
        ));
        // Kafolatli summa — domen taqiqi.
        let mut fixed = answers("5 000 000");
        fixed.profit_fixed_amount = "500 000".into();
        assert!(matches!(
            check_before_sign(&db, &agreement, &fixed),
            Err(SessionError::Domain(DomainError::GuaranteedReturnForbidden))
        ));
    }

    #[test]
    fn buyout_jadvali_va_tolov() {
        let db = database();
        let view = create(&db, NOW, input("MUSHARAKA", "WORKER")).expect("yaratildi");
        let id = view.items[0].id.clone();
        let view = set_buyout(
            &db,
            NOW,
            BuyoutInputDto {
                id: id.clone(),
                total: "9 000 000".into(),
                months: 3,
                start_on: "2026-11-15".into(),
            },
        )
        .expect("buyout");
        let buyout = view.items[0].buyout.as_ref().expect("jadval");
        assert_eq!(buyout.rows.len(), 3);
        assert_eq!(buyout.rows[0].amount.minor, "300000000");
        assert_eq!(buyout.remaining_share_bp, 10_000);
        let view = pay_buyout(
            &db,
            NOW,
            BuyoutPaymentInputDto {
                id: id.clone(),
                amount: "3 000 000".into(),
                paid_on: None,
            },
        )
        .expect("to'lov");
        let buyout = view.items[0].buyout.as_ref().expect("jadval");
        assert!(buyout.rows[0].paid);
        assert!(!buyout.rows[1].paid);
        assert_eq!(buyout.remaining_share_bp, 6_667);
        assert!(matches!(
            pay_buyout(
                &db,
                NOW,
                BuyoutPaymentInputDto {
                    id,
                    amount: "7 000 000".into(),
                    paid_on: None,
                }
            ),
            Err(SessionError::Domain(DomainError::DebtOverpaid))
        ));
    }
}
