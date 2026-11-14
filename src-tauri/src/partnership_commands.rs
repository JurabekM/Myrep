//! D12 IPC commandlari: sheriklik. Qoidalar — [`partnerships`] xizmatida.

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::dto::{
    BuyoutInputDto, BuyoutPaymentInputDto, ConsentInputDto, PartnershipInputDto, PartnershipsDto,
};
use crate::partnerships;
use crate::session::Session;

/// Sherikliklar ro'yxati.
#[tauri::command]
#[specta::specta]
pub async fn get_partnerships(
    session: State<'_, Arc<Session>>,
) -> Result<PartnershipsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| partnerships::list(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Yangi sheriklik (kelishuv qoralamasi bilan).
#[tauri::command]
#[specta::specta]
pub async fn create_partnership(
    session: State<'_, Arc<Session>>,
    input: PartnershipInputDto,
) -> Result<PartnershipsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| partnerships::create(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Buyout shartlari.
#[tauri::command]
#[specta::specta]
pub async fn set_buyout(
    session: State<'_, Arc<Session>>,
    input: BuyoutInputDto,
) -> Result<PartnershipsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| partnerships::set_buyout(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Buyout to'lovi.
#[tauri::command]
#[specta::specta]
pub async fn pay_buyout(
    session: State<'_, Arc<Session>>,
    input: BuyoutPaymentInputDto,
) -> Result<PartnershipsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| partnerships::pay_buyout(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Oilaviy rozilik.
#[tauri::command]
#[specta::specta]
pub async fn consent_partnership(
    session: State<'_, Arc<Session>>,
    input: ConsentInputDto,
) -> Result<PartnershipsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| partnerships::consent(db, OffsetDateTime::now_utc(), input))
    })
    .await
}
