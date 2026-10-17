//! Desktopga xos qism (DESKTOP_PROMPT 7-bo'lim): tray ikonkasi, `Ctrl+Alt+B` global tugmasi va
//! «tez xarajat» mini oynasi.
//!
//! Mini oyna — alohida webview (`quick` yorlig'i), o'sha frontend. Qulf holatida u summa ko'rsatmaydi:
//! buni frontend `get_security_status` orqali hal qiladi, bu yerda faqat oyna boshqaruvi.
//! Tray menyusi matnlari o'zbekcha (ilovaning asosiy tili); tray tilini almashtirish keyingi bosqichda.

use std::sync::Arc;

use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder, WindowEvent};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

use crate::commands::ApiError;
use crate::session::Session;

/// Asosiy oyna yorlig'i.
pub const MAIN_WINDOW: &str = "main";
/// Mini oyna yorlig'i.
pub const QUICK_WINDOW: &str = "quick";

const TRAY_OPEN: &str = "tray-open";
const TRAY_QUICK: &str = "tray-quick";
const TRAY_LOCK: &str = "tray-lock";
const TRAY_QUIT: &str = "tray-quit";

/// Tray ikonkasi va menyusi.
pub fn setup_tray(app: &AppHandle) -> tauri::Result<()> {
    let open = MenuItem::with_id(app, TRAY_OPEN, "Ochish", true, None::<&str>)?;
    let quick = MenuItem::with_id(
        app,
        TRAY_QUICK,
        "Tez xarajat (Ctrl+Alt+B)",
        true,
        None::<&str>,
    )?;
    let lock = MenuItem::with_id(app, TRAY_LOCK, "Qulflash", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, TRAY_QUIT, "Chiqish", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open, &quick, &lock, &quit])?;

    let icon = app
        .default_window_icon()
        .cloned()
        .ok_or_else(|| tauri::Error::AssetNotFound("ilova ikonkasi".to_owned()))?;

    TrayIconBuilder::with_id("main-tray")
        .icon(icon)
        .tooltip("Baraka Daftari")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id().as_ref() {
            TRAY_OPEN => show_main(app),
            TRAY_QUICK => open_quick(app),
            TRAY_LOCK => {
                if let Some(session) = app.try_state::<Arc<Session>>() {
                    session.lock();
                }
            }
            TRAY_QUIT => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let tauri::tray::TrayIconEvent::DoubleClick { .. } = event {
                show_main(tray.app_handle());
            }
        })
        .build(app)?;
    Ok(())
}

/// `Ctrl+Alt+B` — mini oynani ochadi (yoki oldinga keltiradi).
pub fn setup_shortcut(app: &AppHandle) -> tauri::Result<()> {
    let shortcut = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::ALT), Code::KeyB);
    app.global_shortcut()
        .on_shortcut(shortcut, |app, _shortcut, event| {
            if event.state() == ShortcutState::Pressed {
                open_quick(app);
            }
        })
        .map_err(|err| tauri::Error::Anyhow(err.into()))?;
    Ok(())
}

/// Asosiy oynani ko'rsatadi va fokuslaydi.
fn show_main(app: &AppHandle) {
    if let Some(window) = app.get_webview_window(MAIN_WINDOW) {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

/// Mini oynani ochadi: bor bo'lsa ko'rsatadi, yo'q bo'lsa yaratadi. Yopish — yashirish (qayta ochish tez).
fn open_quick(app: &AppHandle) {
    if let Some(window) = app.get_webview_window(QUICK_WINDOW) {
        let _ = window.show();
        let _ = window.set_focus();
        return;
    }
    let built = WebviewWindowBuilder::new(app, QUICK_WINDOW, WebviewUrl::App("index.html".into()))
        .title("Tez xarajat — Baraka Daftari")
        .inner_size(440.0, 420.0)
        .resizable(false)
        .always_on_top(true)
        .skip_taskbar(true)
        .center()
        .theme(Some(tauri::Theme::Dark))
        .build();
    match built {
        Ok(window) => {
            if !cfg!(debug_assertions) {
                let _ = window.set_content_protected(true);
            }
            let hide_target = window.clone();
            window.on_window_event(move |event| {
                if let WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    let _ = hide_target.hide();
                }
            });
            let _ = window.set_focus();
        }
        Err(err) => tracing::warn!(error = %err, "mini oynani ochib bo'lmadi"),
    }
}

/// Asosiy oynani ko'rsatadi (mini oynadagi «Asosiy oynani ochish» tugmasi).
#[tauri::command]
#[specta::specta]
pub fn show_main_window(app: AppHandle) -> Result<(), ApiError> {
    show_main(&app);
    Ok(())
}

/// Mini oynani yashiradi (Escape yoki saqlashdan keyin).
#[tauri::command]
#[specta::specta]
pub fn hide_quick_window(app: AppHandle) -> Result<(), ApiError> {
    if let Some(window) = app.get_webview_window(QUICK_WINDOW) {
        let _ = window.hide();
    }
    Ok(())
}
