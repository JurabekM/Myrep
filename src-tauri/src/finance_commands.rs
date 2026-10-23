//! D4 IPC commandlari: daromad, «Kelajagim», audit, «Kimning puli?», majburiyat va nasiya.
//! Qoida: har command — argumentni o'qish → [`finance`] funksiyasi → DTO. Biznes mantiq bu yerda emas.

use std::sync::Arc;

use time::OffsetDateTime;

use crate::commands::{ApiError, now_unix, run_blocking};
use crate::dto::{
    AuditDto, CategoryDto, DebtDto, HomeDto, IncomeDto, IncomeInputDto, IncomeOutcomeDto,
    ObligationDto, ObligationInputDto, ShareRuleInputDto, VaultDto, WhoseMoneyDto,
    WithdrawInputDto,
};
use crate::finance;
use crate::session::Session;
use tauri::State;

/// Bosh ekran ko'rsatkichlari.
#[tauri::command]
#[specta::specta]
pub async fn get_home(session: State<'_, Arc<Session>>) -> Result<HomeDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| finance::home(db, OffsetDateTime::now_utc())))
        .await
}

/// Shu oydagi daromadlar.
#[tauri::command]
#[specta::specta]
pub async fn list_incomes_this_month(
    session: State<'_, Arc<Session>>,
) -> Result<Vec<IncomeDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| finance::incomes_this_month(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// So'nggi daromadlar (tez kiritish shablonlari).
#[tauri::command]
#[specta::specta]
pub async fn list_recent_incomes(
    session: State<'_, Arc<Session>>,
) -> Result<Vec<IncomeDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| finance::recent_incomes(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Daromad kiritadi va ulush taklifini qaytaradi.
#[tauri::command]
#[specta::specta]
pub async fn create_income(
    session: State<'_, Arc<Session>>,
    input: IncomeInputDto,
) -> Result<IncomeOutcomeDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| finance::create_income(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Ulush taklifini qabul qiladi: summa «Kelajagim»ga yoziladi.
#[tauri::command]
#[specta::specta]
pub async fn accept_share(
    session: State<'_, Arc<Session>>,
    income_id: String,
    amount: String,
) -> Result<VaultDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            finance::accept_share(db, OffsetDateTime::now_utc(), &income_id, &amount)
        })
    })
    .await
}

/// «Kelajagim» ekrani.
#[tauri::command]
#[specta::specta]
pub async fn get_vault(session: State<'_, Arc<Session>>) -> Result<VaultDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| finance::open_vault(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Progressiv taklifga javob: qabul (+1 %) yoki rad.
#[tauri::command]
#[specta::specta]
pub async fn respond_progression(
    session: State<'_, Arc<Session>>,
    accept: bool,
) -> Result<VaultDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session
            .with_database(|db| finance::respond_progression(db, OffsetDateTime::now_utc(), accept))
    })
    .await
}

/// Ulush qoidasini o'zgartiradi.
#[tauri::command]
#[specta::specta]
pub async fn set_share_rule(
    session: State<'_, Arc<Session>>,
    input: ShareRuleInputDto,
) -> Result<VaultDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| finance::set_share_rule(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Boshlang'ich balans (avval yig'ilgan pul) — bir marta.
#[tauri::command]
#[specta::specta]
pub async fn set_initial_balance(
    session: State<'_, Arc<Session>>,
    amount: String,
) -> Result<VaultDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            finance::set_initial_balance(db, OffsetDateTime::now_utc(), &amount)
        })
    })
    .await
}

/// Pul olish. PIN qayta tekshiriladi (noto'g'ri urinish hisoblanadi), so'ng yozuv yoziladi.
#[tauri::command]
#[specta::specta]
pub async fn withdraw(
    session: State<'_, Arc<Session>>,
    pin: String,
    input: WithdrawInputDto,
) -> Result<VaultDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.verify_pin(&pin, now_unix())?;
        session.with_database(|db| {
            finance::withdraw(db, OffsetDateTime::now_utc(), &input.amount, &input.reason)
        })
    })
    .await
}

/// O'tgan oy auditi.
#[tauri::command]
#[specta::specta]
pub async fn get_audit(session: State<'_, Arc<Session>>) -> Result<AuditDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| finance::audit(db, OffsetDateTime::now_utc())))
        .await
}

/// Audit davriga kategoriya bilan xarajat qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_audit_expense(
    session: State<'_, Arc<Session>>,
    amount: String,
    category_id: String,
    note: Option<String>,
) -> Result<AuditDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            finance::add_audit_expense(db, OffsetDateTime::now_utc(), &amount, &category_id, note)
        })
    })
    .await
}

/// Izohsiz qolgan summani «mayda kundalik» deb belgilaydi.
#[tauri::command]
#[specta::specta]
pub async fn mark_unexplained_as_daily(
    session: State<'_, Arc<Session>>,
) -> Result<AuditDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session
            .with_database(|db| finance::mark_unexplained_as_daily(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Auditni yakunlaydi: davr uchun o'zgarmas hisobot yoziladi.
#[tauri::command]
#[specta::specta]
pub async fn finish_audit(session: State<'_, Arc<Session>>) -> Result<AuditDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| finance::finish_audit(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// «Kimning puli?»: `months_back` oy oldingi davr (0 — joriy oy).
#[tauri::command]
#[specta::specta]
pub async fn get_whose_money(
    session: State<'_, Arc<Session>>,
    months_back: u8,
) -> Result<WhoseMoneyDto, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            finance::whose_money_for(db, OffsetDateTime::now_utc(), months_back)
        })
    })
    .await
}

/// Kategoriyalar.
#[tauri::command]
#[specta::specta]
pub async fn list_categories(
    session: State<'_, Arc<Session>>,
) -> Result<Vec<CategoryDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| finance::categories(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Majburiyatlar.
#[tauri::command]
#[specta::specta]
pub async fn list_obligations(
    session: State<'_, Arc<Session>>,
) -> Result<Vec<ObligationDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| finance::obligations(db, OffsetDateTime::now_utc()))
    })
    .await
}

/// Majburiyat qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_obligation(
    session: State<'_, Arc<Session>>,
    input: ObligationInputDto,
) -> Result<Vec<ObligationDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| finance::add_obligation(db, OffsetDateTime::now_utc(), input))
    })
    .await
}

/// Majburiyatni yoqadi yoki o'chiradi.
#[tauri::command]
#[specta::specta]
pub async fn set_obligation_active(
    session: State<'_, Arc<Session>>,
    id: String,
    active: bool,
) -> Result<Vec<ObligationDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            finance::set_obligation_active(db, OffsetDateTime::now_utc(), &id, active)
        })
    })
    .await
}

/// Nasiyalar.
#[tauri::command]
#[specta::specta]
pub async fn list_debts(session: State<'_, Arc<Session>>) -> Result<Vec<DebtDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || session.with_database(|db| finance::debts(db, OffsetDateTime::now_utc())))
        .await
}

/// Nasiya qo'shadi.
#[tauri::command]
#[specta::specta]
pub async fn add_debt(
    session: State<'_, Arc<Session>>,
    creditor: String,
    amount: String,
    note: Option<String>,
) -> Result<Vec<DebtDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session.with_database(|db| {
            finance::add_debt(db, OffsetDateTime::now_utc(), &creditor, &amount, note)
        })
    })
    .await
}

/// Nasiyaga qisman to'lov.
#[tauri::command]
#[specta::specta]
pub async fn pay_debt(
    session: State<'_, Arc<Session>>,
    debt_id: String,
    amount: String,
) -> Result<Vec<DebtDto>, ApiError> {
    let session = session.inner().clone();
    run_blocking(move || {
        session
            .with_database(|db| finance::pay_debt(db, OffsetDateTime::now_utc(), &debt_id, &amount))
    })
    .await
}
