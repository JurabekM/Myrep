//! D7 IPC commandlari: byudjet holati, obunalar, konvertlar, «Qutqarilgan pul» va «Kelajagim»ga o'tkazish.
//! Qoida: har command — argumentni o'qish → [`budget`] funksiyasi → DTO. Biznes mantiq bu yerda emas.

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::budget;
use crate::commands::{ApiError, run_blocking};
use crate::dto::{
    BaselineInputDto, BudgetDto, EnvelopeInputDto, SubscriptionInputDto, TransferInputDto,
};
use crate::session::Session;

/// Byudjet sahifasi: qutqarilgan pul, obunalar, konvertlar.
#[tauri::command]
#[specta::specta]
pub async fn get_budget(session: State<'_, Arc<Session>>) -> Result<BudgetDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| budget::overview(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Obuna qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_subscription(
    session: State<'_, Arc<Session>>,
    input: SubscriptionInputDto,
) -> Result<BudgetDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| budget::add_subscription(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Obunani «ishlatdim» deb belgilaydi.
#[tauri::command]
#[specta::specta]
pub async fn mark_subscription_used(
    session: State<'_, Arc<Session>>,
    id: String,
) -> Result<BudgetDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session
            .with_database(|db| budget::mark_subscription_used(db, OffsetDateTime::now_utc(), &id))
    })
    .await
}

/// Obunani bekor qiladi (tejam bekor qilingan kundan boshlanadi).
#[tauri::command]
#[specta::specta]
pub async fn cancel_subscription(
    session: State<'_, Arc<Session>>,
    id: String,
) -> Result<BudgetDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| budget::cancel_subscription(db, OffsetDateTime::now_utc(), &id))
    })
    .await
}

/// Konvert qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_envelope(
    session: State<'_, Arc<Session>>,
    input: EnvelopeInputDto,
) -> Result<BudgetDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| budget::add_envelope(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Konvert qoldig'ini shu hafta uchun «Qutqarilgan pul» ga yozadi.
#[tauri::command]
#[specta::specta]
pub async fn close_envelope_week(
    session: State<'_, Arc<Session>>,
    envelope_id: String,
) -> Result<BudgetDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            budget::close_envelope_week(db, OffsetDateTime::now_utc(), &envelope_id)
        })
    })
    .await
}

/// «Qutqarilgan pul»dan «Kelajagim»ga o'tkazadi.
#[tauri::command]
#[specta::specta]
pub async fn transfer_to_vault_from_rescue(
    session: State<'_, Arc<Session>>,
    input: TransferInputDto,
) -> Result<BudgetDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            budget::transfer_to_vault_from_rescue(db, OffsetDateTime::now_utc(), &input.amount)
        })
    })
    .await
}

/// Bazaviy davrni tanlaydi (joriy davrdan oldingi davr).
#[tauri::command]
#[specta::specta]
pub async fn set_baseline_period(
    session: State<'_, Arc<Session>>,
    input: BaselineInputDto,
) -> Result<BudgetDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            budget::set_baseline_period(db, OffsetDateTime::now_utc(), &input.period_start)
        })
    })
    .await
}
