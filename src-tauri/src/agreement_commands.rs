//! D8A IPC commandlari: kelishuvlar, imzolar, jurnal, PDF. Qoidalar — [`agreements`] xizmatida.

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::agreements;
use crate::commands::{ApiError, run_blocking};
use crate::dto::{
    AgreementDto, AgreementInputDto, AgreementSummaryDto, JournalDto, JournalEntryInputDto,
    SaveAnswersInputDto, SignInputDto, SignatureInputDto,
};
use crate::session::Session;

/// Kelishuvlar ro'yxati.
#[tauri::command]
#[specta::specta]
pub async fn list_agreements(
    session: State<'_, Arc<Session>>,
) -> Result<Vec<AgreementSummaryDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| agreements::list(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Yangi kelishuv (qoralama).
#[tauri::command]
#[specta::specta]
pub async fn create_agreement(
    session: State<'_, Arc<Session>>,
    input: AgreementInputDto,
) -> Result<AgreementDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| agreements::create(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Bitta kelishuv (javoblar, to'liqlik, imzolar, zanjir).
#[tauri::command]
#[specta::specta]
pub async fn get_agreement(
    session: State<'_, Arc<Session>>,
    id: String,
) -> Result<AgreementDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| agreements::get(db, OffsetDateTime::now_utc(), &id))
    })
    .await
}

/// Javoblarni saqlaydi (versiya oshadi; imzolangan bo'lsa — qayta imzolash kerak).
#[tauri::command]
#[specta::specta]
pub async fn save_agreement_answers(
    session: State<'_, Arc<Session>>,
    input: SaveAnswersInputDto,
) -> Result<AgreementDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| agreements::save_answers(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Imzo qo'shadi (9/9 bo'lmasa — rad etiladi).
#[tauri::command]
#[specta::specta]
pub async fn add_signature(
    session: State<'_, Arc<Session>>,
    input: SignatureInputDto,
) -> Result<AgreementDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| agreements::add_signature(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Imzolashni yakunlaydi: hamma imzo bo'lsa SIGNED; og'zaki kelishuv — o'tmishdagi sana va boshlang'ich balans.
#[tauri::command]
#[specta::specta]
pub async fn sign_agreement(
    session: State<'_, Arc<Session>>,
    input: SignInputDto,
) -> Result<AgreementDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| agreements::sign(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Jurnalga yozuv qo'shadi (faqat imzolangan kelishuv, faqat hisob yurituvchi qurilma).
#[tauri::command]
#[specta::specta]
pub async fn append_journal_entry(
    session: State<'_, Arc<Session>>,
    input: JournalEntryInputDto,
) -> Result<JournalDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| agreements::append_journal(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Jurnal va zanjir tekshiruvi.
#[tauri::command]
#[specta::specta]
pub async fn get_journal(
    session: State<'_, Arc<Session>>,
    agreement_id: String,
) -> Result<JournalDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| agreements::journal(db, &agreement_id))).await
}

/// Kelishuv PDF'ini ilova papkasiga yozadi; yo'lini qaytaradi.
#[tauri::command]
#[specta::specta]
pub async fn create_agreement_pdf(
    app: tauri::AppHandle,
    session: State<'_, Arc<Session>>,
    id: String,
) -> Result<String, ApiError> {
    let dir = crate::data_dir(&app)
        .map_err(|_| ApiError::Internal)?
        .join("reports");
    let session = session.inner().clone();
    let bytes = run_blocking(move || {
        session.with_database(|db| agreements::pdf(db, OffsetDateTime::now_utc(), &id))
    })
    .await?;
    std::fs::create_dir_all(&dir).map_err(|_| ApiError::Internal)?;
    let stamp = OffsetDateTime::now_utc()
        .format(&time::macros::format_description!(
            "[year][month][day]-[hour][minute][second]"
        ))
        .unwrap_or_default();
    let path = dir.join(format!("kelishuv-{stamp}.pdf"));
    std::fs::write(&path, bytes).map_err(|_| ApiError::Internal)?;
    Ok(path.display().to_string())
}
