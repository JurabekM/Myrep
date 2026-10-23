//! D13A IPC commandlari: kelishuvlar markazi. Qoidalar — [`center`] xizmatida.

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::center;
use crate::commands::{ApiError, run_blocking};
use crate::dto::{
    AgreementDto, AgreementOpsDto, CenterDto, DecideDisputeInputDto, DisputeInputDto,
    FamilyConfirmInputDto, FamilyTemplateDto, IncidentInputDto, MarkReviewInputDto,
    OpenReviewInputDto,
};
use crate::session::Session;

fn write_pdf(app: &tauri::AppHandle, prefix: &str, bytes: Vec<u8>) -> Result<String, ApiError> {
    let dir = crate::data_dir(app)
        .map_err(|_| ApiError::Internal)?
        .join("reports");
    std::fs::create_dir_all(&dir).map_err(|_| ApiError::Internal)?;
    let stamp = crate::commands::file_stamp(OffsetDateTime::now_utc());
    let path = dir.join(format!("{prefix}-{stamp}.pdf"));
    std::fs::write(&path, bytes).map_err(|_| ApiError::Internal)?;
    Ok(path.display().to_string())
}

/// Markaz jadvali.
#[tauri::command]
#[specta::specta]
pub async fn get_agreements_center(
    session: State<'_, Arc<Session>>,
) -> Result<CenterDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| center::center(db, OffsetDateTime::now_utc())))
        .await
}

/// Kelishuv amaliyotlari.
#[tauri::command]
#[specta::specta]
pub async fn get_agreement_ops(
    session: State<'_, Arc<Session>>,
    agreement_id: String,
) -> Result<AgreementOpsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| center::ops(db, OffsetDateTime::now_utc(), &agreement_id))
    })
    .await
}

/// Vazifa hodisasi.
#[tauri::command]
#[specta::specta]
pub async fn report_duty_incident(
    session: State<'_, Arc<Session>>,
    input: IncidentInputDto,
) -> Result<AgreementOpsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| center::report_incident(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Hodisani yopadi.
#[tauri::command]
#[specta::specta]
pub async fn resolve_duty_incident(
    session: State<'_, Arc<Session>>,
    id: String,
) -> Result<AgreementOpsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| center::resolve_incident(db, OffsetDateTime::now_utc(), &id))
    })
    .await
}

/// Ko'rik ochadi.
#[tauri::command]
#[specta::specta]
pub async fn open_review(
    session: State<'_, Arc<Session>>,
    input: OpenReviewInputDto,
) -> Result<AgreementOpsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| center::open_review(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Tomon belgisi.
#[tauri::command]
#[specta::specta]
pub async fn mark_review(
    session: State<'_, Arc<Session>>,
    input: MarkReviewInputDto,
) -> Result<AgreementOpsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| center::mark_review(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Ko'rik bayonnomasi PDF.
#[tauri::command]
#[specta::specta]
pub async fn create_review_pdf(
    app: tauri::AppHandle,
    session: State<'_, Arc<Session>>,
    review_id: String,
) -> Result<String, ApiError> {
    let session = session.inner().clone();
    let bytes = run_blocking(move || {
        session.with_database(|db| center::review_pdf(db, OffsetDateTime::now_utc(), &review_id))
    })
    .await?;
    write_pdf(&app, "korik", bytes)
}

/// Nizo ochadi.
#[tauri::command]
#[specta::specta]
pub async fn open_dispute(
    session: State<'_, Arc<Session>>,
    input: DisputeInputDto,
) -> Result<AgreementOpsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| center::open_dispute(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Hakam qarori.
#[tauri::command]
#[specta::specta]
pub async fn decide_dispute(
    session: State<'_, Arc<Session>>,
    input: DecideDisputeInputDto,
) -> Result<AgreementOpsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| center::decide_dispute(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Hakam uchun ish papkasi PDF.
#[tauri::command]
#[specta::specta]
pub async fn create_arbiter_pdf(
    app: tauri::AppHandle,
    session: State<'_, Arc<Session>>,
    agreement_id: String,
) -> Result<String, ApiError> {
    let session = session.inner().clone();
    let bytes = run_blocking(move || {
        session
            .with_database(|db| center::arbiter_pdf(db, OffsetDateTime::now_utc(), &agreement_id))
    })
    .await?;
    write_pdf(&app, "hakam-papkasi", bytes)
}

/// Yillik yangilash: o'zgarishsiz tasdiqlash (yangi versiya).
#[tauri::command]
#[specta::specta]
pub async fn confirm_unchanged(
    session: State<'_, Arc<Session>>,
    agreement_id: String,
) -> Result<AgreementOpsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            center::confirm_unchanged(db, OffsetDateTime::now_utc(), &agreement_id)
        })
    })
    .await
}

/// Oilaviy shablonlar.
#[tauri::command]
#[specta::specta]
pub async fn list_family_templates() -> Result<Vec<FamilyTemplateDto>, ApiError> {
    Ok(center::family_templates())
}

/// Shablondan oilaviy kelishuv.
#[tauri::command]
#[specta::specta]
pub async fn create_family_agreement(
    session: State<'_, Arc<Session>>,
    template_id: String,
) -> Result<AgreementDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            center::create_family_agreement(db, OffsetDateTime::now_utc(), &template_id)
        })
    })
    .await
}

/// ADULT a'zo PIN bilan tasdiqlaydi.
#[tauri::command]
#[specta::specta]
pub async fn confirm_family(
    session: State<'_, Arc<Session>>,
    input: FamilyConfirmInputDto,
) -> Result<AgreementOpsDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| center::confirm_family(db, OffsetDateTime::now_utc(), input))
    })
    .await
}
