//! D14 IPC commandlari: `.baraka` eksport, import ko'rigi va qo'llash. Parol loglanmaydi.

use std::sync::Arc;

use security::KdfParams;
use tauri::State;
use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::dto::{ExportInputDto, ExportResultDto, ImportInputDto, ImportReportDto};
use crate::session::Session;
use crate::sync;

/// `.baraka` eksport (to'liq yoki `since` dan keyingi o'zgarishlar).
#[tauri::command]
#[specta::specta]
pub async fn export_baraka(
    app: tauri::AppHandle,
    session: State<'_, Arc<Session>>,
    input: ExportInputDto,
) -> Result<ExportResultDto, ApiError> {
    let dir = crate::data_dir(&app)
        .map_err(|_| ApiError::Internal)?
        .join("exports");
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            sync::export(
                db,
                OffsetDateTime::now_utc(),
                &dir,
                KdfParams::RECOMMENDED,
                input,
            )
        })
    })
    .await
}

/// Import ko'rigi (hech narsa yozilmaydi).
#[tauri::command]
#[specta::specta]
pub async fn preview_baraka_import(
    session: State<'_, Arc<Session>>,
    input: ImportInputDto,
) -> Result<ImportReportDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| sync::preview(db, input))).await
}

/// Importni qo'llaydi.
#[tauri::command]
#[specta::specta]
pub async fn apply_baraka_import(
    session: State<'_, Arc<Session>>,
    input: ImportInputDto,
) -> Result<ImportReportDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| sync::apply(db, input))).await
}
