//! D6 commandlari: oila a'zolari, toifalar, xarajatlar, havas chegarasi, «Juma shirinligi», odatlar,
//! oila kengashi va PDF bayonnoma. PIN'lar `Zeroizing` ichida, loglarda va xatolarda yo'q.

use domain::{
    date_from_str, date_to_string, Category, Expense, MemberRole, MoneyOwner, Necessity,
    PaymentChannel, ScheduledTreat,
};
use money::{format_money, parse_amount, Locale, Money};
use serde::{Deserialize, Serialize};
use services::{
    categories::{self, NewCategory},
    council,
    expenses::{self, NewExpense},
    habits, havas, local_date, members, treats, Ctx, ServiceError, YearMonth,
};
use specta::Type;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;
use zeroize::Zeroizing;

use crate::{
    commands::{with_session, AppSession, CommandError},
    dto::MoneyDto,
};

const LOCALE: Locale = Locale::Uz;

fn m(v: Money) -> MoneyDto {
    MoneyDto::from_money(v, LOCALE)
}

fn amount(ctx: &Ctx, text: &str) -> Result<Money, ServiceError> {
    Ok(parse_amount(text, ctx.currency)?)
}

fn month(text: &str) -> Result<YearMonth, ServiceError> {
    YearMonth::parse(text)
}

fn day(text: &str) -> Result<domain::Date, ServiceError> {
    date_from_str(text).map_err(|_| ServiceError::Invalid("sana YYYY-MM-DD bo'lishi kerak"))
}

fn ds(d: domain::Date) -> String {
    date_to_string(d).unwrap_or_default()
}

fn u32_of(n: usize) -> u32 {
    u32::try_from(n).unwrap_or(u32::MAX)
}

fn necessity(text: &str) -> Result<Necessity, ServiceError> {
    Necessity::parse(text).ok_or(ServiceError::Invalid("toifani tanlang (Zarur/Kerak/Havas)"))
}

// ---------------------------------------------------------------- a'zolar

#[derive(Debug, Serialize, Type)]
pub struct MemberDto {
    pub id: String,
    pub name: String,
    /// `ADULT` | `CHILD` | `VIEWER`.
    pub role: String,
    pub has_pin: bool,
}

#[tauri::command]
#[specta::specta]
pub fn list_members(state: State<'_, AppSession>) -> Result<Vec<MemberDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            members::list(db.conn(), ctx)?
                .into_iter()
                .map(|x| {
                    Ok(MemberDto {
                        has_pin: members::has_pin(db.conn(), ctx, &x.meta.id)?,
                        id: x.meta.id,
                        name: x.display_name,
                        role: x.role.as_str().to_owned(),
                    })
                })
                .collect()
        })
    })
}

/// Yangi a'zo. PIN berilsa, shu zahoti o'rnatiladi.
#[tauri::command]
#[specta::specta]
pub fn add_member(
    name: String,
    role: String,
    pin: Option<String>,
    state: State<'_, AppSession>,
) -> Result<MemberDto, CommandError> {
    let pin = pin.map(Zeroizing::new);
    with_session(&state, |s| {
        let kdf = s.kdf();
        s.run(|db, env, ctx| {
            let role = MemberRole::parse(&role).ok_or(ServiceError::Invalid("rolni tanlang"))?;
            let member = members::add(db, env, ctx, &name, role)?;
            if let Some(p) = &pin {
                members::set_pin(db, env, ctx, &member.meta.id, p, kdf)?;
            }
            Ok(MemberDto {
                has_pin: pin.is_some(),
                id: member.meta.id,
                name: member.display_name,
                role: member.role.as_str().to_owned(),
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn change_member_pin(
    member_id: String,
    old_pin: Option<String>,
    new_pin: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    let (old_pin, new_pin) = (old_pin.map(Zeroizing::new), Zeroizing::new(new_pin));
    with_session(&state, |s| {
        let kdf = s.kdf();
        s.run(|db, env, ctx| {
            members::change_pin(
                db,
                env,
                ctx,
                &member_id,
                old_pin.as_ref().map(|p| p.as_str()),
                &new_pin,
                kdf,
            )
        })
    })
}

// ---------------------------------------------------------------- toifalar

#[derive(Debug, Serialize, Type)]
pub struct CategoryDto {
    pub id: String,
    pub name: String,
    /// `ZARUR` | `KERAK` | `HAVAS` | `None` (belgilanmagan).
    pub necessity: Option<String>,
    pub is_charity: bool,
    pub is_habit: bool,
    /// Oxirgi o'zgartirgan a'zo va sana: «Dilnoza, 2026-10-09».
    pub last_change: Option<String>,
}

fn category_dto(c: Category, last_change: Option<String>) -> CategoryDto {
    CategoryDto {
        id: c.meta.id,
        name: c.name,
        necessity: c.necessity.map(|n| n.as_str().to_owned()),
        is_charity: c.is_charity,
        is_habit: c.is_habit,
        last_change,
    }
}

#[tauri::command]
#[specta::specta]
pub fn list_categories(state: State<'_, AppSession>) -> Result<Vec<CategoryDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            let history = categories::history(db.conn(), ctx, None)?;
            let names: Vec<(String, String)> = members::list(db.conn(), ctx)?
                .into_iter()
                .map(|x| (x.meta.id, x.display_name))
                .collect();
            Ok(categories::list(db.conn(), ctx)?
                .into_iter()
                .map(|c| {
                    let last = history
                        .iter()
                        .rev()
                        .find(|h| h.category_id == c.meta.id)
                        .map(|h| {
                            let who = names
                                .iter()
                                .find(|(id, _)| *id == h.changed_by)
                                .map_or("?", |(_, n)| n.as_str());
                            format!("{who}, {}", ds(local_date(h.meta.created_at)))
                        });
                    category_dto(c, last)
                })
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_necessity(
    category_id: String,
    necessity_text: String,
    member_id: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            categories::set_necessity(
                db,
                env,
                ctx,
                &category_id,
                necessity(&necessity_text)?,
                &member_id,
            )
        })
    })
}

#[derive(Debug, Deserialize, Type)]
pub struct CategoryInput {
    pub name: String,
    pub necessity: Option<String>,
    pub is_habit: bool,
}

#[tauri::command]
#[specta::specta]
pub fn add_category(
    input: CategoryInput,
    state: State<'_, AppSession>,
) -> Result<CategoryDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let nec = input.necessity.as_deref().map(necessity).transpose()?;
            let c = categories::add(
                db,
                env,
                ctx,
                NewCategory {
                    name: input.name,
                    necessity: nec,
                    owner: None::<MoneyOwner>,
                    is_charity: false,
                    is_habit: input.is_habit,
                },
            )?;
            Ok(category_dto(c, None))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_habit(
    category_id: String,
    is_habit: bool,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| categories::set_habit(db, env, ctx, &category_id, is_habit))
    })
}

// ---------------------------------------------------------------- xarajatlar

#[derive(Debug, Deserialize, Type)]
pub struct ExpenseInput {
    /// `YYYY-MM-DD`.
    pub date: String,
    pub category_id: String,
    pub amount: String,
    /// `CASH` | `CARD`.
    pub channel: String,
    pub note: Option<String>,
    /// `None` — kategoriya toifasi.
    pub necessity: Option<String>,
    pub is_gift: bool,
    pub is_ostentation: bool,
    pub funded_by_debt: bool,
}

#[derive(Debug, Serialize, Type)]
pub struct ExpenseDto {
    pub id: String,
    pub date: String,
    pub category_id: String,
    pub amount: MoneyDto,
    pub channel: String,
    pub note: Option<String>,
    pub is_gift: bool,
    pub is_ostentation: bool,
    pub funded_by_debt: bool,
}

fn expense_dto(e: &Expense) -> ExpenseDto {
    ExpenseDto {
        id: e.meta.id.clone(),
        date: ds(e.spent_on),
        category_id: e.category_id.clone(),
        amount: m(e.amount),
        channel: e.payment_channel.as_str().to_owned(),
        note: e.note.clone(),
        is_gift: e.is_gift == Some(true),
        is_ostentation: e.is_ostentation == Some(true),
        funded_by_debt: e.funded_by_debt == Some(true),
    }
}

/// «Hafta varag'i»: barcha qatorlar bitta tranzaksiyada.
#[tauri::command]
#[specta::specta]
pub fn add_expenses(
    items: Vec<ExpenseInput>,
    state: State<'_, AppSession>,
) -> Result<u32, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let parsed = items
                .into_iter()
                .map(|i| {
                    Ok(NewExpense {
                        date: day(&i.date)?,
                        category_id: i.category_id,
                        amount: amount(ctx, &i.amount)?,
                        channel: PaymentChannel::parse(&i.channel)
                            .ok_or(ServiceError::Invalid("kanalni tanlang"))?,
                        note: i.note,
                        necessity: i.necessity.as_deref().map(necessity).transpose()?,
                        is_gift: i.is_gift,
                        is_ostentation: i.is_ostentation,
                        funded_by_debt: i.funded_by_debt,
                        member_id: None,
                    })
                })
                .collect::<Result<Vec<_>, ServiceError>>()?;
            Ok(u32_of(expenses::add_many(db, env, ctx, parsed)?))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn list_expenses(
    from: String,
    to: String,
    state: State<'_, AppSession>,
) -> Result<Vec<ExpenseDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(
                expenses::list_range(db.conn(), ctx, day(&from)?, day(&to)?)?
                    .iter()
                    .map(expense_dto)
                    .collect(),
            )
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_expense(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| expenses::remove(db, env, ctx, &id))
    })
}

/// Shu izoh bilan oxirgi yozilgan xarajat kategoriyasi (avtomatik to'ldirish uchun).
#[tauri::command]
#[specta::specta]
pub fn suggest_category(
    note: String,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| expenses::suggest_category(db.conn(), ctx, &note))
    })
}

// ---------------------------------------------------------------- havas chegarasi

#[derive(Debug, Serialize, Type)]
pub struct PendingLimitDto {
    pub limit_id: String,
    pub amount: MoneyDto,
    pub consented: Vec<String>,
    /// Hali rozi bo'lmagan kattalar: (ID, ism).
    pub missing: Vec<MemberRef>,
}

#[derive(Debug, Serialize, Type)]
pub struct MemberRef {
    pub id: String,
    pub name: String,
}

#[derive(Debug, Serialize, Type)]
pub struct HavasDto {
    pub month: String,
    /// Faqat barcha kattalar rozi bo'lgan chegara.
    pub limit: Option<MoneyDto>,
    pub pending: Option<PendingLimitDto>,
    pub spent: MoneyDto,
    /// `OK` | `NEAR` | `OVER`; chegara faol bo'lmasa `None`.
    pub state: Option<String>,
    pub used_bp: Option<u32>,
    pub ostentation: MoneyDto,
    pub debt_funded: MoneyDto,
    pub charity: MoneyDto,
    pub gifts_excluded: MoneyDto,
}

fn havas_dto(r: havas::Report) -> HavasDto {
    HavasDto {
        month: r.month.text(),
        limit: r.limit.map(m),
        pending: r.pending.map(|p| PendingLimitDto {
            limit_id: p.limit_id,
            amount: m(p.amount),
            consented: p.consented.into_iter().map(|x| x.display_name).collect(),
            missing: p
                .missing
                .into_iter()
                .map(|x| MemberRef {
                    id: x.meta.id,
                    name: x.display_name,
                })
                .collect(),
        }),
        spent: m(r.spent),
        state: r.status.map(|s| {
            match s.state {
                domain::HavasState::Ok => "OK",
                domain::HavasState::Near => "NEAR",
                domain::HavasState::Over => "OVER",
            }
            .to_owned()
        }),
        used_bp: r
            .status
            .map(|s| u32::try_from(s.used_bp.max(0)).unwrap_or(u32::MAX)),
        ostentation: m(r.ostentation),
        debt_funded: m(r.debt_funded),
        charity: m(r.charity),
        gifts_excluded: m(r.gifts_excluded),
    }
}

#[tauri::command]
#[specta::specta]
pub fn havas_report(
    month_text: String,
    state: State<'_, AppSession>,
) -> Result<HavasDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(havas_dto(havas::report(
                db.conn(),
                ctx,
                month(&month_text)?,
            )?))
        })
    })
}

/// Yangi chegara taklif qiladi: taklif qiluvchi o'z PIN'ini kiritadi.
#[tauri::command]
#[specta::specta]
pub fn propose_limit(
    member_id: String,
    pin: String,
    amount_text: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    let pin = Zeroizing::new(pin);
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            havas::propose(db, env, ctx, &member_id, &pin, amount(ctx, &amount_text)?)?;
            Ok(())
        })
    })
}

/// Har bir kattalar o'z PIN'i bilan rozilik beradi.
#[tauri::command]
#[specta::specta]
pub fn consent_limit(
    limit_id: String,
    member_id: String,
    pin: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    let pin = Zeroizing::new(pin);
    with_session(&state, |s| {
        s.run(|db, env, ctx| havas::consent(db, env, ctx, &limit_id, &member_id, &pin))
    })
}

// ---------------------------------------------------------------- juma shirinligi

#[derive(Debug, Serialize, Type)]
pub struct TreatDto {
    pub id: String,
    pub name: String,
    pub amount: MoneyDto,
    /// 1 = dushanba ... 7 = yakshanba.
    pub weekday: u32,
    pub active: bool,
    pub due_today: bool,
    pub logged_today: bool,
}

fn treat_dto(t: &ScheduledTreat, today: &[treats::TreatToday]) -> TreatDto {
    let due = today.iter().find(|x| x.treat.meta.id == t.meta.id);
    TreatDto {
        id: t.meta.id.clone(),
        name: t.name.clone(),
        amount: m(t.amount),
        weekday: u32::from(t.weekday),
        active: t.active,
        due_today: due.is_some(),
        logged_today: due.is_some_and(|d| d.logged_today),
    }
}

#[tauri::command]
#[specta::specta]
pub fn list_treats(state: State<'_, AppSession>) -> Result<Vec<TreatDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let today = local_date(env.clock.now());
            let due = treats::due_today(db.conn(), ctx, today)?;
            Ok(treats::list(db.conn(), ctx)?
                .iter()
                .map(|t| treat_dto(t, &due))
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_treat(
    name: String,
    amount_text: String,
    weekday: u32,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let wd = u8::try_from(weekday).map_err(|_| ServiceError::Invalid("hafta kuni 1..7"))?;
            treats::add(db, env, ctx, &name, amount(ctx, &amount_text)?, wd)?;
            Ok(())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_treat_active(
    id: String,
    active: bool,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| treats::set_active(db, env, ctx, &id, active))
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_treat(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| treats::remove(db, env, ctx, &id))
    })
}

#[tauri::command]
#[specta::specta]
pub fn log_treat(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| treats::log(db, env, ctx, &id))
    })
}

// ---------------------------------------------------------------- odatlar

#[derive(Debug, Serialize, Type)]
pub struct HabitDto {
    pub category_id: String,
    pub name: String,
    pub window_total: MoneyDto,
    pub week: MoneyDto,
    pub month: MoneyDto,
    pub year: MoneyDto,
}

#[tauri::command]
#[specta::specta]
pub fn habit_stats(state: State<'_, AppSession>) -> Result<Vec<HabitDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let today = local_date(env.clock.now());
            Ok(habits::stats(db.conn(), ctx, today)?
                .into_iter()
                .map(|h| HabitDto {
                    category_id: h.category_id,
                    name: h.name,
                    window_total: m(h.window_total),
                    week: m(h.projection.week),
                    month: m(h.projection.month),
                    year: m(h.projection.year),
                })
                .collect())
        })
    })
}

// ---------------------------------------------------------------- oila kengashi

/// Bayonnomani PDF qiladi va foydalanuvchi **OS «saqlash» oynasida** tanlagan joyga yozadi.
/// Fayl faqat Rust tomonida yoziladi (frontendga fayl tizimi ruxsati berilmaydi).
/// Foydalanuvchi bekor qilsa `None`; muvaffaqiyatda saqlangan fayl nomi.
#[tauri::command]
#[specta::specta]
pub async fn export_council_pdf(
    month_text: String,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    let ym_text = month_text.clone();
    let bytes = with_session(&state, |s| {
        s.run(|db, env, ctx| council::minutes_pdf(db.conn(), env, ctx, month(&ym_text)?))
    })?;
    let suggested = format!("bayonnoma-{month_text}.pdf");
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("PDF", &["pdf"])
        .set_file_name(&suggested)
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let mut path = file.into_path().map_err(|_| CommandError::Internal {
        message: "fayl yo'li noto'g'ri".into(),
    })?;
    if path
        .extension()
        .is_none_or(|e| !e.eq_ignore_ascii_case("pdf"))
    {
        path.set_extension("pdf");
    }
    std::fs::write(&path, bytes).map_err(|_| CommandError::Internal {
        message: "faylni yozib bo'lmadi".into(),
    })?;
    Ok(path.file_name().map(|n| n.to_string_lossy().into_owned()))
}

// Ishlatilmaydigan importlar uchun: format_money keyingi vazifalarda kerak bo'ladi.
const _: fn() = || {
    let _ = format_money;
};
