//! Tray belgisi va global tezkor tugma (`Ctrl+Alt+B` — tez xarajat oynasi).
//! Tez xarajat oynasi alohida kichik oyna: qulf holatida hech qanday summa ko'rsatmaydi
//! (frontend `?window=quick` rejimida holatni so'raydi va qulfda faqat xabar chiqaradi).

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, WebviewUrl, WebviewWindowBuilder,
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

pub const QUICK_LABEL: &str = "quick";

#[must_use]
pub fn quick_shortcut() -> Shortcut {
    Shortcut::new(Some(Modifiers::CONTROL.union(Modifiers::ALT)), Code::KeyB)
}

/// Tez xarajat oynasini ochadi (bor bo'lsa ko'rsatadi va fokus beradi).
pub fn open_quick(app: &AppHandle) {
    if let Some(w) = app.get_webview_window(QUICK_LABEL) {
        let _ = w.show();
        let _ = w.set_focus();
        return;
    }
    let _ = WebviewWindowBuilder::new(
        app,
        QUICK_LABEL,
        WebviewUrl::App("index.html?window=quick".into()),
    )
    .title("Tez xarajat")
    .inner_size(400.0, 360.0)
    .resizable(false)
    .always_on_top(true)
    .center()
    .content_protected(true)
    .build();
}

fn show_main(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.unminimize();
        let _ = w.set_focus();
    }
}

/// Tez xarajat oynasini yashiradi (command orqali; JS'ga oyna ruxsati berilmaydi).
pub fn hide_quick(app: &AppHandle) {
    if let Some(w) = app.get_webview_window(QUICK_LABEL) {
        let _ = w.hide();
    }
}

/// Tray menyusi + global tugma. Tugma band bo'lsa ilova baribir ishlaydi (tray orqali ochiladi).
///
/// # Errors
/// Menyu yoki tray yaratilmasa.
pub fn setup(app: &tauri::App) -> tauri::Result<()> {
    let open = MenuItem::with_id(app, "open", "Ochish", true, None::<&str>)?;
    let quick = MenuItem::with_id(app, "quick", "Tez xarajat (Ctrl+Alt+B)", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Chiqish", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open, &quick, &quit])?;

    let mut tray = TrayIconBuilder::new()
        .tooltip("Baraka daftari")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open" => show_main(app),
            "quick" => open_quick(app),
            "quit" => app.exit(0),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                show_main(tray.app_handle());
            }
        });
    if let Some(icon) = app.default_window_icon() {
        tray = tray.icon(icon.clone());
    }
    tray.build(app)?;

    let _ = app.global_shortcut().register(quick_shortcut());
    Ok(())
}

/// Global tugma plugini: faqat `Ctrl+Alt+B` bosilganda tez xarajat oynasi ochiladi.
#[must_use]
pub fn shortcut_plugin() -> tauri::plugin::TauriPlugin<tauri::Wry> {
    tauri_plugin_global_shortcut::Builder::new()
        .with_handler(|app, shortcut, event| {
            if event.state() == ShortcutState::Pressed && *shortcut == quick_shortcut() {
                open_quick(app);
            }
        })
        .build()
}
