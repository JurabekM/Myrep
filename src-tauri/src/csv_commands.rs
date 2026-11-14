//! CSV import IPC commandlari: ko'rib chiqish va import. Tahlil va yozish — [`csv_import`] da.

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::csv_import;
use crate::dto::{CsvImportInputDto, CsvPreviewDto};
use crate::session::Session;

/// Joylangan matnni ko'rib chiqadi: satrlar, xatolar, nechta import bo'ladi.
#[tauri::command]
#[specta::specta]
pub async fn preview_csv_import(
    session: State<'_, Arc<Session>>,
    input: CsvImportInputDto,
) -> Result<CsvPreviewDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            csv_import::preview(db, OffsetDateTime::now_utc(), &input.text, &input.mapping)
        })
    })
    .await
}

/// Import qiladi (xatoli satr bo'lsa — rad etiladi). Qaytaradi: yozilgan xarajatlar soni.
#[tauri::command]
#[specta::specta]
pub async fn import_csv_expenses(
    session: State<'_, Arc<Session>>,
    input: CsvImportInputDto,
) -> Result<u32, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            csv_import::import(db, OffsetDateTime::now_utc(), &input.text, &input.mapping)
        })
    })
    .await
}
