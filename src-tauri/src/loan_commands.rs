//! D9 IPC commandlari: qarzlar, tekshiruv, to'lov, tilxat. Qoidalar — [`loans`] xizmatida.

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::dto::{
    AgreementDto, BorrowCheckDto, BorrowCheckInputDto, LoanInputDto, LoanPaymentInputDto, LoansDto,
    SellableInputDto,
};
use crate::loans;
use crate::session::Session;

/// Qarzlar sahifasi.
#[tauri::command]
#[specta::specta]
pub async fn get_loans(session: State<'_, Arc<Session>>) -> Result<LoansDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| loans::overview(db, OffsetDateTime::now_utc())))
        .await
}

/// Qarz oldidan tekshiruv (saqlanmaydi).
#[tauri::command]
#[specta::specta]
pub async fn check_borrow(
    session: State<'_, Arc<Session>>,
    input: BorrowCheckInputDto,
) -> Result<BorrowCheckDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| loans::check_borrow(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Qarz qo'shadi (reja bilan).
#[tauri::command]
#[specta::specta]
pub async fn add_loan(
    session: State<'_, Arc<Session>>,
    input: LoanInputDto,
) -> Result<LoansDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| loans::add_loan(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// To'lov yozadi.
#[tauri::command]
#[specta::specta]
pub async fn pay_loan(
    session: State<'_, Arc<Session>>,
    input: LoanPaymentInputDto,
) -> Result<LoansDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| loans::pay(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Tilxat (LOAN kelishuvi) yaratadi yoki mavjudini qaytaradi.
#[tauri::command]
#[specta::specta]
pub async fn create_iou(
    session: State<'_, Arc<Session>>,
    loan_id: String,
) -> Result<AgreementDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| loans::create_iou(db, OffsetDateTime::now_utc(), &loan_id))
    })
    .await
}

/// Yopish tartibi strategiyasi (`SNOWBALL | AVALANCHE`).
#[tauri::command]
#[specta::specta]
pub async fn set_payoff_strategy(
    session: State<'_, Arc<Session>>,
    strategy: String,
) -> Result<LoansDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            loans::set_payoff_strategy(db, OffsetDateTime::now_utc(), &strategy)
        })
    })
    .await
}

/// Sotiladigan buyum qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_sellable_item(
    session: State<'_, Arc<Session>>,
    input: SellableInputDto,
) -> Result<LoansDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| loans::add_sellable(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Buyum sotildi.
#[tauri::command]
#[specta::specta]
pub async fn mark_sellable_sold(
    session: State<'_, Arc<Session>>,
    id: String,
) -> Result<LoansDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| loans::mark_sellable_sold(db, OffsetDateTime::now_utc(), &id))
    })
    .await
}

/// Buyumni olib tashlaydi.
#[tauri::command]
#[specta::specta]
pub async fn remove_sellable_item(
    session: State<'_, Arc<Session>>,
    id: String,
) -> Result<LoansDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| loans::remove_sellable(db, OffsetDateTime::now_utc(), &id))
    })
    .await
}
