//! D10 xizmati: amortizatsiya simulyatori (annuitet, differensial, qat'iy ustama), odatiy va
//! tezlashtirilgan grafik, «qarzsiz kun», `DEBT_RECOVERY` rejimi va 70/20/10 taqsimoti.
//! Hisob domen'da (`amortization`, `recovery`); bu yerda faqat kirish/chiqish.

use domain::DomainError;
use domain::amortization::{
    Schedule, annuity_schedule, differentiated_schedule, fixed_markup_schedule,
};
use domain::loans::add_months;
use domain::recovery::recovery_split;
use money::Money;
use storage::{Database, IncomeRepo, RescueRepo};
use time::format_description::well_known::Iso8601;
use time::{Date, OffsetDateTime};

use crate::dto::{
    MoneyDto, PayoffDto, PayoffInputDto, RecoveryDto, RecoveryInputDto, ScheduleDto, ScheduleRowDto,
};
use crate::finance::{self, CURRENCY, Context, date_text, parse_money};
use crate::session::SessionError;

const MODE_KEY: &str = "budget_mode";
const SPLIT_KEY: &str = "recovery_split_bp";
const DEFAULT_SPLIT: [u64; 3] = [7_000, 2_000, 1_000];

fn parse_date(text: &str) -> Result<Date, SessionError> {
    Date::parse(text, &Iso8601::DATE).map_err(|_| DomainError::InvalidDay.into())
}

fn schedule_dto(schedule: &Schedule, start: Date) -> Result<ScheduleDto, SessionError> {
    let mut rows = Vec::with_capacity(schedule.rows.len());
    for row in &schedule.rows {
        let date = add_months(start, i64::from(row.month) - 1)?;
        rows.push(ScheduleRowDto {
            month: row.month,
            date: date_text(date),
            interest: MoneyDto::of(row.interest),
            principal: MoneyDto::of(row.principal),
            extra: MoneyDto::of(row.extra),
            balance: MoneyDto::of(row.balance),
        });
    }
    let last = rows
        .last()
        .map_or_else(|| date_text(start), |row| row.date.clone());
    Ok(ScheduleDto {
        payment: MoneyDto::of(schedule.payment),
        months: schedule.months,
        total_interest: MoneyDto::of(schedule.total_interest),
        debt_free_day: last,
        rows,
    })
}

fn build(input: &PayoffInputDto, extra: Money) -> Result<Schedule, SessionError> {
    let principal = parse_money(&input.principal)?;
    let term = i64::from(input.term_months);
    let schedule = match input.schedule_type.as_str() {
        "ANNUITY" => annuity_schedule(principal, i64::from(input.annual_bp), term, extra)?,
        "DIFFERENTIATED" => {
            differentiated_schedule(principal, i64::from(input.annual_bp), term, extra)?
        }
        "FIXED_MARKUP" => {
            let markup = if input.markup.trim().is_empty() {
                Money::zero(CURRENCY)
            } else {
                parse_money(&input.markup)?
            };
            // Qat'iy ustamada qo'shimcha to'lov muddatni qisqartirmaydi (ustama kelishilgan) — faqat odatiy jadval.
            fixed_markup_schedule(principal, markup, term)?
        }
        _ => return Err(DomainError::InvalidRule.into()),
    };
    Ok(schedule)
}

/// Simulyatsiya: odatiy (qo'shimcha to'lovsiz) va tezlashtirilgan grafik.
pub fn simulate(
    db: &Database,
    now: OffsetDateTime,
    input: PayoffInputDto,
) -> Result<PayoffDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let start = match input.start_date.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => parse_date(text)?,
        None => add_months(ctx.today, 1)?,
    };
    let extra = if input.extra_per_month.trim().is_empty() {
        Money::zero(CURRENCY)
    } else {
        parse_money(&input.extra_per_month)?
    };
    if extra.minor() < 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    let standard = build(&input, Money::zero(CURRENCY))?;
    let accelerated = build(&input, extra)?;
    let interest_saved = standard
        .total_interest
        .checked_sub(accelerated.total_interest)
        .map_err(DomainError::from)?;
    Ok(PayoffDto {
        months_saved: standard.months.saturating_sub(accelerated.months),
        interest_saved: MoneyDto::of(interest_saved),
        standard: schedule_dto(&standard, start)?,
        accelerated: schedule_dto(&accelerated, start)?,
    })
}

fn month_income(db: &Database, ctx: &Context) -> Result<Money, SessionError> {
    let period = domain::calendar::month_of(ctx.today, ctx.household.month_start_day)
        .ok_or(DomainError::InvalidDay)?;
    let incomes = IncomeRepo::new(db.connection()).list_in_range(&ctx.household.id, period)?;
    Ok(Money::new(
        incomes
            .iter()
            .fold(0_i64, |acc, i| acc.saturating_add(i.amount.minor())),
        CURRENCY,
    ))
}

fn stored_split(db: &Database, ctx: &Context) -> Result<[u64; 3], SessionError> {
    let repo = RescueRepo::new(db.connection());
    let Some(text) = repo.setting(&ctx.household.id, SPLIT_KEY)? else {
        return Ok(DEFAULT_SPLIT);
    };
    let parts: Vec<u64> = text
        .split(',')
        .filter_map(|p| p.trim().parse().ok())
        .collect();
    match parts.as_slice() {
        [a, b, c] => Ok([*a, *b, *c]),
        _ => Ok(DEFAULT_SPLIT),
    }
}

fn recovery_dto(db: &Database, ctx: &Context) -> Result<RecoveryDto, SessionError> {
    let repo = RescueRepo::new(db.connection());
    let mode = repo
        .setting(&ctx.household.id, MODE_KEY)?
        .unwrap_or_else(|| "STANDARD".to_owned());
    let split = stored_split(db, ctx)?;
    let income = month_income(db, ctx)?;
    let parts = recovery_split(income, split)?;
    Ok(RecoveryDto {
        mode,
        split_bp: split
            .iter()
            .map(|v| u32::try_from(*v).unwrap_or(u32::MAX))
            .collect(),
        income: MoneyDto::of(income),
        parts: parts.iter().map(|p| MoneyDto::of(*p)).collect(),
    })
}

/// Rejim va taqsimot (shu oy daromadi bo'yicha qismlar).
pub fn recovery(db: &Database, now: OffsetDateTime) -> Result<RecoveryDto, SessionError> {
    let ctx = finance::context(db, now)?;
    recovery_dto(db, &ctx)
}

/// Rejim va ulushlarni saqlaydi. Jamg'arma ulushini 0 qilib bo'lmaydi (domen qoidasi).
pub fn set_recovery(
    db: &Database,
    now: OffsetDateTime,
    input: RecoveryInputDto,
) -> Result<RecoveryDto, SessionError> {
    let ctx = finance::context(db, now)?;
    if input.mode != "STANDARD" && input.mode != "DEBT_RECOVERY" {
        return Err(DomainError::InvalidRule.into());
    }
    let split: [u64; 3] = match input.split_bp.as_slice() {
        [a, b, c] => [u64::from(*a), u64::from(*b), u64::from(*c)],
        _ => return Err(DomainError::SplitNotHundred.into()),
    };
    // Qoidalar (100 %, jamg'arma ≥ 1 %) domen'da: noto'g'ri ulush saqlanmaydi.
    recovery_split(Money::new(10_000, CURRENCY), split)?;
    let repo = RescueRepo::new(db.connection());
    repo.set_setting(&ctx.household.id, MODE_KEY, &input.mode)?;
    repo.set_setting(
        &ctx.household.id,
        SPLIT_KEY,
        &format!("{},{},{}", split[0], split[1], split[2]),
    )?;
    recovery_dto(db, &ctx)
}

#[cfg(test)]
mod tests {
    use super::*;
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([61; 32])).expect("xotirada baza")
    }

    #[test]
    fn annuitet_qoshimcha_tolov_muddat_va_foizni_qisqartiradi() {
        let db = database();
        let result = simulate(
            &db,
            NOW,
            PayoffInputDto {
                schedule_type: "ANNUITY".into(),
                principal: "39 000 000".into(),
                annual_bp: 2_400,
                markup: String::new(),
                term_months: 14,
                extra_per_month: "1 600 000".into(),
                start_date: Some("2026-11-15".into()),
            },
        )
        .expect("simulyatsiya");
        // amort-002 vektori bilan bir xil raqamlar.
        assert_eq!(result.standard.months, 14);
        assert_eq!(result.accelerated.months, 9);
        assert_eq!(result.months_saved, 5);
        assert_eq!(result.interest_saved.minor, "213048906");
        assert_eq!(result.accelerated.debt_free_day, "2027-07-15");
        assert_eq!(result.standard.rows[0].date, "2026-11-15");
    }

    #[test]
    fn rejim_va_taqsimot_saqlanadi_jamgarma_nol_bolmaydi() {
        let db = database();
        let initial = recovery(&db, NOW).expect("rejim");
        assert_eq!(initial.mode, "STANDARD");
        assert_eq!(initial.split_bp, vec![7_000, 2_000, 1_000]);
        assert!(matches!(
            set_recovery(
                &db,
                NOW,
                RecoveryInputDto {
                    mode: "DEBT_RECOVERY".into(),
                    split_bp: vec![8_000, 2_000, 0]
                }
            ),
            Err(SessionError::Domain(DomainError::SavingsBelowMinimum))
        ));
        let saved = set_recovery(
            &db,
            NOW,
            RecoveryInputDto {
                mode: "DEBT_RECOVERY".into(),
                split_bp: vec![6_000, 3_000, 1_000],
            },
        )
        .expect("saqlandi");
        assert_eq!(saved.mode, "DEBT_RECOVERY");
        assert_eq!(saved.split_bp, vec![6_000, 3_000, 1_000]);
    }
}
