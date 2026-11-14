//! D5 IPC commandlari: boblar, bob sahifasi, haftalik vazifalar va «Daftar sahifasi».
//! Qoida: har command — argumentni o'qish → [`content`] funksiyasi → DTO. Biznes mantiq bu yerda emas.

use std::sync::Arc;

use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::content;
use crate::dto::{ChapterCardDto, ChapterDto, DaftarPageDto, WeeklyTasksDto};
use crate::session::Session;
use tauri::State;

/// Bob ro'yxati: ochiq-yopiqlik, ochilish sanasi va kerakli vazifalar.
#[tauri::command]
#[specta::specta]
pub async fn list_chapters(
    session: State<'_, Arc<Session>>,
) -> Result<Vec<ChapterCardDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| content::list_chapters(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Ochiq bob sahifasi (matn, qonun, vazifalar, «Daftar sahifasi»).
#[tauri::command]
#[specta::specta]
pub async fn get_chapter(
    session: State<'_, Arc<Session>>,
    chapter_id: String,
) -> Result<ChapterDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| content::get_chapter(db, OffsetDateTime::now_utc(), &chapter_id))
    })
    .await
}

/// Joriy bobning shu haftalik vazifalari.
#[tauri::command]
#[specta::specta]
pub async fn get_weekly_tasks(
    session: State<'_, Arc<Session>>,
) -> Result<Option<WeeklyTasksDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| content::weekly_tasks(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Joriy bobning vazifasini shu hafta uchun belgilaydi yoki bekor qiladi.
#[tauri::command]
#[specta::specta]
pub async fn set_task_done(
    session: State<'_, Arc<Session>>,
    task_id: String,
    done: bool,
) -> Result<Option<WeeklyTasksDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            content::set_task_done(db, OffsetDateTime::now_utc(), &task_id, done)
        })
    })
    .await
}

/// «Daftar sahifasi»ni saqlaydi (bob uchun bitta, yangilanadi).
#[tauri::command]
#[specta::specta]
pub async fn save_daftar_page(
    session: State<'_, Arc<Session>>,
    chapter_id: String,
    body: String,
) -> Result<DaftarPageDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            content::save_daftar_page(db, OffsetDateTime::now_utc(), &chapter_id, &body)
        })
    })
    .await
}
