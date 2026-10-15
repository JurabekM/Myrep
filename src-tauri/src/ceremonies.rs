//! D11 xizmati: marosim rejalovchisi — byudjet qatorlari, moliyalash manbalari, stsenariylarni taqqoslash,
//! oilaviy muhokama darvozasi, to'yona o'rniga jamg'arma maqsadi, smeta PDF.
//!
//! Qoida (SPEC 2D.8): `DEBT` manbali qator bo'lsa, marosim muhokamasiz `CONFIRMED` bo'lmaydi — bu domen'da
//! (`domain::ceremony::confirm`), bu yerda faqat chaqiriladi. Pul hisoblari domen va `money`da.

use domain::DomainError;
use domain::ceremony::{BudgetLine, CeremonyPlan, CeremonyStatus, FundingSource, confirm};
use domain::emergency::emergency_target;
use money::Money;
use storage::{CeremonyRepo, CeremonyRow, Database, LineRow, ScenarioRow, StorageError};
use time::format_description::well_known::Iso8601;
use time::{Date, OffsetDateTime};

use crate::dto::{
    CeremoniesDto, CeremonyDto, CeremonyGoalInputDto, CeremonyInputDto, CeremonyLineDto,
    CeremonyLineInputDto, ConfirmCeremonyInputDto, MoneyDto, ScenarioDto, ScenarioInputDto,
};
use crate::finance::{self, CURRENCY, Context, DEVICE_ID, UuidV7, date_text, parse_money};
use crate::session::SessionError;
use crate::{payoff, reserve};

const KINDS: [&str; 5] = ["TOY", "BESHIK", "SUNNAT", "MARAKA", "OTHER"];
const FUNDINGS: [&str; 4] = ["SAVINGS", "FAMILY", "EXPECTED_GIFTS", "DEBT"];
const STATUS_PLANNED: &str = "PLANNED";
const STATUS_CONFIRMED: &str = "CONFIRMED";
const DISCLAIMER: &str = "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.";

fn parse_date(text: &str) -> Result<Date, SessionError> {
    Date::parse(text, &Iso8601::DATE).map_err(|_| DomainError::InvalidDay.into())
}

fn funding_of(code: &str) -> Result<FundingSource, SessionError> {
    match code {
        "SAVINGS" => Ok(FundingSource::Savings),
        "FAMILY" => Ok(FundingSource::FamilyContribution),
        "EXPECTED_GIFTS" => Ok(FundingSource::ExpectedGift),
        "DEBT" => Ok(FundingSource::Debt),
        _ => Err(DomainError::InvalidRule.into()),
    }
}

/// Manba nomi (PDF uchun).
fn funding_label(code: &str) -> &'static str {
    match code {
        "SAVINGS" => "Jamg'arma",
        "FAMILY" => "Oila hissasi",
        "EXPECTED_GIFTS" => "Kutilayotgan to'yona",
        _ => "Qarz",
    }
}

/// Tur nomi (PDF uchun).
fn kind_label(code: &str) -> &'static str {
    match code {
        "TOY" => "To'y",
        "BESHIK" => "Beshik to'yi",
        "SUNNAT" => "Sunnat to'yi",
        "MARAKA" => "Ma'raka",
        _ => "Marosim",
    }
}

fn budget_line(line: &LineRow) -> Result<BudgetLine, SessionError> {
    Ok(BudgetLine {
        name: line.name.clone(),
        quantity: line.quantity,
        unit_price: line.unit_price,
        funding: funding_of(&line.funding)?,
    })
}

/// Stsenariydan domen rejasi (muhokama belgisi marosimdan).
fn plan_of(scenario: &ScenarioRow, discussed: bool) -> Result<CeremonyPlan, SessionError> {
    let mut plan = CeremonyPlan::new();
    for line in &scenario.lines {
        plan.lines.push(budget_line(line)?);
    }
    if discussed {
        plan.record_family_discussion();
    }
    Ok(plan)
}

fn part_of(plan: &CeremonyPlan, funding: FundingSource) -> Result<Money, SessionError> {
    let mut total = Money::zero(CURRENCY);
    for line in plan.lines.iter().filter(|l| l.funding == funding) {
        total = total
            .checked_add(line.total()?)
            .map_err(DomainError::from)?;
    }
    Ok(total)
}

/// `numerator / denominator` yuqoriga yaxlitlangan oylar soni; maxraj 0 bo'lsa — yo'q.
fn months_ceil(numerator: Money, denominator: Money) -> Result<Option<u32>, SessionError> {
    if denominator.minor() <= 0 {
        return Ok(None);
    }
    if numerator.minor() <= 0 {
        return Ok(Some(0));
    }
    // Yuqoriga yaxlitlash: (a + b - 1) / b (i128 — toshmaydi).
    let ceil = (i128::from(numerator.minor()) + i128::from(denominator.minor()) - 1)
        / i128::from(denominator.minor());
    Ok(Some(u32::try_from(ceil).unwrap_or(u32::MAX)))
}

/// `numerator / denominator` pastga yaxlitlangan (to'liq oylar); maxraj 0 bo'lsa — yo'q.
fn months_floor(numerator: Money, denominator: Money) -> Option<u32> {
    if denominator.minor() <= 0 || numerator.minor() < 0 {
        return None;
    }
    let floor = i128::from(numerator.minor()) / i128::from(denominator.minor());
    Some(u32::try_from(floor).unwrap_or(u32::MAX))
}

/// O'rtacha oylik zarur xarajat (ma'lumotli oylar bo'yicha); ma'lumot bo'lmasa — yo'q.
fn monthly_needs(db: &Database, ctx: &Context) -> Result<Option<Money>, SessionError> {
    let months = reserve::monthly_essentials(db, ctx)?;
    Ok(emergency_target(CURRENCY, &months, 1)?)
}

struct Gauges {
    debt_budget: Money,
    monthly_needs: Option<Money>,
}

fn gauges(db: &Database, ctx: &Context) -> Result<Gauges, SessionError> {
    let parts = payoff::split_parts(db, ctx)?;
    Ok(Gauges {
        debt_budget: parts[1],
        monthly_needs: monthly_needs(db, ctx)?,
    })
}

fn scenario_dto(
    scenario: &ScenarioRow,
    discussed: bool,
    gauges: &Gauges,
) -> Result<ScenarioDto, SessionError> {
    let plan = plan_of(scenario, discussed)?;
    let total = plan.total()?;
    let debt_part = plan.debt_part()?;
    let mut lines = Vec::with_capacity(scenario.lines.len());
    for line in &scenario.lines {
        lines.push(CeremonyLineDto {
            id: line.id.clone(),
            name: line.name.clone(),
            quantity: u32::try_from(line.quantity).unwrap_or(u32::MAX),
            unit_price: MoneyDto::of(line.unit_price),
            funding: line.funding.clone(),
            total: MoneyDto::of(budget_line(line)?.total()?),
        });
    }
    // Muqobil maqsad: shu pulga necha TO'LIQ oylik zarur xarajat chiqadi (pastga).
    let months_of_needs = gauges
        .monthly_needs
        .and_then(|needs| months_floor(total, needs));
    Ok(ScenarioDto {
        id: scenario.id.clone(),
        name: scenario.name.clone(),
        guests: scenario.guests,
        days: scenario.days,
        lines,
        total: MoneyDto::of(total),
        debt_part: MoneyDto::of(debt_part),
        savings_part: MoneyDto::of(part_of(&plan, FundingSource::Savings)?),
        family_part: MoneyDto::of(part_of(&plan, FundingSource::FamilyContribution)?),
        gifts_part: MoneyDto::of(part_of(&plan, FundingSource::ExpectedGift)?),
        has_debt: debt_part.minor() > 0,
        payoff_months: if debt_part.minor() > 0 {
            months_ceil(debt_part, gauges.debt_budget)?
        } else {
            None
        },
        months_of_needs,
    })
}

fn ceremony_dto(
    db: &Database,
    row: &CeremonyRow,
    gauges: &Gauges,
) -> Result<CeremonyDto, SessionError> {
    let scenarios = CeremonyRepo::new(db.connection()).scenarios(&row.id)?;
    let mut dtos = Vec::with_capacity(scenarios.len());
    for scenario in &scenarios {
        dtos.push(scenario_dto(scenario, row.family_discussed, gauges)?);
    }
    Ok(CeremonyDto {
        id: row.id.clone(),
        kind: row.kind.clone(),
        title: row.title.clone(),
        event_on: row.event_on.map(date_text),
        status: row.status.clone(),
        family_discussed: row.family_discussed,
        chosen_scenario_id: row.chosen_scenario_id.clone(),
        goal_name: row.goal_name.clone(),
        goal_target: row.goal_target.map(MoneyDto::of),
        has_debt: dtos.iter().any(|s| s.has_debt),
        scenarios: dtos,
    })
}

/// Marosimlar sahifasi.
pub fn overview(db: &Database, now: OffsetDateTime) -> Result<CeremoniesDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let gauges = gauges(db, &ctx)?;
    let rows = CeremonyRepo::new(db.connection()).list(&ctx.household.id)?;
    let mut items = Vec::with_capacity(rows.len());
    for row in &rows {
        items.push(ceremony_dto(db, row, &gauges)?);
    }
    Ok(CeremoniesDto { items })
}

fn load(db: &Database, id: &str) -> Result<CeremonyRow, SessionError> {
    CeremonyRepo::new(db.connection())
        .find(id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))
}

/// Tasdiqlangan marosim o'zgartirilmaydi.
fn ensure_planned(row: &CeremonyRow) -> Result<(), SessionError> {
    if row.status == STATUS_CONFIRMED {
        return Err(DomainError::AgreementLocked.into());
    }
    Ok(())
}

/// Yangi marosim.
pub fn create(
    db: &Database,
    now: OffsetDateTime,
    input: CeremonyInputDto,
) -> Result<CeremoniesDto, SessionError> {
    let ctx = finance::context(db, now)?;
    if !KINDS.contains(&input.kind.as_str()) {
        return Err(DomainError::InvalidRule.into());
    }
    let event_on = match input.event_on.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => Some(parse_date(text)?),
        None => None,
    };
    CeremonyRepo::new(db.connection()).insert(&CeremonyRow {
        id: domain::IdGen::next_id(&UuidV7),
        household_id: ctx.household.id.clone(),
        kind: input.kind,
        title: domain::validate_name(&input.title)?,
        event_on,
        status: STATUS_PLANNED.to_owned(),
        family_discussed: false,
        chosen_scenario_id: None,
        goal_name: None,
        goal_target: None,
        created_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    })?;
    overview(db, now)
}

/// Stsenariy qo'shadi.
pub fn add_scenario(
    db: &Database,
    now: OffsetDateTime,
    input: ScenarioInputDto,
) -> Result<CeremoniesDto, SessionError> {
    let row = load(db, &input.ceremony_id)?;
    ensure_planned(&row)?;
    if input.days == 0 {
        return Err(DomainError::InvalidRule.into());
    }
    CeremonyRepo::new(db.connection()).insert_scenario(
        &ScenarioRow {
            id: domain::IdGen::next_id(&UuidV7),
            ceremony_id: row.id,
            name: domain::validate_name(&input.name)?,
            guests: input.guests,
            days: input.days,
            lines: Vec::new(),
        },
        now,
    )?;
    overview(db, now)
}

/// Byudjet qatori qo'shadi.
pub fn add_line(
    db: &Database,
    now: OffsetDateTime,
    input: CeremonyLineInputDto,
) -> Result<CeremoniesDto, SessionError> {
    let repo = CeremonyRepo::new(db.connection());
    let ceremony_id = repo
        .scenario_ceremony(&input.scenario_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    ensure_planned(&load(db, &ceremony_id)?)?;
    if !FUNDINGS.contains(&input.funding.as_str()) {
        return Err(DomainError::InvalidRule.into());
    }
    if input.quantity == 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    let unit_price = parse_money(&input.unit_price)?;
    if unit_price.minor() < 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    repo.insert_line(
        &input.scenario_id,
        &LineRow {
            id: domain::IdGen::next_id(&UuidV7),
            name: domain::validate_name(&input.name)?,
            quantity: u64::from(input.quantity),
            unit_price,
            funding: input.funding,
        },
    )?;
    overview(db, now)
}

/// Qatorni o'chiradi.
pub fn remove_line(
    db: &Database,
    now: OffsetDateTime,
    line_id: &str,
) -> Result<CeremoniesDto, SessionError> {
    let repo = CeremonyRepo::new(db.connection());
    let ceremony_id = repo
        .line_ceremony(line_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    ensure_planned(&load(db, &ceremony_id)?)?;
    repo.delete_line(line_id)?;
    overview(db, now)
}

/// «Buni qarzsiz qanday o'tkazamiz?» — oilaviy muhokama o'tkazilganini qayd etadi.
pub fn discuss(
    db: &Database,
    now: OffsetDateTime,
    id: &str,
) -> Result<CeremoniesDto, SessionError> {
    let row = load(db, id)?;
    ensure_planned(&row)?;
    CeremonyRepo::new(db.connection()).set_discussed(&row.id, now)?;
    overview(db, now)
}

/// Tasdiqlaydi: tanlangan stsenariy; qarz qatori bo'lsa, muhokama shart (domen).
pub fn confirm_ceremony(
    db: &Database,
    now: OffsetDateTime,
    input: ConfirmCeremonyInputDto,
) -> Result<CeremoniesDto, SessionError> {
    let row = load(db, &input.id)?;
    ensure_planned(&row)?;
    let repo = CeremonyRepo::new(db.connection());
    let scenario = repo
        .scenarios(&row.id)?
        .into_iter()
        .find(|s| s.id == input.scenario_id)
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    let mut plan = plan_of(&scenario, row.family_discussed)?;
    confirm(&mut plan)?;
    if plan.status != CeremonyStatus::Confirmed {
        return Err(DomainError::InvalidRule.into());
    }
    repo.set_status(&row.id, STATUS_CONFIRMED, Some(&scenario.id), now)?;
    overview(db, now)
}

/// To'yona o'rniga jamg'arma maqsadi (`Goal`, MVP'da virtual).
pub fn set_goal(
    db: &Database,
    now: OffsetDateTime,
    input: CeremonyGoalInputDto,
) -> Result<CeremoniesDto, SessionError> {
    let row = load(db, &input.id)?;
    let target = parse_money(&input.target)?;
    if target.minor() <= 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    CeremonyRepo::new(db.connection()).set_goal(
        &row.id,
        &domain::validate_name(&input.name)?,
        target,
        now,
    )?;
    overview(db, now)
}

fn pretty_date(date: Date) -> String {
    date.format(&time::macros::format_description!(
        "[day].[month].[year]"
    ))
    .unwrap_or_default()
}

/// Smeta PDF baytlari (tanlangan stsenariy bo'yicha).
pub fn pdf(
    db: &Database,
    now: OffsetDateTime,
    id: &str,
    scenario_id: &str,
) -> Result<Vec<u8>, SessionError> {
    let ctx = finance::context(db, now)?;
    let row = load(db, id)?;
    let gauges = gauges(db, &ctx)?;
    let scenario = CeremonyRepo::new(db.connection())
        .scenarios(&row.id)?
        .into_iter()
        .find(|s| s.id == scenario_id)
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    let dto = scenario_dto(&scenario, row.family_discussed, &gauges)?;
    let mut subtitle = kind_label(&row.kind).to_owned();
    if let Some(date) = row.event_on {
        subtitle.push_str(&format!(" · {}", pretty_date(date)));
    }
    subtitle.push_str(&format!(
        " · {}: {} kun, {} kishi",
        scenario.name, scenario.days, scenario.guests
    ));
    let lines = dto
        .lines
        .iter()
        .map(|line| {
            [
                line.name.clone(),
                format!("{} × {}", line.quantity, line.unit_price.formatted),
                funding_label(&line.funding).to_owned(),
                line.total.formatted.clone(),
            ]
        })
        .collect();
    let summary = vec![
        ("Umumiy".to_owned(), dto.total.formatted.clone()),
        ("Jamg'arma".to_owned(), dto.savings_part.formatted.clone()),
        ("Oila hissasi".to_owned(), dto.family_part.formatted.clone()),
        (
            "Kutilayotgan to'yona".to_owned(),
            dto.gifts_part.formatted.clone(),
        ),
        ("Qarz".to_owned(), dto.debt_part.formatted.clone()),
    ];
    let status = if row.status == STATUS_CONFIRMED {
        "tasdiqlangan"
    } else {
        "rejalashtirilmoqda"
    };
    let note = if dto.has_debt {
        if row.family_discussed {
            format!("Qarz qatori bor: oilaviy muhokama o'tkazilgan. Holat: {status}.")
        } else {
            format!(
                "Qarz qatori bor: «Buni qarzsiz qanday o'tkazamiz?» — oilaviy muhokama hali o'tkazilmagan. Holat: {status}."
            )
        }
    } else {
        format!("Qarzsiz reja. Holat: {status}.")
    };
    let estimate = pdf::CeremonyEstimate {
        title: row.title.clone(),
        subtitle,
        generated_on: pretty_date(ctx.today),
        lines,
        summary,
        note,
        disclaimer: DISCLAIMER.to_owned(),
    };
    Ok(pdf::render_estimate(&estimate)?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([71; 32])).expect("xotirada baza")
    }

    fn line(scenario_id: &str, name: &str, quantity: u32, price: &str, funding: &str) -> CeremonyLineInputDto {
        CeremonyLineInputDto {
            scenario_id: scenario_id.into(),
            name: name.into(),
            quantity,
            unit_price: price.into(),
            funding: funding.into(),
        }
    }

    fn setup(db: &Database) -> (String, String, String) {
        let view = create(
            db,
            NOW,
            CeremonyInputDto {
                kind: "TOY".into(),
                title: "O'g'limizning to'yi".into(),
                event_on: Some("2027-03-12".into()),
            },
        )
        .expect("marosim");
        let id = view.items[0].id.clone();
        let view = add_scenario(
            db,
            NOW,
            ScenarioInputDto {
                ceremony_id: id.clone(),
                name: "Katta".into(),
                guests: 200,
                days: 3,
            },
        )
        .expect("stsenariy 1");
        let big = view.items[0].scenarios[0].id.clone();
        let view = add_scenario(
            db,
            NOW,
            ScenarioInputDto {
                ceremony_id: id.clone(),
                name: "Ixcham".into(),
                guests: 100,
                days: 1,
            },
        )
        .expect("stsenariy 2");
        let small = view.items[0].scenarios[1].id.clone();
        add_line(db, NOW, line(&big, "Osh", 200, "45 000", "SAVINGS")).expect("qator");
        add_line(db, NOW, line(&big, "Sarpo", 1, "8 000 000", "DEBT")).expect("qator");
        add_line(db, NOW, line(&small, "Osh", 100, "45 000", "SAVINGS")).expect("qator");
        (id, big, small)
    }

    #[test]
    fn stsenariylar_taqqoslanadi_va_qarz_qismi_hisoblanadi() {
        let db = database();
        let (id, _, _) = setup(&db);
        let view = overview(&db, NOW).expect("ro'yxat");
        let ceremony = &view.items[0];
        assert_eq!(ceremony.id, id);
        assert!(ceremony.has_debt);
        let big = &ceremony.scenarios[0];
        assert_eq!(big.total.minor, "1700000000");
        assert_eq!(big.debt_part.minor, "800000000");
        assert!(big.has_debt);
        assert_eq!(big.payoff_months, None, "daromad yo'q — qarz ulushi 0, muddat yo'q");
        let small = &ceremony.scenarios[1];
        assert_eq!(small.total.minor, "450000000");
        assert!(!small.has_debt);
        assert_eq!(small.lines[0].total.minor, "450000000");
    }

    #[test]
    fn qarzli_stsenariy_muhokamasiz_tasdiqlanmaydi() {
        let db = database();
        let (id, big, small) = setup(&db);
        let err = confirm_ceremony(
            &db,
            NOW,
            ConfirmCeremonyInputDto {
                id: id.clone(),
                scenario_id: big.clone(),
            },
        );
        assert!(matches!(
            err,
            Err(SessionError::Domain(DomainError::FamilyDiscussionRequired))
        ));
        // Qarzsiz stsenariy darhol tasdiqlanadi — lekin biz avval muhokama orqali qarzlisini sinaymiz.
        discuss(&db, NOW, &id).expect("muhokama");
        let view = confirm_ceremony(
            &db,
            NOW,
            ConfirmCeremonyInputDto {
                id: id.clone(),
                scenario_id: big.clone(),
            },
        )
        .expect("tasdiqlandi");
        assert_eq!(view.items[0].status, "CONFIRMED");
        assert_eq!(view.items[0].chosen_scenario_id.as_deref(), Some(big.as_str()));
        // Tasdiqlangan reja o'zgarmaydi.
        assert!(matches!(
            add_line(&db, NOW, line(&small, "Xonanda", 1, "1 000 000", "FAMILY")),
            Err(SessionError::Domain(DomainError::AgreementLocked))
        ));
    }

    #[test]
    fn qarzsiz_stsenariy_darhol_tasdiqlanadi_va_pdf_chiqadi() {
        let db = database();
        let (id, _, small) = setup(&db);
        let bytes = pdf(&db, NOW, &id, &small).expect("smeta");
        assert!(bytes.starts_with(b"%PDF-"));
        let view = confirm_ceremony(
            &db,
            NOW,
            ConfirmCeremonyInputDto {
                id: id.clone(),
                scenario_id: small,
            },
        )
        .expect("tasdiqlandi");
        assert_eq!(view.items[0].status, "CONFIRMED");
    }

    #[test]
    fn maqsad_va_qator_ochirish() {
        let db = database();
        let (id, big, _) = setup(&db);
        let view = set_goal(
            &db,
            NOW,
            CeremonyGoalInputDto {
                id: id.clone(),
                name: "Yosh oila uchun boshpana".into(),
                target: "20 000 000".into(),
            },
        )
        .expect("maqsad");
        assert_eq!(view.items[0].goal_name.as_deref(), Some("Yosh oila uchun boshpana"));
        assert_eq!(
            view.items[0].goal_target.as_ref().map(|m| m.minor.as_str()),
            Some("2000000000")
        );
        let debt_line = view.items[0].scenarios[0]
            .lines
            .iter()
            .find(|l| l.funding == "DEBT")
            .expect("qarz qatori")
            .id
            .clone();
        let view = remove_line(&db, NOW, &debt_line).expect("o'chirildi");
        let scenario = view.items[0]
            .scenarios
            .iter()
            .find(|s| s.id == big)
            .expect("stsenariy");
        assert!(!scenario.has_debt);
        assert!(!view.items[0].has_debt);
    }
}
