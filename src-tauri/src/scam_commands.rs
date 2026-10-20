//! 7-qonun IPC commandlari: taklif tekshiruvi, qaror, va'da hisobi, piramida, qal'a devori, hunar shablonlari.
//! Qoidalar — [`scam`] xizmatida.

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::dto::{
    DecideOfferInputDto, HustleTemplateDto, LumpSumInputDto, LumpSumPlanDto, OfferCheckDto,
    OfferInputDto, OffersDto, PromisedReturnDto, PyramidDto,
};
use crate::scam;
use crate::session::Session;

/// Taklifni besh xavf belgisi bilan tekshiradi va yozadi.
#[tauri::command]
#[specta::specta]
pub async fn check_offer(
    session: State<'_, Arc<Session>>,
    input: OfferInputDto,
) -> Result<OfferCheckDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| scam::check_offer(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Tekshiruvlar tarixi.
#[tauri::command]
#[specta::specta]
pub async fn list_offer_checks(session: State<'_, Arc<Session>>) -> Result<OffersDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| scam::list_offers(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// «To'xta, maslahatlash» qarori.
#[tauri::command]
#[specta::specta]
pub async fn decide_offer(
    session: State<'_, Arc<Session>>,
    input: DecideOfferInputDto,
) -> Result<OffersDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| scam::decide_offer(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Oylik va'da → yillik ko'paytma (faqat ogohlantirish).
#[tauri::command]
#[specta::specta]
pub async fn promised_return(monthly_bp: u32) -> Result<PromisedReturnDto, ApiError> {
    scam::promised(monthly_bp).map_err(ApiError::from)
}

/// Piramida modeli (ta'limiy).
#[tauri::command]
#[specta::specta]
pub async fn pyramid_model(
    recruits_per_person: u32,
    population: u32,
) -> Result<PyramidDto, ApiError> {
    scam::pyramid(recruits_per_person, population).map_err(ApiError::from)
}

/// «Qal'a devori» taqsimoti.
#[tauri::command]
#[specta::specta]
pub async fn plan_lump_sum(
    session: State<'_, Arc<Session>>,
    input: LumpSumInputDto,
) -> Result<LumpSumPlanDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| scam::plan_lump_sum(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Hunar shablonlari.
#[tauri::command]
#[specta::specta]
pub async fn list_hustle_templates() -> Result<Vec<HustleTemplateDto>, ApiError> {
    Ok(scam::hustle_templates())
}
