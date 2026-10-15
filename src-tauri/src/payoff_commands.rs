//! D10 IPC commandlari: payoff simulyatsiyasi, rejim va 70/20/10. Hisob — [`payoff`] xizmatida.

use std::sync::Arc;

use tauri::State;
use time::OffsetDateTime;

use crate::commands::{ApiError, run_blocking};
use crate::dto::{PayoffDto, PayoffInputDto, RecoveryDto, RecoveryInputDto};
use crate::payoff;
use crate::session::Session;

/// Amortizatsiya simulyatsiyasi: odatiy va tezlashtirilgan grafik.
#[tauri::command]
#[specta::specta]
pub async fn simulate_payoff(
    session: State<'_, Arc<Session>>,
    input: PayoffInputDto,
) -> Result<PayoffDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| payoff::simulate(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Byudjet rejimi va 70/20/10 taqsimoti.
#[tauri::command]
#[specta::specta]
pub async fn get_recovery(session: State<'_, Arc<Session>>) -> Result<RecoveryDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| payoff::recovery(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Rejim va ulushlarni saqlaydi.
#[tauri::command]
#[specta::specta]
pub async fn set_recovery(
    session: State<'_, Arc<Session>>,
    input: RecoveryInputDto,
) -> Result<RecoveryDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| payoff::set_recovery(db, OffsetDateTime::now_utc(), input))
    })
    .await
}
