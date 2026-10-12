use std::sync::Mutex;

use money::{allocate, Currency, Locale, Money};
use security::KeyringStore;
use serde::Serialize;
use specta::Type;
use tauri::State;
use zeroize::Zeroizing;

use crate::{
    dto::MoneyDto,
    session::{Session, SessionError},
};

pub type AppSession = Mutex<Session<KeyringStore>>;

pub use api::error::{unix_now, CommandError, VaultStateDto};

pub fn with_session<T>(
    state: &State<'_, AppSession>,
    f: impl FnOnce(&mut Session<KeyringStore>) -> Result<T, SessionError>,
) -> Result<T, CommandError> {
    let mut guard = state
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    f(&mut guard).map_err(Into::into)
}

#[tauri::command]
#[specta::specta]
pub fn vault_state(state: State<'_, AppSession>) -> Result<VaultStateDto, CommandError> {
    with_session(&state, |s| s.state()).map(Into::into)
}

/// Birinchi ishga tushirish: PIN o'rnatadi va bazani ochadi.
#[tauri::command]
#[specta::specta]
pub fn setup_pin(pin: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    let pin = Zeroizing::new(pin);
    with_session(&state, |s| s.setup(&pin, unix_now()))
}

#[tauri::command]
#[specta::specta]
pub fn unlock(pin: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    let pin = Zeroizing::new(pin);
    with_session(&state, |s| s.unlock(&pin, unix_now()))
}

#[tauri::command]
#[specta::specta]
pub fn lock(state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.lock();
        Ok(())
    })
}

/// Foydalanuvchi faolligi: avto-qulf hisoblagichini yangilaydi.
#[tauri::command]
#[specta::specta]
pub fn activity(state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.touch(unix_now());
        Ok(())
    })
}

#[derive(Debug, Serialize, Type)]
#[serde(tag = "kind")]
pub enum DemoError {
    InvalidInput { message: String },
}

/// Namunaviy command (D1): summani nisbatlar bo'yicha bo'ladi.
/// Summa string sifatida keladi va Rustda parse qilinadi (frontend pul hisoblamaydi).
#[tauri::command]
#[specta::specta]
pub fn allocate_demo(total_minor: String, ratios: Vec<u32>) -> Result<Vec<MoneyDto>, DemoError> {
    let minor = total_minor
        .parse::<i64>()
        .map_err(|_| DemoError::InvalidInput {
            message: "summa butun son bo'lishi kerak".into(),
        })?;
    let ratios: Vec<u64> = ratios.into_iter().map(u64::from).collect();
    let parts = allocate(Money::new(minor, Currency::Uzs), &ratios).map_err(|e| {
        DemoError::InvalidInput {
            message: e.to_string(),
        }
    })?;
    Ok(parts
        .into_iter()
        .map(|m| MoneyDto::from_money(m, Locale::Uz))
        .collect())
}
