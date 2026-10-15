//! D9 xizmati: qarzlar (olingan/bergan), to'lash rejasi, to'lovlar, «to'xta va o'yla» (friction),
//! «qarzsiz kun» va tilxat (D8A `LOAN` kelishuvi).
//!
//! Qoidalar: rejasiz qarz saqlanmaydi (domen); bergan qarzda foiz yo'q (tuzilma); `STOP` taqiq emas —
//! natija yozuvda qoladi (SPEC 2D.6).

use domain::DomainError;
use domain::debt::{outstanding, validate_payment};
use domain::loans::{BorrowVerdict, borrow_check, debt_free_day, equal_plan, next_installment};
use money::{Money, round_half_up_div};
use storage::{Database, IncomeRepo, LoanDirection, LoanRepo, LoanRow, PaymentRow, StorageError};
use time::format_description::well_known::Iso8601;
use time::{Date, OffsetDateTime};

use crate::agreements;
use crate::dto::{
    AgreementAnswersDto, AgreementDto, AgreementInputDto, BorrowCheckDto, BorrowCheckInputDto,
    ContributionDto, LoanDto, LoanInputDto, LoanPaymentInputDto, LoansDto, MoneyDto, PartyDto,
    SaveAnswersInputDto,
};
use crate::finance::{self, CURRENCY, Context, DEVICE_ID, UuidV7, date_text, parse_money};
use crate::session::SessionError;

const COUNTERPARTY_TYPES: [&str; 5] = ["BANK", "SHOP", "RELATIVE", "FRIEND", "OTHER"];

/// Pul yig'indisi: `MoneyError` domen xatosi orqali seans xatosiga aylanadi.
fn add(left: Money, right: Money) -> Result<Money, SessionError> {
    Ok(left.checked_add(right).map_err(DomainError::from)?)
}

/// Yarim tiyin yuqoriga bo'lish (seans xatosi bilan).
fn div(numerator: i128, denominator: i128) -> Result<i128, SessionError> {
    Ok(round_half_up_div(numerator, denominator).map_err(DomainError::from)?)
}

fn parse_date(text: &str) -> Result<Date, SessionError> {
    Date::parse(text, &Iso8601::DATE).map_err(|_| DomainError::InvalidDay.into())
}

fn direction_of(code: &str) -> Result<LoanDirection, SessionError> {
    match code {
        "TAKEN" => Ok(LoanDirection::Taken),
        "GIVEN" => Ok(LoanDirection::Given),
        _ => Err(DomainError::InvalidRule.into()),
    }
}

fn verdict_code(verdict: BorrowVerdict) -> &'static str {
    match verdict {
        BorrowVerdict::Ok => "OK",
        BorrowVerdict::Caution => "CAUTION",
        BorrowVerdict::Stop => "STOP",
    }
}

/// Shu oy daromadi (friction uchun).
fn monthly_income(db: &Database, ctx: &Context) -> Result<Money, SessionError> {
    let period = domain::calendar::month_of(ctx.today, ctx.household.month_start_day)
        .ok_or(DomainError::InvalidDay)?;
    let incomes = IncomeRepo::new(db.connection()).list_in_range(&ctx.household.id, period)?;
    let minor = incomes.iter().fold(0_i64, |acc, income| {
        acc.saturating_add(income.amount.minor())
    });
    Ok(Money::new(minor, CURRENCY))
}

fn paid_total(db: &Database, loan: &LoanRow) -> Result<Money, SessionError> {
    let payments: Vec<Money> = LoanRepo::new(db.connection())
        .payments(&loan.id)?
        .into_iter()
        .map(|(amount, _)| amount)
        .collect();
    let mut total = Money::zero(loan.principal.currency());
    for payment in payments {
        total = add(total, payment)?;
    }
    Ok(total)
}

fn loan_dto(db: &Database, loan: &LoanRow) -> Result<LoanDto, SessionError> {
    let paid = paid_total(db, loan)?;
    let remaining = outstanding(loan.principal, &[paid])?;
    let next = next_installment(&loan.plan, paid);
    let last = loan
        .plan
        .installments()
        .last()
        .map(|i| i.due_on)
        .ok_or(DomainError::RepaymentPlanRequired)?;
    Ok(LoanDto {
        id: loan.id.clone(),
        direction: loan.direction.code().to_owned(),
        counterparty: loan.counterparty.clone(),
        counterparty_type: loan.counterparty_type.clone(),
        reason: loan.reason.clone(),
        principal: MoneyDto::of(loan.principal),
        paid: MoneyDto::of(paid),
        outstanding: MoneyDto::of(remaining),
        has_markup: loan.has_markup,
        incurred_on: date_text(loan.incurred_on),
        next_due_on: next.map(|i| date_text(i.due_on)),
        next_amount: next.map(|i| MoneyDto::of(i.amount)),
        last_due_on: date_text(last),
        installments: u32::try_from(loan.plan.installments().len()).unwrap_or(u32::MAX),
        borrow_verdict: loan.borrow_verdict.clone(),
        agreement_id: loan.agreement_id.clone(),
        settled: remaining.minor() == 0,
    })
}

/// Ochiq olingan qarzlarning keyingi to'lovlari yig'indisi (oylik yuk).
fn burden_of(db: &Database, taken: &[LoanRow]) -> Result<Money, SessionError> {
    let mut total = Money::zero(CURRENCY);
    for loan in taken {
        let paid = paid_total(db, loan)?;
        if let Some(next) = next_installment(&loan.plan, paid) {
            total = add(total, next.amount)?;
        }
    }
    Ok(total)
}

/// Qarzlar sahifasi.
pub fn overview(db: &Database, now: OffsetDateTime) -> Result<LoansDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let repo = LoanRepo::new(db.connection());
    let taken = repo.list(&ctx.household.id, LoanDirection::Taken)?;
    let given = repo.list(&ctx.household.id, LoanDirection::Given)?;
    let mut total_outstanding = Money::zero(CURRENCY);
    let mut total_receivable = Money::zero(CURRENCY);
    let mut taken_dtos = Vec::with_capacity(taken.len());
    for loan in &taken {
        let dto = loan_dto(db, loan)?;
        total_outstanding = add(
            total_outstanding,
            outstanding(loan.principal, &[paid_total(db, loan)?])?,
        )?;
        taken_dtos.push(dto);
    }
    let mut given_dtos = Vec::with_capacity(given.len());
    for loan in &given {
        let dto = loan_dto(db, loan)?;
        total_receivable = add(
            total_receivable,
            outstanding(loan.principal, &[paid_total(db, loan)?])?,
        )?;
        given_dtos.push(dto);
    }
    let open_plans: Vec<&domain::loans::RepaymentPlan> = taken
        .iter()
        .zip(taken_dtos.iter())
        .filter(|(_, dto)| !dto.settled)
        .map(|(loan, _)| &loan.plan)
        .collect();
    Ok(LoansDto {
        taken: taken_dtos,
        given: given_dtos,
        total_outstanding: MoneyDto::of(total_outstanding),
        total_receivable: MoneyDto::of(total_receivable),
        monthly_burden: MoneyDto::of(burden_of(db, &taken)?),
        monthly_income: MoneyDto::of(monthly_income(db, &ctx)?),
        debt_free_day: debt_free_day(&open_plans).map(date_text),
    })
}

fn check_with(
    db: &Database,
    ctx: &Context,
    principal: Money,
    installments: u32,
) -> Result<BorrowCheckDto, SessionError> {
    if installments == 0 {
        return Err(DomainError::RepaymentPlanRequired.into());
    }
    let taken = LoanRepo::new(db.connection()).list(&ctx.household.id, LoanDirection::Taken)?;
    let existing = burden_of(db, &taken)?;
    let new_monthly = div(i128::from(principal.minor()), i128::from(installments))?;
    let burden = add(
        existing,
        Money::new(i64::try_from(new_monthly).unwrap_or(i64::MAX), CURRENCY),
    )?;
    let income = monthly_income(db, ctx)?;
    let verdict = borrow_check(burden, income)?;
    let bp = if income.minor() <= 0 {
        10_000
    } else {
        u32::try_from(div(
            i128::from(burden.minor()) * 10_000,
            i128::from(income.minor()),
        )?)
        .unwrap_or(u32::MAX)
    };
    Ok(BorrowCheckDto {
        verdict: verdict_code(verdict).to_owned(),
        monthly_burden: MoneyDto::of(burden),
        monthly_income: MoneyDto::of(income),
        burden_bp: bp,
    })
}

/// Qarz oldidan tekshiruv: oylik yuk va natija (saqlanmaydi).
pub fn check_borrow(
    db: &Database,
    now: OffsetDateTime,
    input: BorrowCheckInputDto,
) -> Result<BorrowCheckDto, SessionError> {
    let ctx = finance::context(db, now)?;
    check_with(db, &ctx, parse_money(&input.principal)?, input.installments)
}

/// Qarz qo'shadi (reja majburiy; olingan qarzda friction natijasi saqlanadi).
pub fn add_loan(
    db: &Database,
    now: OffsetDateTime,
    input: LoanInputDto,
) -> Result<LoansDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let direction = direction_of(&input.direction)?;
    if !COUNTERPARTY_TYPES.contains(&input.counterparty_type.as_str()) {
        return Err(DomainError::InvalidRule.into());
    }
    let principal = parse_money(&input.principal)?;
    if principal.minor() <= 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    let first_due = parse_date(&input.first_due_on)?;
    let incurred_on = match input
        .incurred_on
        .as_deref()
        .filter(|t| !t.trim().is_empty())
    {
        Some(text) => parse_date(text)?,
        None => ctx.today,
    };
    if first_due < incurred_on {
        return Err(DomainError::InvalidDay.into());
    }
    let plan = equal_plan(principal, input.installments, first_due)?;
    let verdict = if direction == LoanDirection::Taken {
        Some(check_with(db, &ctx, principal, input.installments)?.verdict)
    } else {
        None
    };
    let row = LoanRow {
        id: domain::IdGen::next_id(&UuidV7),
        household_id: ctx.household.id.clone(),
        direction,
        counterparty: domain::validate_name(&input.counterparty)?,
        counterparty_type: input.counterparty_type,
        reason: input.reason.filter(|r| !r.trim().is_empty()),
        principal,
        has_markup: direction == LoanDirection::Taken && input.has_markup,
        incurred_on,
        borrow_verdict: verdict,
        friction_necessity: input.friction_necessity,
        friction_alternative: input.friction_alternative,
        agreement_id: None,
        plan,
        created_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    };
    LoanRepo::new(db.connection()).insert(&row)?;
    overview(db, now)
}

/// To'lov (olingan — to'ladim; bergan — qaytardi). Qoldiqdan oshmaydi.
pub fn pay(
    db: &Database,
    now: OffsetDateTime,
    input: LoanPaymentInputDto,
) -> Result<LoansDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let repo = LoanRepo::new(db.connection());
    let loan = repo
        .find(&input.loan_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    let amount = parse_money(&input.amount)?;
    let remaining = outstanding(loan.principal, &[paid_total(db, &loan)?])?;
    validate_payment(remaining, amount)?;
    let paid_on = match input.paid_on.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => parse_date(text)?,
        None => ctx.today,
    };
    if paid_on > ctx.today {
        return Err(DomainError::InvalidDay.into());
    }
    repo.insert_payment(&PaymentRow {
        id: domain::IdGen::next_id(&UuidV7),
        household_id: ctx.household.id.clone(),
        loan_id: loan.id.clone(),
        amount,
        paid_on,
        created_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    })?;
    overview(db, now)
}

/// Tilxat: qarz uchun `LOAN` kelishuvi qoralamasi (tomonlar, hissa, jadval, muddat oldindan to'ldirilgan).
/// Hakam (8-savol) foydalanuvchi tomonidan to'ldiriladi — usta 8/9 bilan ochiladi.
pub fn create_iou(
    db: &Database,
    now: OffsetDateTime,
    loan_id: &str,
) -> Result<AgreementDto, SessionError> {
    let repo = LoanRepo::new(db.connection());
    let loan = repo
        .find(loan_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    if let Some(existing) = &loan.agreement_id {
        return agreements::get(db, now, existing);
    }
    let created = agreements::create(
        db,
        now,
        AgreementInputDto {
            kind: "LOAN".to_owned(),
            title: format!("Qarz tilxati — {}", loan.counterparty),
        },
    )?;
    let (me_role, other_role) = match loan.direction {
        LoanDirection::Taken => ("qarz oluvchi", "qarz beruvchi"),
        LoanDirection::Given => ("qarz beruvchi", "qarz oluvchi"),
    };
    let lender_id = if loan.direction == LoanDirection::Taken {
        "P2"
    } else {
        "P1"
    };
    let borrower_id = if lender_id == "P1" { "P2" } else { "P1" };
    let last_due = loan
        .plan
        .installments()
        .last()
        .map(|i| i.due_on)
        .ok_or(DomainError::RepaymentPlanRequired)?;
    let mut answers = created.answers.clone();
    answers.parties = vec![
        PartyDto {
            id: "P1".into(),
            name: "O'zim".into(),
            role: me_role.into(),
            relation: String::new(),
            is_me: true,
        },
        PartyDto {
            id: "P2".into(),
            name: loan.counterparty.clone(),
            role: other_role.into(),
            relation: String::new(),
            is_me: false,
        },
    ];
    answers.contributions = vec![
        ContributionDto {
            party_id: lender_id.into(),
            kind: "money".into(),
            amount: loan.principal.minor().to_string(),
            description: "qarz summasi (qarzi hasana, foizsiz)".into(),
        },
        ContributionDto {
            party_id: borrower_id.into(),
            kind: "labor".into(),
            amount: String::new(),
            description: "reja bo'yicha qaytarish majburiyati".into(),
        },
    ];
    answers.has_schedule = true;
    answers.custody_location = "Qarz oluvchida".into();
    answers.keeper_party_id = Some(lender_id.into());
    answers.exit_valuation = "Qoldiq summa".into();
    answers.exit_payout = "Muddatidan oldin to'lash mumkin, qo'shimcha to'lovsiz".into();
    answers.term_months = u32::try_from(loan.plan.installments().len())
        .unwrap_or(1)
        .max(1);
    answers.review_date = date_text(last_due);
    // Hissa summasi minor birlikda keldi — `parse_money` uchun so'm ko'rinishiga keltiriladi.
    answers.contributions[0].amount = MoneyDto::of(loan.principal).formatted;
    let saved = agreements::save_answers(
        db,
        now,
        SaveAnswersInputDto {
            id: created.id.clone(),
            version: created.version,
            answers: AgreementAnswersDto { ..answers },
        },
    )?;
    repo.set_agreement(&loan.id, &saved.id, now)?;
    Ok(saved)
}

#[cfg(test)]
mod tests {
    use super::*;
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([51; 32])).expect("xotirada baza")
    }

    fn loan_input(direction: &str, principal: &str, installments: u32) -> LoanInputDto {
        LoanInputDto {
            direction: direction.into(),
            counterparty: "Dilshod".into(),
            counterparty_type: "FRIEND".into(),
            reason: Some("ta'mir".into()),
            principal: principal.into(),
            has_markup: false,
            incurred_on: None,
            installments,
            first_due_on: "2026-11-15".into(),
            friction_necessity: Some(true),
            friction_alternative: Some(true),
        }
    }

    #[test]
    fn rejasiz_qarz_saqlanmaydi_va_daromadsiz_xonadonda_stop() {
        let db = database();
        assert!(matches!(
            add_loan(&db, NOW, loan_input("TAKEN", "1 200 000", 0)),
            Err(SessionError::Domain(DomainError::RepaymentPlanRequired))
        ));
        let check = check_borrow(
            &db,
            NOW,
            BorrowCheckInputDto {
                principal: "1 200 000".into(),
                installments: 12,
            },
        )
        .expect("tekshiruv");
        assert_eq!(check.verdict, "STOP", "daromad yo'q — to'xtash");
        assert_eq!(check.monthly_burden.minor, "10000000");
    }

    #[test]
    fn qarz_tolovlari_va_qarzsiz_kun() {
        let db = database();
        let view = add_loan(&db, NOW, loan_input("TAKEN", "1 200 000", 12)).expect("qo'shildi");
        assert_eq!(view.taken.len(), 1);
        assert_eq!(view.taken[0].borrow_verdict.as_deref(), Some("STOP"));
        assert_eq!(view.taken[0].next_due_on.as_deref(), Some("2026-11-15"));
        assert_eq!(view.debt_free_day.as_deref(), Some("2027-10-15"));
        let id = view.taken[0].id.clone();

        let after = pay(
            &db,
            NOW,
            LoanPaymentInputDto {
                loan_id: id.clone(),
                amount: "150 000".into(),
                paid_on: None,
            },
        )
        .expect("to'landi");
        assert_eq!(after.taken[0].outstanding.minor, "105000000");
        assert_eq!(after.taken[0].next_due_on.as_deref(), Some("2026-12-15"));
        assert!(matches!(
            pay(
                &db,
                NOW,
                LoanPaymentInputDto {
                    loan_id: id,
                    amount: "2 000 000".into(),
                    paid_on: None
                }
            ),
            Err(SessionError::Domain(DomainError::DebtOverpaid))
        ));
    }

    #[test]
    fn tilxat_loan_kelishuvi_8_9_bilan_ochiladi() {
        let db = database();
        let view = add_loan(&db, NOW, loan_input("TAKEN", "1 200 000", 12)).expect("qo'shildi");
        let iou = create_iou(&db, NOW, &view.taken[0].id).expect("tilxat");
        assert_eq!(iou.kind, "LOAN");
        assert_eq!(
            iou.completeness.missing,
            vec![8],
            "faqat hakam qoladi: {:?}",
            iou.completeness
        );
        assert!(iou.answers.has_schedule);
        let again = create_iou(&db, NOW, &view.taken[0].id).expect("mavjud tilxat");
        assert_eq!(again.id, iou.id);
        let listed = overview(&db, NOW).expect("ro'yxat");
        assert_eq!(
            listed.taken[0].agreement_id.as_deref(),
            Some(iou.id.as_str())
        );
    }

    #[test]
    fn bergan_qarzda_foiz_yoq_va_friction_saqlanmaydi() {
        let db = database();
        let mut input = loan_input("GIVEN", "500 000", 5);
        input.has_markup = true;
        let view = add_loan(&db, NOW, input).expect("qo'shildi");
        assert!(
            !view.given[0].has_markup,
            "bergan qarzda ustama belgisi bo'lmaydi"
        );
        assert_eq!(view.given[0].borrow_verdict, None);
        assert_eq!(view.total_receivable.minor, "50000000");
    }
}
