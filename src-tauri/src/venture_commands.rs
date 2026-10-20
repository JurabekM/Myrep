//! D13 IPC commandlari: kassa daftari, davr yopish, davr hisoboti, taklif detektori, «Hunardan ishga».

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::dto::{
    AttachReceiptInputDto, ClosePeriodInputDto, HustleInputDto, HustlePlanDto, VentureDto,
    VentureEntryInputDto,
};
use crate::session::Session;
use crate::ventures;

/// Kassa daftari.
#[tauri::command]
#[specta::specta]
pub async fn get_venture(
    session: State<'_, Arc<Session>>,
    partnership_id: String,
) -> Result<VentureDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session
            .with_database(|db| ventures::venture(db, OffsetDateTime::now_utc(), &partnership_id))
    })
    .await
}

/// Ledger yozuvi.
#[tauri::command]
#[specta::specta]
pub async fn add_venture_entry(
    session: State<'_, Arc<Session>>,
    input: VentureEntryInputDto,
) -> Result<VentureDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ventures::add_entry(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Davrni yopadi va taqsimlaydi.
#[tauri::command]
#[specta::specta]
pub async fn close_venture_period(
    session: State<'_, Arc<Session>>,
    input: ClosePeriodInputDto,
) -> Result<VentureDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ventures::close_period(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Davr hisoboti PDF'ini ilova papkasiga yozadi; yo'lini qaytaradi.
#[tauri::command]
#[specta::specta]
pub async fn create_period_report_pdf(
    app: tauri::AppHandle,
    session: State<'_, Arc<Session>>,
    period_id: String,
) -> Result<String, ApiError> {
    let dir = crate::data_dir(&app)
        .map_err(|_| ApiError::Internal)?
        .join("reports");
    let session = session.inner().clone();
    let bytes = run_blocking(move || {
        session.with_database(|db| ventures::period_pdf(db, OffsetDateTime::now_utc(), &period_id))
    })
    .await?;
    std::fs::create_dir_all(&dir).map_err(|_| ApiError::Internal)?;
    let stamp = OffsetDateTime::now_utc()
        .format(&time::macros::format_description!(
            "[year][month][day]-[hour][minute][second]"
        ))
        .unwrap_or_default();
    let path = dir.join(format!("davr-{stamp}.pdf"));
    std::fs::write(&path, bytes).map_err(|_| ApiError::Internal)?;
    Ok(path.display().to_string())
}

/// «Hunardan ishga»: uch stsenariy (saqlanmaydi).
#[tauri::command]
#[specta::specta]
pub async fn hustle_plan(input: HustleInputDto) -> Result<HustlePlanDto, ApiError> {
    ventures::hustle(input).map_err(ApiError::from)
}

/// Ledger yozuviga chek rasmi.
#[tauri::command]
#[specta::specta]
pub async fn attach_receipt(
    session: State<'_, Arc<Session>>,
    input: AttachReceiptInputDto,
) -> Result<VentureDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ventures::attach_receipt(db, OffsetDateTime::now_utc(), input))
    })
    .await
}
