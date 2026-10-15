//! D8 IPC commandlari: zaxira holati va «Narx daftari». Hisob — [`reserve`] xizmatida.

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::dto::{PriceItemInputDto, PricesDto, ReserveDto};
use crate::reserve;
use crate::session::Session;

/// Qorovul zaxirasi: maqsad, necha oylik zaxira, darvoza.
#[tauri::command]
#[specta::specta]
pub async fn get_reserve(session: State<'_, Arc<Session>>) -> Result<ReserveDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| reserve::reserve(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Narx daftari: yozuvlar, indeks, «Sichqon kemirgani».
#[tauri::command]
#[specta::specta]
pub async fn get_prices(session: State<'_, Arc<Session>>) -> Result<PricesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| reserve::prices(db, OffsetDateTime::now_utc())))
        .await
}

/// Narx yozuvi qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_price_item(
    session: State<'_, Arc<Session>>,
    input: PriceItemInputDto,
) -> Result<PricesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| reserve::add_price_item(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Joriy narxni yangilaydi.
#[tauri::command]
#[specta::specta]
pub async fn update_price(
    session: State<'_, Arc<Session>>,
    id: String,
    current_price: String,
) -> Result<PricesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            reserve::update_price(db, OffsetDateTime::now_utc(), &id, &current_price)
        })
    })
    .await
}

/// Narx yozuvini o'chiradi.
#[tauri::command]
#[specta::specta]
pub async fn remove_price_item(
    session: State<'_, Arc<Session>>,
    id: String,
) -> Result<PricesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| reserve::remove_price_item(db, OffsetDateTime::now_utc(), &id))
    })
    .await
}
