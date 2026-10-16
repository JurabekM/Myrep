//! Baraka Daftari — Tauri ilovasining yadro qatlami.
//!
//! Oyna va commandlar shu yerda yig'iladi. Biznes mantiq bu yerda emas:
//! commandlar yupqa bo'ladi (DESKTOP_PROMPT.md 3.2).

mod agreement_commands;
mod agreements;
mod budget;
mod budget_commands;
mod center;
mod center_commands;
mod ceremonies;
mod ceremony_commands;
mod commands;
mod content;
mod content_commands;
mod csv_commands;
mod csv_import;
mod desktop;
mod dto;
mod family;
mod family_commands;
mod finance;
mod finance_commands;
mod loan_commands;
mod loans;
mod notify;
mod partnership_commands;
mod partnerships;
mod payoff;
mod payoff_commands;
mod report;
mod reserve;
mod reserve_commands;
mod session;
mod sync;
mod sync_commands;
mod venture_commands;
mod ventures;

use std::sync::Arc;

use security::{KdfParams, KeyringSecretStore};
use session::{AUTO_LOCK_TICK, Paths, Session};
use tauri::{App, Manager, WindowEvent};
use tauri_specta::{Builder, collect_commands};

/// TypeScript bindinglari yoziladigan fayl (frontend tomonida, git'da saqlanadi).
#[cfg(any(debug_assertions, test))]
const BINDINGS_PATH: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../ui/src/bindings/bindings.ts"
);

/// Bindings fayli boshiga qo'yiladigan izoh.
#[cfg(any(debug_assertions, test))]
const BINDINGS_HEADER: &str =
    "// Bu fayl avtomatik yaratiladi (tauri-specta). Qo'lda tahrirlamang.";

/// Asosiy oyna nomi (tauri.conf.json → app.windows[0].label).
const MAIN_WINDOW: &str = "main";

/// Barcha commandlar bitta ro'yxatda: ham ilova, ham TypeScript bindinglari shu ro'yxatdan olinadi.
fn specta_builder() -> Builder<tauri::Wry> {
    Builder::<tauri::Wry>::new().commands(collect_commands![
        commands::get_app_info,
        commands::get_security_status,
        commands::setup_pin,
        commands::unlock,
        commands::lock,
        finance_commands::get_home,
        finance_commands::list_incomes_this_month,
        finance_commands::list_recent_incomes,
        finance_commands::create_income,
        finance_commands::accept_share,
        finance_commands::get_vault,
        finance_commands::respond_progression,
        finance_commands::set_share_rule,
        finance_commands::set_initial_balance,
        finance_commands::withdraw,
        finance_commands::get_audit,
        finance_commands::add_audit_expense,
        finance_commands::mark_unexplained_as_daily,
        finance_commands::finish_audit,
        finance_commands::get_whose_money,
        finance_commands::list_categories,
        finance_commands::list_obligations,
        finance_commands::add_obligation,
        finance_commands::set_obligation_active,
        finance_commands::list_debts,
        finance_commands::add_debt,
        finance_commands::pay_debt,
        content_commands::list_chapters,
        content_commands::get_chapter,
        content_commands::get_weekly_tasks,
        content_commands::set_task_done,
        content_commands::save_daftar_page,
        family_commands::get_month_summary,
        family_commands::list_month_expenses,
        family_commands::add_expense,
        family_commands::set_category_necessity,
        family_commands::get_havas_limit,
        family_commands::set_havas_limit,
        family_commands::consent_havas_limit,
        family_commands::list_members,
        family_commands::add_member,
        family_commands::set_member_pin,
        family_commands::list_treats,
        family_commands::add_treat,
        family_commands::add_expenses,
        family_commands::list_habits,
        family_commands::add_habit,
        family_commands::create_council_report,
        budget_commands::get_budget,
        budget_commands::add_subscription,
        budget_commands::mark_subscription_used,
        budget_commands::cancel_subscription,
        budget_commands::add_envelope,
        budget_commands::close_envelope_week,
        budget_commands::transfer_to_vault_from_rescue,
        budget_commands::set_baseline_period,
        csv_commands::preview_csv_import,
        csv_commands::import_csv_expenses,
        desktop::show_main_window,
        desktop::hide_quick_window,
        reserve_commands::get_reserve,
        reserve_commands::get_prices,
        reserve_commands::add_price_item,
        reserve_commands::update_price,
        reserve_commands::remove_price_item,
        agreement_commands::list_agreements,
        agreement_commands::create_agreement,
        agreement_commands::get_agreement,
        agreement_commands::save_agreement_answers,
        agreement_commands::add_signature,
        agreement_commands::sign_agreement,
        agreement_commands::append_journal_entry,
        agreement_commands::get_journal,
        agreement_commands::create_agreement_pdf,
        loan_commands::get_loans,
        loan_commands::check_borrow,
        loan_commands::add_loan,
        loan_commands::pay_loan,
        loan_commands::create_iou,
        loan_commands::set_payoff_strategy,
        loan_commands::add_sellable_item,
        loan_commands::mark_sellable_sold,
        loan_commands::remove_sellable_item,
        venture_commands::attach_receipt,
        payoff_commands::simulate_payoff,
        payoff_commands::get_recovery,
        payoff_commands::set_recovery,
        ceremony_commands::get_ceremonies,
        ceremony_commands::create_ceremony,
        ceremony_commands::add_ceremony_scenario,
        ceremony_commands::add_ceremony_line,
        ceremony_commands::remove_ceremony_line,
        ceremony_commands::discuss_ceremony,
        ceremony_commands::confirm_ceremony,
        ceremony_commands::set_ceremony_goal,
        ceremony_commands::create_ceremony_pdf,
        partnership_commands::get_partnerships,
        partnership_commands::create_partnership,
        partnership_commands::set_buyout,
        partnership_commands::pay_buyout,
        partnership_commands::consent_partnership,
        venture_commands::get_venture,
        venture_commands::add_venture_entry,
        venture_commands::close_venture_period,
        venture_commands::create_period_report_pdf,
        venture_commands::check_offer,
        venture_commands::hustle_plan,
        center_commands::get_agreements_center,
        center_commands::get_agreement_ops,
        center_commands::report_duty_incident,
        center_commands::resolve_duty_incident,
        center_commands::open_review,
        center_commands::mark_review,
        center_commands::create_review_pdf,
        center_commands::open_dispute,
        center_commands::decide_dispute,
        center_commands::create_arbiter_pdf,
        center_commands::confirm_unchanged,
        center_commands::list_family_templates,
        center_commands::create_family_agreement,
        center_commands::confirm_family,
        sync_commands::export_baraka,
        sync_commands::preview_baraka_import,
        sync_commands::apply_baraka_import,
    ])
}

/// Ilovani ishga tushiradi. Ishga tushmasa, xatoni logga yozib, jarayon 1 kod bilan tugaydi.
pub fn run() {
    init_tracing();

    let builder = specta_builder();

    #[cfg(debug_assertions)]
    export_bindings(&builder);

    let result = tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .invoke_handler(builder.invoke_handler())
        .setup(|app| setup_security(app))
        .run(tauri::generate_context!());

    if let Err(err) = result {
        tracing::error!(error = %err, "ilovani ishga tushirib bo'lmadi");
        std::process::exit(1);
    }
}

/// Ma'lumotlar papkasi: odatda `app_data_dir` (`%APPDATA%\\uz.barakadaftari.desktop`). `BARAKA_DATA_DIR` muhit
/// o'zgaruvchisi berilsa — o'sha papka (faqat ishlab chiqish va sinov: toza profil bilan ishga tushirish uchun;
/// relizda foydalanuvchi uni o'rnatmaydi).
pub(crate) fn data_dir(app: &tauri::AppHandle) -> tauri::Result<std::path::PathBuf> {
    if let Some(dir) = std::env::var_os("BARAKA_DATA_DIR").filter(|d| !d.is_empty()) {
        return Ok(std::path::PathBuf::from(dir));
    }
    app.path().app_data_dir()
}

/// Seansni yaratadi, oynani himoyalaydi va avto-qulflashni ulaydi.
///
/// - Relizda oyna ekran suratiga va ekran yozuvga tushmaydi (`set_content_protected`).
///   Ishlab chiqishda bu o'chiq: skrinshot bilan tekshirish uchun.
/// - Oyna fokusdan tushsa, `AutoLockPolicy` taymeri boshlanadi; vaqt o'tsa baza qulflanadi.
fn setup_security(app: &mut App) -> Result<(), Box<dyn std::error::Error>> {
    let data_dir = data_dir(app.handle())?;
    std::fs::create_dir_all(&data_dir)?;

    let session = Arc::new(Session::new(
        Paths::in_dir(&data_dir),
        Arc::new(KeyringSecretStore::new()),
        KdfParams::RECOMMENDED,
    ));
    app.manage(Arc::clone(&session));

    let window = app
        .get_webview_window(MAIN_WINDOW)
        .ok_or("asosiy oyna topilmadi")?;

    if !cfg!(debug_assertions) {
        window.set_content_protected(true)?;
    }

    // Tray va Ctrl+Alt+B: ishlamasa ilova baribir ishga tushadi (faqat ogohlantirish).
    if let Err(err) = desktop::setup_tray(app.handle()) {
        tracing::warn!(error = %err, "tray ikonkasi yaratilmadi");
    }
    if let Err(err) = desktop::setup_shortcut(app.handle()) {
        tracing::warn!(error = %err, "global tugma ro'yxatdan o'tmadi");
    }

    let focus_session = Arc::clone(&session);
    window.on_window_event(move |event| {
        if let WindowEvent::Focused(focused) = event {
            focus_session.focus_changed(*focused);
        }
    });

    let tick_session = Arc::clone(&session);
    std::thread::Builder::new()
        .name("avto-qulflash".to_owned())
        .spawn(move || {
            loop {
                std::thread::sleep(AUTO_LOCK_TICK);
                tick_session.enforce_auto_lock();
            }
        })?;

    let notify_session = Arc::clone(&session);
    let notify_app = app.handle().clone();
    std::thread::Builder::new()
        .name("juma-eslatma".to_owned())
        .spawn(move || {
            let mut last_day = None;
            loop {
                notify::notify_due_treats(&notify_session, &notify_app, &mut last_day);
                std::thread::sleep(notify::CHECK_INTERVAL);
            }
        })?;

    Ok(())
}

/// Log darajasi: ishlab chiqishda batafsil, relizda faqat ogohlantirish va xatolar.
/// Logga summa, ism, izoh, PIN yoki kalit yozilmaydi (SPEC 6-bo'lim).
fn init_tracing() {
    let default_level = if cfg!(debug_assertions) {
        "info"
    } else {
        "warn"
    };
    let filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(default_level));

    // Qayta chaqirilsa (masalan, testlarda) xato bo'lmasligi uchun natija e'tiborsiz qoldiriladi.
    let _ = tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .try_init();
}

/// Ishlab chiqish rejimida bindinglarni yangilab turadi. Xato dasturni to'xtatmaydi.
#[cfg(debug_assertions)]
fn export_bindings(builder: &Builder<tauri::Wry>) {
    let language = specta_typescript::Typescript::new().header(BINDINGS_HEADER);
    if let Err(err) = builder.export(language, BINDINGS_PATH) {
        tracing::warn!(error = %err, "TypeScript bindinglarini yozib bo'lmadi");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// CI shu testni yurgizadi: bindinglar commandlar bilan sinxron bo'lishi shart.
    /// Agar fayl o'zgarsa, `git diff --exit-code ui/src/bindings` xato beradi.
    #[test]
    fn typescript_bindinglari_yaratiladi() {
        let language = specta_typescript::Typescript::new().header(BINDINGS_HEADER);
        specta_builder()
            .export(language, BINDINGS_PATH)
            .expect("TypeScript bindinglari yozilishi kerak");
    }
}
