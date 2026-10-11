//! Birinchi ishga tushirish ko'rsatmasi (D15): tugagan yoki o'tkazib yuborilgani bazada eslab qolinadi.

use storage::Connection;

use crate::{learning, Ctx, Env, ServiceError};

const KEY: &str = "onboarding.done";

/// # Errors
/// Baza xatosi.
pub fn is_done(conn: &Connection, ctx: &Ctx) -> Result<bool, ServiceError> {
    Ok(learning::setting(conn, ctx, KEY)?.is_some_and(|s| s.value == "1"))
}

/// # Errors
/// Baza xatosi.
pub fn complete(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<(), ServiceError> {
    learning::put_setting(conn, env, ctx, KEY, "1")
}
