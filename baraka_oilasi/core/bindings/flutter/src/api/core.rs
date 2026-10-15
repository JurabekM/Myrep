use std::path::Path;
use std::sync::Arc;

use baraka_agreements::{AgreementDraft, Completeness};
use baraka_app::*;
use zeroize::Zeroize;

/// Android avto-qulf vaqti (7.4): fonga o'tgandan 2 daqiqa.
const IDLE_LOCK_MINUTES: i64 = 2;

pub fn core_version() -> String {
    baraka_app::core_version().to_string()
}

/// Dart tomonida opaque obyekt. Platforma siri Kotlin `PlatformSecretApi` (Keystore) dan keladi.
pub struct BarakaCore {
    session: Session,
}

/// Kotlin'dan kelgan baytlar ishlatilgandan keyin xotirada qoldirilmaydi.
fn take_secret(mut bytes: Vec<u8>) -> Result<PlatformSecret, AppError> {
    let secret = PlatformSecret::from_slice(&bytes).map_err(AppError::from);
    bytes.zeroize();
    secret
}

impl BarakaCore {
    /// `data_dir` — ilovaning private storage papkasi (`Context.filesDir`).
    pub fn new(data_dir: String) -> BarakaCore {
        BarakaCore {
            session: Session::new(
                Path::new(&data_dir),
                KdfParams::ANDROID,
                chrono::Duration::minutes(IDLE_LOCK_MINUTES),
                Arc::new(SystemClock),
                Arc::new(UuidV7Gen),
            ),
        }
    }

    pub fn status(&self) -> Result<SessionStatus, AppError> {
        self.session.status()
    }

    pub fn setup(
        &self,
        platform_secret: Vec<u8>,
        pin: String,
        input: BootstrapInput,
    ) -> Result<SetupResult, AppError> {
        self.session
            .setup(&take_secret(platform_secret)?, &pin, input)
    }

    pub fn unlock(&self, platform_secret: Vec<u8>, pin: String) -> Result<HouseholdDto, AppError> {
        self.session.unlock(&take_secret(platform_secret)?, &pin)
    }

    pub fn unlock_with_recovery(
        &self,
        platform_secret: Vec<u8>,
        recovery_code: String,
        new_pin: String,
    ) -> Result<HouseholdDto, AppError> {
        self.session
            .unlock_with_recovery(&take_secret(platform_secret)?, &recovery_code, &new_pin)
    }

    pub fn lock(&self) -> Result<(), AppError> {
        self.session.lock()
    }

    /// Ilova fonga o'tganda va qaytganda chaqiriladi.
    pub fn lock_if_idle(&self) -> Result<bool, AppError> {
        self.session.lock_if_idle()
    }

    pub fn household(&self) -> Result<HouseholdDto, AppError> {
        self.session.app()?.household()
    }

    pub fn categories(&self, space_id: String) -> Result<Vec<CategoryDto>, AppError> {
        self.session.app()?.categories(&space_id)
    }

    pub fn record_income(
        &self,
        space_id: String,
        input: NewIncomeInput,
    ) -> Result<IncomeRecordedDto, AppError> {
        self.session.app()?.record_income(&space_id, input)
    }

    pub fn allocate_to_vault(
        &self,
        space_id: String,
        income_id: String,
        amount: String,
    ) -> Result<VaultTxDto, AppError> {
        self.session
            .app()?
            .allocate_to_vault(&space_id, &income_id, &amount)
    }

    pub fn record_initial_balance(
        &self,
        space_id: String,
        amount: String,
    ) -> Result<VaultTxDto, AppError> {
        self.session
            .app()?
            .record_initial_balance(&space_id, &amount)
    }

    pub fn deposit_to_vault(
        &self,
        space_id: String,
        amount: String,
        note: Option<String>,
    ) -> Result<VaultTxDto, AppError> {
        self.session
            .app()?
            .deposit_to_vault(&space_id, &amount, note.as_deref())
    }

    /// «Kelajagim»dan pul olish: PIN qayta tasdiqlanadi va sabab majburiy.
    pub fn withdraw_from_vault(
        &self,
        platform_secret: Vec<u8>,
        space_id: String,
        pin: String,
        amount: String,
        reason: String,
    ) -> Result<VaultTxDto, AppError> {
        self.session
            .confirm_pin(&take_secret(platform_secret)?, &pin)?;
        self.session
            .app()?
            .withdraw_from_vault(&space_id, &amount, &reason)
    }

    pub fn vault(&self, space_id: String) -> Result<VaultDto, AppError> {
        self.session.app()?.vault(&space_id)
    }

    pub fn set_allocation_rule(
        &self,
        space_id: String,
        input: AllocationRuleInput,
    ) -> Result<AllocationRuleDto, AppError> {
        self.session.app()?.set_allocation_rule(&space_id, input)
    }

    pub fn record_expense(
        &self,
        space_id: String,
        input: NewExpenseInput,
    ) -> Result<ExpenseDto, AppError> {
        self.session.app()?.record_expense(&space_id, input)
    }

    pub fn monthly_summary(
        &self,
        space_id: String,
        date: Option<String>,
        balance_delta: Option<String>,
    ) -> Result<MonthlySummaryDto, AppError> {
        self.session
            .app()?
            .monthly_summary(&space_id, date.as_deref(), balance_delta.as_deref())
    }

    pub fn simulate_loan(&self, input: LoanSimulationInput) -> Result<LoanSimulationDto, AppError> {
        self.session.app()?.simulate_loan(input)
    }

    pub fn check_agreement(
        &self,
        agreement_type: String,
        draft: AgreementDraft,
    ) -> Result<Completeness, AppError> {
        self.session.app()?.check_agreement(&agreement_type, draft)
    }

    /// O'zgarish hodisalari: Android vazifasida FRB `StreamSink<ChangeEvent>` bilan ulanadi.
    /// Hozircha bloklovchi o'qish — keyingi hodisani kutadi (`None` — sessiya yopildi).
    pub fn next_change(&self) -> Result<Option<ChangeEvent>, AppError> {
        let rx = self.session.app()?.subscribe();
        Ok(rx.recv().ok())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adapter_matches_desktop_flow() {
        let dir = tempfile::tempdir().unwrap();
        let core = BarakaCore::new(dir.path().display().to_string());
        assert!(!core.status().unwrap().initialized);
        let secret = PlatformSecret::generate().unwrap().as_bytes().to_vec();
        let setup = core
            .setup(
                secret.clone(),
                "135790".into(),
                BootstrapInput {
                    household_name: "Karim akaning oilasi".into(),
                    device_name: "Telefon".into(),
                    platform: "android".into(),
                    locale: "uz-Cyrl".into(),
                    base_currency: "UZS".into(),
                    month_start_day: 10,
                    spaces: vec!["UY".into()],
                    members: vec![NewMemberInput {
                        display_name: "Karim".into(),
                        role: "ADULT".into(),
                    }],
                },
            )
            .unwrap();
        let uy = setup.household.spaces[0].id.clone();
        let rec = core
            .record_income(
                uy.clone(),
                NewIncomeInput {
                    amount: "3 000 000".into(),
                    source: "Oylik".into(),
                    channel: "CARD".into(),
                    member_id: None,
                    occurred_on: None,
                    source_type: None,
                    note: None,
                },
            )
            .unwrap();
        assert_eq!(rec.suggested_share.formatted, "150\u{a0}000\u{a0}сўм");
        core.lock().unwrap();
        assert_eq!(core.household().unwrap_err().code, "LOCKED");
        assert!(core.unlock(secret, "135790".into()).is_ok());
        assert_eq!(
            take_secret(vec![1, 2, 3]).map(|_| ()).unwrap_err().code,
            "KEYFILE_CORRUPT"
        );
    }
}
