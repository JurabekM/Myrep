//! D6 oila va havas (SPEC 2B.1–2B.4, 2B.8): uch toifa, xarajatlar, havas chegarasi va rozilik,
//! a'zolar PIN'i, Juma shirinligi.
//!
//! Qoidalar `domain`da, saqlash `storage`da; bu yerda ular ulanadi va DTO tayyorlanadi. Pul hisobi
//! Rust'da: frontend faqat ko'rsatadi.

use domain::calendar::{DateRange, month_of, tashkent_date};
use domain::limit::{self, LimitLevel, SpendLine};
use domain::{
    Category, CategoryKey, DomainError, Expense, ExpenseDraft, HavasLimit, LimitConsent, Member,
    MemberRole, Necessity, ScheduledTreat, TaskTrigger,
};
use money::Money;
use security::{
    KdfParams, SecurityError, create_member_verifier, retry_after_secs, verify_member_pin,
};
use storage::{
    CategoryRepo, Database, ExpenseRepo, LimitRepo, MemberRepo, PinRepo, StorageError, TreatRepo,
};
use time::OffsetDateTime;

use crate::content;
use crate::dto::{
    AdultConsentDto, CategoryDto, ExpenseDto, ExpenseInputDto, HavasLimitDto, MemberDto,
    MemberInputDto, MoneyDto, MonthSummaryDto, TreatDto, TreatInputDto,
};
use crate::finance::{self, CURRENCY, Context, DEVICE_ID, UuidV7, date_text, parse_money};
use crate::session::SessionError;

/// PIN hosil qilish parametri: ishlab chiqarishda `RECOMMENDED` (sekin, xavfsiz), testlarda tez.
fn kdf_params() -> KdfParams {
    if cfg!(test) {
        KdfParams::FAST_FOR_TESTS
    } else {
        KdfParams::RECOMMENDED
    }
}

/// Toifa kodini domen qiymatiga aylantiradi. Noma'lum kod — `INVALID_RULE`.
fn necessity_of(code: &str) -> Result<Necessity, SessionError> {
    Necessity::from_code(code).ok_or_else(|| DomainError::InvalidRule.into())
}

/// Joriy oyning davri (xonadon oylik kuni bo'yicha).
fn current_month(ctx: &Context) -> Result<DateRange, SessionError> {
    month_of(ctx.today, ctx.household.month_start_day).ok_or_else(|| DomainError::InvalidDay.into())
}

/// Summalar yig'indisi (minor birlikda, to'yinish bilan — panic yo'q).
fn sum<'a>(amounts: impl Iterator<Item = &'a Money>) -> Money {
    let minor = amounts.fold(0_i64, |acc, money| acc.saturating_add(money.minor()));
    Money::new(minor, CURRENCY)
}

/// Xarajat uchun havas hisobi qatori. Sadaqa — kategoriya kaliti bo'yicha.
fn spend_line(expense: &Expense, categories: &[Category]) -> SpendLine {
    SpendLine {
        necessity: expense.necessity,
        is_gift: expense.is_gift,
        is_sadaqa: is_sadaqa(expense, categories),
        amount: expense.amount,
    }
}

fn is_sadaqa(expense: &Expense, categories: &[Category]) -> bool {
    expense.category_id.as_deref().is_some_and(|id| {
        categories
            .iter()
            .any(|c| c.id == id && c.system_key == Some(CategoryKey::Sadaqa))
    })
}

fn category_name(category_id: Option<&str>, categories: &[Category]) -> Option<String> {
    category_id.and_then(|id| {
        categories
            .iter()
            .find(|c| c.id == id)
            .map(|c| c.name.clone())
    })
}

fn expense_dto(expense: &Expense, categories: &[Category]) -> ExpenseDto {
    ExpenseDto {
        id: expense.id.clone(),
        occurred_on: date_text(expense.occurred_on),
        amount: MoneyDto::of(expense.amount),
        category_name: category_name(expense.category_id.as_deref(), categories),
        necessity: expense.necessity.code().to_owned(),
        note: expense.note.clone(),
        is_gift: expense.is_gift,
        is_ostentation: expense.is_ostentation,
        funded_by_debt: expense.funded_by_debt,
    }
}

/// Shu oyning xarajatlari va havas sarfi. Qayta ishlatiladigan yordamchi.
fn month_expenses(
    db: &Database,
    ctx: &Context,
    period: DateRange,
) -> Result<(Vec<Expense>, Vec<Category>), SessionError> {
    let expenses = ExpenseRepo::new(db.connection()).list_in_range(&ctx.household.id, period)?;
    let categories = CategoryRepo::new(db.connection()).list(&ctx.household.id)?;
    Ok((expenses, categories))
}

/// Oylik xulosa: uch toifa, sadaqa, sovg'alar, obro' va qarz bayroqlari bo'yicha.
pub fn month_summary(db: &Database, now: OffsetDateTime) -> Result<MonthSummaryDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let period = current_month(&ctx)?;
    let (expenses, categories) = month_expenses(db, &ctx, period)?;
    let by = |necessity: Necessity| {
        sum(expenses
            .iter()
            .filter(|e| e.necessity == necessity)
            .map(|e| &e.amount))
    };
    let lines: Vec<SpendLine> = expenses
        .iter()
        .map(|e| spend_line(e, &categories))
        .collect();
    Ok(MonthSummaryDto {
        period_start: date_text(period.start),
        period_end: date_text(period.end),
        zarur: MoneyDto::of(by(Necessity::Zarur)),
        kerak: MoneyDto::of(by(Necessity::Kerak)),
        havas: MoneyDto::of(limit::spent_on_havas(&lines, CURRENCY)),
        sadaqa: MoneyDto::of(sum(expenses
            .iter()
            .filter(|e| is_sadaqa(e, &categories))
            .map(|e| &e.amount))),
        gifts: MoneyDto::of(sum(expenses
            .iter()
            .filter(|e| e.is_gift)
            .map(|e| &e.amount))),
        ostentation: MoneyDto::of(sum(expenses
            .iter()
            .filter(|e| e.is_ostentation)
            .map(|e| &e.amount))),
        funded_by_debt: MoneyDto::of(sum(expenses
            .iter()
            .filter(|e| e.funded_by_debt)
            .map(|e| &e.amount))),
    })
}

/// Shu oyning xarajatlari (yangi birinchi).
pub fn month_expense_list(
    db: &Database,
    now: OffsetDateTime,
) -> Result<Vec<ExpenseDto>, SessionError> {
    let ctx = finance::context(db, now)?;
    let period = current_month(&ctx)?;
    let (expenses, categories) = month_expenses(db, &ctx, period)?;
    Ok(expenses
        .iter()
        .map(|e| expense_dto(e, &categories))
        .collect())
}

/// Xarajat qo'shadi. Toifa kategoriyadan olinadi (kategoriyasiz — `KERAK`); `EXPENSE_RECORDED` hodisasi yoziladi.
pub fn add_expense(
    db: &Database,
    now: OffsetDateTime,
    input: ExpenseInputDto,
) -> Result<ExpenseDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let amount = parse_money(&input.amount)?;
    let categories = CategoryRepo::new(db.connection()).list(&ctx.household.id)?;
    let necessity = match input.category_id.as_deref() {
        Some(id) => categories
            .iter()
            .find(|c| c.id == id)
            .map(|c| c.necessity)
            .ok_or(StorageError::NotFound)?,
        None => Necessity::Kerak,
    };
    let expense = Expense::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        ExpenseDraft {
            member_id: ctx.owner_id.clone(),
            category_id: input.category_id,
            amount,
            occurred_on: ctx.today,
            note: input.note,
            necessity,
            is_gift: input.is_gift,
            is_ostentation: input.is_ostentation,
            funded_by_debt: input.funded_by_debt,
        },
        now,
        DEVICE_ID,
    )?;
    ExpenseRepo::new(db.connection()).insert(&expense)?;
    content::record_event(db, now, TaskTrigger::ExpenseRecorded)?;
    Ok(expense_dto(&expense, &categories))
}

fn category_dto_of(category: &Category) -> CategoryDto {
    CategoryDto {
        id: category.id.clone(),
        name: category.name.clone(),
        system_key: category.system_key.map(|k| k.code().to_owned()),
        necessity: category.necessity.code().to_owned(),
    }
}

/// Kategoriyaning toifasini o'zgartiradi. Tarix yoziladi (kim, qachon, qaysidan qaysiga).
pub fn set_category_necessity(
    db: &Database,
    now: OffsetDateTime,
    category_id: &str,
    code: &str,
) -> Result<CategoryDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let to = necessity_of(code)?;
    let categories = CategoryRepo::new(db.connection());
    let category = categories
        .list(&ctx.household.id)?
        .into_iter()
        .find(|c| c.id == category_id)
        .ok_or(StorageError::NotFound)?;
    let (updated, change) = category.change_necessity(
        to,
        &ctx.owner_id,
        &domain::IdGen::next_id(&UuidV7),
        now,
        DEVICE_ID,
    )?;
    categories.update_necessity(&updated)?;
    categories.insert_necessity_change(&change)?;
    Ok(category_dto_of(&updated))
}

/// Havas chegarasi holati: summa, sarf, daraja, kattalar roziligi.
pub fn havas_limit(db: &Database, now: OffsetDateTime) -> Result<HavasLimitDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let period = current_month(&ctx)?;
    let (expenses, categories) = month_expenses(db, &ctx, period)?;
    let lines: Vec<SpendLine> = expenses
        .iter()
        .map(|e| spend_line(e, &categories))
        .collect();
    let spent = limit::spent_on_havas(&lines, CURRENCY);
    let members = MemberRepo::new(db.connection()).list_for_household(&ctx.household.id)?;
    let adults: Vec<&Member> = members
        .iter()
        .filter(|m| m.role == MemberRole::Adult)
        .collect();
    let limit_row = LimitRepo::new(db.connection()).latest(&ctx.household.id)?;
    let consented: Vec<String> = match &limit_row {
        Some(row) => LimitRepo::new(db.connection()).consented_members(&row.id)?,
        None => Vec::new(),
    };
    let adult_ids: Vec<&str> = adults.iter().map(|m| m.id.as_str()).collect();
    let consented_ids: Vec<&str> = consented.iter().map(String::as_str).collect();
    let active = limit_row.is_some() && limit::is_active(&adult_ids, &consented_ids);
    let level = match &limit_row {
        Some(row) => match limit::level(spent, row.monthly) {
            LimitLevel::Ok => "OK",
            LimitLevel::Warning => "WARNING",
            LimitLevel::Reached => "REACHED",
        },
        None => "OK",
    };
    let mut adult_views = Vec::with_capacity(adults.len());
    for adult in &adults {
        let pin = PinRepo::new(db.connection()).find(&adult.id)?;
        adult_views.push(AdultConsentDto {
            member_id: adult.id.clone(),
            name: adult.name.clone(),
            consented: consented.contains(&adult.id),
            has_pin: pin.and_then(|p| p.verifier).is_some(),
        });
    }
    Ok(HavasLimitDto {
        limit: limit_row.as_ref().map(|row| MoneyDto::of(row.monthly)),
        spent: MoneyDto::of(spent),
        level: level.to_owned(),
        active,
        adults: adult_views,
    })
}

/// Yangi havas chegarasini o'rnatadi. Oldingi rozilik yangi chegaraga o'tmaydi: hammasi qayta roziligi kerak.
pub fn set_havas_limit(
    db: &Database,
    now: OffsetDateTime,
    amount: &str,
) -> Result<HavasLimitDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let monthly = parse_money(amount)?;
    let row = HavasLimit::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        monthly,
        now,
        DEVICE_ID,
    )?;
    LimitRepo::new(db.connection()).insert_limit(&row)?;
    havas_limit(db, now)
}

/// Kattaning roziligi: uning o'z PIN'i tekshiriladi. Noto'g'ri urinishlar hisoblanadi (lockout).
pub fn consent_havas_limit(
    db: &Database,
    now: OffsetDateTime,
    member_id: &str,
    pin: &str,
) -> Result<HavasLimitDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let limit_row = LimitRepo::new(db.connection())
        .latest(&ctx.household.id)?
        .ok_or(StorageError::NotFound)?;
    let member = MemberRepo::new(db.connection())
        .find(member_id)?
        .ok_or(StorageError::NotFound)?;
    if member.role != MemberRole::Adult {
        return Err(DomainError::InvalidRole.into());
    }
    let pins = PinRepo::new(db.connection());
    let state = pins.find(member_id)?.ok_or(StorageError::NotFound)?;
    let verifier = state.verifier.clone().ok_or(DomainError::PinNotSet)?;
    if let Some(failed_at) = state.failed_at
        && let Some(wait) = retry_after_secs(
            state.failed_attempts,
            failed_at.unix_timestamp(),
            now.unix_timestamp(),
        )
    {
        return Err(SecurityError::LockedOut {
            retry_after_secs: wait,
        }
        .into());
    }
    if !verify_member_pin(pin, &verifier, kdf_params())? {
        pins.record_failure(member_id, now)?;
        return Err(SecurityError::WrongPin.into());
    }
    pins.reset_failures(member_id)?;
    let limits = LimitRepo::new(db.connection());
    if !limits
        .consented_members(&limit_row.id)?
        .iter()
        .any(|id| id == member_id)
    {
        let consent = LimitConsent::create(
            &domain::IdGen::next_id(&UuidV7),
            &ctx.household.id,
            &limit_row.id,
            member_id,
            now,
            DEVICE_ID,
        )?;
        limits.insert_consent(&consent)?;
    }
    havas_limit(db, now)
}

/// Oila a'zolari va ularning PIN holati.
pub fn members(db: &Database, now: OffsetDateTime) -> Result<Vec<MemberDto>, SessionError> {
    let ctx = finance::context(db, now)?;
    let list = MemberRepo::new(db.connection()).list_for_household(&ctx.household.id)?;
    let mut out = Vec::with_capacity(list.len());
    for member in &list {
        let pin = PinRepo::new(db.connection()).find(&member.id)?;
        out.push(MemberDto {
            id: member.id.clone(),
            name: member.name.clone(),
            role: member.role.code().to_owned(),
            has_pin: pin.and_then(|p| p.verifier).is_some(),
        });
    }
    Ok(out)
}

/// A'zo qo'shadi. Kattaga PIN majburiy; PIN tekshiriladi va saqlanadi (tuz bilan hosil qilingan verifier).
pub fn add_member(
    db: &Database,
    now: OffsetDateTime,
    input: MemberInputDto,
) -> Result<MemberDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let role = match input.role.as_str() {
        "ADULT" => MemberRole::Adult,
        "CHILD" => MemberRole::Child,
        _ => return Err(DomainError::InvalidRole.into()),
    };
    let verifier = match (role, input.pin.as_deref()) {
        (MemberRole::Adult, Some(pin)) => Some(create_member_verifier(pin, kdf_params())?),
        (MemberRole::Adult, None) => return Err(DomainError::PinNotSet.into()),
        (MemberRole::Child, _) => None,
    };
    let member = Member::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        &input.name,
        role,
        now,
        DEVICE_ID,
    )?;
    MemberRepo::new(db.connection()).insert(&member)?;
    if let Some(verifier) = verifier {
        PinRepo::new(db.connection()).set_verifier(&member.id, &verifier)?;
    }
    Ok(MemberDto {
        id: member.id,
        name: member.name,
        role: role.code().to_owned(),
        has_pin: role == MemberRole::Adult,
    })
}

/// Kattaning PIN'ini o'rnatadi yoki almashtiradi (urinishlar hisobi nolga tushadi).
pub fn set_member_pin(
    db: &Database,
    member_id: &str,
    pin: &str,
) -> Result<MemberDto, SessionError> {
    let member = MemberRepo::new(db.connection())
        .find(member_id)?
        .ok_or(StorageError::NotFound)?;
    if member.role != MemberRole::Adult {
        return Err(DomainError::InvalidRole.into());
    }
    let verifier = create_member_verifier(pin, kdf_params())?;
    PinRepo::new(db.connection()).set_verifier(member_id, &verifier)?;
    Ok(MemberDto {
        id: member.id,
        name: member.name,
        role: member.role.code().to_owned(),
        has_pin: true,
    })
}

fn treat_dto(treat: &ScheduledTreat, today: time::Date) -> TreatDto {
    TreatDto {
        id: treat.id.clone(),
        name: treat.name.clone(),
        amount: MoneyDto::of(treat.amount),
        weekday: domain::treat::weekday_index(treat.weekday),
        due_today: treat.is_due_on(today),
    }
}

/// Juma shirinligi ro'yxati; bugun kuni belgilanadi.
pub fn treats(db: &Database, now: OffsetDateTime) -> Result<Vec<TreatDto>, SessionError> {
    let ctx = finance::context(db, now)?;
    let list = TreatRepo::new(db.connection()).list_treats(&ctx.household.id)?;
    Ok(list.iter().map(|t| treat_dto(t, ctx.today)).collect())
}

/// Juma shirinligini qo'shadi (hafta kuni va summa).
pub fn add_treat(
    db: &Database,
    now: OffsetDateTime,
    input: TreatInputDto,
) -> Result<TreatDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let weekday =
        domain::treat::weekday_from_index(input.weekday).ok_or(DomainError::InvalidRule)?;
    let amount = parse_money(&input.amount)?;
    let treat = ScheduledTreat::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        &input.name,
        amount,
        weekday,
        now,
        DEVICE_ID,
    )?;
    TreatRepo::new(db.connection()).insert_treat(&treat)?;
    Ok(treat_dto(&treat, tashkent_date(now)))
}

#[cfg(test)]
mod tests {
    #![allow(clippy::expect_used, clippy::unwrap_used)]

    use domain::CategoryKey;
    use security::SecretKey;
    use time::macros::datetime;

    use super::*;

    const OWNER_PIN: &str = "111111";
    const SPOUSE_PIN: &str = "222222";
    const WRONG_PIN: &str = "000000";

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([8; 32])).expect("xotirada baza")
    }

    fn thursday() -> OffsetDateTime {
        datetime!(2026-10-15 06:00 UTC)
    }

    fn owner_id(db: &Database) -> String {
        members(db, thursday())
            .expect("a'zolar")
            .into_iter()
            .find(|m| m.role == "ADULT")
            .expect("egasi")
            .id
    }

    fn category_id(db: &Database, key: CategoryKey) -> String {
        members(db, thursday()).expect("kategoriyalar uchun kontekst");
        CategoryRepo::new(db.connection())
            .list(
                &finance::context(db, thursday())
                    .expect("kontekst")
                    .household
                    .id,
            )
            .expect("kategoriyalar")
            .into_iter()
            .find(|c| c.system_key == Some(key))
            .expect("tizim kategoriyasi")
            .id
    }

    fn add_spouse(db: &Database) -> String {
        add_member(
            db,
            thursday(),
            MemberInputDto {
                name: "Dilshod".to_owned(),
                role: "ADULT".to_owned(),
                pin: Some(SPOUSE_PIN.to_owned()),
            },
        )
        .expect("katta qo'shilsin")
        .id
    }

    fn expense(db: &Database, amount: &str, category: &str, is_gift: bool) -> ExpenseDto {
        add_expense(
            db,
            thursday(),
            ExpenseInputDto {
                amount: amount.to_owned(),
                category_id: Some(category.to_owned()),
                note: None,
                is_gift,
                is_ostentation: false,
                funded_by_debt: false,
            },
        )
        .expect("xarajat")
    }

    fn minor_of(amount: &str) -> String {
        parse_money(amount).expect("summa").minor().to_string()
    }

    #[test]
    fn bir_kattaning_roziligi_chegarani_faollashtirmaydi() {
        let db = database();
        let owner = owner_id(&db);
        set_member_pin(&db, &owner, OWNER_PIN).expect("egasi PIN");
        let spouse = add_spouse(&db);
        set_havas_limit(&db, thursday(), "1 000 000").expect("chegara");

        let after_owner = consent_havas_limit(&db, thursday(), &owner, OWNER_PIN).expect("rozilik");
        assert!(!after_owner.active, "bitta kattaning roziligi yetarli emas");

        assert!(matches!(
            consent_havas_limit(&db, thursday(), &spouse, WRONG_PIN),
            Err(SessionError::Security(SecurityError::WrongPin))
        ));
        assert!(!havas_limit(&db, thursday()).expect("holat").active);

        let both = consent_havas_limit(&db, thursday(), &spouse, SPOUSE_PIN).expect("rozilik");
        assert!(both.active, "barcha kattalar rozi bo'lgach chegara faol");
    }

    #[test]
    fn uch_marta_notogri_pin_qulflaydi() {
        let db = database();
        let owner = owner_id(&db);
        set_member_pin(&db, &owner, OWNER_PIN).expect("egasi PIN");
        set_havas_limit(&db, thursday(), "500 000").expect("chegara");
        for _ in 0..3 {
            assert!(consent_havas_limit(&db, thursday(), &owner, WRONG_PIN).is_err());
        }
        assert!(matches!(
            consent_havas_limit(&db, thursday(), &owner, OWNER_PIN),
            Err(SessionError::Security(SecurityError::LockedOut { .. }))
        ));
    }

    #[test]
    fn pin_otmagan_katta_rozi_bololmaydi() {
        let db = database();
        let owner = owner_id(&db);
        set_havas_limit(&db, thursday(), "500 000").expect("chegara");
        assert!(matches!(
            consent_havas_limit(&db, thursday(), &owner, OWNER_PIN),
            Err(SessionError::Domain(DomainError::PinNotSet))
        ));
        assert!(matches!(
            add_member(
                &db,
                thursday(),
                MemberInputDto {
                    name: "Ali".to_owned(),
                    role: "ADULT".to_owned(),
                    pin: None
                },
            ),
            Err(SessionError::Domain(DomainError::PinNotSet))
        ));
    }

    #[test]
    fn sadaqa_va_sovga_havas_hisobiga_kirmaydi() {
        let db = database();
        let snacks = category_id(&db, CategoryKey::Snacks);
        let sadaqa = category_id(&db, CategoryKey::Sadaqa);
        // Sadaqa toifasini HAVAS qilib qo'yamiz: uni faqat sadaqa belgisi havas hisobidan chiqaradi.
        set_category_necessity(&db, thursday(), &sadaqa, "HAVAS").expect("toifa");

        expense(&db, "100 000", &snacks, false);
        expense(&db, "500 000", &sadaqa, false);
        expense(&db, "200 000", &snacks, true);

        let limit = havas_limit(&db, thursday()).expect("holat");
        assert_eq!(limit.spent.minor, minor_of("100 000"));

        let summary = month_summary(&db, thursday()).expect("xulosa");
        assert_eq!(summary.sadaqa.minor, minor_of("500 000"));
        assert_eq!(summary.gifts.minor, minor_of("200 000"));
    }

    #[test]
    fn toifa_ozgarishi_keyingi_xarajatga_tasir_qiladi() {
        let db = database();
        let snacks = category_id(&db, CategoryKey::Snacks);
        let changed = set_category_necessity(&db, thursday(), &snacks, "KERAK").expect("toifa");
        assert_eq!(changed.necessity, "KERAK");

        let created = expense(&db, "20 000", &snacks, false);
        assert_eq!(created.necessity, "KERAK");

        assert!(matches!(
            set_category_necessity(&db, thursday(), &snacks, "KERAK"),
            Err(SessionError::Domain(DomainError::NecessityUnchanged))
        ));
    }

    #[test]
    fn juma_shirinligi_bugun_kuni_belgilanadi() {
        let db = database();
        let friday = datetime!(2026-10-16 06:00 UTC);
        let treat = add_treat(
            &db,
            friday,
            TreatInputDto {
                name: "Juma shirinligi".to_owned(),
                amount: "50 000".to_owned(),
                weekday: 4,
            },
        )
        .expect("ritual");
        assert!(treat.due_today, "2026-10-16 — juma");
        let listed = treats(&db, datetime!(2026-10-17 06:00 UTC)).expect("ro'yxat");
        assert!(!listed[0].due_today, "shanba — ritual kuni emas");
    }
}
