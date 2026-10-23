//! Juma shirinligi bildirishnomasi (SPEC 2B.4, DESKTOP_PROMPT 7): ilova ishlab turganda, ritual kuni bir marta.
//!
//! Ilova qulfli bo'lsa yoki baza hali ochilmagan bo'lsa, tekshiruv jim o'tkaziladi; qulf ochilgach keyingi
//! tekshiruvda bildirishnoma yuboriladi. Bildirishnomada summa yoki izoh yo'q, faqat ritual nomi.

use std::time::Duration;

use domain::calendar::tashkent_date;
use tauri::AppHandle;
use tauri_plugin_notification::NotificationExt;
use time::{Date, OffsetDateTime};
use tracing::warn;

use crate::family;
use crate::session::Session;

/// Tekshiruv oralig'i: 5 daqiqa.
pub const CHECK_INTERVAL: Duration = Duration::from_secs(300);

/// Ritual kunini tekshiradi va kerak bo'lsa bildirishnoma yuboradi. `last_day` — oxirgi yuborilgan kun.
pub fn notify_due_treats(session: &Session, app: &AppHandle, last_day: &mut Option<Date>) {
    let now = OffsetDateTime::now_utc();
    let Ok(names) = session.with_database(|db| family::due_treat_names(db, now)) else {
        return;
    };
    let today = tashkent_date(now);
    if names.is_empty() || !family::should_notify(*last_day, today) {
        return;
    }
    for name in &names {
        let shown = app
            .notification()
            .builder()
            .title("Juma shirinligi")
            .body(format!("Bugun: {name}"))
            .show();
        if shown.is_err() {
            warn!("bildirishnoma ko'rsatilmadi");
        }
    }
    *last_day = Some(today);
}
