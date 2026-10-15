//! D11 IPC commandlari: marosimlar. Qoidalar — [`ceremonies`] xizmatida.

use std::sync::Arc;

use tauri::{Manager, State};
use time::OffsetDateTime;

use crate::ceremonies;
use crate::commands::{ApiError, run_blocking};
use crate::dto::{
    CeremoniesDto, CeremonyGoalInputDto, CeremonyInputDto, CeremonyLineInputDto,
    ConfirmCeremonyInputDto, ScenarioInputDto,
};
use crate::session::Session;

/// Marosimlar sahifasi.
#[tauri::command]
#[specta::specta]
pub async fn get_ceremonies(session: State<'_, Arc<Session>>) -> Result<CeremoniesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ceremonies::overview(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Yangi marosim.
#[tauri::command]
#[specta::specta]
pub async fn create_ceremony(
    session: State<'_, Arc<Session>>,
    input: CeremonyInputDto,
) -> Result<CeremoniesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ceremonies::create(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Stsenariy qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_ceremony_scenario(
    session: State<'_, Arc<Session>>,
    input: ScenarioInputDto,
) -> Result<CeremoniesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ceremonies::add_scenario(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Byudjet qatori qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_ceremony_line(
    session: State<'_, Arc<Session>>,
    input: CeremonyLineInputDto,
) -> Result<CeremoniesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ceremonies::add_line(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Qatorni o'chiradi.
#[tauri::command]
#[specta::specta]
pub async fn remove_ceremony_line(
    session: State<'_, Arc<Session>>,
    line_id: String,
) -> Result<CeremoniesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ceremonies::remove_line(db, OffsetDateTime::now_utc(), &line_id))
    })
    .await
}

/// Oilaviy muhokama o'tkazilganini qayd etadi.
#[tauri::command]
#[specta::specta]
pub async fn discuss_ceremony(
    session: State<'_, Arc<Session>>,
    id: String,
) -> Result<CeremoniesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ceremonies::discuss(db, OffsetDateTime::now_utc(), &id))
    })
    .await
}

/// Tasdiqlaydi (tanlangan stsenariy bilan).
#[tauri::command]
#[specta::specta]
pub async fn confirm_ceremony(
    session: State<'_, Arc<Session>>,
    input: ConfirmCeremonyInputDto,
) -> Result<CeremoniesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            ceremonies::confirm_ceremony(db, OffsetDateTime::now_utc(), input)
        })
    })
    .await
}

/// To'yona o'rniga jamg'arma maqsadi.
#[tauri::command]
#[specta::specta]
pub async fn set_ceremony_goal(
    session: State<'_, Arc<Session>>,
    input: CeremonyGoalInputDto,
) -> Result<CeremoniesDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| ceremonies::set_goal(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Smeta PDF'ini ilova papkasiga yozadi; yo'lini qaytaradi.
#[tauri::command]
#[specta::specta]
pub async fn create_ceremony_pdf(
    app: tauri::AppHandle,
    session: State<'_, Arc<Session>>,
    id: String,
    scenario_id: String,
) -> Result<String, ApiError> {
    let dir = app
        .path()
        .app_data_dir()
        .map_err(|_| ApiError::Internal)?
        .join("reports");
    let session = session.inner().clone();
    let bytes = run_blocking(move || {
        session.with_database(|db| {
            ceremonies::pdf(db, OffsetDateTime::now_utc(), &id, &scenario_id)
        })
    })
    .await?;
    std::fs::create_dir_all(&dir).map_err(|_| ApiError::Internal)?;
    let stamp = OffsetDateTime::now_utc()
        .format(&time::macros::format_description!(
            "[year][month][day]-[hour][minute][second]"
        ))
        .unwrap_or_default();
    let path = dir.join(format!("smeta-{stamp}.pdf"));
    std::fs::write(&path, bytes).map_err(|_| ApiError::Internal)?;
    Ok(path.display().to_string())
}
