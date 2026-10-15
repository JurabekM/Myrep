//! D6 IPC commandlari: toifalar, xarajatlar, havas chegarasi va rozilik, a'zolar, Juma shirinligi.
//! Qoida: har command — argumentni o'qish → [`family`] funksiyasi → DTO. Biznes mantiq bu yerda emas.

use std::sync::Arc;

use tauri::{Manager, State};
use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::dto::{
    CategoryDto, ExpenseDto, ExpenseInputDto, HavasLimitDto, MemberDto, MemberInputDto,
    MonthSummaryDto, OdatHabitDto, TreatDto, TreatInputDto,
};
use crate::family;
use crate::session::Session;

/// Oylik xulosa: toifalar, sadaqa, sovg'alar, obro' va qarz bayroqlari.
#[tauri::command]
#[specta::specta]
pub async fn get_month_summary(
    session: State<'_, Arc<Session>>,
) -> Result<MonthSummaryDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| family::month_summary(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Shu oyning xarajatlari.
#[tauri::command]
#[specta::specta]
pub async fn list_month_expenses(
    session: State<'_, Arc<Session>>,
) -> Result<Vec<ExpenseDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| family::month_expense_list(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Xarajat qo'shadi (toifa kategoriyadan olinadi).
#[tauri::command]
#[specta::specta]
pub async fn add_expense(
    session: State<'_, Arc<Session>>,
    input: ExpenseInputDto,
) -> Result<ExpenseDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| family::add_expense(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Kategoriyaning toifasini o'zgartiradi (tarix yoziladi).
#[tauri::command]
#[specta::specta]
pub async fn set_category_necessity(
    session: State<'_, Arc<Session>>,
    category_id: String,
    necessity: String,
) -> Result<CategoryDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            family::set_category_necessity(db, OffsetDateTime::now_utc(), &category_id, &necessity)
        })
    })
    .await
}

/// Havas chegarasi holati.
#[tauri::command]
#[specta::specta]
pub async fn get_havas_limit(session: State<'_, Arc<Session>>) -> Result<HavasLimitDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| family::havas_limit(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Havas chegarasini o'rnatadi (yangi rozilik talab qilinadi).
#[tauri::command]
#[specta::specta]
pub async fn set_havas_limit(
    session: State<'_, Arc<Session>>,
    amount: String,
) -> Result<HavasLimitDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| family::set_havas_limit(db, OffsetDateTime::now_utc(), &amount))
    })
    .await
}

/// Kattaning roziligi: uning o'z PIN'i bilan.
#[tauri::command]
#[specta::specta]
pub async fn consent_havas_limit(
    session: State<'_, Arc<Session>>,
    member_id: String,
    pin: String,
) -> Result<HavasLimitDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            family::consent_havas_limit(db, OffsetDateTime::now_utc(), &member_id, &pin)
        })
    })
    .await
}

/// Oila a'zolari.
#[tauri::command]
#[specta::specta]
pub async fn list_members(session: State<'_, Arc<Session>>) -> Result<Vec<MemberDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| family::members(db, OffsetDateTime::now_utc())))
        .await
}

/// Oila a'zosini qo'shadi. Kattaga PIN majburiy.
#[tauri::command]
#[specta::specta]
pub async fn add_member(
    session: State<'_, Arc<Session>>,
    input: MemberInputDto,
) -> Result<MemberDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| family::add_member(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Kattaning PIN'ini o'rnatadi yoki almashtiradi. PIN bor bo'lsa, joriy PIN majburiy (faqat PIN egasi).
#[tauri::command]
#[specta::specta]
pub async fn set_member_pin(
    session: State<'_, Arc<Session>>,
    member_id: String,
    current_pin: Option<String>,
    new_pin: String,
) -> Result<MemberDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            family::set_member_pin(
                db,
                OffsetDateTime::now_utc(),
                &member_id,
                current_pin.as_deref(),
                &new_pin,
            )
        })
    })
    .await
}

/// Juma shirinligi ro'yxati.
#[tauri::command]
#[specta::specta]
pub async fn list_treats(session: State<'_, Arc<Session>>) -> Result<Vec<TreatDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| family::treats(db, OffsetDateTime::now_utc())))
        .await
}

/// Juma shirinligini qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_treat(
    session: State<'_, Arc<Session>>,
    input: TreatInputDto,
) -> Result<TreatDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| family::add_treat(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Hafta varag'i: bir nechta xarajatni birdan kiritadi (qisman yozilish yo'q).
#[tauri::command]
#[specta::specta]
pub async fn add_expenses(
    session: State<'_, Arc<Session>>,
    rows: Vec<ExpenseInputDto>,
) -> Result<Vec<ExpenseDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| family::add_expenses(db, OffsetDateTime::now_utc(), rows))
    })
    .await
}

/// Odatlar ro'yxati: oyiga va yiliga jami (statistika).
#[tauri::command]
#[specta::specta]
pub async fn list_habits(session: State<'_, Arc<Session>>) -> Result<Vec<OdatHabitDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| family::habits(db, OffsetDateTime::now_utc())))
        .await
}

/// Yangi odat qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_habit(
    session: State<'_, Arc<Session>>,
    name: String,
) -> Result<OdatHabitDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| family::add_habit(db, OffsetDateTime::now_utc(), &name))
    })
    .await
}

/// Oila kengashi bayonnomasi (PDF): ilova ma'lumot papkasiga yoziladi; yo'li qaytariladi.
#[tauri::command]
#[specta::specta]
pub async fn create_council_report(
    app: tauri::AppHandle,
    session: State<'_, Arc<Session>>,
) -> Result<String, ApiError> {
    let dir = app
        .path()
        .app_data_dir()
        .map_err(|_| ApiError::Internal)?
        .join("reports");
    let session = session.inner().clone();
    let bytes = run_blocking(move || {
        session.with_database(|db| crate::report::council_pdf(db, OffsetDateTime::now_utc()))
    })
    .await?;
    std::fs::create_dir_all(&dir).map_err(|_| ApiError::Internal)?;
    let stamp = OffsetDateTime::now_utc()
        .format(&time::macros::format_description!(
            "[year][month][day]-[hour][minute][second]"
        ))
        .unwrap_or_default();
    let path = dir.join(format!("bayonnoma-{stamp}.pdf"));
    std::fs::write(&path, bytes).map_err(|_| ApiError::Internal)?;
    Ok(path.display().to_string())
}
