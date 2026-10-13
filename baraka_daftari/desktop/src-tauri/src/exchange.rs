//! D14 commandlari: `.baraka` eksport/import. Fayllar OS dialogi orqali Rust tomonida o'qiladi va
//! yoziladi; parol va shifrlangan baytlar frontendga qaytmaydi. Tanlangan fayl import tasdiqlanguncha
//! xotirada turadi (parolni qayta kiritish uchun faylni qaytadan tanlash shart emas).

use std::sync::Mutex;

use security::KdfParams;
use serde::Serialize;
use services::interchange::{self, ImportReport};
use specta::Type;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;
use zeroize::Zeroizing;

use crate::commands::{with_session, AppSession, CommandError};
use crate::tray;

#[derive(Default)]
pub struct PendingImport(Mutex<Option<Vec<u8>>>);

impl PendingImport {
    fn set(&self, v: Option<Vec<u8>>) {
        *self
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = v;
    }

    fn get(&self) -> Option<Vec<u8>> {
        self.0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone()
    }
}

fn internal(msg: &str) -> CommandError {
    CommandError::Internal {
        message: msg.into(),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct ExchangeStatusDto {
    /// Oxirgi muvaffaqiyatli eksport (RFC 3339) — inkremental eksport shundan boshlanadi.
    pub last_export: Option<String>,
}

#[derive(Debug, Serialize, Type)]
pub struct ConflictDto {
    pub table: String,
    pub id: String,
    /// `DIVERGED` | `CLOSED_PERIOD` | `SIGNED_CONTRACT` | `JOURNAL` | `REJECTED`.
    pub kind: String,
    /// `KEPT_LOCAL` | `TOOK_INCOMING` | `SKIPPED`.
    pub resolution: String,
    pub label: String,
}

#[derive(Debug, Serialize, Type)]
pub struct ImportReportDto {
    pub inserted: u32,
    pub updated: u32,
    pub unchanged: u32,
    pub kept_local: u32,
    pub conflicts: Vec<ConflictDto>,
    /// PIN'siz kattalar: ularga PIN o'rnatilmaguncha havas chegarasiga rozilik bera olmaydi.
    pub adults_without_pin: Vec<String>,
}

fn report_dto(r: &ImportReport) -> ImportReportDto {
    use interchange::{ConflictKind as K, Resolution as R};
    ImportReportDto {
        inserted: r.inserted,
        updated: r.updated,
        unchanged: r.unchanged,
        kept_local: r.kept_local,
        adults_without_pin: r.adults_without_pin.clone(),
        conflicts: r
            .conflicts
            .iter()
            .map(|c| ConflictDto {
                table: c.table.clone(),
                id: c.id.clone(),
                kind: match c.kind {
                    K::Diverged => "DIVERGED",
                    K::ClosedPeriod => "CLOSED_PERIOD",
                    K::SignedContract => "SIGNED_CONTRACT",
                    K::Journal => "JOURNAL",
                    K::Rejected => "REJECTED",
                }
                .into(),
                resolution: match c.resolution {
                    R::KeptLocal => "KEPT_LOCAL",
                    R::TookIncoming => "TOOK_INCOMING",
                    R::Skipped => "SKIPPED",
                }
                .into(),
                label: c.label.clone(),
            })
            .collect(),
    }
}

#[tauri::command]
#[specta::specta]
pub fn exchange_status(state: State<'_, AppSession>) -> Result<ExchangeStatusDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            let last =
                interchange::last_export(db, ctx)?.and_then(|t| domain::ts_to_string(t).ok());
            Ok(ExchangeStatusDto { last_export: last })
        })
    })
}

/// `.baraka` faylini OS «saqlash» oynasi orqali yozadi. Bekor qilinsa `None`.
#[tauri::command]
#[specta::specta]
pub async fn export_baraka(
    password: String,
    incremental: bool,
    include_attachments: bool,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    let password = Zeroizing::new(password);
    let opts = interchange::ExportOptions {
        incremental,
        include_attachments,
        ..interchange::ExportOptions::default()
    };
    let bytes = with_session(&state, |s| {
        s.run(|db, env, ctx| {
            interchange::export_bytes_with(db, env, ctx, &password, KdfParams::production(), opts)
        })
    })?;
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("Baraka", &["baraka"])
        .set_file_name("baraka.baraka")
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let mut path = file
        .into_path()
        .map_err(|_| internal("fayl yo'li noto'g'ri"))?;
    if path
        .extension()
        .is_none_or(|e| !e.eq_ignore_ascii_case("baraka"))
    {
        path.set_extension("baraka");
    }
    std::fs::write(&path, bytes).map_err(|_| internal("faylni yozib bo'lmadi"))?;
    with_session(&state, |s| {
        s.run(|db, env, ctx| interchange::mark_exported(db, env, ctx))
    })?;
    Ok(path.file_name().map(|n| n.to_string_lossy().into_owned()))
}

/// Import faylini tanlaydi (hali ochmaydi). Qaytadi: fayl nomi; bekor qilinsa `None`.
#[tauri::command]
#[specta::specta]
pub async fn import_baraka_pick(
    app: AppHandle,
    state: State<'_, AppSession>,
    pending: State<'_, PendingImport>,
) -> Result<Option<String>, CommandError> {
    with_session(&state, |s| s.run(|_, _, _| Ok(())))?;
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("Baraka", &["baraka"])
        .blocking_pick_file()
    else {
        return Ok(None);
    };
    let path = file
        .into_path()
        .map_err(|_| internal("fayl yo'li noto'g'ri"))?;
    let meta = std::fs::metadata(&path).map_err(|_| internal("faylni o'qib bo'lmadi"))?;
    if meta.len() > u64::try_from(interchange::MAX_FILE_BYTES).unwrap_or(u64::MAX) {
        return Err(CommandError::BadFile {
            message: "fayl juda katta (512 MB dan ko'p)".into(),
        });
    }
    let data = std::fs::read(&path).map_err(|_| internal("faylni o'qib bo'lmadi"))?;
    pending.set(Some(data));
    Ok(path.file_name().map(|n| n.to_string_lossy().into_owned()))
}

/// Ziddiyatlar ro'yxati: hech narsa saqlanmaydi.
#[tauri::command]
#[specta::specta]
pub fn import_baraka_preview(
    password: String,
    state: State<'_, AppSession>,
    pending: State<'_, PendingImport>,
) -> Result<ImportReportDto, CommandError> {
    let password = Zeroizing::new(password);
    let bytes = pending.get().ok_or(CommandError::Invalid {
        message: "avval faylni tanlang".into(),
    })?;
    with_session(&state, |s| {
        s.run(|db, _, ctx| interchange::preview(db, ctx, &bytes, &password))
    })
    .map(|r| report_dto(&r))
}

/// Birlashtirishni qo'llaydi (yagona tranzaksiya) va tanlangan faylni xotiradan tozalaydi.
#[tauri::command]
#[specta::specta]
pub fn import_baraka_apply(
    password: String,
    state: State<'_, AppSession>,
    pending: State<'_, PendingImport>,
) -> Result<ImportReportDto, CommandError> {
    let password = Zeroizing::new(password);
    let bytes = pending.get().ok_or(CommandError::Invalid {
        message: "avval faylni tanlang".into(),
    })?;
    let r = with_session(&state, |s| {
        s.run(|db, _, ctx| interchange::import(db, ctx, &bytes, &password))
    })?;
    pending.set(None);
    Ok(report_dto(&r))
}

#[tauri::command]
#[specta::specta]
pub fn import_baraka_cancel(pending: State<'_, PendingImport>) {
    pending.set(None);
}

// ---------------------------------------------------------------- onboarding va ilova ma'lumoti

#[tauri::command]
#[specta::specta]
pub fn onboarding_done(state: State<'_, AppSession>) -> Result<bool, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| services::onboarding::is_done(db.conn(), ctx))
    })
}

#[tauri::command]
#[specta::specta]
pub fn complete_onboarding(state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| services::onboarding::complete(db.conn(), env, ctx))
    })
}

#[derive(Debug, Serialize, Type)]
pub struct AppInfoDto {
    pub version: String,
    /// Shartnoma PDF'ini chiqarish mumkinmi (relizda shablon tasdiqlanmaguncha `false`).
    pub contract_pdf_available: bool,
    /// `Ctrl+Alt+B` tez xarajat tugmasi ro'yxatdan o'tdimi (boshqa dastur band qilgan bo'lishi mumkin).
    pub quick_hotkey_registered: bool,
    /// Sheriklik shartnomasi shabloni ulamo/yurist tasdig'idan o'tganmi (reliz to'sig'i, OPEN_QUESTIONS 65).
    pub templates_approved: bool,
}

#[tauri::command]
#[specta::specta]
pub fn app_info(hotkey: State<'_, tray::HotkeyStatus>) -> AppInfoDto {
    AppInfoDto {
        version: env!("CARGO_PKG_VERSION").into(),
        templates_approved: services::TEMPLATES_APPROVED,
        contract_pdf_available: services::templates_releasable(cfg!(debug_assertions)),
        quick_hotkey_registered: hotkey.registered,
    }
}
